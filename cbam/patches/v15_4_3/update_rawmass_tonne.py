import frappe

def execute():
    for doctype in ["Good", "External Good"]:
        table = f"tab{doctype}"

        try:
            frappe.db.sql(f"""
                UPDATE `{table}`
                SET `raw_mass_tonne` = `raw_mass` / 1000
                WHERE `raw_mass` IS NOT NULL
                  AND `raw_mass_tonne` IS NULL
                  AND CAST(`raw_mass` AS DECIMAL) IS NOT NULL
            """)
            frappe.db.commit()
        except Exception as e:
            frappe.logger().error(f"Failed updating {doctype}: {e}")
