# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class ETSImportLog(Document):
    """Controller for ETS Import Log doctype"""
    
    def before_insert(self):
        """Set default values before insert"""
        if not self.imported_by:
            self.imported_by = frappe.session.user
    
    def after_insert(self):
        """Actions after insert"""
        # Log the import activity
        frappe.logger().info(f"ETS Import Log created: {self.name} - Status: {self.status}")
    
    def validate(self):
        """Validate the document before save"""
        if self.status == "Failed" and not self.error_message:
            frappe.throw(_("Error message is required when status is Failed"))
        
        if self.records_imported and self.records_imported < 0:
            frappe.throw(_("Records imported cannot be negative"))
    
    def on_update(self):
        """Actions after update"""
        # Update any related records if needed
        pass
