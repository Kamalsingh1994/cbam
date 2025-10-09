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
  refresh(frm) {
    add_custom_links("report_id", "CBAM Report", cur_frm.doc.report_id, "CBAM Report");
    add_custom_links("reporting_period", "Customs Import", cur_frm.doc.reporting_period, "Reporting Period");
  },
  raw_mass_tonne(frm) {
      if (frm.doc.raw_mass_tonne != null) {
          const value = flt(frm.doc.raw_mass_tonne) * 1000;
          if (flt(frm.doc.raw_mass) !== value) {
              frm.set_value("raw_mass", value);
          }
      }
  },
  raw_mass: function (frm) {
    if (frm.doc.raw_mass != null) {
      const value = flt(frm.doc.raw_mass) / 1000;
      if (flt(frm.doc.raw_mass_tonne) !== value) {
          frm.set_value("raw_mass_tonne", value);
      }
    }
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

add_custom_links = (fieldname, doctype, docname, doctype_label) => {
  doctype_url = doctype.replace(/ /g, "-").toLowerCase();
  cur_frm.fields_dict[fieldname].$wrapper.html(
    `<div class="form-group">
        <div class="clearfix">
          <label class="control-label" style="padding-right: 0px;">${doctype_label}</label>
        </div>
        <div class="control-input-wrapper">
          <a class="control-value like-disabled-input" href="/app/${doctype_url}/${docname}">${docname}</a>
        </div>
      </div>`
  );
}