// // Copyright (c) 2024, phamos GmbH and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Operating Company", {
// 	refresh(frm) {
//         if(frm.doc.status != "CBAM Rep User Conflict" ){
//             frm.add_custom_button(__("Send Signup Request"), function(){
//                 frappe.call({
//                     method: "send_signup_request",
//                     doc: frm.doc,
//                     callback(r){
//                         msgprint("request sent successfully")
//                     }
//                 })
//             })
//         }
//         if(frappe.user.has_role("System Manager")){
//             frm.add_custom_button(__("Update Contact"), function(){
            
//                 let d = new frappe.ui.Dialog({
//                     "title": "Update Contact Details",
//                     fields :[
//                         {
//                             label: 'Contact Type',
//                             fieldname: 'type',
//                             fieldtype: 'Select',
//                             options: "\nCommercial Contact\nCBAM Representative",
//                             reqd: 1,
//                             onchange: function() {
//                                 if(d.get_value("type")== "Commercial Contact"){
//                                     d.set_value("first_name", frm.doc.main_contact_employee_first_name)
//                                     d.set_value("email", frm.doc.main_contact_employee_email)
//                                     d.set_value("position", frm.doc.main_contact_employee_position)
//                                     d.set_value("last_name", frm.doc.main_contact_employee_last_name)
//                                     d.set_value("phone_no", frm.doc.main_contact_employee_phone_number)
//                                 }
//                                 else if(d.get_value("type")== "CBAM Representative"){
//                                     d.set_value("first_name", frm.doc.cbam_representive_employee_first_name)
//                                     d.set_value("email", frm.doc.cbam_representive_employee_email)
//                                     d.set_value("position", frm.doc.cbam_representive_employee_position)
//                                     d.set_value("last_name", frm.doc.cbam_representive_last_name)
//                                     d.set_value("phone_no", frm.doc.cbam_representive_employee_first_name)
//                                 }
//                             }
//                         },
//                         {
//                             fieldtype: "Section Break",
//                             depends_on: "eval:doc.type"
//                         },
//                         {
//                             label: 'First Name',
//                             fieldname: 'first_name',
//                             fieldtype: 'Data'
//                         },
//                         {
//                             label: 'Email',
//                             fieldname: 'email',
//                             fieldtype: 'Data',
//                             options: "Email",
//                             reqd: 1
//                         },
//                         {
//                             label: 'Position',
//                             fieldname: 'position',
//                             fieldtype: 'Data'
//                         },
                       
//                         {
//                             fieldtype: "Column Break"
//                         },
//                         {
//                             label: 'Last Name',
//                             fieldname: 'last_name',
//                             fieldtype: 'Data',
//                             reqd: 1
//                         },
//                         {
//                             label: 'Phone No',
//                             fieldname: 'phone_no',
//                             fieldtype: 'Data'
//                         },
//                     ],
//                     size: 'large',
//                     primary_action_label: "Update Contact",
//                     primary_action(values){
                        
//                         frappe.call({
//                             method: "update_contact",
//                             doc: frm.doc,
//                             args:{
//                                 values: values
//                             },
//                             freeze: true, 
//                             freeze_message: "Updating Contact Details",
//                             callback(r){
                                
//                                 msgprint("Contact Updated Successfully")
//                                 d.hide()
//                                 frm.refresh_doc()
//                             }
//                         })
//                     }
//                 })
//                 d.show()
    
                
                
//             })
//         }
        
// 	},
    
// });



// Copyright (c) 2024, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Operating Company", {
	refresh(frm) {
		if (frappe.user.has_role("System Manager")) {
			frm.add_custom_button("Update Contact", function () {
				show_contact_update_dialog(frm);
			});
		}
	}
});

function show_contact_update_dialog(frm) {
	const table_fields = [
		{ fieldname: "contact_email", label: "Email", fieldtype: "Data", in_list_view: 1, reqd: 1, width: 350},
		{ fieldname: "first_name", label: "First Name", fieldtype: "Data", in_list_view: 1, width: 150,},
		{ fieldname: "last_name", label: "Last Name", fieldtype: "Data", in_list_view: 1, width: 150, },
		{ fieldname: "phone_no", label: "Phone No", fieldtype: "Data", in_list_view: 1, width: 150, },
		{ fieldname: "position", label: "Position", fieldtype: "Data", in_list_view: 1, width: 150, }
	];

	let dialog = new frappe.ui.Dialog({
        size: 'large',
		title: "Update Contact Details",
		fields: [
			{
				fieldname: "contact_type",
				label: "Contact Type",
				fieldtype: "Select",
				options: ["Commercial Contact", "CBAM Representative"],
				reqd: 1,
				onchange: function () {
					let type = dialog.get_value("contact_type");
					let filtered_rows = frm.doc.contact_persons
						.filter(row => row.contact_type === type)
						.map(row => ({
							idx: row.idx,
							contact_email: row.contact_email,
							first_name: row.first_name,
							last_name: row.last_name,
							phone_no: row.phone_no,
							position: row.position
						}));
					dialog.fields_dict.contacts.df.data = filtered_rows;
					dialog.fields_dict.contacts.grid.refresh();
				}
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "contacts",
				fieldtype: "Table",
				label: "Contacts",
				cannot_add_rows: false,
				in_place_edit: true,
				fields: table_fields
			}
		],
		primary_action_label: "Update",
		primary_action(values) {
			const selected_type = values.contact_type;
			const updated_contacts = values.contacts;

			frm.doc.contact_persons.forEach(row => {
				if (row.contact_type === selected_type) {
					let updated = updated_contacts.find(u => u.idx === row.idx);
					if (updated) {
						row.contact_email = updated.contact_email;
						row.first_name = updated.first_name;
						row.last_name = updated.last_name;
						row.phone_no = updated.phone_no;
						row.position = updated.position;
					}
				}
			});

			frm.save().then(() => {
				frappe.msgprint("Contacts updated.");
				frm.refresh_field("contact_persons");
				dialog.hide();
			});
		}
	});

    dialog.show();
    
}
