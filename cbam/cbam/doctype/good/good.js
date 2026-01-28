// Copyright (c) 2024, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('Good', {
    supplier(frm) {
        frm.set_query("employee", (doc) => {
            return {
                filters: {
                    "supplier_company": doc.supplier
                }
            }
        });
    },
    refresh(frm) {
        frm.set_query("employee", (doc) => {
            return {
                filters: {
                    "supplier_company": doc.supplier
                }
            }
        });

        // Add recalculate benchmark button
        if (frm.doc.cn_code && frm.doc.country_of_origin && !frm.is_new()) {
            frm.add_custom_button(__("Recalculate Benchmark"), function() {
                recalculate_benchmark(frm);
            }, __("Actions"));
        }

        // Show calculation status indicator
        if (frm.doc.benchmark_calculation_status) {
            show_benchmark_status(frm);
        }
        highlight_applicable_product_rows(frm);
    },
	onload(frm) {
		highlight_applicable_product_rows(frm);
	},
    internal_customs_import_number(frm) {
        if (frm.__customs_import_year_cache) {
            frm.__customs_import_year_cache = null;
        }
        highlight_applicable_product_rows(frm);
    },
    raw_mass(frm) {
        if (frm.doc.raw_mass != null) {
            const value = flt(frm.doc.raw_mass) / 1000;
            if (flt(frm.doc.raw_mass_tonne) !== value) {
                frm.set_value("raw_mass_tonne", value);
            }
        }
    },
    raw_mass_tonne(frm) {
        if (frm.doc.raw_mass_tonne != null) {
            const value = flt(frm.doc.raw_mass_tonne) * 1000;
            if (flt(frm.doc.raw_mass) !== value) {
                frm.set_value("raw_mass", value);
            }
        }
    }
})


frappe.ui.form.on('Good', {
    installation(frm) {
        frm.set_query("emission_data", (doc) => {
            return {
                filters: {
                    "cbam_installation": doc.installation
                }
            }
        });
    }
})

frappe.ui.form.on("Good", {
    refresh(frm) {
        // Make emission attachment clickable - should work for all statuses
        if (frm.doc.emission_data_attachment) {
            let path = frm.doc.emission_data_attachment;
            // Always show as clickable if path starts with /files/ or /private/files/
            if ((path.startsWith('/files/') || path.startsWith('/private/files/'))) {
                let file_name = path.split('/').pop();
                let html = `<a href="${path}" target="_blank" style="color: #2490ef; text-decoration: underline;">${file_name}</a>`;
                frm.fields_dict.emission_data_attachment.$wrapper.html(html);
            } else {
                // fallback, show as plain text or non-clickable
                frm.fields_dict.emission_data_attachment.$wrapper.html(path);
            }
        }

        // Add emission data attachment to sidebar
        if (frm.doc.emission_data_attachment) {
            let attachment_path = frm.doc.emission_data_attachment;
            let file_name = attachment_path.split('/').pop();

            // Wait for sidebar to be ready
            setTimeout(() => {
                let sidebar_attachment = $(frm.sidebar.wrapper).find('.sidebar-attachments');
                if (sidebar_attachment.length) {
                    // Check if already added
                    let existing_link = sidebar_attachment.find(`a[href="${attachment_path}"]`);
                    if (existing_link.length === 0) {
                        // Create attachment link
                        let attachment_html = `
                            <div class="attachment-row" style="padding: 8px; border-bottom: 1px solid #e0e0e0;">
                                <a href="${attachment_path}" target="_blank" class="attachment-link" style="color: #2490ef; text-decoration: none;">
                                    <i class="fa fa-file-o" style="margin-right: 5px;"></i>
                                    ${file_name}
                                </a>
                                <div style="font-size: 11px; color: #757575; margin-top: 2px;">
                                    Emission Data Attachment
                                </div>
                            </div>
                        `;
                        // Add to top of attachments list
                        sidebar_attachment.prepend(attachment_html);
                    }
                } else {
                    // If sidebar attachments section doesn't exist, create it
                    let sidebar_content = $(frm.sidebar.wrapper).find('.sidebar-content');
                    if (sidebar_content.length) {
                        let attachment_section = `
                            <div class="sidebar-section" style="margin-top: 10px;">
                                <div class="section-head" style="padding: 8px; font-weight: 600; border-bottom: 1px solid #e0e0e0;">
                                    ${__('Attachments')}
                                </div>
                                <div class="sidebar-attachments" style="max-height: 300px; overflow-y: auto;">
                                    <div class="attachment-row" style="padding: 8px; border-bottom: 1px solid #e0e0e0;">
                                        <a href="${attachment_path}" target="_blank" class="attachment-link" style="color: #2490ef; text-decoration: none;">
                                            <i class="fa fa-file-o" style="margin-right: 5px;"></i>
                                            ${file_name}
                                        </a>
                                        <div style="font-size: 11px; color: #757575; margin-top: 2px;">
                                            Emission Data Attachment
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        sidebar_content.append(attachment_section);
                    }
                }
            }, 500);
        }

        // Don't show "Send Data Request" button for these statuses
        if(["Data Submitted", "Rejected"].includes(frm.doc.status)){
            return
        }

        frm.add_custom_button(__("Send Data Request"), function () {
            // console.log("create new supplier");
            frappe.call({
                method: "send_data_request",
                doc: frm.doc,
                freeze: true,
                freeze_message: "Sending Data Request....",
                callback(r){
                    msgprint("Data Requested Successfully")
                    frm.reload_doc()
                }
            });
        });

        // Add recalculate benchmark button
        if (frm.doc.cn_code && frm.doc.country_of_origin && !frm.is_new()) {
            frm.add_custom_button(__("Recalculate Benchmark"), function() {
                recalculate_benchmark(frm);
            }, __("Actions"));
        }

        // Show calculation status indicator
        if (frm.doc.benchmark_calculation_status) {
            show_benchmark_status(frm);
        }
    },
});

function recalculate_benchmark(frm) {
    frappe.call({
        method: "cbam.utils.benchmark.recalculate_good_benchmark",
        args: {
            good_name: frm.doc.name
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

function show_benchmark_status(frm) {
    const status = frm.doc.benchmark_calculation_status;
    const status_colors = {
        "Calculated": "green",
        "Missing Data": "orange",
        "Error": "red",
        "Manual Override": "blue"
    };

    const color = status_colors[status] || "gray";
    const benchmark_value = frm.doc.country_specific_default_cbam_benchmark;

    // Parse calculation details to check if global default was used
    let source_info = "";
    let show_warning = false;
    try {
        if (frm.doc.benchmark_calculation_details) {
            const details = JSON.parse(frm.doc.benchmark_calculation_details);
            if (details.source === "global_default") {
                show_warning = true;
                source_info = '<span style="color: orange; font-size: 11px; margin-left: 10px;">⚠ Using Global Default (no country-specific default found)</span>';
            }
        }
    } catch (e) {
        // Ignore JSON parse errors
    }

    if (frm.fields_dict.benchmark_calculation_status) {
        const status_field = frm.fields_dict.benchmark_calculation_status;
        const wrapper = $(status_field.$wrapper);

        // Remove existing indicator if any
        wrapper.find('.benchmark-status-indicator').remove();

        // Add status indicator
        if (status && (benchmark_value !== null && benchmark_value !== undefined || status !== "Calculated")) {
            wrapper.append(`
                <div class="benchmark-status-indicator" style="margin-top: 5px;">
                    <span class="indicator-pill ${color}" style="padding: 4px 8px; border-radius: 3px; font-size: 11px; background-color: ${color === "green" ? "#d4edda" : color === "orange" ? "#fff3cd" : color === "red" ? "#f8d7da" : "#d1ecf1"}; color: ${color === "green" ? "#155724" : color === "orange" ? "#856404" : color === "red" ? "#721c24" : "#0c5460"};">
                        ${status}
                    </span>
                    ${benchmark_value ? `<span style="margin-left: 10px; font-weight: 600;">Value: ${benchmark_value}</span>` : ''}
                    ${source_info}
                </div>
            `);
        }
    }
}

function update_default_emission_toggle(frm) {
    const rows = frm.doc.country_specific_default_emission_values || [];
    const hasApplicable = rows.some(row => row.applicable_product);
    const shouldSelect = rows.length > 1 && !hasApplicable;
    if (frm.doc.select_applicable_product_for_cn_code !== (shouldSelect ? 1 : 0)) {
        frm.set_value("select_applicable_product_for_cn_code", shouldSelect ? 1 : 0);
    }
}

frappe.ui.form.on("Good", {
    country_specific_default_emission_values_add(frm) {
        update_default_emission_toggle(frm);
    },
    country_specific_default_emission_values_remove(frm) {
        update_default_emission_toggle(frm);
    },
    refresh(frm) {
        update_default_emission_toggle(frm);
    }
});

frappe.ui.form.on("Good Default Emission Value", {
    applicable_product(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.applicable_product) {
            update_default_emission_toggle(frm);
            return;
        }
        (frm.doc.country_specific_default_emission_values || []).forEach(other => {
            if (other.name !== row.name && other.applicable_product) {
                other.applicable_product = 0;
            }
        });
        frm.refresh_field("country_specific_default_emission_values");
        frm.set_value("select_applicable_product_for_cn_code", 0);
        highlight_applicable_product_rows(frm);
    },
    form_render(frm, cdt, cdn) {
        highlight_applicable_product_rows(frm);
    }
});

frappe.ui.form.on("Good", {
    refresh(frm) {
        show_rejection_banner(frm);
    }
});

function highlight_applicable_product_rows(frm) {
    const grid = frm.fields_dict.country_specific_default_emission_values?.grid;
    if (!grid || !grid.grid_rows || grid.grid_rows.length === 0) {
        setTimeout(() => highlight_applicable_product_rows(frm), 150);
        return;
    }
    get_customs_import_year(frm).then(customs_year => {
        const year_field = get_default_emission_year_field(customs_year);
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
            highlight_applicable_product_form(grid_row, row.applicable_product, year_field);
        });
    });
}

function highlight_applicable_product_form(grid_row, is_applicable, year_field) {
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

function get_default_emission_year_field(year) {
    if (!year) {
        return null;
    }
    if (year < 2026) {
        return "default_value_total_emissions";
    }
    if (year === 2026) {
        return "default_value_2026";
    }
    if (year === 2027) {
        return "default_value_2027";
    }
    if (year === 2028) {
        return "default_value_2028_onwards";
    }
    return "default_value_total_emissions";
}

function get_customs_import_year(frm) {
    const customs_import = frm.doc.internal_customs_import_number;
    if (!customs_import) {
        return Promise.resolve(null);
    }
    if (frm.__customs_import_year_cache?.name === customs_import) {
        return Promise.resolve(frm.__customs_import_year_cache.year);
    }
    return frappe.db.get_value("Customs Import", customs_import, "year")
        .then(res => {
            const year_link = res && res.message ? res.message.year : null;
            if (!year_link) {
                frm.__customs_import_year_cache = { name: customs_import, year: null };
                return null;
            }
            return frappe.db.get_value("Year", year_link, "year").then(year_res => {
                const year_value = year_res && year_res.message ? parseInt(year_res.message.year, 10) : null;
                frm.__customs_import_year_cache = { name: customs_import, year: year_value };
                return year_value;
            });
        });
}

function show_rejection_banner(frm) {
    if (frm.doc.status !== "Rejected") {
        frm.dashboard.clear_headline();
        return;
    }
    let message = "";
    if (frm.doc.rejected_within_supply_chain) {
        message = __("This good has been rejected within the supply chain and has not been rejected to the Declarant.");
    } else if (frm.doc.rejected_to_declarant) {
        message = __("This good has been rejected back to the Declarant.");
    }
    if (message) {
        frm.dashboard.set_headline(message);
    }
}
