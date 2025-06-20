# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from collections import defaultdict

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters=filters)
    return columns, data, None

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
			"label": "Real Emission Value"
		},
        {
			"fieldname": "standard_emission_value",
			"fieldtype": "Data",
			"label": "Standard Emission Value"
		},
        {
			"fieldname": "ets_carbon_price",
			"fieldtype": "Data",
			"label": "ETS Carbon Price"
		},
		{
			"fieldname": "real_emission_cost",
			"fieldtype": "Data",
			"label": "Real Emission Cost"
		},
        {
			"fieldname": "standard_emission_cost",
			"fieldtype": "Data",
			"label": "Standard Emission Cost"
		},
		{
			"fieldname": "carbon_price_due",
			"fieldtype": "Data",
			"label": "Carbon Price Due"
		}
	]
             
    return columns

def get_data(filters=None):
    filters = filters or {}

    ets_carbon_price = frappe.db.get_value(
        "ETS Carbon Price",
        {"ets_price_type": "Actual"},
        "price",
        order_by="date desc"
    ) or 0

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
        where_clauses.append(f"(g.reporting_period IN ({reporting_period_list}))")
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
            eg.raw_mass,
            eg.mass_per_article,
            eg.buying_price_per_mass AS buying_price,
            eg.carbon_price_due,
            eg.real_emissions_value AS real_emission_value,
            e.emission_value AS standard_emission_value,
            b.bench_mark,
            eg.reporting_period,
            {ets_carbon_price} AS ets_carbon_price,
            (eg.raw_mass * eg.real_emissions_value * {ets_carbon_price}) AS real_emission_cost,
            (eg.raw_mass * e.emission_value * {ets_carbon_price}) AS standard_emission_cost
        FROM `tabExternal Good` eg
        LEFT JOIN `tabStandard Emission Value` e 
            ON eg.cn_code = e.cn_code AND eg.installation_country = e.country
        LEFT JOIN `tabCN Code Bench Mark` b 
            ON b.cn_code = eg.cn_code
		{where_sql_eg}
        
        UNION ALL

        SELECT 
            g.cn_code,
            g.article_number,
            g.supplier_name AS supplier,
            g.installation_country,	
            g.raw_mass,
            g.mass_per_article,
            g.buying_price,
            g.carbon_price_due,
            g.specific_direct_embedded_emissions AS real_emission_value,
            e.emission_value AS standard_emission_value,
            b.bench_mark,
            g.internal_customs_import_number as reporting_period,
            {ets_carbon_price} AS ets_carbon_price,
            (g.raw_mass * g.specific_direct_embedded_emissions * {ets_carbon_price}) AS real_emission_cost,
            (g.raw_mass * e.emission_value * {ets_carbon_price}) AS standard_emission_cost
        FROM `tabGood` g
        LEFT JOIN `tabStandard Emission Value` e 
            ON g.cn_code = e.cn_code AND g.installation_country = e.country
        LEFT JOIN `tabCN Code Bench Mark` b 
            ON b.cn_code = g.cn_code
        {where_sql}
    """, as_dict=1)

    return data


def get_declarant_for_user(user):
    result = frappe.db.get_all(
        "Declarant User",
        filters={"user": user},
        fields=["parent"],
        distinct=True
    )
    return [row.parent for row in result]  # List of declarant names
