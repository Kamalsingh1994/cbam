import frappe
import json


@frappe.whitelist()
def get_supplier():
    return frappe.db.get_value("Operating Company", {"commercial_contact_user": frappe.session.user}, "name")

@frappe.whitelist()
def confirm_details(values):
    values = json.loads(values)
    doc = frappe.get_doc("Operating Company", {"commercial_contact_user": frappe.session.user})
    doc.update(values)
    if values.get('verify'):
        doc.status = "Company Verified"
    doc.save(ignore_permissions=True)



@frappe.whitelist()
def get_supplier_details(sup):
    if frappe.db.exists("Operating Company", sup):
        return frappe.get_doc("Operating Company", sup).as_dict()