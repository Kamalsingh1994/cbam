import frappe

@frappe.whitelist()
def get_fields(doctype):
    return frappe.get_doc("Dialog Form", doctype).get_fields()