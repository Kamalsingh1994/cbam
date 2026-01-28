# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.sessions import datetime
from frappe.utils import flt, getdate
from cbam.utils.benchmark import pick_default_emission_value
from collections import defaultdict

@frappe.whitelist()
def get_ets_prices(price_type=None, month=None, year=None):
    conditions = []
    values = []

    if price_type:
        conditions.append("ets_price_type = %s")
        values.append(price_type)

    if month and year:
        try:
            month_number = datetime.strptime(month, "%B").month
            conditions.append("MONTH(price_date) = %s")
            conditions.append("YEAR(price_date) = %s")
            values.extend([month_number, year])
        except ValueError:
            frappe.throw("Invalid month format")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    data = frappe.db.sql(f"""
        SELECT DISTINCT price, price_date FROM `tabETS Carbon Price`
        {where_clause}
        ORDER BY price_date DESC
    """, values, as_dict=True)

    return data


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    columns =  [
		{
			"fieldname": "cn_code",
			"fieldtype": "Data",
			"label": "CN Code",
			"width": 150
		},
		{
			"fieldname": "article_number",
			"fieldtype": "Data",
			"label": "Article Number",
		},
		{
			"fieldname": "supplier",
			"fieldtype": "Data",
			"label": "Supplier",
            "width": 200
		},
        {
			"fieldname": "installation_country",
			"fieldtype": "Data",
			"label": "Installation Country"
		},
		{
			"fieldname": "raw_mass",
			"fieldtype": "Data",
			"label": "Mass [kg]",
			"width": 150
		},
		{
			"fieldname": "mass_per_article",
			"fieldtype": "Data",
			"label": "Mass per Article"
		},
        {
			"fieldname": "buying_price",
			"fieldtype": "Data",
			"label": "Buying Price per Mass"
		},
		{
			"fieldname": "real_emission_value",
			"fieldtype": "Data",
			"label": "Specific (Direct) Emission Value"
		},
        {
			"fieldname": "default_emission_value",
			"fieldtype": "Data",
			"label": "Default Emission Value"
		},
		{
			"fieldname": "real_emission_cost",
			"fieldtype": "Data",
			"label": "Emission Cost based on Actual Emission Value"
		},
        {
			"fieldname": "default_emission_cost",
			"fieldtype": "Data",
			"label": "Emission Cost based on Default Emission Value"
		},
		{
			"fieldname": "carbon_price_due",
			"fieldtype": "Data",
			"label": "Carbon Price Due"
		},
        {
            "fieldname": "cbam_factor",
			"fieldtype": "Data",
			"label": "CBAM Factor",
        },
        {
            "fieldname": "bench_mark",
            "fieldtype": "Data",
            "label": "Bench Mark",
        },
        {
            "fieldname": "ets_carbon_price",
            "fieldtype": "Data",
            "label": "ETS Carbon Price",
        }
	]

    return columns

def get_data(filters=None):
    filters = filters or {}

    ets_carbon_price = filters.get('ets_price') or 0

    user = frappe.session.user
    declarants = get_declarant_for_user(user)

    where_clauses = []
    where_clauses_eg = []


    # Declarant restriction (only for Good)
    if declarants:
        declarant_list = ', '.join(f"'{d}'" for d in declarants)
        where_clauses.append(f"g.declarant IN ({declarant_list})")

    # CN Code filter
    if filters.get("cn_code"):
        cn_code_list = ', '.join(f"'{c}'" for c in filters["cn_code"])
        where_clauses.append(f"(g.cn_code IN ({cn_code_list}))")
        where_clauses_eg.append(f"(eg.cn_code IN ({cn_code_list}))")

    # Supplier filter
    if filters.get("supplier"):
        supplier_list = ', '.join(f"'{s}'" for s in filters["supplier"])
        where_clauses.append(f"(g.supplier_name IN ({supplier_list}))")
        where_clauses_eg.append(f"(eg.supplier IN ({supplier_list}))")

	# Article Number filter
    if filters.get("article_number"):
        article_number_list = ', '.join(f"'{s}'" for s in filters["article_number"])
        where_clauses.append(f"(g.article_number IN ({article_number_list}))")
        where_clauses_eg.append(f"(eg.article_no IN ({article_number_list}))")

    # Reporting Period filter
    if filters.get("reporting_period"):
        reporting_period_list = ', '.join(f"'{s}'" for s in filters["reporting_period"])
        where_clauses.append(f"(g.internal_customs_import_number IN ({reporting_period_list}))")
        where_clauses_eg.append(f"(eg.reporting_period IN ({reporting_period_list}))")


    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    where_sql_eg = ""
    if where_clauses_eg:
        where_sql_eg = "WHERE " + " AND ".join(where_clauses_eg) if where_clauses_eg else ""

    data = frappe.db.sql(f"""
        SELECT
            eg.cn_code,
            eg.article_no AS article_number,
            eg.supplier,
            eg.installation_country,
            IFNULL(eg.raw_mass,0.0) AS raw_mass,
            IFNULL(eg.mass_per_article,0.0) AS mass_per_article,
            IFNULL(eg.buying_price_per_mass,0.0) AS buying_price,
            IFNULL(eg.carbon_price_due,0.0) as carbon_price_due,
            IFNULL(eg.specific_direct_embedded_emissions,0.0) AS real_emission_value,
            0.0 AS default_emission_value,
            COALESCE(eg.country_specific_default_cbam_benchmark, 0.0) AS bench_mark,
            NULL AS good_name,
            eg.reporting_period,
            eg.year as external_good_year,
            IFNULL(cbam.cbam_factor,0.0) AS cbam_factor,
            {ets_carbon_price} as ets_carbon_price,
            ((
                IFNULL(eg.specific_direct_embedded_emissions,0) - (IFNULL(cbam.cbam_factor,0) * COALESCE(eg.country_specific_default_cbam_benchmark, 0.0))
                - ((IFNULL(eg.specific_direct_embedded_emissions,0) * IFNULL(eg.carbon_price_due, 0)) / {ets_carbon_price})
            ) * IFNULL(eg.raw_mass, 0) * {ets_carbon_price}) AS real_emission_cost,

            0.0 AS default_emission_cost

        FROM `tabExternal Good` eg
        LEFT JOIN `tabReporting Period` rp
            ON rp.reporting_period = eg.reporting_period AND rp.parent IS NOT NULL AND rp.parenttype = 'CBAM Factor'

        LEFT JOIN `tabCBAM Factor` cbam
            ON cbam.name = rp.parent

		{where_sql_eg}

        UNION

        SELECT
            g.cn_code,
            g.article_number,
            g.supplier_name AS supplier,
            g.installation_country,
            IFNULL(g.raw_mass,0.0) AS raw_mass,
            IFNULL(g.mass_per_article,0.0) AS mass_per_article,
            IFNULL(g.buying_price,0.0) AS buying_price,
            IFNULL(g.carbon_price_due,0.0) AS carbon_price_due,
            IFNULL(g.specific_direct_embedded_emissions,0) AS real_emission_value,
            0.0 AS default_emission_value,
            COALESCE(g.country_specific_default_cbam_benchmark, 0.0) AS bench_mark,
            g.name AS good_name,
            g.internal_customs_import_number as reporting_period,
            NULL as external_good_year,
            IFNULL(cbam.cbam_factor,0.0) AS cbam_factor,
            {ets_carbon_price} as ets_carbon_price,
            ((
                IFNULL(g.specific_direct_embedded_emissions,0.0) - (IFNULL(cbam.cbam_factor,0.0) * COALESCE(g.country_specific_default_cbam_benchmark, 0.0))
                - ((IFNULL(g.specific_direct_embedded_emissions,0.0) * IFNULL(g.carbon_price_due,0.0)) / {ets_carbon_price})
            ) * IFNULL(g.raw_mass,0.0) * {ets_carbon_price}) AS real_emission_cost,

            0.0 AS default_emission_cost

        FROM `tabGood` g

        LEFT JOIN `tabReporting Period` rp
            ON rp.reporting_period = g.internal_customs_import_number AND rp.parent IS NOT NULL
        LEFT JOIN `tabCBAM Factor` cbam
            ON cbam.name = rp.parent AND rp.parenttype = 'CBAM Factor'

        {where_sql}
    """, as_dict=1)

    unique_keys = set()
    final_data = []

    good_names = [row.get("good_name") for row in data if row.get("good_name")]
    external_good_names = [row.get("name") for row in data if not row.get("good_name")]
    default_values_by_good = get_good_default_emission_values(good_names)
    default_values_by_external_good = get_external_good_default_emission_values(external_good_names)
    reporting_periods = [row.get("reporting_period") for row in data if row.get("reporting_period")]
    reporting_years = get_customs_import_year_map(reporting_periods)

    for row in data:
        key = (
            row["cn_code"], row["article_number"], row["supplier"], row["installation_country"]
        )

        if key not in unique_keys:
            # Optional: skip rows that have mostly blanks
            if any([row.get("real_emission_value"), row.get("default_emission_value"), row.get("buying_price")]):
                # Round benchmark value to 4 decimal places (German calculation standard)
                if row.get("bench_mark") is not None:
                    row["bench_mark"] = round(float(row["bench_mark"]), 4)

                from cbam.utils.benchmark import resolve_report_year
                report_year = (
                    resolve_report_year(row.get("external_good_year"))
                    or reporting_years.get(row.get("reporting_period"))
                )
                if row.get("good_name"):
                    default_rows = default_values_by_good.get(row.get("good_name"), [])
                    default_value = select_default_emission_value(default_rows, report_year)
                    if default_value is not None:
                        row["default_emission_value"] = default_value
                else:
                    eg_rows = default_values_by_external_good.get(row.get("name"), [])
                    default_value = select_default_emission_value(eg_rows, report_year)
                    if default_value is not None:
                        row["default_emission_value"] = default_value

                if default_value is not None and row.get("bench_mark") and row.get("cbam_factor") and row.get("raw_mass"):
                    try:
                        default_emission_cost = (
                            (default_value - (row["bench_mark"] * row["cbam_factor"])
                            - ((default_value * row.get("carbon_price_due", 0.0)) / ets_carbon_price if ets_carbon_price else 0))
                            * row["raw_mass"] * ets_carbon_price
                        )
                        row["default_emission_cost"] = default_emission_cost
                    except Exception:
                        pass

                final_data.append(row)
                unique_keys.add(key)

    return final_data


def get_good_default_emission_values(good_names):
    if not good_names:
        return {}
    rows = frappe.get_all(
        "Good Default Emission Value",
        filters={"parent": ["in", list(set(good_names))]},
        fields=[
            "parent",
            "cn_code",
            "description",
            "default_value_direct_emissions",
            "default_value_indirect_emissions",
            "default_value_total_emissions",
            "default_value_2026",
            "default_value_2027",
            "default_value_2028_onwards",
            "production_route_cbam_benchmark_indicator",
            "applicable_product",
        ]
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row.parent, []).append(row)
    return grouped


def get_external_good_default_emission_values(external_good_names):
    if not external_good_names:
        return {}
    rows = frappe.get_all(
        "External Good Default Emission Value",
        filters={"parent": ["in", list(set(external_good_names))]},
        fields=[
            "parent",
            "cn_code",
            "description",
            "default_value_direct_emissions",
            "default_value_indirect_emissions",
            "default_value_total_emissions",
            "default_value_2026",
            "default_value_2027",
            "default_value_2028_onwards",
            "production_route_cbam_benchmark_indicator",
            "applicable_product",
        ]
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row.parent, []).append(row)
    return grouped


def get_customs_import_year_map(customs_import_names):
    if not customs_import_names:
        return {}
    customs_imports = frappe.get_all(
        "Customs Import",
        filters={"name": ["in", list(set(customs_import_names))]},
        fields=["name", "year"]
    )
    year_names = list({row.year for row in customs_imports if row.year})
    year_values = frappe.get_all(
        "Year",
        filters={"name": ["in", year_names]},
        fields=["name", "year"]
    ) if year_names else []
    year_map = {row.name: row.year for row in year_values}
    return {row.name: year_map.get(row.year) for row in customs_imports}


def select_default_emission_value(rows, report_year):
    if not rows:
        return None
    applicable = [row for row in rows if row.get("applicable_product")]
    if len(applicable) > 1:
        return None
    if applicable:
        return pick_default_emission_value(applicable[0], report_year)
    if len(rows) == 1:
        return pick_default_emission_value(rows[0], report_year)
    return None


def get_declarant_for_user(user):
    result = frappe.db.get_all(
        "Declarant User",
        filters={"user": user},
        fields=["parent"],
        distinct=True
    )
    return [row.parent for row in result]  # List of declarant names


def get_chart(data, filters=None):
    if not data:
        return {}

    filters = filters or {}

    def to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    # Always group by article + supplier
    real_emission_map = defaultdict(float)
    default_emission_map = defaultdict(float)

    for row in data:
        article = row.get("article_number") or "Unknown"
        supplier = row.get("supplier") or "Unknown"

        if filters.get("supplier") and filters.get("supplier").strip():
            if supplier != filters.get("supplier").strip():
                continue  # only include rows matching selected supplier

        label = f"{article} ({supplier})"
        real_emission_map[label] += to_float(row.get("real_emission_cost"))
        default_emission_map[label] += to_float(row.get("default_emission_cost"))

    labels = list(real_emission_map.keys())
    real_values = [real_emission_map[label] for label in labels]
    standard_values = [default_emission_map[label] for label in labels]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Emission Cost based on Actual Emission Value",
                    "values": real_values
                },
                {
                    "name": "Default Emission Cost",
                    "values": standard_values
                }
            ]
        },
        "colors": ["#5e64ff", "#ff5858"]
    }


