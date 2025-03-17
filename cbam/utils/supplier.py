import frappe
import json


@frappe.whitelist()
def get_supplier():
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles() and not "Commercial Contact" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}
    return frappe.db.get_value("Operating Company", filters, "name")

@frappe.whitelist()
def confirm_details(values):
    values = json.loads(values)
    doc = frappe.get_doc("Operating Company", {"commercial_contact_user": frappe.session.user})
    doc.update(values)
    if values.get('verify'):
        doc.status = "Company Verified"
    doc.save(ignore_permissions=True)



@frappe.whitelist()
def get_supplier_details():
    sup = get_supplier()
    if frappe.db.exists("Operating Company", sup):
        return frappe.get_doc("Operating Company", sup).as_dict()
    


@frappe.whitelist()
def get_child_suppliers():
    parent_company = get_supplier()
    return frappe.db.get_all("Operating Company", {"parent_operating_company": parent_company}, ["name as value", "supplier_name as label"])
    