import frappe

def execute():
    """Remove old pages: financial_evaluation_report and cbam_report_cost_forecast"""
    
    pages_to_remove = [
        "financial-evaluation-report",
        "cbam-report-cost-forecast"
    ]
    
    for page_name in pages_to_remove:
        if frappe.db.exists("Page", page_name):
            frappe.delete_doc("Page", page_name, force=True)
            print(f"Deleted page: {page_name}")
        else:
            print(f"Page not found: {page_name}") 