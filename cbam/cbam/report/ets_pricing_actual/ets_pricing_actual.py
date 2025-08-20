# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {"label": "Name", "fieldname": "name", "fieldtype": "Link", "options":"ETS Carbon Price", "width": 320},
        {"label": "ETS Price Type", "fieldname": "ets_price_type", "fieldtype": "Data", "width": 150},
        {"label": "Creation Date", "fieldname": "creation_date", "fieldtype": "Datetime", "width": 180},
        {"label": "Price Date", "fieldname": "price_date", "fieldtype": "Date", "width": 180},
        {"label": "ETS Carbon Price", "fieldname": "price", "fieldtype": "Currency", "width": 180},
        {"label": "Source", "fieldname": "carbon_price_source", "fieldtype": "Data", "width": 180}
    ]

def get_data(filters):
    conditions = {"ets_price_type": "Spot Price"}

    # Apply date filter only if both from and to dates are provided
    if filters.get("from_date") and filters.get("to_date"):
        conditions["price_date"] = ["between", [filters["from_date"], filters["to_date"]]]

    return frappe.get_all(
        "ETS Carbon Price",
        filters=conditions,
        fields=["name", "price_date", "price", "ets_price_type", "carbon_price_source", "creation_date"],
        order_by="price_date asc"
    )


def get_chart(data):
    return {
        "data": {
            "labels": [d["price_date"] for d in data],
            "datasets": [{
                "name": "ETS Carbon Price",
                "values": [d["price"] for d in data]
            }]
        },
        "type": "line"
    }

