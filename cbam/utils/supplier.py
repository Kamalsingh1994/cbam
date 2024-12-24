import frappe
import json


@frappe.whitelist()
def get_supplier():
    return frappe.get_doc("Operating Company", frappe.db.get_value("User Permission", {"user": frappe.session.user, "allow": "Operating Company"}, "for_value")).as_dict()

@frappe.whitelist()
def confirm_details(values):
    values = json.loads(values)
    doc = frappe.get_doc("Operating Company", frappe.db.get_value("User Permission", {"user": frappe.session.user, "allow": "Operating Company"}, "for_value"))
    doc.update(values)
    doc.status = "Company Verified"
    doc.save(ignore_permissions=True)