from frappe.model.document import Document

class ExcelColumnMapping(Document):
    """Child table for mapping Excel columns to data types"""
    
    def before_insert(self):
        """Set default values before insert"""
        if not self.column_type:
            self.column_type = "Other"
    
    def on_update(self):
        """Handle updates to the document"""
        pass
    
    def validate(self):
        """Validate the document"""
        if not self.column_name:
            frappe.throw("Column name is required")
        
        # Ensure column name doesn't contain special characters
        if not self.column_name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
            frappe.throw("Column name should only contain letters, numbers, spaces, hyphens, and underscores")
