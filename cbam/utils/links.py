import frappe

@frappe.whitelist()
def get_links(doctype, filters={}, fields=[]):
    if not fields:
        fields = ["name as value", "name as label"]
    return frappe.get_list(doctype, fields=fields, filters=filters)

@frappe.whitelist()
def get_installation(emission):
    return frappe.db.get_value("CBAM Emission Data Item", {"emission_data": emission}, "parent")