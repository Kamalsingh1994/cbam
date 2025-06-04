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
			"label": "CN Number"
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
			"label": "Land"
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
			"fieldname": "carbon_price_due",
			"fieldtype": "Data",
			"label": "Carbon Price Due"
		},
        {
			"fieldname": "ets_carbon_price",
			"fieldtype": "Data",
			"label": "ETS Carbon Price"
		},
	]
             
    return columns

def get_data():
    
<<<<<<< Updated upstream
    ets_carbon_price = frappe.db.get_value(
        "ETS Carbon Price",
        {"ets_price_type": "Actual"},
        "price",
        order_by="date desc"
    ) or 0
    
=======
    user = frappe.session.user
    declarants = get_declarant_for_user(user)

    # If user has Declarant restrictions
    good_filter_clause = ""
    if declarants:
        # Safely format for SQL IN clause
        declarant_list = ', '.join(f"'{d}'" for d in declarants)
        good_filter_clause = f"WHERE g.declarant IN ({declarant_list})"
        
>>>>>>> Stashed changes
    data = frappe.db.sql(f"""
        SELECT 
            eg.cn_code AS cn_number,
            eg.article_no AS article_number,
            eg.supplier,
            eg.country,
            eg.raw_mass AS raw_mass,
            eg.mass_per_article,
            eg.buying_price_per_mass AS buying_price,
            eg.carbon_price_due,
            eg.real_emissions_value as real_emission_value,
			e.emission_value,
<<<<<<< Updated upstream
        	b.bench_mark,
			{ets_carbon_price} AS ets_carbon_price
=======
        	b.bench_mark
>>>>>>> Stashed changes
        FROM `tabExternal Good` eg
		join `tabStandard Emission Value` as e 
        on eg.cn_code = e.cn_code and eg.country = e.country
		join `tabCN Code Bench Mark` as b
<<<<<<< Updated upstream
		on b.cn_code = eg.cn_code              
=======
		on b.cn_code = eg.cn_code
        
>>>>>>> Stashed changes
        UNION ALL
        SELECT 
            g.customs_tariff_number AS cn_number,
            g.article_number,
            g.supplier_name AS supplier,
            g.country_of_origin AS country,
            g.raw_mass,
            g.mass_per_article,
            g.buying_price,
            g.carbon_price_due,
			e.emission_value,
            g.specific_direct_embedded_emissions as real_emission_value,
<<<<<<< Updated upstream
            b.bench_mark,
            {ets_carbon_price} AS ets_carbon_price
=======
            b.bench_mark
>>>>>>> Stashed changes
        FROM `tabGood` g 
			join `tabStandard Emission Value`
			as e on g.customs_tariff_number = e.cn_code and g.country_of_origin = e.country
			join `tabCN Code Bench Mark` as b
			on b.cn_code = g.customs_tariff_number
<<<<<<< Updated upstream
=======
        {good_filter_clause}
>>>>>>> Stashed changes
    """, as_dict=1)

    return data

<<<<<<< Updated upstream


=======
def get_declarant_for_user(user):
    result = frappe.db.get_all(
        "Declarant User",
        filters={"user": user},
        fields=["parent"],
        distinct=True
    )
    return [row.parent for row in result]  # List of declarant names
>>>>>>> Stashed changes
