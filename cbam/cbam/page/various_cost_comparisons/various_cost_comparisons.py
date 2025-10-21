import frappe
import json
from datetime import datetime
from frappe.utils.user import get_system_managers


@frappe.whitelist()
def get_report_data(filters=None, selected_filters=None, start=0, page_length=50):
    if filters and isinstance(filters, str):
        filters = json.loads(filters)
    filters = filters or {}
    if selected_filters and isinstance(selected_filters, str):
        selected_filters = json.loads(selected_filters)
    selected_filters = selected_filters or {}
    try:
        start = int(start)
    except Exception:
        start = 0
    try:
        page_length = int(page_length)
    except Exception:
        page_length = 50

    columns = get_columns()

    data, total_count = get_data(filters, selected_filters, start, page_length)
    chart_data = get_chart_data(data)
    return {"columns": columns, "data": data, "chart_data": chart_data, "total_count": total_count}


def get_columns():
    return [
        {"fieldname": "reporting_period", "fieldtype": "Data", "label": "Reporting Period", "width": 180},
        {"fieldname": "cn_code", "fieldtype": "Data", "label": "CN Code", "width": 150},
        {"fieldname": "article_number", "fieldtype": "Data", "label": "Article Number", "width": 200},
        {"fieldname": "data_source", "fieldtype": "Data", "label": "Data Source", "width": 180},
        {"fieldname": "supplier", "fieldtype": "Data", "label": "Supplier", "width": 200},
        {"fieldname": "raw_mass_tonne", "fieldtype": "Data", "label": "Mass [t]", "width": 150},
        {"fieldname": "installation_country", "fieldtype": "Data", "label": "Installation Country", "width": 180},
        {"fieldname": "cbam_benchmark", "fieldtype": "Data", "label": "CBAM Benchmark [tCO2/t product]", "width": 200},
        {"fieldname": "standard_emission_factor", "fieldtype": "Data", "label": "Standard Emission Factor [tCO2/t product]", "width": 220},
        {"fieldname": "standard_emission_cost", "fieldtype": "Data", "label": "Standard Cost [€]", "width": 180},
        {"fieldname": "real_emission_value", "fieldtype": "Data", "label": "Specific (Direct) Emission Value [tCO2/t product]", "width": 280},
        {"fieldname": "real_emission_cost", "fieldtype": "Data", "label": "Cost Based on Specific Emissions [€]", "width": 280},
        {"fieldname": "calculation_data_status", "fieldtype": "Data", "label": "Calculation Data", "width": 140},
    ]

def get_data(filters=None, selected_filters=None, start=0, page_length=50):
    filters = filters or {}
    selected_filters = selected_filters or {}
    try:
        start = int(start)
    except Exception:
        start = 0
    try:
        page_length = int(page_length)
    except Exception:
        page_length = 50
 
    # Merge selected_filters into filters, but only non-empty values
    for key, value in selected_filters.items():
        if value is not None and value != '' and value != []:
            if isinstance(value, list):
                if len(value) > 0:
                    filters[key] = value
            else:
                filters[key] = value

    where_clauses = []
    where_clauses_eg = []

    user = frappe.session.user
    declarants = get_declarant_for_user(user)

    #set where conditions
    where_sql, where_sql_eg = set_conditions(declarants, filters, where_clauses, where_clauses_eg)
    
    # Initialize values with default values
    cbam_factor = 0.0
    ets_carbon_price = 0.0
    
    # Fetch cbam_factor and ets_price from backend based on year
    year = selected_filters.get('year', None)
    ets_price_type = selected_filters.get('ets_price_type', None)
    
    # Validate year and ets_price_type
    if not year or year == '' or not ets_price_type or ets_price_type == '':
        year = None
        ets_price_type = None
    
    if year and ets_price_type:
        # Get the values from the same tables used in get_cards_value
        sql_params = {
            'year': year,
            'ets_price_type': ets_price_type
        }
        
        # Get CBAM factor and ETS price (these are year-specific, not cn_code/country specific)
        sql = """
            SELECT 
                cf.cbam_factor,
                ecp.price AS ets_price
            FROM `tabCBAM Factor` cf
            LEFT JOIN (
                -- Get the latest price_date within the selected year for the specific ETS price type
                SELECT 
                    price_year,
                    ets_price_type,
                    price,
                    price_date
                FROM `tabETS Carbon Price` ecp_inner
                WHERE ecp_inner.price_year = %(year)s
                AND ecp_inner.ets_price_type = %(ets_price_type)s
                ORDER BY
                    CASE
                        WHEN %(ets_price_type)s = 'Spot Price' THEN ecp_inner.price_date
                        ELSE ecp_inner.modified
                    END DESC
                LIMIT 1
            ) ecp ON ecp.price_year = %(year)s AND ecp.ets_price_type = %(ets_price_type)s
            WHERE cf.year = %(year)s
            LIMIT 1
        """
        
        result = frappe.db.sql(sql, sql_params, as_dict=True)
        if result:
            cbam_factor = float(result[0].get('cbam_factor', 0.0) or 0.0)
            ets_carbon_price = float(result[0].get('ets_price', 0.0) or 0.0)
    
    # Count total rows for pagination
    total_count = get_count(where_sql, where_sql_eg)

    # Helper function to build cost calculation expressions
    def build_cost_calculations(table_alias):
        # Use appropriate table aliases based on the table
        cnb_alias = f"cnb_{table_alias}"
        sev_alias = f"sev_{table_alias}"
        
        return f"""
            IFNULL({cnb_alias}.bench_mark, 0.0) AS cbam_benchmark,
            IFNULL({sev_alias}.emission_value, 0.0) AS standard_emission_factor,
            ((
                IFNULL({sev_alias}.emission_value, 0.0)
                - (IFNULL({cnb_alias}.bench_mark, 0.0) * {cbam_factor})
                - ((IFNULL({sev_alias}.emission_value, 0.0) * IFNULL({table_alias}.carbon_price_due, 0.0)) / {ets_carbon_price})
            ) * IFNULL({table_alias}.raw_mass_tonne, 0.0) * {ets_carbon_price}) AS standard_emission_cost,
            IFNULL({table_alias}.specific_direct_embedded_emissions,0.0) AS real_emission_value,
            ((
                IFNULL({table_alias}.specific_direct_embedded_emissions,0.0) - ({cbam_factor} * IFNULL({cnb_alias}.bench_mark, 0.0))
                - ((IFNULL({table_alias}.specific_direct_embedded_emissions,0.0) * IFNULL({table_alias}.carbon_price_due, 0.0)) / {ets_carbon_price})
            ) * IFNULL({table_alias}.raw_mass_tonne, 0.0) * {ets_carbon_price}) AS real_emission_cost
        """

    # Main data query with LIMIT/OFFSET for pagination
    if year:
        # Query with year-based JOINs to fetch correct emission values
        data_query = f"""
            SELECT * FROM (
                SELECT 
                    eg.cn_code,
                    eg.article_no AS article_number,
                    eg.supplier,
                    IFNULL(eg.raw_mass_tonne,0.0) AS raw_mass_tonne,
                    eg.installation_country,
                    {build_cost_calculations('eg')},
                    eg.name,
                    'CBAM Report Data' as data_source,
                    eg.reporting_period as reporting_period
                FROM `tabExternal Good` eg
                LEFT JOIN `tabCBAM Benchmark` cnb_eg 
                    ON cnb_eg.year = {year} AND cnb_eg.cn_code = eg.cn_code
                LEFT JOIN `tabStandard Emission Value` sev_eg 
                    ON sev_eg.year = {year} AND sev_eg.cn_code = eg.cn_code AND sev_eg.country = eg.installation_country
                {where_sql_eg}
                UNION
                SELECT 
                    g.cn_code,
                    g.article_number,
                    g.supplier_name AS supplier,
                    IFNULL(g.raw_mass_tonne,0.0) AS raw_mass_tonne,
                    g.installation_country,    
                    {build_cost_calculations('g')},
                    g.name,
                    'Supplier Data' as data_source,
                    g.internal_customs_import_number as reporting_period
                FROM `tabGood` g
                LEFT JOIN `tabCBAM Benchmark` cnb_g 
                    ON cnb_g.year = {year} AND cnb_g.cn_code = g.cn_code
                LEFT JOIN `tabStandard Emission Value` sev_g 
                    ON sev_g.year = {year} AND sev_g.cn_code = g.cn_code AND sev_g.country = g.installation_country
                {where_sql}
            ) AS main_table
            LIMIT {page_length} OFFSET {start}
        """
    else:
        # Query without year-based JOINs (fallback to basic data)
        data_query = f"""
            SELECT * FROM (
                SELECT 
                    eg.cn_code,
                    eg.article_no AS article_number,
                    eg.supplier,
                    IFNULL(eg.raw_mass_tonne,0.0) AS raw_mass_tonne,
                    eg.installation_country,
                    0.0 AS cbam_benchmark,
                    0.0 AS standard_emission_factor,
                    0.0 AS standard_emission_cost,
                    IFNULL(eg.specific_direct_embedded_emissions,0.0) AS real_emission_value,
                    0.0 AS real_emission_cost,
                    eg.name,
                    'CBAM Report Data' as data_source,
                    eg.reporting_period as reporting_period
                FROM `tabExternal Good` eg
                {where_sql_eg}
                UNION
                SELECT 
                    g.cn_code,
                    g.article_number,
                    g.supplier_name AS supplier,
                    IFNULL(g.raw_mass_tonne,0.0) AS raw_mass_tonne,
                    g.installation_country,
                    0.0 AS cbam_benchmark,
                    0.0 AS standard_emission_factor,
                    0.0 AS standard_emission_cost,
                    IFNULL(g.specific_direct_embedded_emissions,0.0) AS real_emission_value,
                    0.0 AS real_emission_cost,
                    g.name,
                    'Supplier Data' as data_source,
                    g.internal_customs_import_number as reporting_period
                FROM `tabGood` g
                {where_sql}
            ) AS main_table
            LIMIT {page_length} OFFSET {start}
        """
    data = frappe.db.sql(data_query, as_dict=1)

    required_fields = [
        ("cbam_benchmark", "CBAM Benchmark"),
        ("standard_emission_factor", "Standard Emission Value"),
        ("real_emission_value", "Specific Direct Emission Value"),
    ]
    for row in data:
        missing = []
        for key, label in required_fields:
            val = row.get(key)
            if is_missing(val):
                missing.append(label)
        row['calculation_data_status'] = "<span style='color:#d97a12;font-weight:600'>Missing</span>" if missing else "<span style='color:#1f77b4;font-weight:600'>Available</span>"
        row['missing_data_reason'] = ", ".join(missing) if missing else ""
    
    return data, total_count

def set_conditions(declarants, filters, where_clauses, where_clauses_eg):
    if declarants:
        declarant_list = ', '.join(f"'{d}'" for d in declarants)
        where_clauses.append(f"g.declarant IN ({declarant_list})")
        where_clauses_eg.append(f"eg.declarant IN ({declarant_list})")

    if filters.get("cn_code") and isinstance(filters["cn_code"], list) and len(filters["cn_code"]) > 0:
        cn_code_list = ', '.join(f"'{c}'" for c in filters["cn_code"])
        where_clauses.append(f"(g.cn_code IN ({cn_code_list}))")
        where_clauses_eg.append(f"(eg.cn_code IN ({cn_code_list}))")

    if filters.get("supplier") and isinstance(filters["supplier"], list) and len(filters["supplier"]) > 0:
        supplier_list = ', '.join(f"'{s}'" for s in filters["supplier"])
        where_clauses.append(f"(g.supplier_name IN ({supplier_list}))")
        where_clauses_eg.append(f"(eg.supplier IN ({supplier_list}))")

    if filters.get("article_number") and isinstance(filters["article_number"], list) and len(filters["article_number"]) > 0:
        article_number_list = ', '.join(f"'{s}'" for s in filters["article_number"])
        where_clauses.append(f"(g.article_number IN ({article_number_list}))")
        where_clauses_eg.append(f"(eg.article_no IN ({article_number_list}))")
    
    if filters.get("reporting_period") and isinstance(filters["reporting_period"], list) and len(filters["reporting_period"]) > 0:
        reporting_period_list = ', '.join(f"'{s}'" for s in filters["reporting_period"])
        where_clauses.append(f"(g.internal_customs_import_number IN ({reporting_period_list}))")
        where_clauses_eg.append(f"(eg.reporting_period IN ({reporting_period_list}))")

    # Only fetch Good records with status = 'Data Submitted' OR 'Data Assigned'
    where_clauses.append("g.status IN ('Data Submitted', 'Data Assigned')")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    where_sql_eg = "WHERE " + " AND ".join(where_clauses_eg) if where_clauses_eg else ""

    return where_sql, where_sql_eg

def get_count(where_sql, where_sql_eg):
    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT 
                eg.name, eg.cn_code, eg.article_no as article_number, eg.supplier, eg.raw_mass_tonne, eg.installation_country,
                eg.specific_direct_embedded_emissions, eg.carbon_price_due
            FROM `tabExternal Good` eg
            {where_sql_eg}
            UNION
            SELECT 
                g.name, g.cn_code, g.article_number, g.supplier_name as supplier, g.raw_mass_tonne, g.installation_country,
                g.specific_direct_embedded_emissions, g.carbon_price_due
            FROM `tabGood` g
            {where_sql}
        ) AS count_table

    """
    result = frappe.db.sql(count_query)
    return result[0][0] if result else 0

def get_chart_data(data):
    """Process data to create chart data grouped by article and supplier for bar chart"""
    if not data:
        return {'labels': [], 'articles': [], 'suppliers': [], 'actual_costs': [], 'standard_costs': []}
    
    # If data contains article_number and supplier, use those for x-axis
    articles, suppliers, actual_costs, standard_costs, labels = [], [], [], [], []

    for row in data:
        article = row.get('article_number', '')
        supplier = row.get('supplier', '')
        articles.append(article)
        suppliers.append(supplier)
        labels.append(f"{article} ({supplier})")
        # Ensure costs are numbers, not objects
        actual_cost = float(row.get('real_emission_cost', 0.0) or 0.0)
        standard_cost = float(row.get('standard_emission_cost', 0.0) or 0.0)
        actual_costs.append(actual_cost)
        standard_costs.append(standard_cost)

    chart_data = { 
        'labels': labels,
        'articles': articles,
        'suppliers': suppliers,
        'actual_costs': actual_costs,
        'standard_costs': standard_costs
    }
    return chart_data


def get_declarant_for_user(user):
    result = frappe.db.get_all(
        "Declarant User",
        filters={"user": user},
        fields=["parent"],
        distinct=True
    )
    return [row.parent for row in result]  # List of declarant names

@frappe.whitelist()
def get_cards_value(filters=None):
    import json

    filters = json.loads(filters) if filters else {}
    
    # Provide default values for missing keys
    year = filters.get('year', datetime.now().year) # Fixed datetime access
    ets_price_type = filters.get('ets_price_type', 'Spot Price')  # Default to Spot Price if not provided
    
    # Create a safe parameters dict for SQL
    sql_params = {
        'year': year,
        'ets_price_type': ets_price_type
    }

    sql = """
        SELECT 
            cf.cbam_factor,
            cnb.bench_mark,
            sev.emission_value,
            ecp.price AS ets_price
        FROM `tabCBAM Factor` cf
        LEFT JOIN `tabCBAM Benchmark` cnb 
            ON cnb.year = %(year)s
        LEFT JOIN `tabStandard Emission Value` sev 
            ON sev.year = %(year)s
        LEFT JOIN (
            -- Get the latest price_date within the selected year for the specific ETS price type
            SELECT 
                price_year,
                ets_price_type,
                price,
                price_date
            FROM `tabETS Carbon Price` ecp_inner
            WHERE ecp_inner.price_year = %(year)s 
            AND ecp_inner.ets_price_type = %(ets_price_type)s
            ORDER BY 
                CASE 
                    WHEN %(ets_price_type)s = 'Spot Price' THEN ecp_inner.price_date
                    ELSE ecp_inner.modified
                END DESC
            LIMIT 1
        ) ecp ON ecp.price_year = %(year)s AND ecp.ets_price_type = %(ets_price_type)s
        WHERE cf.year = %(year)s
        LIMIT 1
    """

    result = list(frappe.db.sql(sql, sql_params, as_dict=True))
    return result[0] if result else {}


def _build_filter_options(filter_type, txt, declarants, cn_code_list, supplier_list, table_name, field_mappings):
    """Helper function to build filter options for both Good and External Good tables"""
    filters = []
    if declarants:
        filters.append(["declarant", "in", declarants])
    if cn_code_list:
        filters.append(["cn_code", "in", cn_code_list])
    
    supplier_field = field_mappings["supplier"]
    if supplier_list and filter_type != "supplier":
        filters.append([supplier_field, "in", supplier_list])
    
    if txt:
        if filter_type == "supplier":
            filters.append([supplier_field, "like", f"%{txt}%"])
        elif filter_type == "article_number":
            filters.append([field_mappings["article_number"], "like", f"%{txt}%"])
        elif filter_type == "reporting_period":
            filters.append([field_mappings["reporting_period"], "like", f"%{txt}%"])
    
    field = field_mappings.get(filter_type)
    if not field:
        return []
    
    results = frappe.db.get_list(table_name, fields=[field], filters=filters, distinct=True, limit=20)
    return [row.get(field) for row in results if row.get(field)]


def fetch_external_good_options(filter_type, txt, declarants, cn_code_list, supplier_list):
    field_mappings = {
        "supplier": "supplier",
        "article_number": "article_no",
        "reporting_period": "reporting_period"
    }
    return _build_filter_options(filter_type, txt, declarants, cn_code_list, supplier_list, "External Good", field_mappings)


def fetch_good_options(filter_type, txt, declarants, cn_code_list, supplier_list):
    field_mappings = {
        "supplier": "supplier_name",
        "article_number": "article_number",
        "reporting_period": "internal_customs_import_number"
    }
    return _build_filter_options(filter_type, txt, declarants, cn_code_list, supplier_list, "Good", field_mappings)


def merge_and_format_options(*option_lists):
    seen = set()
    options = []
    for option_list in option_lists:
        for val in option_list:
            if val and val not in seen:
                options.append({"value": val, "description": val})
                seen.add(val)
    return options

@frappe.whitelist()
def get_filter_options(txt=None, filter_type=None, cn_code=None, supplier=None):
    user = frappe.session.user
    declarants = get_declarant_for_user(user)
    cn_code_list = [c.strip() for c in cn_code.split(",") if c.strip()] if cn_code else []
    supplier_list = [s.strip() for s in supplier.split(",") if s.strip()] if supplier else []

    eg_options = fetch_external_good_options(filter_type, txt, declarants, cn_code_list, supplier_list)
    g_options = fetch_good_options(filter_type, txt, declarants, cn_code_list, supplier_list)
    return merge_and_format_options(eg_options, g_options)


@frappe.whitelist()
def get_available_years():
    """Get years from ETS Carbon Price table that have prices"""
    # Get distinct years from ETS Carbon Price table that have prices
    sql = """
        SELECT DISTINCT price_year 
        FROM `tabETS Carbon Price` 
        WHERE price_year IS NOT NULL 
        AND price IS NOT NULL 
        AND price > 0
        ORDER BY price_year ASC
    """
    
    result = frappe.db.sql(sql, as_dict=True)
    
    # Extract years and format them for Link field
    years = [str(row.price_year) for row in result if row.price_year]
    
    return years

@frappe.whitelist()
def get_latest_ets_price(year=None, ets_price_type=None):
    """Get the latest available ETS price for given year and type"""
    if not year or not ets_price_type:
        return None
    
    # Convert year to integer if it's a string
    try:
        year = int(year)
    except (ValueError, TypeError):
        return None
    
    # Use different ordering logic based on ETS price type
    if ets_price_type == 'Spot Price':
        # For Spot Price: order by price_date DESC to get the most recent price within the selected year
        order_clause = "ORDER BY price_date DESC, modified DESC"
    else:
        # For Future (Dec) prices: order by creation date to get most recently announced/created price within the selected year
        order_clause = "ORDER BY modified DESC"
    
    sql = f"""
        SELECT 
            price,
            price_date,
            ets_price_type,
            price_year
        FROM `tabETS Carbon Price`
        WHERE price_year = %(year)s 
        AND ets_price_type = %(ets_price_type)s
        {order_clause}
        LIMIT 1
    """
    
    sql_params = {"year": year, "ets_price_type": ets_price_type}
    result = frappe.db.sql(sql, sql_params, as_dict=True)
    
    return result[0] if result else None

def is_missing(val):
    try:
        return val is None or str(val).strip() in ("", "0", "0.0")
    except Exception:
        return True
