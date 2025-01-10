frappe.listview_settings['Operating Company'] = {
    onload(listview) {
        // add button to menu
        listview.page.add_action_item(__("Send Signup Request"), function() {
            frappe.call({
                method: "cbam.cbam.doctype.operating_company.operating_company.send_bulk_signup_request",
                args:{
                    operating_companys: listview.get_checked_items()
                }, 
                freeze: true,
                freeze_message: "Sending Signup Request, please wait.",
                callback(r){
                    msgprint("Signup Request Sent Successfully.")
                }
            })
        });
    }
};