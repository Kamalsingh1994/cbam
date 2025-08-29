# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from .ets_import_processor import ETSImportProcessor

def scheduled_ets_import():
    """Scheduled job for automatic ETS price import"""
    try:
        # Get all active import settings
        active_settings = frappe.get_all(
            "ETS Import Settings",
            filters={
                "auto_import": 1,
                "status": "Active"
            },
            fields=["name", "import_frequency", "next_import"]
        )
        
        if not active_settings:
            frappe.log_error("No active ETS auto-import settings found")
            return
        
        current_time = frappe.utils.now()
        processed_count = 0
        
        for setting in active_settings:
            try: 
                frappe.log_error(f"Starting scheduled ETS price import for {setting.name}...")
                
                # Get the full settings document
                settings = frappe.get_doc("ETS Import Settings", setting.name)
                
                # Execute import
                processor = ETSImportProcessor(settings)
                result = processor.import_ets_prices()
                
                # Update settings
                settings.last_import = current_time
                settings.save(ignore_permissions=True)
                
                # Log success
                settings.log_import_result(result, "Scheduled")
                
                frappe.logger().info(f"Scheduled ETS import completed for {setting.name}: {result}")
                processed_count += 1
                
            except Exception as setting_error:
                frappe.log_error(f"Scheduled ETS import failed for {setting.name}: {str(setting_error)}")
                
                # Try to log the error
                try:
                    if 'settings' in locals():
                        settings.log_import_result({
                            "status": "Failed", 
                            "error": str(setting_error)
                        }, "Scheduled")
                except:
                    pass
                continue
        
        frappe.logger().info(f"Scheduled ETS import completed for {processed_count} settings")
        
    except Exception as e:
        frappe.log_error(f"Scheduled ETS import failed: {str(e)}")