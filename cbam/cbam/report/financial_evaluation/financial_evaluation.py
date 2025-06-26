# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from collections import defaultdict

# @frappe.whitelist()
# def get_ets_prices():
#     return frappe.get_all("ETS Carbon Price", fields=["price"], order_by="creation desc")

@frappe.whitelist()
def get_ets_prices(price_type=None, from_date=None, to_date=None):
    conditions = []
    values = []

    if price_type:
        conditions.append("ets_price_type = %s")
        values.append(price_type)

    if from_date:
        conditions.append("price_date >= %s")
        values.append(from_date)

    if to_date:
        conditions.append("price_date <= %s")
        values.append(to_date)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    data = frappe.db.sql(f"""
        SELECT DISTINCT price FROM `tabETS Carbon Price`
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
			"fieldname": "standard_emission_value",
			"fieldtype": "Data",
			"label": "Standard Emission Value"
		},
		{
			"fieldname": "real_emission_cost",
			"fieldtype": "Data",
			"label": "Emission Cost based on Actual Emission Value"
		},
        {
			"fieldname": "standard_emission_cost",
			"fieldtype": "Data",
			"label": "Emission Cost based on Standard Emission Value"
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
            IFNULL(e.emission_value,0.0) AS standard_emission_value,
            IFNULL(b.bench_mark,0.0) AS bench_mark,
            eg.reporting_period,
            IFNULL(cbam.cbam_factor,0.0) AS cbam_factor,
            {ets_carbon_price} as ets_carbon_price,
            ((
                IFNULL(eg.specific_direct_embedded_emissions,0) - (IFNULL(cbam.cbam_factor,0) * IFNULL(b.bench_mark,0))
                - ((IFNULL(eg.specific_direct_embedded_emissions,0) * IFNULL(eg.carbon_price_due, 0)) / {ets_carbon_price})
            ) * IFNULL(eg.raw_mass, 0) * {ets_carbon_price}) AS real_emission_cost,

            ((
                IFNULL(e.emission_value, 0.0) 
                - (IFNULL(b.bench_mark, 0.0) * IFNULL(cbam.cbam_factor, 0.0))
                - ((IFNULL(e.emission_value, 0.0) * IFNULL(eg.carbon_price_due, 0.0)) / {ets_carbon_price})
            ) 
            * IFNULL(eg.raw_mass, 0.0) * {ets_carbon_price}) AS standard_emission_cost

        FROM `tabExternal Good` eg
        LEFT JOIN `tabStandard Emission Value` e 
            ON eg.cn_code = e.cn_code AND eg.installation_country = e.country
        LEFT JOIN `tabCN Code Bench Mark Emission Value` b 
            ON b.cn_code = eg.cn_code

        LEFT JOIN `tabReporting Period` rp
            ON rp.reporting_period = eg.reporting_period

        LEFT JOIN `tabCBAM Factor` cbam
            ON cbam.name = rp.parent AND rp.parenttype = 'CBAM Factor'

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
            IFNULL(e.emission_value,0.0) AS standard_emission_value,
            IFNULL(b.bench_mark,0.0) AS bench_mark,
            g.internal_customs_import_number as reporting_period,
            IFNULL(cbam.cbam_factor,0.0) AS cbam_factor,
            {ets_carbon_price} as ets_carbon_price,
            ((
                IFNULL(g.specific_direct_embedded_emissions,0.0) - (IFNULL(cbam.cbam_factor,0.0) * IFNULL(b.bench_mark,0.0))
                - ((IFNULL(g.specific_direct_embedded_emissions,0.0) * IFNULL(g.carbon_price_due,0.0)) / {ets_carbon_price})
            ) * IFNULL(g.raw_mass,0.0) * {ets_carbon_price}) AS real_emission_cost,

            ((
                IFNULL(e.emission_value, 0.0)
                - (IFNULL(b.bench_mark, 0.0) * IFNULL(cbam.cbam_factor, 0.0))
                - ((IFNULL(e.emission_value, 0.0) * IFNULL(g.carbon_price_due, 0.0)) / {ets_carbon_price})
            )
            * IFNULL(g.raw_mass, 0.0) * {ets_carbon_price}) AS standard_emission_cost

        FROM `tabGood` g

        LEFT JOIN `tabStandard Emission Value` e 
            ON g.cn_code = e.cn_code AND g.installation_country = e.country
        LEFT JOIN `tabCN Code Bench Mark Emission Value` b 
            ON b.cn_code = g.cn_code
 
        LEFT JOIN `tabReporting Period` rp
            ON rp.reporting_period = g.internal_customs_import_number
        LEFT JOIN `tabCBAM Factor` cbam
            ON cbam.name = rp.parent AND rp.parenttype = 'CBAM Factor'

        {where_sql}
    """, as_dict=1)

    unique_keys = set()
    final_data = []

    for row in data:
        key = (
            row["cn_code"], row["article_number"], row["supplier"], row["installation_country"]
        )

        if key not in unique_keys:
            # Optional: skip rows that have mostly blanks
            if any([row.get("real_emission_value"), row.get("standard_emission_value"), row.get("buying_price")]):
                final_data.append(row)
                unique_keys.add(key)

    return final_data



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
    standard_emission_map = defaultdict(float)

    for row in data:
        article = row.get("article_number") or "Unknown"
        supplier = row.get("supplier") or "Unknown"

        if filters.get("supplier") and filters.get("supplier").strip():
            if supplier != filters.get("supplier").strip():
                continue  # only include rows matching selected supplier

        label = f"{article} ({supplier})"
        real_emission_map[label] += to_float(row.get("real_emission_cost"))
        standard_emission_map[label] += to_float(row.get("standard_emission_cost"))

    labels = list(real_emission_map.keys())
    real_values = [real_emission_map[label] for label in labels]
    standard_values = [standard_emission_map[label] for label in labels]

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
                    "name": "Standard Emission Cost",
                    "values": standard_values
                }
            ]
        },
        "colors": ["#5e64ff", "#ff5858"]
    }


