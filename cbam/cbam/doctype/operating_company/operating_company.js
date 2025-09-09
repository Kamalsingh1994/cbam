// Copyright (c) 2024, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Operating Company", {
	refresh(frm) {
        if(frm.doc.status != "CBAM Rep User Conflict" ){
            frm.add_custom_button(__("Send Signup Request"), function(){
                frappe.call({
                    method: "send_signup_request",
                    doc: frm.doc,
                    callback(r){
                        msgprint("request sent successfully")
                    }
                })
            })
        }
        if(frappe.user.has_role("System Manager")){
            frm.add_custom_button(__("Update Contact"), function(){
            
                let d = new frappe.ui.Dialog({
                    "title": "Update Contact Details",
                    fields :[
                        {
                            label: 'Contact Type',
                            fieldname: 'type',
                            fieldtype: 'Select',
                            default: "Commercial Contact",
                            options: "\nCommercial Contact\nCBAM Representative",
                            reqd: 1,
                            onchange: function() {
                                if(d.get_value("type")== "Commercial Contact"){
                                    d.set_value("first_name", frm.doc.main_contact_employee_first_name)
                                    d.set_value("email", frm.doc.main_contact_employee_email)
                                    d.set_value("position", frm.doc.main_contact_employee_position)
                                    d.set_value("last_name", frm.doc.main_contact_employee_last_name)
                                    d.set_value("phone_no", frm.doc.main_contact_employee_phone_number)
                                }
                                else if(d.get_value("type")== "CBAM Representative"){
                                    d.set_value("first_name", frm.doc.cbam_representive_employee_first_name)
                                    d.set_value("email", frm.doc.cbam_representive_employee_email)
                                    d.set_value("position", frm.doc.cbam_representive_employee_position)
                                    d.set_value("last_name", frm.doc.cbam_representive_last_name)
                                    d.set_value("phone_no", frm.doc.cbam_representive_employee_phone_number)
                                }
                            }
                        },
                        {
                            fieldtype: "Section Break",
                            depends_on: "eval:doc.type"
                        },
                        {
                            label: 'First Name',
                            fieldname: 'first_name',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            label: 'Email',
                            fieldname: 'email',
                            fieldtype: 'Data',
                            options: "Email",
                            reqd: 1
                        },
                        {
                            label: 'Position',
                            fieldname: 'position',
                            fieldtype: 'Data'
                        },
                       
                        {
                            fieldtype: "Column Break"
                        },
                        {
                            label: 'Last Name',
                            fieldname: 'last_name',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            label: 'Phone No',
                            fieldname: 'phone_no',
                            fieldtype: 'Data'
                        },
                    ],
                    size: 'large',
                    primary_action_label: "Update Contact",
                    primary_action(values){
                        values.name = frm.doc.name;
                        frappe.call({
                            method: "update_contact",
                            doc: frm.doc,
                            args:{
                                values: values
                            },
                            freeze: true, 
                            freeze_message: "Updating Contact Details",
                            callback(r){
                                
                                msgprint("Contact Updated Successfully")
                                d.hide()
                                frm.reload_doc()
                            }
                        })
                    }
                })
                d.show()
    
                
                
            })
        }
        
	},
    
});
