import frappe
import json

@frappe.whitelist()
def create_new_doc(doc):
    doc = json.loads(doc)
    return frappe.get_doc(doc).insert()