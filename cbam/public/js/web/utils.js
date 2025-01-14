frappe.provide("cbam.utils")

$.extend(cbam.utils, {
    
    new_doc(doc){
        frappe.call({
            method: "cbam.utils.create_new_doc",
            args:{doc: doc},
            freeze: true,
            freeze_message: `Creating new ${doc.doctype}, please wait....`,
            callback(r){
                msgprint(`New ${doc.doctype}: ${r.message.name} created`)
            }
        })
    },

    _get_links(doctype, filters, fields){
       return new Promise(function(reslove, reject) {
            frappe.call({
                method: "cbam.utils.links.get_links",
                args:{
                    doctype: doctype,
                    filters: filters,
                    fields: fields
                },
                callback(r){
                    if(r.message){
                        reslove(r.message)
                    }
                }
            })
            
            
        });
    
    },
    async get_links(doctype, filters, fields){
        return await cbam.utils._get_links(doctype, filters, fields);
    },
    _get_installation(emission){
        return new Promise(function(reslove, reject) {
             frappe.call({
                 method: "cbam.utils.links.get_installation",
                 args:{
                    emission: emission
                 },
                 callback(r){
                     if(r.message){
                         reslove(r.message)
                     }
                 }
             })
             
             
         });
     
     },
     async get_installation(emission){
        return await cbam.utils._get_installation(emission);
    },
    set_local_storage(){
        
        frappe.call({
            method: "cbam.utils.get_supplier",
            args:{
                
            },
            callback(r){
                if(r.message){
                    localStorage.setItem("parent_supplier", r.message)
                }
            }
        })
    },
    get_parent_supplier(){
        
        if (!localStorage.getItem("parent_supplier")){
            cbam.utils.set_local_storage()  
        }
        return localStorage.getItem("parent_supplier")

    },
    
            
        
})
