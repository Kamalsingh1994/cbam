// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('ETS Import Log', {
    refresh: function(frm) {
        // Add custom buttons or actions
        if (frm.doc.status === 'Failed') {
            frm.add_custom_button(__('Retry Import'), function() {
                // Add retry logic here if needed
                frappe.msgprint(__('Retry functionality can be implemented here.'));
            });
        }
        
        // Add view source file button if Google Drive file ID exists
        if (frm.doc.google_drive_file_id) {
            frm.add_custom_button(__('View in Google Drive'), function() {
                const driveUrl = `https://drive.google.com/file/d/${frm.doc.google_drive_file_id}/view`;
                window.open(driveUrl, '_blank');
            });
        }
    },
    
    status: function(frm) {
        // Show/hide error message field based on status
        if (frm.doc.status === 'Failed') {
            frm.set_df_property('error_message', 'reqd', 1);
        } else {
            frm.set_df_property('error_message', 'reqd', 0);
        }
    },
    
    execution_time: function(frm) {
        // Validate execution time
        if (frm.doc.execution_time && frm.doc.execution_time < 0) {
            frappe.msgprint(__('Execution time cannot be negative.'));
            frm.set_value('execution_time', 0);
        }
    }
});
