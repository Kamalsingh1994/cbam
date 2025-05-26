frappe.provide("cbam.supplier")

// This is to load the translations from the server

if (!window.location.pathname.startsWith("/app")) {
    frappe.ready(() => {
        window.__translations = {};
        frappe.call({
        method: "cbam.api.get_translations",
        callback: function (r) {
            if (r.message) {
            window.__translations = r.message;
            }
        }
        });

        window.__ = function (key, args = []) {
            let translated = window.__translations[key] || key;
            return translated;
        };
    });
};
  
// end of translation

$.extend(cbam.supplier, {
    async confirm_supplier_details(){
        let supplier_details = await cbam.supplier.get_supplier();
        const cc_add = __("Company Contact and Address")
        let d = new frappe.ui.Dialog({
            title: __("Please Confrim your Operating Company Details"),
            fields: [
                {
                    label: __("Operating Company Name"),
                    fieldname: "supplier_name",
                    fieldtype: "Data",
                    
                    default: supplier_details.supplier_name,
                    read_only:1
                    //options: "\nSub Supplier\nCollegue"
                },
                {
                    label: `<strong>${cc_add}</strong>`,
                    fieldname: "sb1",
                    fieldtype: "Section Break",
                    
                    
                },
                {
                    label: __("Company Phone Number"),
                    fieldname: "company_phone_number",
                    fieldtype: "Data",
                    default: supplier_details.company_phone_number
                    
                },
                {
                    label: __("Company Email"),
                    fieldname: "company_email",
                    fieldtype: "Data",
                    default: supplier_details.company_email
                    
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                    
                    
                },
                {
                    label: __("Street and Number"),
                    fieldname: "street_and_number",
                    fieldtype: "Data",
                    default: supplier_details.street_and_number
                    
                },
                {
                    label: __("Zip Code"),
                    fieldname: "zip_code",
                    fieldtype: "Data",
                    default: supplier_details.zip_code
                    
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                    
                    
                },
                {
                    label: __("City"),
                    fieldname: "city",
                    fieldtype: "Data",
                    default: supplier_details.city
                    
                },
                {
                    label: __("Country"),
                    fieldname: "country",
                    fieldtype: "Data",
                    default: supplier_details.country
                    
                }
                

            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: __('Confirm Details'),
            //secondary_action_label: '',
            primary_action(values) {
                d.hide();
                return true
            },
            secondary_action(values) {
                
                
                
                no+=1
                
            }
        });
        d.show()
    },

    get_supplier(){
        return new Promise(function(resolve, reject) {
            frappe.call({
                method: "cbam.utils.supplier.get_supplier",
                args:{
                    
                },
                callback(r){
                    if(r.message){
                        resolve(r.message)
                    }
                }
            })
            
            
        });
    },
    get_supplier_details(){
        return new Promise(function(resolve, reject) {
            frappe.call({
                method: "cbam.utils.supplier.get_supplier_details",
                args:{
                    
                },
                callback(r){
                    if(r.message){
                        resolve(r.message)
                    }
                }
            })
            
            
        });
    },
    get_child_suppliers(filters){
        return new Promise(function(resolve, reject) {
            frappe.call({
                method: "cbam.utils.supplier.get_child_suppliers",
                args:{
                    filters: filters
                },
                callback(r){
                    if(r.message){
                        resolve(r.message)
                    }
                }
            })
            
            
        });
    },
    get_parent_supplier(){
        return new Promise(function(resolve, reject) {
            frappe.call({
                method: "cbam.utils.get_supplier",
                args:{
                    
                },
                callback(r){
                    if(r.message){
                        resolve(r.message)
                    }
                }
            })
            
            
        });
    },
    confirm_details(details){
        frappe.call({
            method: "cbam.utils.supplier.confirm_details",
            args:{
                values: details
            },
            callback(r){
                
            }
        })
    }

})