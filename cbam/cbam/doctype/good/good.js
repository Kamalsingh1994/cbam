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
    },
});