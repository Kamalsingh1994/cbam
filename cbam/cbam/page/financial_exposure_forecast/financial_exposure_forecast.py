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
    default_emission_value_cache = {}
	default_emission_rows_cache = {}
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
                    # Use quarter_year for filtering instead of ETS price year to get actual report data
                    report_year = quarter_year

                    if (from_year and report_year < from_year) or (to_year and report_year > to_year):
                        continue

                    ets_price = extract_numeric_value(latest_ets.price)
                else:
                    continue

                # Use quarter_year (report year) for all lookups to ensure consistency
                report_year = quarter_year
                if report_year not in cbam_factor_cache:
                    cbam_factor_doc = frappe.get_all(
                        "CBAM Factor",
                        filters={"year": report_year, "disable": 0},
                        fields=["cbam_factor"],
                        limit=1
                    )
                    cbam_factor_cache[report_year] = cbam_factor_doc[0].cbam_factor if cbam_factor_doc else None
                cbam_factor = cbam_factor_cache[report_year]

                if cbam_factor is None:
                    continue

                cbam_factor = extract_numeric_value(cbam_factor)

                # Get benchmark from External Good (stored value)
                # Fallback to 0.0 if not calculated
                bench_mark = extract_numeric_value(getattr(eg, "country_specific_default_cbam_benchmark", None) or 0.0)
                # Round to 4 decimal places (German calculation standard)
                bench_mark = round(bench_mark, 4)
                sev_key = (report_year, installation_country, cn_code)

                if sev_key not in default_emission_value_cache:
                    sev_value = None
                    if eg.name not in default_emission_rows_cache:
                        default_emission_rows_cache[eg.name] = frappe.get_all(
                            "External Good Default Emission Value",
                            filters={"parent": eg.name},
                            fields=[
                                "cn_code",
                                "default_value_total_emissions",
                                "default_value_2026",
                                "default_value_2027",
                                "default_value_2028_onwards",
                                "production_route_cbam_benchmark_indicator",
                                "applicable_product",
                            ]
                        )
                    from cbam.utils.benchmark import pick_default_emission_value
                    selected_rows = default_emission_rows_cache[eg.name]
                    applicable = [row for row in selected_rows if row.get("applicable_product")]
                    if len(applicable) == 1:
                        sev_value = pick_default_emission_value(applicable[0], report_year)
                    elif len(selected_rows) == 1:
                        sev_value = pick_default_emission_value(selected_rows[0], report_year)
                    if sev_value is None:
                        from cbam.utils.benchmark import get_default_emission_value
                        sev_value = get_default_emission_value(installation_country, cn_code, report_year)
                    default_emission_value_cache[sev_key] = sev_value or 0.0

                default_emission_value = extract_numeric_value(default_emission_value_cache[sev_key])

                try:
                    real_emission_cost = (
                        (specific_direct_embedded_emissions - (cbam_factor * bench_mark)
                        - ((specific_direct_embedded_emissions * carbon_price_due) / ets_price if ets_price else 0))
                        * raw_mass_tonne * ets_price
                    )
                except Exception:
                    real_emission_cost = 0.0

                try:
                    default_emission_cost = (
                        (default_emission_value - (bench_mark * cbam_factor)
                        - ((default_emission_value * carbon_price_due) / ets_price if ets_price else 0))
                        * raw_mass_tonne * ets_price
                    )
                except Exception:
                    default_emission_cost = 0.0

                row_data = {
                    "year": quarter_year,  # Use quarter_year (report year) instead of ETS price year
                    "quarter": quarter,
                    "quarter_year": quarter_year,
                    "cn_code": cn_code,
                    "article_no": article_no,
                    "supplier": supplier,
                    "raw_mass_tonne": raw_mass_tonne,
                    "carbon_price_due": carbon_price_due,
                    "installation_country": installation_country,
                    "specific_direct_embedded_emissions": specific_direct_embedded_emissions,
                    "default_emission_value": default_emission_value,
                    "bench_mark_emission_value": bench_mark,
                    "cbam_factor": cbam_factor,
                    "ets_price": ets_price,
                    "real_emission_cost": real_emission_cost,
                    "default_emission_cost": default_emission_cost,
                    "from_date": parent.from_date,
                    "to_date": parent.to_date,
                }
                base_rows.append(row_data)
    return base_rows, uploaded_quarters, years_with_reports, year_due_dates

def duplicate_future_year_rows(base_rows, future_years):
    future_rows = []
    for future_year in future_years:
        # Duplicate each individual base row for the future year
        for base_row in base_rows:
            future_row = base_row.copy()
            future_row["year"] = future_year
            future_row["quarter_year"] = f"Q{base_row.get('quarter', 1)} {future_year}"
            # Fetch year-specific values and recalculate as in build_row
            cn_code = future_row.get("cn_code")
            installation_country = future_row.get("installation_country")
            raw_mass_tonne = future_row.get("raw_mass_tonne", 0.0)
            carbon_price_due = future_row.get("carbon_price_due", 0.0)
            specific_direct_embedded_emissions = future_row.get("specific_direct_embedded_emissions", 0.0)
            # ETS Price
            ets_price_doc = frappe.get_all(
                "ETS Carbon Price",
                filters={"price_year": future_year},
                fields=["price"],
                order_by="price_date desc",
                limit=1
            )
            ets_price = extract_numeric_value(ets_price_doc[0].price) if ets_price_doc else 0.0
            future_row["ets_price"] = ets_price
            # CBAM Factor
            cbam_factor_doc = frappe.get_all(
                "CBAM Factor",
                filters={"year": future_year, "disable": 0},
                fields=["cbam_factor"],
                limit=1
            )
            cbam_factor = extract_numeric_value(cbam_factor_doc[0].cbam_factor) if cbam_factor_doc else 0.0
            future_row["cbam_factor"] = cbam_factor
            # Benchmark - recalculate for future year
            # Try to get from stored value first, but for future years we need to recalculate
            from cbam.utils.benchmark import calculate_country_specific_benchmark
            benchmark_result = calculate_country_specific_benchmark(
                cn_code,
                installation_country,
                f"{future_year}-01-01"  # Reference date for future year
            )
            bench_mark = benchmark_result.get("benchmark_value") or 0.0
            # Round to 4 decimal places (German calculation standard)
            bench_mark = round(extract_numeric_value(bench_mark), 4)
            future_row["bench_mark_emission_value"] = bench_mark
            # SEV with fallback to parent CN code groups
            from cbam.utils.benchmark import get_default_emission_value
            sev = get_default_emission_value(installation_country, cn_code, future_year) or 0.0
            future_row["default_emission_value"] = extract_numeric_value(sev)

            # Recalculate costs
            try:
                default_emission_cost = (
                    (future_row["default_emission_value"] - (future_row["bench_mark_emission_value"] * future_row["cbam_factor"]))
                    * raw_mass_tonne * ets_price
                )
            except Exception:
                default_emission_cost = 0.0
            future_row["default_emission_cost"] = default_emission_cost
            try:
                real_emission_cost = (
                    (specific_direct_embedded_emissions - (cbam_factor * future_row["bench_mark_emission_value"]))
                    * raw_mass_tonne * ets_price
                )
            except Exception:
                real_emission_cost = 0.0
            future_row["real_emission_cost"] = real_emission_cost
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
            year_totals[year]["standard"] += row.get("default_emission_cost", 0) or 0

    # Mark years as actual data if they have uploaded quarters, others as forecast
    for year in year_totals:
        has_uploaded_quarters = any((year, q) in uploaded_quarters for q in range(1, 5))
        year_totals[year]["is_forecast"] = not has_uploaded_quarters

    return year_totals

def build_chart_data(data, year_totals, current_year, uploaded_quarters, year_due_dates, cbam_factor_cache, max_future_year, base_rows=None, future_rows=None, base_year=None):
    import calendar
    chart_categories = []
    actual_data = []
    forecast_data = []
    ets_prices = []

    # Use base_year if provided, otherwise fall back to current_year
    if base_year is None:
        base_year = current_year

    # If base_rows and future_rows are not provided, fall back to splitting data
    if base_rows is None or future_rows is None:
        base_rows = [row for row in data if row.get('year') == base_year]
        future_rows = [row for row in data if row.get('year') > base_year]

    # Build a set of all years (selected year + future) and all quarters
    all_years = sorted(set(row.get('year') for row in base_rows + future_rows if row.get('year')))

    # Ensure we show the selected year and ALL years after it (including gaps)
    # This ensures 2024, 2025, 2026, 2027 are all shown when 2024 is selected
    if base_year not in all_years:
        all_years = [base_year] + [y for y in all_years if y > base_year]
    else:
        # Include the selected year and all years after it, even if there are gaps
        all_years = [y for y in all_years if y >= base_year]

    # Also include any missing years between base_year and max_future_year
    max_year_in_data = max(all_years) if all_years else base_year
    for year in range(base_year + 1, max_year_in_data + 1):
        if year not in all_years:
            all_years.append(year)

    # Sort again to maintain order
    all_years = sorted(all_years)

    for year in all_years:
        for quarter in range(1, 5):
            last_month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
            month_name = calendar.month_name[last_month]
            category_label = f"{month_name} {year}"
            chart_categories.append(category_label)
            if year == base_year:
                # Sum all default_emission_cost for this quarter
                quarter_rows = [r for r in base_rows if r.get('year') == year and r.get('quarter') == quarter]
                quarter_sum = sum(r.get('default_emission_cost', 0) or 0 for r in quarter_rows)
                if quarter_rows and quarter_sum != 0:
                    actual_data.append(quarter_sum)
                    forecast_data.append(None)
                    ets_price = next((r.get('ets_price') for r in quarter_rows if r.get('ets_price') is not None), None)
                    if ets_price is None:
                        # Try to fetch from ETS Carbon Price table
                        ets_price_doc = frappe.get_all(
                            "ETS Carbon Price",
                            filters={"price_year": year},
                            fields=["price"],
                            order_by="price_date desc",
                            limit=1
                        )
                        ets_price = extract_numeric_value(ets_price_doc[0].price) if ets_price_doc else None
                    ets_prices.append(ets_price)
                else:
                    # No data for this quarter, forecast = sum of standard values for previous quarters
                    actual_data.append(None)
                    prev_quarters = [r.get('default_emission_cost') for r in base_rows
                                     if r.get('year') == year and r.get('quarter') is not None
                                     and r.get('quarter') < quarter and r.get('default_emission_cost') is not None]
                    forecast_value = sum(prev_quarters) if prev_quarters else 0.0
                    forecast_data.append(forecast_value)
                    # ETS price fallback
                    ets_price_doc = frappe.get_all(
                        "ETS Carbon Price",
                        filters={"price_year": year},
                        fields=["price"],
                        order_by="price_date desc",
                        limit=1
                    )
                    ets_price = extract_numeric_value(ets_price_doc[0].price) if ets_price_doc else None
                    ets_prices.append(ets_price)
            else:
                # For future years, sum all rows for this quarter (like current year)
                quarter_rows = [r for r in future_rows if r.get('year') == year and r.get('quarter') == quarter]
                quarter_sum = sum(r.get('default_emission_cost', 0) or 0 for r in quarter_rows)
                actual_data.append(None)

                # Debug logging removed to prevent BrokenPipeError

                if quarter_rows and quarter_sum != 0:
                    # Q1 and Q2: use sum of all duplicated row values
                    forecast_data.append(quarter_sum)
                    ets_price = next((r.get('ets_price') for r in quarter_rows if r.get('ets_price') is not None), None)
                    ets_prices.append(ets_price)
                else:
                    # Q3 and Q4: calculate as sum of previous quarters (like current year)
                    prev_quarters = [r.get('default_emission_cost') for r in future_rows
                                   if r.get('year') == year and r.get('quarter') is not None
                                   and r.get('quarter') < quarter and r.get('default_emission_cost') is not None]
                    forecast_value = sum(prev_quarters) if prev_quarters else 0.0
                    # Debug logging removed to prevent BrokenPipeError
                    forecast_data.append(forecast_value)
                    # ETS price fallback
                    ets_price_doc = frappe.get_all(
                        "ETS Carbon Price",
                        filters={"price_year": year},
                        fields=["price"],
                        order_by="price_date desc",
                        limit=1
                    )
                    ets_price = extract_numeric_value(ets_price_doc[0].price) if ets_price_doc else None
                    ets_prices.append(ets_price)

    # Fill any None in ets_prices with last available value or 0.0
    for i in range(len(ets_prices)):
        if ets_prices[i] is None:
            ets_prices[i] = ets_prices[i-1] if i > 0 else 0.0

    # Ensure year_due_dates is always populated
    year_due_dates = extend_year_due_dates_with_future_years(year_due_dates, current_year)

    chart_data = {
        "categories": chart_categories,
        "series": [
            {"name": f"Selected Year ({base_year}): Quarterly Financial Exposure", "data": actual_data},
            {"name": f"Future Year Projections ({base_year + 1}+)", "data": forecast_data},
        ],
        "ets_prices": ets_prices,
        "year_due_dates": year_due_dates
    }
    return chart_data

@frappe.whitelist()
def get_cbam_report_data(cbam_reports=None, start=0, page_length=50, year=None, from_year=None, to_year=None):
    import json
    try:
        if isinstance(cbam_reports, str):
            cbam_reports = json.loads(cbam_reports)
        cbam_reports = cbam_reports or []
        start = int(start or 0)
        page_length = int(page_length or 50)
        if not cbam_reports:
            return {"columns": [], "data": [], "chart_data": {}, "total_count": 0}
    except Exception as e:
        frappe.log_error("Error parsing parameters in get_cbam_report_data", str(e))
        return {"columns": [], "data": [], "chart_data": {}, "total_count": 0, "error": str(e)}

    try:
        # Support both 'year' and 'from_year' parameters for backward compatibility
        if year is not None:
            from_year = int(year)
        elif from_year is not None:
            from_year = int(from_year)
        else:
            from_year = None

        to_year = int(to_year) if to_year else None
        columns = get_columns()

        base_rows, uploaded_quarters, years_with_reports, year_due_dates = fetch_cbam_report_rows(cbam_reports, from_year, to_year)
    except Exception as e:
        frappe.log_error("Error in get_cbam_report_data processing", str(e))
        return {"columns": [], "data": [], "chart_data": {}, "total_count": 0, "error": str(e)}

    try:
        # Determine future years (e.g., from ETS Carbon Price)
        # This part of the logic needs to be re-evaluated to correctly identify future years
        # For now, we'll assume future years are those for which we have ETS Carbon Price data
        # and we need to ensure we include all years up to the max_future_year.
        current_year = datetime.now().year
        # Determine max future year based on ETS Carbon Price years
        ets_years = set(int(d.price_year) for d in frappe.get_all(
            "ETS Carbon Price",
            fields=["price_year"],
        ) if d.price_year is not None)

        if ets_years:
            max_future_year = max(ets_years)
        else:
            max_future_year = current_year  # fallback: no future projection if no ETS price

        future_years = [year for year in range(current_year + 1, max_future_year + 1) if year not in years_with_reports]
        future_rows = duplicate_future_year_rows(base_rows, future_years)

        all_data = base_rows + future_rows  # Keep full data for chart

        # Initialize cbam_factor_cache
        cbam_factor_cache = {}
        for year in years_with_reports:
            if year not in cbam_factor_cache:
                cbam_factor_doc = frappe.get_all(
                    "CBAM Factor",
                    filters={"year": year, "disable": 0},
                    fields=["cbam_factor"],
                    limit=1
                )
                cbam_factor_cache[year] = cbam_factor_doc[0].cbam_factor if cbam_factor_doc else None

        # Determine base_year - if no year selected, use the earliest year with data
        if from_year:
            base_year = int(from_year)
        else:
            # If no year selected, use the earliest year that has data
            available_years = sorted(set(row.get('year') for row in all_data if row.get('year')))
            base_year = available_years[0] if available_years else current_year

        # Show selected year and all future duplicated rows in the data table
        table_data = [row for row in all_data if int(row.get('year')) >= base_year]
        total_count = len(table_data)
        table_data = table_data[start:start+page_length]

        # Calculate year totals from full data
        year_totals = aggregate_year_totals(all_data, uploaded_quarters)

        # For chart_data, treat selected year as current year and all greater years as future
        chart_data = build_chart_data(all_data, year_totals, base_year, uploaded_quarters, year_due_dates, cbam_factor_cache, max_future_year, base_rows=[row for row in all_data if row.get('year') == base_year], future_rows=[row for row in all_data if row.get('year') > base_year])

        return {"columns": columns, "data": table_data, "chart_data": chart_data, "total_count": total_count}
    except Exception as e:
        frappe.log_error("get_cbam_report_data main processing", str(e))
        return {"columns": [], "data": [], "chart_data": {}, "total_count": 0, "error": str(e)}

@frappe.whitelist()
def get_available_years():
    """Get available years from CBAM report from_date and to_date"""
    user = frappe.session.user
    current_year = datetime.now().year

    # Check if user is a System Manager
    user_roles = frappe.get_roles(user)
    is_system_manager = 'System Manager' in user_roles
    filters = {}
    # Only filter by Declarant if user has explicit restrictions
    if not is_system_manager:
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

    # Filter by user permissions if not System Manager
    user_roles = frappe.get_roles(user)
    is_system_manager = 'System Manager' in user_roles

    filters = {}

    # Only filter by Declarant if user has explicit restrictions (not all non-managers)
    if not is_system_manager:
        # Check if user has limited scope
        declarant = frappe.db.get_value("Declarant", {"email": user}, "name")
        if declarant:
            filters["declarant"] = declarant
    # System Managers and users with broader access see all reports

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
        {"id": "default_emission_value", "name": _( "Default Emission Value"), "width": 200},
        {"id": "bench_mark_emission_value", "name": _( "Benchmark Emission Value"), "width": 210},
        {"id": "cbam_factor", "name": _( "CBAM Factor"), "width": 120},
        {"id": "ets_price", "name": _( "ETS Price"), "width": 120},
        {"id": "default_emission_cost", "name": _( "Default Cost"), "width": 150},
    ]

    return columns

def extend_year_due_dates_with_future_years(year_due_dates, base_year):
    try:
        # Collect all years from ETS Carbon Price
        ets_years = set(int(d.price_year) for d in frappe.get_all(
            "ETS Carbon Price",
            fields=["price_year"]
        ) if d.price_year)

        if ets_years:
            ets_years.add(max(ets_years) + 1)

        # Only add years greater than base_year
        for year in ets_years:
            if year > base_year:
                year_str = str(year)
                if year_str not in year_due_dates:
                    # Fetch due date from custom import doctype using year field
                    custom_imports = frappe.get_all(
                        "Customs Import",  # Replace with actual doctype name
                        filters={"year": year-1},
                        fields=["due_date"],
                        limit=1
                    )

                    if custom_imports and custom_imports[0].due_date:
                        year_due_dates[year_str] = custom_imports[0].due_date
                    else:
                        # Fallback to default due date
                        year_due_dates[year_str] = f"{year}-01-31"

        return year_due_dates
    except Exception as e:
        frappe.log_error("extend_year_due_dates_with_future_years", str(e))
        return year_due_dates
