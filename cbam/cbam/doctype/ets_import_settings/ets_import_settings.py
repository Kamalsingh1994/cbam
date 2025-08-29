# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import time
from cbam.utils.ets_import.google_drive_service import GoogleDriveService
from cbam.utils.ets_import.ets_import_processor import ETSImportProcessor

class ETSImportSettings(Document):
    def validate(self):
        """Validate the import settings"""
        if self.source_type == "Google Drive":
            self.validate_google_drive_settings()
    
    def validate_google_drive_settings(self):
        """Validate Google Drive specific settings"""
        if not self.google_drive_folder_id:
            frappe.throw(_("Google Drive Folder ID is required for Google Drive source type"))
        
        if not self.google_service_account_email:
            frappe.throw(_("Service Account Email is required for Google Drive source type"))
        
        if not self.google_private_key:
            frappe.throw(_("Private Key is required for Google Drive source type"))
    


@frappe.whitelist()
def test_google_drive_connection(settings_name):
    """Test Google Drive connection and folder access"""
    try:
        # Get the settings document
        settings = frappe.get_doc("ETS Import Settings", settings_name)
        
        # Check if required fields are filled
        if not settings.google_private_key:
            frappe.throw(_("Private key is empty"))
        
        if not settings.google_drive_folder_id:
            frappe.throw(_("Google Drive Folder ID is empty"))
        
        if not settings.file_pattern:
            frappe.throw(_("File pattern is empty"))
        
        # Test the connection by creating the service
        drive_service = GoogleDriveService(settings)
        
        # Test folder access
        files = drive_service.list_files_in_folder(
            settings.google_drive_folder_id, 
            settings.file_pattern
        )

        if files:
            frappe.msgprint(
                _("✅ Connection successful! Found {0} files matching pattern '{1}'").format(
                    len(files), settings.file_pattern
                ),
                title=_("Connection Test - SUCCESS")
            )
            return {
                "status": "Success",
                "files_found": len(files),
                "sample_files": [f["name"] for f in files[:5]]
            }
        else:
            frappe.msgprint(
                _("⚠️ Connection successful but no files found matching pattern '{0}'").format(
                    settings.file_pattern
                ),
                title=_("Connection Test - WARNING")
            )
            return {
                "status": "Warning",
                "files_found": 0,
                "message": "No files found matching pattern"
            }
            
    except Exception as e:
        frappe.log_error(f"Google Drive connection test failed: {str(e)}")
        frappe.throw(
            _("❌ Connection failed: {0}").format(str(e)),
            title=_("Connection Test Failed")
        )

@frappe.whitelist()
def trigger_manual_import(settings_name):
    """Manually trigger ETS price import"""
    try:
        # Get the settings document
        settings = frappe.get_doc("ETS Import Settings", settings_name)
        
        if not frappe.has_permission("ETS Import Settings", "write"):
            frappe.throw(_("Insufficient permissions to trigger import"))
        
        start_time = time.time()
        
        # Process the import first to check if there are records to process
        processor = ETSImportProcessor(settings)
        result = processor.import_ets_prices()
        
        # Only create import log if there are records to process
        if result["status"] == "Success" and result["records"] > 0:
            import_log = frappe.get_doc({
                "doctype": "ETS Import Log",
                "import_date": frappe.utils.now(),
                "source_file": "Manual Import",
                "status": "Success",
                "imported_by": frappe.session.user,
                "import_type": "Manual"
            })
            import_log.insert(ignore_permissions=True)
            processor.current_import_log = import_log.name
            
            # Now store the Excel data rows since we have a log
            if hasattr(processor, 'pending_excel_data'):
                processor._store_excel_data_rows(
                    processor.pending_excel_data['df'], 
                    processor.pending_excel_data['filename'], 
                    processor.pending_excel_data['successful_rows']
                )
                frappe.log_error("excel_data_stored", "Excel data rows stored successfully after import log creation")
            else:
                frappe.log_error("no_pending_data", "No pending Excel data to store")
        
        execution_time = time.time() - start_time
        
        # Update last import time
        settings.last_import = frappe.utils.now()
        # Use frappe.db.set_value to avoid potential recursion issues
        frappe.db.set_value(
            "ETS Import Settings", 
            settings.name, 
            "last_import", 
            settings.last_import
        )
        
        # Update import log with final status (only if it was created)
        if result["status"] == "Success":
            if 'import_log' in locals() and import_log:
                frappe.db.set_value("ETS Import Log", import_log.name, "status", "Success")
                frappe.db.set_value("ETS Import Log", import_log.name, "source_file", result["file"])
                frappe.db.set_value("ETS Import Log", import_log.name, "google_drive_file_id", result["file_id"])
                frappe.db.set_value("ETS Import Log", import_log.name, "records_imported", result["records"])
                frappe.db.set_value("ETS Import Log", import_log.name, "execution_time", execution_time)
                
                frappe.msgprint(
                    _("✅ Import completed successfully! Imported {0} records from '{1}'").format(
                        result["records"], result["file"]
                    ),
                    title=_("Import Success")
                )
            else:
                frappe.msgprint(
                    _("ℹ️ No records to import."),
                    title=_("Import Completed")
                )
        elif result["status"] == "Skipped":
            if 'import_log' in locals() and import_log:
                frappe.db.set_value("ETS Import Log", import_log.name, "status", "Skipped")
                frappe.db.set_value("ETS Import Log", import_log.name, "source_file", result["file"])
                frappe.db.set_value("ETS Import Log", import_log.name, "google_drive_file_id", result["file_id"])
                frappe.db.set_value("ETS Import Log", import_log.name, "execution_time", execution_time)
            
            frappe.msgprint(
                _("ℹ️ Import skipped: {0}").format(result.get("reason", "File already processed")),
                title=_("Import Skipped")
            )
        
        return result
        
    except Exception as e:
        # Update import log with error status (only if it was created)
        if 'import_log' in locals() and import_log:
            try:
                frappe.db.set_value("ETS Import Log", import_log.name, "status", "Failed")
                frappe.db.set_value("ETS Import Log", import_log.name, "error_message", str(e))
                frappe.db.set_value("ETS Import Log", import_log.name, "execution_time", time.time() - start_time)
            except Exception as log_error:
                frappe.log_error(f"Failed to update import log status: {str(log_error)}")
        
        frappe.log_error(f"Manual ETS import failed: {str(e)}")
        frappe.throw(
            _("❌ Import failed: {0}").format(str(e)),
            title=_("Import Error")
        )
