from frappe.utils.user import get_system_managers
import frappe
from cbam.cbam.page.various_cost_comparisons.various_cost_comparisons import get_report_data
from datetime import datetime

def send_missing_data_summary():
    year = str(datetime.now().year)
    filters = {}
    selected_filters = {"year": year}
    all_data = get_report_data(filters=filters, selected_filters=selected_filters, start=0, page_length=100000)["data"]
    # Check if "Missing" is in the status string (handles HTML formatted status)
    missing = [r for r in all_data if "Missing" in str(r.get('calculation_data_status', ''))]
    if not missing:
        return
    html = """
        <b>The following rows are missing calculation data:</b>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; min-width:900px;">
        <thead>
        <tr style="background:#f8f8f8;">
        <th>Supplier</th>
        <th>Article</th>
        <th>CN</th>
        <th>Country</th>
        <th>Year</th>
        <th>Missing Data</th>
        </tr>
        </thead>
        <tbody>
    """
    for r in missing:
        html += f"<tr>"
        html += f"<td>{r.get('supplier', '')}</td>"
        html += f"<td>{r.get('article_number', '')}</td>"
        html += f"<td>{r.get('cn_code', '')}</td>"
        html += f"<td>{r.get('installation_country', '')}</td>"
        html += f"<td>{year}</td>"
        html += f"<td style='color:#d97a12;font-weight:600'>{r.get('missing_data_reason', '')}</td>"
        html += f"</tr>"
    html += "</tbody></table>"
    recipients = get_system_managers()
    frappe.sendmail(recipients=recipients, subject="[CBAM] Missing Calculation Data", content=html)
    frappe.db.commit()
