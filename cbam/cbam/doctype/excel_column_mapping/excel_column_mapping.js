frappe.ui.form.on('Excel Column Mapping', {
    refresh: function(frm) {
        // Refresh logic if needed
    },
    
    column_name: function(frm, cdt, cdn) {
        // Auto-suggest column type based on column name
        let row = locals[cdt][cdn];
        if (row.column_name) {
            let columnName = row.column_name.toLowerCase();
            
            if (columnName.includes('date') || columnName.includes('time')) {
                row.column_type = 'Date';
            } else if (columnName.includes('price') || columnName.includes('cost') || columnName.includes('amount')) {
                row.column_type = 'Price';
            } else if (columnName.includes('currency') || columnName.includes('curr')) {
                row.column_type = 'Currency';
            } else if (columnName.includes('source') || columnName.includes('provider')) {
                row.column_type = 'Source';
            } else {
                row.column_type = 'Other';
            }
            
            frm.refresh_field('column_type');
        }
    },
    
    column_type: function(frm, cdt, cdn) {
        // Auto-set required for essential columns
        let row = locals[cdt][cdn];
        if (row.column_type === 'Date' || row.column_type === 'Price') {
            row.required = 1;
            frm.refresh_field('required');
        }
    }
});
