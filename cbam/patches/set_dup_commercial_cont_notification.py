import frappe

def execute():
    frappe.db.set_single_value("CBAM Settings", "Duplicate Commercial Contact")