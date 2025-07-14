import frappe

def execute():
    if frappe.db.table_exists("Good") and frappe.db.table_exists("CN Code"):
        result = frappe.db.sql("""
            SELECT DISTINCT customs_tariff_number
            FROM `tabGood`
            WHERE customs_tariff_number IS NOT NULL AND customs_tariff_number != ''
        """, as_dict=True)

        codes = [row.customs_tariff_number.strip() for row in result]
        frappe.enqueue(
            method=insert_cn_codes_in_background,
            queue='default',
            timeout=600,
            codes=codes,
            now=False
        )
        print(f"Queued background job to insert CN Codes ({len(codes)} total).")

def insert_cn_codes_in_background(codes):
    created = 0
    skipped = 0

    for code in codes:
        if not (code.isdigit() and len(code) == 8):
            skipped += 1
            continue

        if not frappe.db.exists("CN Code", {"cn_code": code}):
            frappe.get_doc({
                "doctype": "CN Code",
                "cn_code": code
            }).insert(ignore_permissions=True)
            created += 1

    frappe.log_error("cn_code_import_complete", {
        "message": f"Inserted {created} CN Codes. Skipped {skipped} invalid entries."
    })
