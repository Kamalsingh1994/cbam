import frappe

@frappe.whitelist()
def get_links(doctype):
    return [d.name for d in frappe.get_list(doctype)]

@frappe.whitelist()
def get_installation(emission):
    return frappe.db.get_value("CBAM Emission Data Item", {"emission_data": emission}, "parent")