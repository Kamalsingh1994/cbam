frappe.listview_settings['Good'] = {
    has_indicator_for_draft: true,
    onload(listview) {
        // add button to menu
        listview.page.add_action_item(__("Send Data Request"), function() {
            console.log(listview.get_checked_items())
            frappe.call({
                method: "cbam.cbam.doctype.good.good.send_data_request",
                args:{
                    goods: listview.get_checked_items()
                },
                freeze: true,
                freeze_message: "Sending Data Request, please wait.",
                callback(r){
                    msgprint("Data Request Sent Successfully.")
                }
            })
        });

        if (frappe.user.has_role("Declarant")) {
            listview.page.add_action_item(__("Filter: Rejected within Supply Chain"), function() {
                listview.filter_area.add([["Good", "rejected_within_supply_chain", "=", 1]]);
            });
        }
    }
};



