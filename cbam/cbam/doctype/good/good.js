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