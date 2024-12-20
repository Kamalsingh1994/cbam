import frappe

@frappe.whitelist()
def get_links(doctype, fields = []):
    if not fields:
        fields = ["name as label", "name as value"]
    return frappe.get_list(doctype, fields=fields)

@frappe.whitelist()
def get_installation(emission):
    return frappe.db.get_value("CBAM Emission Data Item", {"emission_data": emission}, "parent")