import frappe

def execute():
    report_name = "Financial Evaluation"
    roles_to_remove = ["Commercial Contact", "CBAM Representative"]

 # Replace with exact report name
    report = frappe.db.get("Report", {"name": report_name, "report_type": "Script Report"})
    if report:
        frappe.db.set_value("Report", report_name, "disabled", 1)
        # Remove only the specified roles
        frappe.db.sql("""
            DELETE FROM `tabHas Role`
            WHERE parent = %s AND parenttype = 'Report' AND role IN %s
        """, (report_name, tuple(roles_to_remove)))

        frappe.db.commit()
