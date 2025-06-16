# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "ETS Carbon Price", "width": 320},
        {"label": "ETS Price Type", "fieldname": "ets_price_type", "fieldtype": "Data", "width": 150},
        {"label": "Creation Date", "fieldname": "creation_date", "fieldtype": "Datetime", "width": 180},
        {"label": "Price Date", "fieldname": "price_date", "fieldtype": "Date", "width": 180},
        {"label": "ETS Carbon Price", "fieldname": "price", "fieldtype": "Currency", "width": 180},
        {"label": "Source", "fieldname": "carbon_price_source", "fieldtype": "Data", "width": 180}
    ]

def get_data(filters):
    conditions = {"ets_price_type": "Prediction"}

    # Optional date filtering
    if filters.get("from_date") and filters.get("to_date"):
        conditions["price_date"] = ["between", [filters["from_date"], filters["to_date"]]]

    return frappe.get_all(
        "ETS Carbon Price",
        filters=conditions,
        fields=["name", "price_date", "price", "ets_price_type", "carbon_price_source", "creation_date"],
        order_by="price_date asc, creation_date asc"
    )

def get_chart(data):
    if not data:
        return {}

    from collections import defaultdict

    # Group all prices per date
    date_map = defaultdict(list)
    for row in data:
        date_map[row["price_date"]].append(row["price"])

    sorted_dates = sorted(date_map.keys())
    average_values = [sum(v)/len(v) for v in [date_map[d] for d in sorted_dates]]

    avg_line = {
        "name": "Average Price",
        "type": "line",
        "values": average_values
    }

    return {
        "type": "axis-mixed",
        "data": {
            "labels": sorted_dates,
            "datasets": [avg_line]
        },
        "colors": ["#0066cc"]
    }
