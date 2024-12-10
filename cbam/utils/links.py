import frappe

@frappe.whitelist()
def get_links(doctype):
    return [d.name for d in frappe.get_list(doctype)]