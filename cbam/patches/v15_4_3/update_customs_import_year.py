# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime

def execute():
    """Update year field in existing Customs Import records based on from_date"""
    
    # Get all Customs Import records that have from_date but no year
    customs_imports = frappe.get_all(
        "Customs Import",
        filters={
            "from_date": ["is", "set"],
            "year": ["is", "not set"]
        },
        fields=["name", "from_date"]
    )
    
    updated_count = 0
    
    for record in customs_imports:
        try:
            # Extract year from from_date
            if record.from_date:
                if isinstance(record.from_date, str):
                    # Parse string date
                    try:
                        date_obj = datetime.strptime(record.from_date, '%Y-%m-%d')
                        year = date_obj.year
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(record.from_date, '%Y-%m-%d %H:%M:%S')
                            year = date_obj.year
                        except ValueError:
                            frappe.log_error(f"Invalid date format for Customs Import {record.name}: {record.from_date}")
                            continue
                else:
                    # Date object
                    year = record.from_date.year
                
                # Update the year field
                frappe.db.set_value("Customs Import", record.name, "year", year)
                updated_count += 1
                
        except Exception as e:
            frappe.log_error(f"Error updating year for Customs Import {record.name}: {str(e)}")
            continue
    
    frappe.db.commit()
    
    if updated_count > 0:
        frappe.msgprint(f"Successfully updated year field for {updated_count} Customs Import records")
    else:
        frappe.msgprint("No Customs Import records needed year field updates")
