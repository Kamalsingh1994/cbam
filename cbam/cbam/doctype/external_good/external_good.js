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
    
    // Add recalculate benchmark button
    if (frm.doc.cn_code && frm.doc.installation_country && !frm.is_new()) {
      frm.add_custom_button(__("Recalculate Benchmark"), function() {
        recalculate_external_good_benchmark(frm);
      }, __("Actions"));
    }
    
    // Show calculation status indicator
    if (frm.doc.benchmark_calculation_status) {
      show_benchmark_status_eg(frm);
    }
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

function recalculate_external_good_benchmark(frm) {
  frappe.call({
    method: "cbam.utils.benchmark.recalculate_external_good_benchmark",
    args: {
      external_good_name: frm.doc.name
    },
    freeze: true,
    freeze_message: __("Recalculating benchmark..."),
    callback: function(r) {
      if (r.message && r.message.success) {
        frappe.show_alert({
          message: __("Benchmark recalculated successfully"),
          indicator: "green"
        });
        frm.reload_doc();
      } else {
        frappe.show_alert({
          message: __("Error recalculating benchmark: {0}", [r.message?.error || "Unknown error"]),
          indicator: "red"
        });
      }
    }
  });
}

function show_benchmark_status_eg(frm) {
  const status = frm.doc.benchmark_calculation_status;
  const status_colors = {
    "Calculated": "green",
    "Missing Data": "orange",
    "Error": "red",
    "Manual Override": "blue"
  };
  
  const color = status_colors[status] || "gray";
  const benchmark_value = frm.doc.country_specific_default_cbam_benchmark;
  
  if (frm.fields_dict.benchmark_calculation_status && benchmark_value !== null && benchmark_value !== undefined) {
    const status_field = frm.fields_dict.benchmark_calculation_status;
    const wrapper = $(status_field.$wrapper);
    
    // Add status indicator
    if (!wrapper.find('.benchmark-status-indicator').length) {
      wrapper.append(`
        <div class="benchmark-status-indicator" style="margin-top: 5px;">
          <span class="indicator-pill ${color}" style="padding: 4px 8px; border-radius: 3px; font-size: 11px;">
            ${status}
          </span>
          ${benchmark_value ? `<span style="margin-left: 10px; font-weight: 600;">Value: ${benchmark_value}</span>` : ''}
        </div>
      `);
    }
  }
}