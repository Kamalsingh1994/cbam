import frappe

def execute():
    for doctype in ["Good", "External Good"]:
        table = f"tab{doctype}"
        frappe.db.sql(f"""
            UPDATE `{table}`
            SET `raw_mass_tonne` = `raw_mass` / 1000
            WHERE `raw_mass` IS NOT NULL and `raw_mass_tonne` IS NULL
        """)
        frappe.db.commit()
