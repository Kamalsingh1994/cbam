import frappe

def execute():
    # Fetch records with customs_tariff_number > 8 characters
    goods = frappe.db.sql("""
        SELECT name, cn_code
        FROM `tabGood`
        WHERE CHAR_LENGTH(cn_code) > 8
    """, as_dict=True)

    for good in goods:
        number = good.get("cn_code")

        # Only process valid numeric codes longer than 8 digits
        if number and number.isdigit() and len(number) > 8:
            prefix = number[:8]
            frappe.log_error("prefix: " + prefix, "Truncate CN Code")
            # Ensure CN Code exists, or create it
            if not frappe.db.exists("CN Code", prefix):
                frappe.log_error("121 Creating CN Code")
                frappe.get_doc({
                    "doctype": "CN Code",
                    "cn_code": prefix
                }).insert(ignore_permissions=True)
                frappe.db.commit()
    
            # Update Good's cn_code to the 8-digit value
            frappe.db.set_value("Good", good["name"], {
                "cn_code": prefix
            }, update_modified=False)

            frappe.db.commit()
