import frappe

def execute():
    # Fetch records with customs_tariff_number > 8 chars
    goods = frappe.db.sql("""
        SELECT name, customs_tariff_number
        FROM `tabGood`
        WHERE CHAR_LENGTH(customs_tariff_number) > 8
    """, as_dict=True)

    for good in goods:
        number = good.get("customs_tariff_number")

        if number and number.isdigit() and len(number) > 8:
            prefix = number[:8]

            # Update both fields
            frappe.db.set_value("Good", good["name"], {
                "customs_tariff_number": prefix
            }, update_modified=False)

    frappe.db.commit()

