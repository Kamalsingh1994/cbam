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
			"fieldname": "land",
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
			"fieldtype": "Small Text",
			"label": "Good Description"
		},
		{
			"fieldname": "buying_price",
			"fieldtype": "Data",
			"label": "Buying Price"
		},
		{
			"fieldname": "carbon_price_due",
			"fieldtype": "Data",
			"label": "Carbon Price Due"
		}
	]
             
    return columns

def get_data():
    data = frappe.db.sql("""
        SELECT 
            eg.cn_code AS cn_number,
            eg.article_no AS article_number,
            eg.supplier,
            eg.land,
            eg.mass_kg AS raw_mass,
            eg.mass_per_article,
            eg.buying_price_per_mass AS buying_price,
            eg.carbon_price_due
        FROM `tabExternal Good` eg

        UNION ALL

        SELECT 
            g.customs_tariff_number AS cn_number,
            g.article_number,
            g.supplier_name AS supplier,
            g.country_of_origin AS land,
            g.raw_mass,
            g.mass_per_article,
            g.buying_price,
            g.carbon_price_due
        FROM `tabGood` g
    """, as_dict=1)

    return data


