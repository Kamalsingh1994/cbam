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


import frappe
import json
@frappe.whitelist()
def forward_goods(supplier, goods):
    goods = json.loads(goods)
    for g in goods:
        
        doc = frappe.get_doc("Good", g)
        doc.forward_to_supplier = supplier
        doc.status = "Forwarded"
        doc.save(ignore_permissions=True)
1
