import frappe
import json

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
        {"fieldname": "cn_code", "fieldtype": "Data", "label": "CN Code", "width": 150},
        {"fieldname": "article_number", "fieldtype": "Data", "label": "Article Number", "width": 200},
        {"fieldname": "supplier", "fieldtype": "Data", "label": "Supplier", "width": 200},
        {"fieldname": "raw_mass", "fieldtype": "Data", "label": "Mass [kg]", "width": 150},
        {"fieldname": "carbon_price_due", "fieldtype": "Data", "label": "Carbon Price Due", "width": 150},
        {"fieldname": "installation_country", "fieldtype": "Data", "label": "Installation Country", "width": 180},
        {"fieldname": "real_emission_value", "fieldtype": "Data", "label": "Specific (Direct) Emission Value", "width": 250},
        {"fieldname": "real_emission_cost", "fieldtype": "Data", "label": "Actual Cost", "width": 180},
        {"fieldname": "standard_emission_cost", "fieldtype": "Data", "label": "Standard Cost", "width": 180},
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
    if declarants:
        declarant_list = ', '.join(f"'{d}'" for d in declarants)
        where_clauses.append(f"g.declarant IN ({declarant_list})")

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

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
    where_sql_eg = ""
    if where_clauses_eg:
        where_sql_eg = "WHERE " + " AND ".join(where_clauses_eg) if where_clauses_eg else ""

    cbam_factor = float(selected_filters.get('cbam_factor', 0.0) or 0.0)
    bench_mark = float(selected_filters.get('bench_mark', 0.0) or 0.0)
    emission_value = float(selected_filters.get('emission_value', 0.0) or 0.0)
    ets_carbon_price = float(selected_filters.get('ets_price_value', 0.0) or selected_filters.get('ets_price', 0.0) or 0.0)

    # Count total rows for pagination
    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT 
                eg.cn_code, eg.article_no as article_number, eg.supplier, eg.raw_mass, eg.installation_country,
                eg.specific_direct_embedded_emissions, eg.carbon_price_due
            FROM `tabExternal Good` eg
            {where_sql_eg}
            
            UNION
            SELECT 
                g.cn_code, g.article_number, g.supplier_name as supplier, g.raw_mass, g.installation_country,
                g.specific_direct_embedded_emissions, g.carbon_price_due
            FROM `tabGood` g
            {where_sql}
        ) AS count_table

    """
    total_count = frappe.db.sql(count_query)[0][0]

    # Main data query with LIMIT/OFFSET for pagination
    data_query = f"""
        SELECT * FROM (
            SELECT 
                eg.cn_code,
                eg.article_no AS article_number,
                eg.supplier,
                IFNULL(eg.raw_mass,0.0) AS raw_mass,
                IFNULL(eg.carbon_price_due,0.0) as carbon_price_due,
                eg.installation_country,
                IFNULL(eg.specific_direct_embedded_emissions,0.0) AS real_emission_value,             
                ((
                    IFNULL(eg.specific_direct_embedded_emissions,0.0) - ({cbam_factor} * {bench_mark})
                    - ((IFNULL(eg.specific_direct_embedded_emissions,0.0) * IFNULL(eg.carbon_price_due, 0.0)) / {ets_carbon_price})
                ) * IFNULL(eg.raw_mass, 0.0) * {ets_carbon_price}) AS real_emission_cost,

                ((
                    {emission_value}
                    - ({bench_mark} * {cbam_factor})
                    - (({emission_value} * IFNULL(eg.carbon_price_due, 0.0)) / {ets_carbon_price})
                ) * IFNULL(eg.raw_mass, 0.0) * {ets_carbon_price}) AS standard_emission_cost
            FROM `tabExternal Good` eg
            {where_sql_eg}
            UNION
            SELECT 
                g.cn_code,
                g.article_number,
                g.supplier_name AS supplier,
                IFNULL(g.raw_mass,0.0) AS raw_mass,
                IFNULL(g.carbon_price_due,0.0) AS carbon_price_due,
                g.installation_country,    
                IFNULL(g.specific_direct_embedded_emissions,0.0) AS real_emission_value,
                ((
                    IFNULL(g.specific_direct_embedded_emissions,0.0) - ({cbam_factor} * {bench_mark})
                    - ((IFNULL(g.specific_direct_embedded_emissions,0.0) * IFNULL(g.carbon_price_due,0.0)) / {ets_carbon_price})
                ) * IFNULL(g.raw_mass,0.0) * {ets_carbon_price}) AS real_emission_cost,
                ((
                    {emission_value}
                    - ({bench_mark} * {cbam_factor})
                    - (({emission_value} * IFNULL(g.carbon_price_due, 0.0)) / {ets_carbon_price})
                )
                * IFNULL(g.raw_mass, 0.0) * {ets_carbon_price}) AS standard_emission_cost
            FROM `tabGood` g
            {where_sql}
        ) AS main_table
        LIMIT {page_length} OFFSET {start}
    """
    data = frappe.db.sql(data_query, as_dict=1)
    frappe.log_error("121test",{
        "data_length": len(data),
        "total_count": total_count,
        "start": start,
        "page_length": page_length
    })
    return data, total_count


def get_chart_data(data):
    """Process data to create chart data grouped by year"""
    year_data = {}
    
    for row in data:
        # Extract year from reporting_period or use current year as fallback
        year = None
        if row.get('reporting_period'):
            try:
                # Try to extract year from reporting_period field
                year = str(row['reporting_period'])[:4]  # Take first 4 characters as year
            except:
                pass
        
        if not year:
            # Fallback to current year if no reporting_period
            from datetime import datetime
            year = str(datetime.now().year)
        
        if year not in year_data:
            year_data[year] = {
                'actual_cost': 0.0,
                'standard_cost': 0.0,
                'count': 0
            }
        
        # Sum up the costs for each year
        year_data[year]['actual_cost'] += float(row.get('real_emission_cost', 0.0) or 0.0)
        year_data[year]['standard_cost'] += float(row.get('standard_emission_cost', 0.0) or 0.0)
        year_data[year]['count'] += 1
    
    # Convert to chart format
    chart_data = {
        'labels': [],
        'actual_costs': [],
        'standard_costs': []
    }
    
    # Sort by year
    for year in sorted(year_data.keys()):
        chart_data['labels'].append(year)
        chart_data['actual_costs'].append(year_data[year]['actual_cost'])
        chart_data['standard_costs'].append(year_data[year]['standard_cost'])
    
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
    filters = json.loads(filters)

    filters = filters or {}

    sql = """
        SELECT 
            cf.cbam_factor,
            cnb.bench_mark,
            sev.emission_value,
            ecp.price AS ets_price
        FROM `tabCBAM Factor` cf
        LEFT JOIN `tabCN Code Bench Mark Emission Value` cnb 
            ON cnb.year = %(year)s
        LEFT JOIN `tabStandard Emission Value` sev 
            ON sev.year = %(year)s
        LEFT JOIN `tabETS Carbon Price` ecp 
            ON YEAR(ecp.price_date) = %(year)s AND ecp.ets_price_type = %(ets_price_type)s
        WHERE cf.year = %(year)s
        LIMIT 1
    """

    result = frappe.db.sql(sql, filters, as_dict=True)
    return result[0] if result else {}

