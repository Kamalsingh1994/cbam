window.addEventListener("DOMContentLoaded", executeJS);

function executeJS() {
    const contentContainer = document.querySelectorAll(".content-container");
    const infoContainer = document.querySelector(".info-container");
    const cbamSection = document.querySelector("#cbam_representive");
    const company_contact = document.querySelector("#company_contact");
    const commercial_contact = document.querySelector("#commerical_contact");
    const cbam_rep = document.querySelector("#cbam_rep");
    const cbamBtnCont = document.querySelector(".cbam-btn-container");

    // ✅ Parse doc_dict ONCE and store globally
    const doc_dict_el = document.querySelector("#doc_dict");
    if (doc_dict_el) {
        let raw = doc_dict_el.textContent;

        raw = raw
            .replace(/datetime\.datetime\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)\)/g,
                (_, y, m, d, h, min, s, ms) => `"${new Date(Date.UTC(y, m - 1, d, h, min, s, ms / 1000)).toISOString()}"`
            )
            .replace(/None/g, "null")
            .replace(/'/g, '"');

        try {
            window.supplier_details = JSON.parse(raw);
        } catch (err) {
            console.error("Error parsing supplier_details:", err);
            window.supplier_details = {};
        }
    }

    const supplier_details = window.supplier_details || {};

    const confirmDetails = function(values, d) {
        frappe.call({
            method: "cbam.utils.supplier.confirm_details",
            args: { values },
            callback: function (r) {
                frappe.call({
                    method: "cbam.www.operating_company.index.get_operating_company_partial_html",
                    callback: function (r) {
                        if (r.message) {
                            contentContainer.forEach(container => container.remove());
                            document.querySelector('.list-row-container').insertAdjacentHTML('beforeend', r.message);
                            executeJS();
                        }
                    }
                });
                d.hide();
                window.location.reload();
            }
        });
    };

    let cbamHasFieldVals = true;
    cbamSection?.querySelectorAll(".tc-field").forEach(field => {
        if (!field.textContent) cbamHasFieldVals = false;
    });
    if (!cbamHasFieldVals && cbamBtnCont) {
        cbamBtnCont.classList.remove("hidden");
    }

    // 🔁 Dialog Definitions (unchanged, uses `supplier_details`)
    const UpdateContactDetails = async function () {
        const cc_add = __("Company Contact and Address");
        let d = new frappe.ui.Dialog({
            title: __("Please Confrim your Operating Company Details"),
            fields: [
                { label: __("Operating Company Name"), fieldname: "supplier_name", fieldtype: "Data", default: supplier_details.supplier_name },
                { label: `<strong>${cc_add}</strong>`, fieldname: "sb1", fieldtype: "Section Break" },
                { label: __("Company Phone Number"), fieldname: "company_phone_number", fieldtype: "Data", default: supplier_details.company_phone_number },
                { label: __("Company Email"), fieldname: "company_email", fieldtype: "Data", default: supplier_details.company_email, options: "Email" },
                { fieldname: "cb1", fieldtype: "Column Break" },
                { label: __("Street and Number"), fieldname: "street_and_number", fieldtype: "Data", default: supplier_details.street_and_number },
                { label: __("Zip Code"), fieldname: "zip_code", fieldtype: "Data", default: supplier_details.zip_code },
                { fieldname: "cb2", fieldtype: "Column Break" },
                { label: __("City"), fieldname: "city", fieldtype: "Data", default: supplier_details.city },
                { label: __("Country"), fieldname: "country", fieldtype: "Autocomplete", options: await cbam.utils.get_links("Country"), default: supplier_details.country },
            ],
            size: 'extra-large',
            primary_action_label: __('Confirm Details'),
            primary_action(values) {
                confirmDetails(values, d);
            }
        });
        d.show();
    };

    const UpdateCommericalDetails = async function () {
        const cc_details = __("Commercial Contact Details");
        let d = new frappe.ui.Dialog({
            title: __("Please Confirm your Commercial Contact Details"),
            fields: [
                { label: __("Operating Company"), fieldname: "supplier_name", fieldtype: "Data", default: supplier_details.supplier_name, read_only: 1 },
                { label: `<strong>${cc_details}</strong>`, fieldname: "sb1", fieldtype: "Section Break" },
                { label: __("Last Name"), fieldname: "main_contact_employee_last_name", fieldtype: "Data", default: supplier_details.main_contact_employee_last_name },
                { label: __("Position"), fieldname: "main_contact_employee_position", fieldtype: "Data", default: supplier_details.main_contact_employee_position },
                { fieldname: "cb1", fieldtype: "Column Break" },
                { label: __("First Name"), fieldname: "main_contact_employee_first_name", fieldtype: "Data", default: supplier_details.main_contact_employee_first_name },
                { label: __("Phone Number"), fieldname: "main_contact_employee_phone_number", fieldtype: "Data", default: supplier_details.main_contact_employee_phone_number },
                { fieldname: "cb2", fieldtype: "Column Break" },
                { label: __("Email"), fieldname: "main_contact_employee_email", fieldtype: "Data", default: supplier_details.main_contact_employee_email, options: "Email", read_only: 1 },
            ],
            size: 'extra-large',
            primary_action_label: __('Confirm Details'),
            primary_action(values) {
                confirmDetails(values, d);
            }
        });
        d.show();
    };

    const UpdateRepresentativeDetails = async function () {
        const cbr_details = __("CBAM Representative Details");
        let d = new frappe.ui.Dialog({
            title: __("Please Confirm your CBAM Representative Details"),
            fields: [
                { label: __("Operating Company"), fieldname: "supplier_name", fieldtype: "Data", default: supplier_details.supplier_name, read_only: 1 },
                { label: `<strong>${cbr_details}</strong>`, fieldname: "sb1", fieldtype: "Section Break" },
                { label: __("Last Name"), fieldname: "cbam_representive_last_name", fieldtype: "Data", default: supplier_details.cbam_representive_last_name },
                { label: __("First Name"), fieldname: "cbam_representive_employee_first_name", fieldtype: "Data", default: supplier_details.cbam_representive_employee_first_name },
                { fieldname: "cb1", fieldtype: "Column Break" },
                { label: __("Email"), fieldname: "cbam_representive_employee_email", fieldtype: "Data", default: supplier_details.cbam_representive_employee_email, options: "Email", read_only: supplier_details.cbam_representative_user ? 1 : 0 },
                { label: __("Phone Number"), fieldname: "cbam_representive_employee_phone_number", fieldtype: "Data", default: supplier_details.cbam_representive_employee_phone_number },
                { fieldname: "cb2", fieldtype: "Column Break" },
                { label: __("Position"), fieldname: "cbam_representive_employee_position", fieldtype: "Data", default: supplier_details.cbam_representive_employee_position },
            ],
            size: 'extra-large',
            primary_action_label: __('Confirm Details'),
            primary_action(values) {
                confirmDetails(values, d);
            }
        });
        d.show();
    };

    // 🔁 Bind buttons
    company_contact?.addEventListener("click", e => { e.preventDefault(); UpdateContactDetails(); });
    commercial_contact?.addEventListener("click", e => { e.preventDefault(); UpdateCommericalDetails(); });
    cbam_rep?.addEventListener("click", e => { e.preventDefault(); UpdateRepresentativeDetails(); });
}

// ✅ SINGLE GLOBAL FUNCTION NOW
function edit_contact_person(row_idx) {
    const row = (window.supplier_details?.contact_persons || []).find(r => r.idx === parseInt(row_idx));
    if (!row) {
        frappe.msgprint("Contact person not found.");
        return;
    }

    const d = new frappe.ui.Dialog({
        size: 'large',
        title: 'Edit Contact Person',
        fields: [
            { fieldname: 'contact_type', label: 'Contact Type', fieldtype: 'Select', options: ['Commercial Contact', 'CBAM Representative'], default: row.contact_type, reqd: 1, read_only:1},
            { fieldname: 'first_name', label: 'First Name', fieldtype: 'Data', default: row.first_name },
            { fieldname: 'phone_no', label: 'Phone No', fieldtype: 'Data', default: row.phone_no },
            { fieldname: 'column_break1', fieldtype: 'Column Break' },
            { fieldname: 'contact_email', label: 'Email', fieldtype: 'Data', reqd: 1, default: row.contact_email, read_only: 1 },
            { fieldname: 'last_name', label: 'Last Name', fieldtype: 'Data', default: row.last_name },
            { fieldname: 'position', label: 'Position', fieldtype: 'Data', default: row.position },
        ],
        primary_action_label: 'Update',
        primary_action(values) {
            // Update locally
            Object.assign(row, values);

            frappe.call({
                method: "cbam.utils.supplier.update_contact_person",
                args: {
                    contact_email: row.contact_email,
                    updated_values: values  // values is a JS object here
                },
                callback: function (r) {
                    if (r.message === "success") {
                        frappe.show_alert({
                            message:__('Contact person updated successfully'),
                            indicator:'green'
                        }, 5);
                        setInterval(() => {
                            location.reload(); // Refresh updated list
                        }, 500);
                        
                    } else {
                        frappe.msgprint(__('Update failed'));
                    }
                }
            });

            d.hide();
        }
    });
    d.show();
}

function create_cbam_representative() {
    let d = new frappe.ui.Dialog({
        title: 'Add CBAM Representative',
        fields: [
            { fieldname: 'contact_email', label: 'Email', fieldtype: 'Data', reqd: 1 },
            { fieldname: 'first_name', label: 'First Name', fieldtype: 'Data' },
            { fieldname: 'last_name', label: 'Last Name', fieldtype: 'Data' },
            { fieldname: 'phone_no', label: 'Phone No', fieldtype: 'Data' },
            { fieldname: 'position', label: 'Position', fieldtype: 'Data' },
        ],
        primary_action_label: 'Add',
        primary_action(values) {
            frappe.call({
                method: 'cbam.utils.supplier.add_cbam_representative',
                args: {
                    values: values
                },
                callback: function (r) {
                    if (r.message === 'success') {
                        frappe.show_alert({ message: 'CBAM Representative added', indicator: 'green' });
                        location.reload(); // Refresh view to show new contact
                    } else {
                        frappe.msgprint(__('Failed to add contact'));
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}


