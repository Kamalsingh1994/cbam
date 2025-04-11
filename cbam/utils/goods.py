import frappe
import json
@frappe.whitelist()
def assign_emission(goods, emission):
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        doc.emission_data = emission
        doc.status = "Data Assigned"
        doc.save(ignore_permissions=True)

@frappe.whitelist()
def forward_goods(goods, supplier):
    doc = {}
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        doc.forwarded_from_supplier = doc.operating_company
        doc.supplier_name, doc.supplier_number = frappe.db.get_values("Operating Company", supplier, ["supplier_name", "supplier_number"])[0]
        doc.operating_company = supplier
        doc.status = "Forwarded"
        doc.save(ignore_permissions=True)
    if doc:
        doc.send_data_request()

@frappe.whitelist()
def submit_goods(goods):
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        if doc.status == "Data Assigned":
            doc.status = "Data Submitted"
            doc.save(ignore_permissions=True)
            doc.submit()


@frappe.whitelist()
def reject_goods(goods, reason=None):
    goods = json.loads(goods)
    _goods = ""
    for g in goods:
        parent_operating_company = {}
        doc = frappe.get_doc("Good", g)
        doc.rejected_from_supplier = doc.operating_company
        doc.rejection_reason = reason
        _parent_operating_company = frappe.db.get_value("Operating Company", doc.operating_company, "parent_operating_company")
        if _parent_operating_company: #if tier n+1 supplier
            parent_operating_company = frappe.get_doc("Operating Company", _parent_operating_company)
            doc.supplier_name, doc.supplier_number = parent_operating_company.supplier_name , parent_operating_company.supplier_number
            doc.status = "Data Requested"
        else:    
            doc.supplier_name, doc.supplier_number = "", ""
            doc.rejection_reason = reason
            doc.status = "Rejected"
        doc.save(ignore_permissions=True)
        if _goods:
            _goods = f"{_goods}, {doc.article_number}"
        else:
            _goods = doc.article_number

        dec = frappe.get_doc("Declarant", doc.declarant)

        email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "supplier_good_rejection_notification_template"))
        if _parent_operating_company:
            dec.email = parent_operating_company.main_contact_employee_email

        dec.goods = _goods
        email.send(dec)

@frappe.whitelist()
def split_goods(good, values):
    details = json.loads(values)
    good_doc = frappe.get_doc("Good", good)
    good_doc.add_split_good_details(details)
    good_doc.split_goods()
    frappe.msgprint("Goods splitted successfully.")