import frappe
from frappe import _
from datetime import datetime
from collections import defaultdict

from pypika import Column

@frappe.whitelist()
def get_cbam_report_data(cbam_reports=None, start=0, page_length=50):
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

    for report in cbam_reports:
        parent = frappe.get_doc("CBAM Report", report)
        report_year = get_year_from_creation(parent.creation)
        for row in parent.get('cbam_report_data') or []:
            if row.external_good:
                eg = frappe.get_doc("External Good", row.external_good)
                cn_code = getattr(eg, "cn_code", "")
                article_no = getattr(eg, "article_no", "")
                supplier = getattr(eg, "supplier", "")
                raw_mass_tonne = float(getattr(eg, "raw_mass_tonne", 0.0) or 0.0)
                carbon_price_due = float(getattr(eg, "carbon_price_due", 0.0) or 0.0)
                installation_country = getattr(eg, "installation_country", "")
                specific_direct_embedded_emissions = float(getattr(eg, "specific_direct_embedded_emissions", 0.0) or 0.0)

                # Fetch all ETS prices for price_year >= report_year
                future_ets_prices = frappe.get_all(
                    "ETS Carbon Price",
                    filters={"price_year": [">=", report_year]},
                    fields=["price_year", "price"],
                    order_by="price_year asc"
                )
                for ets in future_ets_prices:
                    year = int(ets.price_year)
                    ets_price = float(ets.price or 0)

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
                    cbam_factor = float(cbam_factor or 0.0)

                    # Fetch Benchmark for year and cn_code
                    bench_mark_key = (year, cn_code)
                    if bench_mark_key not in bench_mark_cache:
                        bench_mark_cache[bench_mark_key] = frappe.db.get_value("CBAM Benchmark", {"year": year, "cn_code": cn_code}, "bench_mark") or 0.0
                    bench_mark = float(bench_mark_cache[bench_mark_key] or 0.0)

                    # Fetch Standard Emission Value for year, country, cn_code
                    sev_key = (year, installation_country, cn_code)
                    if sev_key not in standard_emission_value_cache:
                        standard_emission_value_cache[sev_key] = frappe.db.get_value(
                            "Standard Emission Value",
                            {"year": year, "country": installation_country, "cn_code": cn_code},
                            "emission_value"
                        ) or 0.0
                    standard_emission_value = float(standard_emission_value_cache[sev_key] or 0.0)

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
                    }
                    all_rows.append(row_data)

    total_count = len(all_rows)
    data = all_rows[start:start+page_length]

    # Chart data: sum actual and standard cost by year
    year_totals = defaultdict(lambda: {"actual": 0, "standard": 0})
    for row in all_rows:
        y = row["year"]
        year_totals[y]["actual"] += row.get("real_emission_cost", 0) or 0
        year_totals[y]["standard"] += row.get("standard_emission_cost", 0) or 0
    chart_data = {
        "categories": sorted(year_totals.keys()),
        "series": [
            {"name": "Actual Cost", "data": [year_totals[y]["actual"] for y in sorted(year_totals.keys())]},
            {"name": "Standard Cost", "data": [year_totals[y]["standard"] for y in sorted(year_totals.keys())]},
        ]
    }

    return {"columns": columns, "data": data, "chart_data": chart_data, "total_count": total_count}
    
def get_columns():
    columns = [
        {"id": "year", "name": _( "Year"), "width": 80},
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
