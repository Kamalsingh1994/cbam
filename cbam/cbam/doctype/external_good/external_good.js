// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("External Good", {
	onload: function (frm) {
        frm.set_query('declarant', () => {
          return {
            query: 'cbam.utils.utils.get_declarant_for_user',
            filters: {
              user: frappe.session.user
            }
          };
        });
      }
});
