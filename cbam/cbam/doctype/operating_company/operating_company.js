// Copyright (c) 2024, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Operating Company", {
	refresh(frm) {
        frm.add_custom_button(__("Send Signup Request"), function(){
            frappe.call({
                method: "send_signup_request",
                doc: frm.doc,
                callback(r){
                    msgprint("request sent successfully")
                }
            })
        })
	},
});
