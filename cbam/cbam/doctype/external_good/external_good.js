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
    update_external_default_emission_toggle(frm);
    highlight_external_applicable_product_rows(frm);
  },
  year(frm) {
    if (frm.__external_good_year_cache) {
      frm.__external_good_year_cache = null;
    }
    highlight_external_applicable_product_rows(frm);
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

function update_external_default_emission_toggle(frm) {
  const rows = frm.doc.country_specific_default_emission_values || [];
  const hasApplicable = rows.some(row => row.applicable_product);
  const shouldSelect = rows.length > 1 && !hasApplicable;
  if (frm.doc.select_applicable_product_for_cn_code !== (shouldSelect ? 1 : 0)) {
    frm.set_value("select_applicable_product_for_cn_code", shouldSelect ? 1 : 0);
  }
}

frappe.ui.form.on("External Good", {
  country_specific_default_emission_values_add(frm) {
    update_external_default_emission_toggle(frm);
  },
  country_specific_default_emission_values_remove(frm) {
    update_external_default_emission_toggle(frm);
  }
});

frappe.ui.form.on("External Good Default Emission Value", {
  applicable_product(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.applicable_product) {
      update_external_default_emission_toggle(frm);
      return;
    }
    (frm.doc.country_specific_default_emission_values || []).forEach(other => {
      if (other.name !== row.name && other.applicable_product) {
        other.applicable_product = 0;
      }
    });
    frm.refresh_field("country_specific_default_emission_values");
    frm.set_value("select_applicable_product_for_cn_code", 0);
    highlight_external_applicable_product_rows(frm);
  },
  form_render(frm, cdt, cdn) {
    highlight_external_applicable_product_rows(frm);
  }
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

function highlight_external_applicable_product_rows(frm) {
  const grid = frm.fields_dict.country_specific_default_emission_values?.grid;
  if (!grid || !grid.grid_rows || grid.grid_rows.length === 0) {
    setTimeout(() => highlight_external_applicable_product_rows(frm), 150);
    return;
  }
  get_external_good_year_value(frm).then(year_value => {
    const year_field = get_external_default_emission_year_field(year_value);
    (frm.doc.country_specific_default_emission_values || []).forEach(row => {
      const grid_row = grid.get_row(row.name);
      if (!grid_row || !grid_row.row) {
        return;
      }
      const $row = $(grid_row.row);
      $row.toggleClass("applicable-product-row", !!row.applicable_product);
      $row.find(".applicable-product-year").removeClass("applicable-product-year");
      if (row.applicable_product && year_field) {
        $row.find(`[data-fieldname="${year_field}"]`).addClass("applicable-product-year");
      }
      highlight_external_applicable_product_form(grid_row, row.applicable_product, year_field);
    });
  });
}

function highlight_external_applicable_product_form(grid_row, is_applicable, year_field) {
  if (!grid_row || !grid_row.grid_form || !grid_row.grid_form.fields_dict) {
    return;
  }
  const fields = [
    "default_value_total_emissions",
    "default_value_2026",
    "default_value_2027",
    "default_value_2028_onwards"
  ];
  fields.forEach(fieldname => {
    const field = grid_row.grid_form.fields_dict[fieldname];
    if (!field || !field.$wrapper) {
      return;
    }
    field.$wrapper.removeClass("applicable-product-year");
    field.$wrapper.find(".control-label, input, .input-with-feedback, .static-area")
      .removeClass("applicable-product-year");
  });
  if (!is_applicable || !year_field) {
    return;
  }
  const target = grid_row.grid_form.fields_dict[year_field];
  if (!target || !target.$wrapper) {
    return;
  }
  target.$wrapper.addClass("applicable-product-year");
  target.$wrapper.find(".control-label, input, .input-with-feedback, .static-area")
    .addClass("applicable-product-year");
}

function get_external_default_emission_year_field(year) {
  if (!year) {
    return "default_value_total_emissions";
  }
  if (year === 2026) {
    return "default_value_2026";
  }
  if (year === 2027) {
    return "default_value_2027";
  }
  if (year >= 2028) {
    return "default_value_2028_onwards";
  }
  return "default_value_total_emissions";
}

function get_external_good_year_value(frm) {
  const year_link = frm.doc.year;
  if (!year_link) {
    return Promise.resolve(null);
  }
  if (frm.__external_good_year_cache?.name === year_link) {
    return Promise.resolve(frm.__external_good_year_cache.year);
  }
  return frappe.db.get_value("Year", year_link, "year").then(year_res => {
    const year_value = year_res && year_res.message ? parseInt(year_res.message.year, 10) : null;
    frm.__external_good_year_cache = { name: year_link, year: year_value };
    return year_value;
  });
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
