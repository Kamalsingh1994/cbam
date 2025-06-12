// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("External Good", {
  onload: function (frm) {
    if (frappe.session.user != "Administrator") {
      frm.set_df_property('declarant', 'read_only', 1);
    }
    if (frappe.session.user != "Administrator" && frm.doc.__islocal) {
      frappe.call({
        method: "cbam.utils.utils.get_declarant_for_user",
        callback: function (r) {
          if (r.message) {
            frm.set_value('declarant', r.message[0]);
          }
        }
      });
    }
  }
});
