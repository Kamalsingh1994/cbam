import frappe

def execute():
    if frappe.db.has_column("Good", "cn_code"):
        frappe.db.sql("""
            UPDATE `tabGood`
            SET cn_code = customs_tariff_number
            WHERE customs_tariff_number IS NOT NULL AND customs_tariff_number != ''
        """)
