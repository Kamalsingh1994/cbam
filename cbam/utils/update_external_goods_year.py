# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

"""
Script to directly update year field for existing External Goods based on CBAM Report dates
Run with: bench --site [site-name] execute cbam.utils.update_external_goods_year.update_years
"""

import frappe
from frappe.utils import getdate
from datetime import datetime


def get_or_create_year(year_value):
    """Get or create Year record for a given year value"""
    if not year_value:
        return None
    
    # Year doctype uses autoname: field:year, so name is the year value itself
    year_name = str(year_value)
    
    # Check if Year exists
    if frappe.db.exists("Year", year_name):
        return year_name
    
    # Create Year record
    try:
        year_doc = frappe.get_doc({
            "doctype": "Year",
            "year": int(year_value)
        })
        year_doc.insert(ignore_permissions=True)
        return year_doc.name
    except Exception as e:
        frappe.log_error(f"Error creating Year {year_value}: {str(e)}", "Year Creation Error")
        return None


def update_years():
    """
    Directly update year field for existing External Goods based on their CBAM Report dates
    Updates database directly using SQL
    """
    # First, ensure the year column exists in the database
    table_name = "tabExternal Good"
    columns = frappe.db.sql(f"SHOW COLUMNS FROM `{table_name}` LIKE 'year'", as_dict=True)
    
    if not columns:
        print("⚠️  'year' column doesn't exist. Adding it to the database...")
        try:
            # Add year column as Link to Year doctype
            frappe.db.sql(f"""
                ALTER TABLE `{table_name}`
                ADD COLUMN `year` VARCHAR(140) NULL
            """)
            frappe.db.commit()
            print("✓ Added 'year' column to External Good table")
        except Exception as e:
            print(f"✗ Error adding column: {str(e)}")
            return
    
    # Get all External Goods with report_id using SQL (more reliable)
    external_goods = frappe.db.sql("""
        SELECT name, report_id 
        FROM `tabExternal Good`
        WHERE report_id IS NOT NULL 
        AND report_id != ''
        AND (year IS NULL OR year = '')
    """, as_dict=True)
    
    if not external_goods:
        print("No External Goods found that need year update")
        return
    
    print(f"Found {len(external_goods)} External Goods to update")
    
    updated = 0
    errors = 0
    
    for eg in external_goods:
        try:
            # Get CBAM Report
            cbam_report = frappe.get_doc("CBAM Report", eg.report_id)
            
            # Extract year from from_date (preferred) or to_date
            date_to_use = cbam_report.from_date or cbam_report.to_date
            if not date_to_use:
                errors += 1
                print(f"  ⚠️  External Good {eg.name}: CBAM Report {eg.report_id} has no from_date or to_date")
                continue
            
            # Parse date and extract year
            if isinstance(date_to_use, str):
                date_obj = datetime.strptime(date_to_use.split()[0], '%Y-%m-%d')
            else:
                date_obj = getdate(date_to_use)
            
            year_value = date_obj.year
            
            # Get or create Year record
            year = get_or_create_year(year_value)
            if not year:
                errors += 1
                print(f"  ⚠️  External Good {eg.name}: Failed to get/create Year {year_value}")
                continue
            
            # Update External Good directly in database using SQL
            frappe.db.sql("""
                UPDATE `tabExternal Good`
                SET `year` = %s
                WHERE name = %s
            """, (year, eg.name))
            updated += 1
            print(f"  ✓ Updated {eg.name} with year {year_value}")
            
        except Exception as e:
            errors += 1
            error_msg = str(e)[:500]
            print(f"  ✗ Error updating {eg.name}: {error_msg}")
            title = f"Error updating year for Ext Good {eg.name}"[:140]
            frappe.log_error(title, f"External Good: {eg.name}\nReport: {eg.report_id}\nError: {error_msg}")
    
    # Commit all changes
    frappe.db.commit()
    
    print(f"\n✅ Update complete: {updated} updated, {errors} errors, {len(external_goods)} total")


if __name__ == "__main__":
    update_years()
