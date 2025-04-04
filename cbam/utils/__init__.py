import frappe
import json

@frappe.whitelist()
def create_new_doc(doc):
    doc = json.loads(doc)
    return frappe.get_doc(doc).insert(ignore_permissions=True)

@frappe.whitelist()
def update_doc(doc):
    doc = json.loads(doc)
    if not frappe.db.exists(doc.get("doctype"), doc.get("name")):
        frappe.throw("Document doesn't exist")
    
    existing_doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))
    existing_doc.update(doc)
    existing_doc.save(ignore_permissions=True)
    return existing_doc

@frappe.whitelist()
def get_supplier():
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}
    if frappe.db.exists("Operating Company", filters):
        return frappe.db.get_value("Operating Company", filters, "name")
    
@frappe.whitelist()
def get_field_options(doc, fieldname):
    meta = frappe.get_meta(doc)
    field = meta.get_field(fieldname)
    if field and field.options:
        return field.options.split("\n")
    return []