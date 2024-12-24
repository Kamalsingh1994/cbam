frappe.provide("cbam.dialog")

$.extend(cbam.dialog, {
    async get_dialog(doctype, title, _primary_action){
        let d = new frappe.ui.Dialog({
            title: title,
            fields: await cbam.dialog.get_fields(doctype),
            size: 'small', // small, large, extra-large 
            primary_action_label: 'Reject Goods',
            
            primary_action(values) {
                _primary_action.apply(values)
            },
            
        });
    },
    async get_fields(doctype){
        return new Promise(function(res, rej){
            frappe.call({
                method: 'cbam.utils.dialog.get_fields',
                args:{
                    doctype: doctype,
                    callback(r){
                        console.log(r.message)
                        res(r.message)
                    }
                }
            })
        })
    }
})