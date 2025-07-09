import frappe
import json


@frappe.whitelist()
def get_supplier():
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles() and not "Commercial Contact" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}

    return frappe.get_value("Operating Company", filters, [
        "name", "supplier_name", "company_phone_number", "company_email",
        "street_and_number", "zip_code", "city", "country", "cbam_representive_last_name", "cbam_representive_employee_email", "cbam_representive_employee_position", "cbam_representive_employee_first_name", "cbam_representive_employee_phone_number"
    ], as_dict=True) or {}


@frappe.whitelist()
def confirm_details(values):
    values = json.loads(values)
    doc = frappe.get_doc("Operating Company", get_supplier())
    doc.update(values)
    if values.get('varify'):
        doc.status = "Company Verified"
    doc.save(ignore_permissions=True)



@frappe.whitelist()
def get_supplier_details(sup=None):
    if not sup:
        sup = get_supplier()
    if frappe.db.exists("Operating Company", sup):
        return frappe.get_doc("Operating Company", sup).as_dict()
    


@frappe.whitelist()
def get_child_suppliers(filters={}):
    parent_company = get_supplier()
    _filters = {"parent_operating_company": parent_company}
    if filters:
        _filters.update(json.loads(filters))
   
    return frappe.db.get_all("Operating Company", _filters, ["name as value", "supplier_name as label"])
    