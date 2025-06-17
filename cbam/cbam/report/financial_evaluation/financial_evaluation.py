# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from collections import defaultdict

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data, None

def get_columns():
    columns =  [
		{
			"fieldname": "cn_number",
			"fieldtype": "Data",
			"label": "CN Code"
		},
		{
			"fieldname": "article_number",
			"fieldtype": "Data",
			"label": "Article Number",
		},
		{
			"fieldname": "supplier",
			"fieldtype": "Data",
			"label": "Supplier"
		},
        {
			"fieldname": "country",
			"fieldtype": "Data",
			"label": "Country"
		},
		{
			"fieldname": "raw_mass",
			"fieldtype": "Data",
			"label": "Mass [kg]"
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

def get_data():
    
    ets_carbon_price = frappe.db.get_value(
        "ETS Carbon Price",
        {"ets_price_type": "Actual"},
        "price",
        order_by="date desc"
    ) or 0
    
    user = frappe.session.user
    declarants = get_declarant_for_user(user)
    
    # If user has Declarant restrictions
    good_filter_clause = ""
    if declarants:
        # Safely format for SQL IN clause
        declarant_list = ', '.join(f"'{d}'" for d in declarants)
        good_filter_clause = f" where g.declarant in ({declarant_list})"
        
    
    data = frappe.db.sql(f"""
		SELECT 
			eg.cn_code AS cn_number,
			eg.article_no AS article_number,
			eg.supplier,
			eg.shipping_country_name AS country,
			eg.raw_mass,
			eg.mass_per_article,
			eg.buying_price_per_mass AS buying_price,
			eg.carbon_price_due,
			eg.real_emissions_value AS real_emission_value,
			e.emission_value AS standard_emission_value,
			b.bench_mark,
			{ets_carbon_price} AS ets_carbon_price,
			(eg.raw_mass * eg.real_emissions_value * {ets_carbon_price}) AS real_emission_cost,
			(eg.raw_mass * e.emission_value * {ets_carbon_price}) AS standard_emission_cost
		FROM `tabExternal Good` eg
		LEFT JOIN `tabStandard Emission Value` e 
			ON eg.cn_code = e.cn_code AND eg.shipping_country_name = e.country
		LEFT JOIN `tabCN Code Bench Mark` b 
			ON b.cn_code = eg.cn_code

		UNION ALL

		SELECT 
			g.cn_code AS cn_number,
			g.article_number,
			g.supplier_name AS supplier,
			g.country_of_origin AS country,	
			g.raw_mass,
			g.mass_per_article,
			g.buying_price,
			g.carbon_price_due,
			g.specific_direct_embedded_emissions AS real_emission_value,
			e.emission_value AS standard_emission_value,
			b.bench_mark,
			{ets_carbon_price} AS ets_carbon_price,
			(g.raw_mass * g.specific_direct_embedded_emissions * {ets_carbon_price}) AS real_emission_cost,
			(g.raw_mass * e.emission_value * {ets_carbon_price}) AS standard_emission_cost
		FROM `tabGood` g
		LEFT JOIN `tabStandard Emission Value` e 
			ON g.cn_code = e.cn_code AND g.country_of_origin = e.country
		LEFT JOIN `tabCN Code Bench Mark` b 
			ON b.cn_code = g.cn_code
		{good_filter_clause}
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
