import frappe
from frappe import _
from datetime import datetime
from collections import defaultdict
import re
import calendar

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

def fetch_cbam_report_rows(cbam_reports, from_year, to_year):
    base_rows = []
    uploaded_quarters = set()
    years_with_reports = set()
    year_due_dates = {}
    cbam_factor_cache = {}
    bench_mark_cache = {}
    standard_emission_value_cache = {}
    for report in cbam_reports:
        parent = frappe.get_doc("CBAM Report", report)
        report_year = get_year_from_creation(parent.creation)
        quarter = get_quarter_from_dates(parent.from_date, parent.to_date)
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
                ets_prices = frappe.get_all(
                    "ETS Carbon Price",
                    filters={"price_year": quarter_year},
                    fields=["price_year", "price", "price_date"],
                    order_by="price_date desc"
                )
                if ets_prices:
                    latest_ets = ets_prices[0]
                    year = int(latest_ets.price_year)
                    if (from_year and year < from_year) or (to_year and year > to_year):
                        continue
                    ets_price = extract_numeric_value(latest_ets.price)
                else:
                    continue
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
                    continue
                cbam_factor = extract_numeric_value(cbam_factor)
                bench_mark_key = (year, cn_code)
                if bench_mark_key not in bench_mark_cache:
                    bench_mark_cache[bench_mark_key] = frappe.db.get_value("CBAM Benchmark", {"year": year, "cn_code": cn_code}, "bench_mark") or 0.0
                bench_mark = extract_numeric_value(bench_mark_cache[bench_mark_key])
                sev_key = (year, installation_country, cn_code)
                if sev_key not in standard_emission_value_cache:
                    standard_emission_value_cache[sev_key] = frappe.db.get_value(
                        "Standard Emission Value",
                        {"year": year, "country": installation_country, "cn_code": cn_code},
                        "emission_value"
                    ) or 0.0
                standard_emission_value = extract_numeric_value(standard_emission_value_cache[sev_key])
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
                    "quarter": quarter,
                    "quarter_year": quarter_year,
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
                base_rows.append(row_data)
    return base_rows, uploaded_quarters, years_with_reports, year_due_dates

def duplicate_future_year_rows(base_rows, future_years):
    future_rows = []
    for future_year in future_years:
        for row in base_rows:
            # Copy and recalculate for future year (reuse build_row logic if available)
            future_row = row.copy()
            future_row["year"] = future_year
            future_row["quarter_year"] = f"Q{future_row.get('quarter')} {future_year}" if future_row.get('quarter') else f"{future_year}"
            # Fetch year-specific values and recalculate as in build_row
            # ... (reuse your cost calculation logic here) ...
            future_rows.append(future_row)
    return future_rows

def aggregate_year_totals(data, uploaded_quarters):
    year_totals = defaultdict(lambda: {"actual": 0, "standard": 0, "is_forecast": False})
    
    # Aggregate data by YEAR using the new fields in all_rows
    for row in data:
        year = row.get("year")
        if year:
            # Sum all items for each year to get total CBAM cost for that year
            year_totals[year]["actual"] += row.get("real_emission_cost", 0) or 0
            year_totals[year]["standard"] += row.get("standard_emission_cost", 0) or 0
    
    # Mark years as actual data if they have uploaded quarters, others as forecast
    for year in year_totals:
        has_uploaded_quarters = any((year, q) in uploaded_quarters for q in range(1, 5))
        year_totals[year]["is_forecast"] = not has_uploaded_quarters

    return year_totals

def build_chart_data(data, year_totals, current_year, uploaded_quarters, year_due_dates, cbam_factor_cache):
    # Add future years for projections (even without CBAM reports)
    # This ensures we show future cost projections using future values
    max_future_year = current_year + 10  # Show projections up to 10 years ahead
    
    # Get the latest year from due dates to ensure we cover all relevant future years
    if year_due_dates:
        max_due_year = max(int(year) for year in year_due_dates.keys())
        max_future_year = max(max_future_year, max_due_year)
    
    # Add future years for projections
    for future_year in range(current_year + 1, max_future_year + 1):
        if future_year not in year_totals:
            year_totals[future_year] = {"actual": 0, "standard": 0, "is_forecast": True}
    
    # Also add years that have due dates, even if no CBAM reports exist for those years
    # This ensures due date lines can be plotted for future years
    for due_year_str in year_due_dates.keys():
        due_year = int(due_year_str)
        if due_year not in year_totals:
            year_totals[due_year] = {"actual": 0, "standard": 0, "is_forecast": True}
    

    # Build a list of all years with reports
    all_years = []
    for year in sorted(year_totals.keys()):
        all_years.append(year)
    # Ensure year_totals has an entry for every year
    for year in all_years:
        if year not in year_totals:
            year_totals[year] = {"actual": 0, "standard": 0, "is_forecast": True}
    
    # Create chart data with quarterly labels for current year and yearly labels for other years
    chart_categories = []
    actual_data = []
    forecast_data = []
    ets_prices = []
    
    for year in sorted(year_totals.keys()):
        # Get the year's total costs (sum of all items for that year)
        year_actual = year_totals[year]["actual"]
        year_standard = year_totals[year]["standard"]
        year_is_forecast = year_totals[year]["is_forecast"]
        
        print(f"DEBUG: Processing year {year}, actual: {year_actual}, standard: {year_standard}, is_forecast: {year_is_forecast}")
        
        if year <= current_year:
            # For current and past years, show quarterly breakdown
            import calendar
            for quarter in range(1, 5):
                last_month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
                month_name = calendar.month_name[last_month]
                category_label = f"{month_name} {year}"
                chart_categories.append(category_label)
                print(f"DEBUG: Added quarterly category: {category_label}")
                
                # Get ETS price for this quarter
                ets_price = None
                for row in data:
                    if row.get("year") == year and row.get("quarter") == quarter:
                        ets_price = row.get("ets_price")
                        if ets_price is not None:
                            break
                
                # If no ETS price found for this quarter, fetch it directly from ETS Carbon Price table
                if ets_price is None:
                    ets_price_doc = frappe.get_all(
                        "ETS Carbon Price",
                        filters={"price_year": year},
                        fields=["price"],
                        order_by="price_date desc",  # Use latest price date for the year
                        limit=1
                    )
                    if ets_price_doc:
                        ets_price = extract_numeric_value(ets_price_doc[0].price)
                    else:
                        ets_price = 0.0  # No fallback to previous years
                
                ets_prices.append(ets_price)
                
                # Check if this quarter has actual data
                quarter_key = (year, quarter)
                has_actual_data = quarter_key in uploaded_quarters
                
                if has_actual_data:
                    # Get actual data for this quarter
                    quarter_actual = 0
                    for row in data:
                        if row.get("year") == year and row.get("quarter") == quarter:
                            quarter_actual += row.get("real_emission_cost", 0) or 0
                    
                    actual_data.append(quarter_actual)
                    forecast_data.append(None)
                    print(f"DEBUG: Current year {year} Q{quarter}: actual={quarter_actual}")
                else:
                    # Forecast for this quarter - use average of actual quarters or standard emission cost
                    actual_data.append(None)
                    
                    # Calculate forecast based on actual quarters in this year
                    actual_quarters_data = []
                    for q in range(1, 5):
                        q_key = (year, q)
                        if q_key in uploaded_quarters:
                            # Get actual data for this quarter
                            q_actual = 0
                            for row in data:
                                if row.get("year") == year and row.get("quarter") == q:
                                    q_actual += row.get("real_emission_cost", 0) or 0
                            if q_actual > 0:
                                actual_quarters_data.append(q_actual)
                    
                    if actual_quarters_data:
                        # Use average of actual quarters for forecast
                        avg_actual = sum(actual_quarters_data) / len(actual_quarters_data)
                        forecast_data.append(avg_actual)
                        print(f"DEBUG: Current year {year} Q{quarter}: forecast={avg_actual} (avg of actual quarters)")
                    else:
                        # Fallback to standard emission cost if no actual quarters
                        forecast_data.append(year_standard / 4)
                        print(f"DEBUG: Current year {year} Q{quarter}: forecast={year_standard / 4} (fallback)")
        else:
            # For future years, show calculated projections using future values
            if year > current_year:
                # For future years, create a compact representation with calculated costs
                category_label = f"{year}"  # Compact label for future years
                chart_categories.append(category_label)
                print(f"DEBUG: Added future year category: {category_label}")
                
                # Use helper function to calculate future year projections
                # This function is no longer needed as future year projections are handled by row duplication
                # future_cost, ets_price = calculate_future_year_projection(year, current_year, cbam_factor_cache, bench_mark_cache, standard_emission_value_cache)
                
                ets_prices.append(ets_price) # This will be None for future years
                actual_data.append(None)
                forecast_data.append(year_standard) # This will be the standard emission cost for future years
                print(f"DEBUG: Future year {year}: calculated forecast={year_standard}")
                
            else:
                # For current year without quarterly data, show yearly totals
                category_label = f"{year}"
                chart_categories.append(category_label)
                print(f"DEBUG: Added current year category: {category_label}")
                
                # Get ETS price for this year
                ets_price = None
                ets_price_doc = frappe.get_all(
                    "ETS Carbon Price",
                    filters={"price_year": year},
                    fields=["price"],
                    order_by="price_date desc",
                    limit=1
                )
                if ets_price_doc:
                    ets_price = extract_numeric_value(ets_price_doc[0].price)
                else:
                    ets_price = 0.0
                
                ets_prices.append(ets_price)
                
                # Add data for this year
                if year_is_forecast:
                    actual_data.append(None)
                    forecast_data.append(year_standard)
                    print(f"DEBUG: Current year {year}: forecast={year_standard}")
                else:
                    actual_data.append(year_actual)
                    forecast_data.append(None)
                    print(f"DEBUG: Current year {year}: actual={year_actual}")
    
    # Ensure ets_prices array covers ALL chart categories (including overlays)
    # If there are more categories than ETS prices, extend the array with fallback values
    while len(ets_prices) < len(chart_categories):
        # Use the last available ETS price as fallback for additional categories
        last_ets_price = ets_prices[-1] if ets_prices else None
        ets_prices.append(last_ets_price)
    
    # Add future year summary rows to the table data
    for year in sorted(year_totals.keys()):
        if year > current_year:
            # Create a summary row for future years showing calculated total cost
            # This function is no longer needed as future year projections are handled by row duplication
            # future_cost, future_ets_price = calculate_future_year_projection(year, current_year, cbam_factor_cache, bench_mark_cache, standard_emission_value_cache)
            
            # Get CBAM factor for display
            future_cbam_factor = cbam_factor_cache.get(year, 0.1)
            
            future_row = {
                "year": year,
                "quarter": "Projection",
                "quarter_year": f"{year} (Projection)",
                "cn_code": "N/A",
                "article_no": "Future Year Projection",
                "supplier": "Calculated using future values",
                "raw_mass_tonne": 10.0,  # Default mass used in calculation
                "carbon_price_due": 0.0,
                "installation_country": "N/A",
                "specific_direct_embedded_emissions": 1.0,  # Default emission factor used
                "standard_emission_value": 1.0,
                "bench_mark_emission_value": 0.0,
                "cbam_factor": future_cbam_factor,
                "ets_price": 0.0, # This will be 0.0 for future years
                "real_emission_cost": 0.0,  # No real data for future years
                "standard_emission_cost": year_standard, # This will be the standard emission cost for future years
                "from_date": f"{year}-01-01",
                "to_date": f"{year}-12-31",
            }
            data.append(future_row) # Append to the main data list
    
    print(f"DEBUG: Final chart_categories length: {len(chart_categories)}")
    print(f"DEBUG: Final actual_data length: {len(actual_data)}")
    print(f"DEBUG: Final forecast_data length: {len(forecast_data)}")
    print(f"DEBUG: Sample categories: {chart_categories[:8] if len(chart_categories) > 8 else chart_categories}")


    # Before building chart_data, call the function to extend year_due_dates
    year_due_dates = extend_year_due_dates_with_future_years(year_due_dates, current_year)

    chart_data = {
        "categories": chart_categories,
        "series": [
            {"name": "Current Year: Quarterly Financial Exposure (Real Data)", "data": actual_data},  # Shows quarterly for current/past years, yearly for future
            {"name": "Current Year: Quarterly Financial Exposure (Forecasts) + Future Year Projections", "data": forecast_data},
        ],
        "ets_prices": ets_prices,
        "year_due_dates": year_due_dates
    }

    return chart_data

@frappe.whitelist()
def get_cbam_report_data(cbam_reports=None, start=0, page_length=50, from_year=None, to_year=None):
    import json
    if isinstance(cbam_reports, str):
        cbam_reports = json.loads(cbam_reports)
    cbam_reports = cbam_reports or []
    start = int(start or 0)
    page_length = int(page_length or 50)
    if not cbam_reports:
        return {"columns": [], "data": [], "chart_data": {}, "total_count": 0}
    from_year = int(from_year) if from_year else None
    to_year = int(to_year) if to_year else None
    columns = get_columns()
    base_rows, uploaded_quarters, years_with_reports, year_due_dates = fetch_cbam_report_rows(cbam_reports, from_year, to_year)
    # Determine future years (e.g., from ETS Carbon Price)
    # This part of the logic needs to be re-evaluated to correctly identify future years
    # For now, we'll assume future years are those for which we have ETS Carbon Price data
    # and we need to ensure we include all years up to the max_future_year.
    current_year = datetime.now().year
    max_future_year = current_year + 10  # Show projections up to 10 years ahead
    ets_years = set(int(d.price_year) for d in frappe.get_all(
        "ETS Carbon Price",
        fields=["price_year"]
    ) if d.price_year)
    if ets_years:
        max_due_year = max(int(year) for year in ets_years)
        max_future_year = max(max_future_year, max_due_year)
    
    future_years = [year for year in range(current_year + 1, max_future_year + 1) if year not in years_with_reports]
    
    future_rows = duplicate_future_year_rows(base_rows, future_years)
    data = base_rows + future_rows
    total_count = len(data)
    data = data[start:start+page_length]
    year_totals = aggregate_year_totals(data, uploaded_quarters)
    cbam_factor_cache = {} # Initialize cbam_factor_cache here
    for year in years_with_reports:
        if year not in cbam_factor_cache:
            cbam_factor_doc = frappe.get_all(
                "CBAM Factor",
                filters={"year": year, "disable": 0},
                fields=["cbam_factor"],
                limit=1
            )
            cbam_factor_cache[year] = cbam_factor_doc[0].cbam_factor if cbam_factor_doc else None
    # Assume base_year is the selected year (from filter or argument)
    base_year = int(from_year) if from_year else current_year

    # Only show current year rows in the data table
    table_data = [row for row in data if int(row.get('year')) == base_year]
    total_count = len(table_data)
    table_data = table_data[start:start+page_length]

    # For chart_data, still use the full data list
    chart_data = build_chart_data(data, year_totals, current_year, uploaded_quarters, year_due_dates, cbam_factor_cache)

    return {"columns": columns, "data": table_data, "chart_data": chart_data, "total_count": total_count}
    
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

@frappe.whitelist()
def get_available_years():
    """Get available years from CBAM report from_date and to_date"""
    user = frappe.session.user
    current_year = datetime.now().year
    
    # Check if user is a System Manager
    user_roles = frappe.get_roles(user)
    is_system_manager = 'System Manager' in user_roles
    filters = {}
    if not is_system_manager:
        # Try to find a declarant linked to this user
        declarant = frappe.db.get_value("Declarant", {"email": user}, "name")
        if declarant:
            filters["declarant"] = declarant

    # Get all CBAM Reports and extract years from from_date and to_date
    reports = frappe.db.get_list(
        "CBAM Report",
        filters=filters,
        fields=["from_date", "to_date"],
        order_by="creation desc"
    )
    
    available_years = set()
    for report in reports:
        # Try to get year from from_date first, then to_date
        year = None
        if report.get("from_date"):
            try:
                if isinstance(report["from_date"], str):
                    year = datetime.strptime(report["from_date"], '%Y-%m-%d').year
                else:
                    year = report["from_date"].year
            except:
                pass
        
        if not year and report.get("to_date"):
            try:
                if isinstance(report["to_date"], str):
                    year = datetime.strptime(report["to_date"], '%Y-%m-%d').year
                else:
                    year = report["to_date"].year
            except:
                pass
        
        if year and year <= current_year:  # Only include past and current years
            available_years.add(year)
    
    # Return sorted list of available years (descending order)
    return sorted(list(available_years), reverse=True)

@frappe.whitelist()
def get_cbam_reports_by_year(year):
    """Get CBAM reports for a specific year based on from_date and to_date"""
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
    
    # Add year filter using from_date and to_date
    year = int(year)
    filters["from_date"] = [">=", f"{year}-01-01"]
    filters["to_date"] = ["<=", f"{year}-12-31"]

    # Get CBAM Reports for the specified year
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

def extend_year_due_dates_with_future_years(year_due_dates, base_year):
    # Collect all years from ETS Carbon Price, CBAM Factor, Standard Emission Value, and CBAM Benchmark
    ets_years = set(int(d.price_year) for d in frappe.get_all(
        "ETS Carbon Price",
        fields=["price_year"]
    ) if d.price_year)

    cbam_factor_years = set(int(d.year) for d in frappe.get_all(
        "CBAM Factor",
        fields=["year"],
        filters={"disable": 0}
    ) if d.year)
    sev_years = set(int(d.year) for d in frappe.get_all(
        "Standard Emission Value",
        fields=["year"]
    ) if d.year)
    benchmark_years = set(int(d.year) for d in frappe.get_all(
        "CBAM Benchmark",
        fields=["year"]
    ) if d.year)
    all_years = ets_years | cbam_factor_years | sev_years | benchmark_years
    print(f"DEBUG: All years: {all_years}")
    # Add one more year (max + 1) if all_years is not empty
    if all_years:
        all_years.add(max(all_years) + 1)
    # Only add years greater than base_year
    for year in all_years:
        if year > base_year:
            year_str = str(year)
            if year_str not in year_due_dates:
                year_due_dates[year_str] = f"{year}-01-31"
    return year_due_dates
