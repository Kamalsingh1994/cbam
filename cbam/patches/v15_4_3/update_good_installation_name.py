import frappe

def execute():
    good_docs = frappe.get_all("Good", filters={"operating_company": ["!=", ""]}, fields=["name", "operating_company"])

    for good in good_docs:
        latest_cbam = frappe.db.get_value(
            "CBAM Emission Data",
            {"operating_company": good["operating_company"]},
            "installation_name",
            order_by="creation desc"
        )

        if latest_cbam:
            frappe.db.set_value("Good", good["name"], "installation_name", latest_cbam)
            frappe.db.commit()
