// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('Declarant User', {
    is_primary: function (frm, cdt, cdn) {
        let selected_row = locals[cdt][cdn];

        if (selected_row.is_primary) {
            // Loop through all rows and uncheck others
            frm.doc.declarant_user.forEach(row => {
                if (row.name !== selected_row.name) {
                    row.is_primary = 0;
                }
            });

            // Set the email field on parent with selected user
            frm.set_value('email', selected_row.user);

            // Refresh the child table field to reflect changes
            frm.refresh_field('declarant_user');
        } else {
            // Clear parent email if unchecked
            frm.set_value('email', '');
        }
    }
});

