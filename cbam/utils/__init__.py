import frappe
import json

@frappe.whitelist()
def create_new_doc(doc):
    doc = json.loads(doc)
    return frappe.get_doc(doc).insert(ignore_permissions=True)


@frappe.whitelist()
def get_supplier():
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}
    if frappe.db.exists("Operating Company", filters):
        return frappe.db.get_value("Operating Company", filters, "name")