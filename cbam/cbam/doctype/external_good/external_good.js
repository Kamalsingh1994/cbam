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
  },
  raw_mass: function (frm) {
    calculate_quantity(frm);
    calculate_mass_per_article(frm);
  },
  mass_per_article: function(frm) {
    calculate_quantity(frm);
  },
  quantity_of_articles: function(frm) {
    calculate_mass_per_article(frm);
    },
});

function calculate_quantity(frm) {
  if (frm.doc.raw_mass && frm.doc.mass_per_article) {
    frm.set_value('quantity_of_articles', frm.doc.raw_mass / frm.doc.mass_per_article);
  }
}

function calculate_mass_per_article(frm) {
  if (frm.doc.raw_mass && frm.doc.quantity_of_articles) {
    frm.set_value('mass_per_article', frm.doc.raw_mass / frm.doc.quantity_of_articles);
  }
}