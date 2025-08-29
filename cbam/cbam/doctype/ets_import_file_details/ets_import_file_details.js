frappe.ui.form.on('ETS Import File Details', {
    refresh: function(frm) {
        // Refresh logic if needed
    },
    
    date: function(frm, cdt, cdn) {
        // Validate date format
        let row = locals[cdt][cdn];
        if (row.date && !frappe.datetime.validate(row.date)) {
            frappe.throw("Invalid date format. Please use YYYY-MM-DD");
        }
    },
    
    price: function(frm, cdt, cdn) {
        // Validate price is positive
        let row = locals[cdt][cdn];
        if (row.price && row.price <= 0) {
            frappe.throw("Price must be greater than 0");
        }
    }
});
