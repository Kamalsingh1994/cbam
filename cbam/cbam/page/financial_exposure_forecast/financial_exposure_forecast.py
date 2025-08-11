import frappe
from frappe import _
from datetime import datetime
from collections import defaultdict
import re
import calendar

@frappe.whitelist()
def get_cbam_report_data(cbam_reports=None, start=0, page_length=50, from_year=None, to_year=None):
    """
    Fetch CBAM report dashboard data, optimized for batch DB access and Frappe best practices.
    Returns: dict with columns, data, chart_data, total_count.
    """
    import json
    if isinstance(cbam_reports, str):
        cbam_reports = json.loads(cbam_reports)
    cbam_reports = cbam_reports or []
    start = int(start or 0)
    page_length = int(page_length or 50)
    if not cbam_reports:
        return {"columns": [], "data": [], "chart_data": {}, "total_count": 0}

    # Convert from_year and to_year to int if provided
    from_year = int(from_year) if from_year else None
    to_year = int(to_year) if to_year else None

    columns = get_columns()

    all_rows = []
    # Caches to avoid repeated DB hits
    cbam_factor_cache = {}
    bench_mark_cache = {}
    standard_emission_value_cache = {}

    def get_year_from_creation(creation_val):
        if isinstance(creation_val, datetime):
            return creation_val.year
        elif isinstance(creation_val, str):
            try:
                return datetime.strptime(creation_val, '%Y-%m-%d %H:%M:%S.%f').year
            except ValueError:
                return datetime.strptime(creation_val, '%Y-%m-%d %H:%M:%S').year
        else:
            return 0

    def get_quarter_from_dates(from_date, to_date):
        """Get quarter number from from_date and to_date"""
        if not from_date or not to_date:
            return None
        
        # Convert to datetime if string
        if isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d')
        if isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d')
        
        # Determine quarter based on to_date
        month = to_date.month
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4

    def get_quarter_end_month(quarter):
        """Get the end month name for a quarter"""
        quarter_end_months = {1: "Mar", 2: "Jun", 3: "Sep", 4: "Dec"}
        return quarter_end_months.get(quarter, "")

    def extract_numeric_value(value):
        """Extract numeric value from strings that may contain units like '0 t CO2/unit'"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Try to extract the first number from the string
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            if match:
                return float(match.group(1))
        return 0.0

    # Track uploaded quarters for forecasting
    uploaded_quarters = set()
    years_with_reports = set()
    current_year = datetime.now().year

    # Collect due dates for each year from the CBAM reports
    year_due_dates = {}
    for report in cbam_reports:
        parent = frappe.get_doc("CBAM Report", report)
        due_date = getattr(parent, 'due_date', None)
        if due_date:
            # Extract year from due_date string (assume format YYYY-MM-DD)
            year = str(due_date)[:4]
            year_due_dates[year] = str(due_date)

    for report in cbam_reports:
        parent = frappe.get_doc("CBAM Report", report)
        report_year = get_year_from_creation(parent.creation)
        
        # Get quarter from from_date and to_date
        quarter = get_quarter_from_dates(parent.from_date, parent.to_date)
        
        # Determine the correct year for this quarter based on from_date and to_date
        quarter_year = None
        if parent.from_date:
            if isinstance(parent.from_date, str):
                quarter_year = datetime.strptime(parent.from_date, '%Y-%m-%d').year
            else:
                quarter_year = parent.from_date.year
        elif parent.to_date:
            if isinstance(parent.to_date, str):
                quarter_year = datetime.strptime(parent.to_date, '%Y-%m-%d').year
            else:
                quarter_year = parent.to_date.year
        else:
            quarter_year = report_year
        
        if quarter and quarter_year:
            uploaded_quarters.add((quarter_year, quarter))
            years_with_reports.add(quarter_year)
        
        for row in parent.get('cbam_report_data') or []:
            if row.external_good:
                eg = frappe.get_doc("External Good", row.external_good)
                cn_code = getattr(eg, "cn_code", "")
                article_no = getattr(eg, "article_no", "")
                supplier = getattr(eg, "supplier", "")
                raw_mass_tonne = extract_numeric_value(getattr(eg, "raw_mass_tonne", 0.0))
                carbon_price_due = extract_numeric_value(getattr(eg, "carbon_price_due", 0.0))
                installation_country = getattr(eg, "installation_country", "")
                specific_direct_embedded_emissions = extract_numeric_value(getattr(eg, "specific_direct_embedded_emissions", 0.0))

                # Only fetch ETS prices for the quarter_year (not all years >= report_year)
                ets_prices = frappe.get_all(
                    "ETS Carbon Price",
                    filters={"price_year": quarter_year},
                    fields=["price_year", "price"],
                    order_by="price_year asc"
                )
                for ets in ets_prices:
                    year = int(ets.price_year)
                    # Filter by from_year and to_year if provided
                    if (from_year and year < from_year) or (to_year and year > to_year):
                        continue
                    ets_price = extract_numeric_value(ets.price)

                    # Fetch CBAM Factor for the year, only if not disabled
                    if year not in cbam_factor_cache:
                        cbam_factor_doc = frappe.get_all(
                            "CBAM Factor",
                            filters={"year": year, "disable": 0},
                            fields=["cbam_factor"],
                            limit=1
                        )
                        cbam_factor_cache[year] = cbam_factor_doc[0].cbam_factor if cbam_factor_doc else None
                    cbam_factor = cbam_factor_cache[year]
                    if cbam_factor is None:
                        continue  # Skip this year if CBAM Factor is disabled or missing
                    cbam_factor = extract_numeric_value(cbam_factor)

                    # Fetch Benchmark for year and cn_code
                    bench_mark_key = (year, cn_code)
                    if bench_mark_key not in bench_mark_cache:
                        bench_mark_cache[bench_mark_key] = frappe.db.get_value("CBAM Benchmark", {"year": year, "cn_code": cn_code}, "bench_mark") or 0.0
                    bench_mark = extract_numeric_value(bench_mark_cache[bench_mark_key])

                    # Fetch Standard Emission Value for year, country, cn_code
                    sev_key = (year, installation_country, cn_code)
                    if sev_key not in standard_emission_value_cache:
                        standard_emission_value_cache[sev_key] = frappe.db.get_value(
                            "Standard Emission Value",
                            {"year": year, "country": installation_country, "cn_code": cn_code},
                            "emission_value"
                        ) or 0.0
                    standard_emission_value = extract_numeric_value(standard_emission_value_cache[sev_key])

                    # Calculations
                    try:
                        real_emission_cost = (
                            (specific_direct_embedded_emissions - (cbam_factor * bench_mark)
                            - ((specific_direct_embedded_emissions * carbon_price_due) / ets_price if ets_price else 0))
                            * raw_mass_tonne * ets_price
                        )
                    except Exception:
                        real_emission_cost = 0.0

                    try:
                        standard_emission_cost = (
                            (standard_emission_value - (bench_mark * cbam_factor)
                            - ((standard_emission_value * carbon_price_due) / ets_price if ets_price else 0))
                            * raw_mass_tonne * ets_price
                        )
                    except Exception:
                        standard_emission_cost = 0.0

                    row_data = {
                        "year": year,
                        "quarter": quarter,  # Add quarter to the data row
                        "quarter_year": quarter_year,  # Add quarter_year to the data row
                        "cn_code": cn_code,
                        "article_no": article_no,
                        "supplier": supplier,
                        "raw_mass_tonne": raw_mass_tonne,
                        "carbon_price_due": carbon_price_due,
                        "installation_country": installation_country,
                        "specific_direct_embedded_emissions": specific_direct_embedded_emissions,
                        "standard_emission_value": standard_emission_value,
                        "bench_mark_emission_value": bench_mark,
                        "cbam_factor": cbam_factor,
                        "ets_price": ets_price,
                        "real_emission_cost": real_emission_cost,
                        "standard_emission_cost": standard_emission_cost,
                        "from_date": parent.from_date,
                        "to_date": parent.to_date,
                    }
                    all_rows.append(row_data)

    total_count = len(all_rows)
    data = all_rows[start:start+page_length]

    # Chart data: sum actual and standard cost by quarter
    quarter_totals = defaultdict(lambda: {"actual": 0, "standard": 0, "is_forecast": False})
    # Aggregate data by quarter using the new fields in all_rows
    for row in all_rows:
        qkey = (row.get("quarter_year"), row.get("quarter"))
        if qkey[0] and qkey[1]:
            quarter_totals[qkey]["actual"] += row.get("real_emission_cost", 0) or 0
            quarter_totals[qkey]["standard"] += row.get("standard_emission_cost", 0) or 0
    # Mark uploaded quarters as actual data, others as forecast
    for quarter_key in quarter_totals:
        if quarter_key in uploaded_quarters:
            quarter_totals[quarter_key]["is_forecast"] = False
        else:
            quarter_totals[quarter_key]["is_forecast"] = True

    # Build a list of all quarters for each year with reports
    all_quarters = []
    for year in sorted(years_with_reports):
        for quarter in range(1, 5):
            all_quarters.append((year, quarter))
    # Ensure quarter_totals has an entry for every quarter
    for q in all_quarters:
        if q not in quarter_totals:
            quarter_totals[q] = {"actual": 0, "standard": 0, "is_forecast": True}
    # Create chart data with quarter labels and separate actual/forecast series
    chart_categories = []
    actual_data = []
    forecast_data = []
    import calendar
    for year in sorted(years_with_reports):
        year_quarters = [(year, q) for q in range(1, 5)]
        # Calculate average of actuals for this year only
        actual_values = [quarter_totals[q]["actual"] for q in year_quarters if not quarter_totals[q]["is_forecast"] and quarter_totals[q]["actual"] is not None]
        avg_actual = sum(actual_values) / len(actual_values) if actual_values else 0
        for q in year_quarters:
            _, quarter = q
            last_month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
            month_name = calendar.month_name[last_month]
            category_label = f"{month_name} {year}"
            chart_categories.append(category_label)
            if quarter_totals[q]["is_forecast"]:
                actual_data.append(None)
                forecast_data.append(avg_actual)
            else:
                actual_data.append(quarter_totals[q]["actual"])
                forecast_data.append(None)
    chart_data = {
        "categories": chart_categories,
        "series": [
            {"name": "Actual Cost", "data": actual_data},
            {"name": "Forecast", "data": forecast_data},
        ],
        "year_due_dates": year_due_dates
    }

    return {"columns": columns, "data": data, "chart_data": chart_data, "total_count": total_count}
    
@frappe.whitelist()
def get_all_cbam_reports():
    """Get all CBAM reports for the current user"""
    user = frappe.session.user
    # Check if user is a System Manager
    user_roles = frappe.get_roles(user)
    is_system_manager = 'System Manager' in user_roles
    filters = {}
    if not is_system_manager:
        # Try to find a declarant linked to this user
        declarant = frappe.db.get_value("Declarant", {"email": user}, "name")
        if declarant:
            filters["declarant"] = declarant

    # Get all CBAM Reports (for this declarant or any)
    reports = frappe.db.get_list(
        "CBAM Report",
        filters=filters,
        fields=["name"],
        order_by="creation desc"
    )
    return [report["name"] for report in reports]

def get_columns():
    columns = [
        {"id": "year", "name": _( "Year"), "width": 80},
        {"id": "quarter", "name": _( "Quarter"), "width": 80},
        {"id": "quarter_year", "name": _( "Quarter Year"), "width": 120},
        {"id": "cn_code", "name": _( "CN Code"), "width": 100},
        {"id": "article_no", "name": _( "Article No."), "width": 120},
        {"id": "supplier", "name": _( "Supplier"), "width": 280},
        {"id": "raw_mass_tonne", "name": _( "Raw Mass [t]"), "width": 120},
        {"id": "carbon_price_due", "name": _( "Carbon Price Due"), "width": 150},
        {"id": "installation_country", "name": _( "Installation Country"), "width": 170},
        {"id": "specific_direct_embedded_emissions", "name": _( "Direct Embedded Emissions"), "width": 170},
        {"id": "standard_emission_value", "name": _( "Standard Emission Value"), "width": 200},
        {"id": "bench_mark_emission_value", "name": _( "Benchmark Emission Value"), "width": 210},
        {"id": "cbam_factor", "name": _( "CBAM Factor"), "width": 120},
        {"id": "ets_price", "name": _( "ETS Price"), "width": 120},
        {"id": "real_emission_cost", "name": _( "Actual Cost"), "width": 200},
        {"id": "standard_emission_cost", "name": _( "Standard Cost"), "width": 150},
    ]

    return columns
