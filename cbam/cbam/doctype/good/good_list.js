frappe.listview_settings['Good'] = {
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
    }
};
