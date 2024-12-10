frappe.provide("cbam.utils")

$.extend(cbam.utils, {
    add_new_supplier(doc){
        console.log("aaa")
    },
    new_doc(doc){
        frappe.call({
            method: "cbam.utils.create_new_doc",
            args:{doc: doc},
            freeze: true,
            freeze_message: `Creating new ${doc.doctype}, please wait....`,
            callback(r){
                msgprint("Created new doc.")
            }
        })
    },
    _get_links(doctype){
       return new Promise(function(reslove, reject) {
            frappe.call({
                method: "cbam.utils.links.get_links",
                args:{
                    doctype: doctype
                },
                callback(r){
                    if(r.message){
                        reslove(r.message)
                    }
                }
            })
            
            
        });
    
    },
    async get_links(doctype){
        return await cbam.utils._get_links(doctype);
    }
})