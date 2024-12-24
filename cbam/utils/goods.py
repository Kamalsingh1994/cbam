import frappe
import json
@frappe.whitelist()
def assign_emission(emission, goods):
    goods = json.loads(goods)
    for g in goods:
        
        doc = frappe.get_doc("Good", g)
        doc.emission_data = emission
        doc.status = "Data Assigned"
        doc.save(ignore_permissions=True)



@frappe.whitelist()
def forward_goods(supplier, goods):
    goods = json.loads(goods)
    for g in goods:
        
        doc = frappe.get_doc("Good", g)
        doc.forwarded_from_supplier = doc.operating_company
        doc.supplier_name, doc.supplier_number = frappe.db.get_values("Operating Company", supplier, ["supplier_name", "supplier_number"])[0]
        doc.operating_company = supplier
        doc.status = "Forwarded"
        doc.save(ignore_permissions=True)






@frappe.whitelist()
def submit_goods(goods):
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        if doc.status == "Data Assigned":
            doc.status = "Data Submitted"
            doc.save(ignore_permissions=True)


@frappe.whitelist()
def reject_goods(goods, reason=None):
    goods = json.loads(goods)
    for g in goods:
        
        doc = frappe.get_doc("Good", g)
        doc.rejected_from_supplier = doc.operating_company
        doc.supplier_name, doc.supplier_number = "", ""
        doc.rejection_reason = reason
        doc.status = "Rejected"
        doc.save(ignore_permissions=True)