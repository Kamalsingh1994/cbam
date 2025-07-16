import frappe
import json

@frappe.whitelist()
def get_table_data(doctype, fields, filters=None, start=0, page_length=50):

    filters = json.loads(filters) if filters else {}
    fields = json.loads(fields) if isinstance(fields, str) else fields
    start = int(start or 0)
    page_length = int(page_length or 50)

    data = frappe.get_all(doctype, fields=fields, filters=filters, start=start, page_length=page_length, order_by="price_date desc")

    total_count = frappe.db.count(doctype, filters=filters)
    
    return {"data": data, "total_count": total_count}
