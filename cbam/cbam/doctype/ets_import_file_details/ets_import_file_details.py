from frappe.model.document import Document

class ETSImportFileDetails(Document):
    """Child table for storing Excel row data"""
    
    def before_insert(self):
        """Set default values before insert"""
        if not self.processing_status:
            self.processing_status = "Pending"
    
    def on_update(self):
        """Handle updates to the document"""
        pass
    
    def validate(self):
        """Validate the document"""
        if not self.date:
            frappe.throw("Date is required")
        if not self.price or self.price <= 0:
            frappe.throw("Price must be greater than 0")
        if not self.currency:
            frappe.throw("Currency is required")
        if not self.source:
            frappe.throw("Source is required")
