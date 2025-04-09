window.addEventListener("DOMContentLoaded", executeJS);

function executeJS() {
    const contentContainer = document.querySelectorAll(".content-container");
    const infoContainer = document.querySelector(".info-container");
    const cbamSection = document.querySelector("#cbam_representive");
    const company_contact = document.querySelector("#company_contact");
    const commercial_contact = document.querySelector("#commerical_contact");
    const cbam_rep = document.querySelector("#cbam_rep");
    const cbamBtnCont = document.querySelector(".cbam-btn-container");

    const confirmDetails = function(values, d) {
        frappe.call({
            method: "cbam.utils.supplier.confirm_details",
            args: {
                values: values
            },
            callback: function(r) {
                frappe.call({
                    method: "cbam.www.operating_company.index.get_operating_company_partial_html",
                    callback: function(r) {
                        if(r.message) {
                            contentContainer.forEach(container => {
                                container.remove();
                            });
                            document.querySelector('.list-row-container').insertAdjacentHTML('beforeend', r.message);
                            executeJS();
                        }
                    }
                })
                d.hide();
            }
        })
    }

    let doc_dict = document.querySelector("#doc_dict").textContent;
    doc_dict = doc_dict.replace(/datetime\.datetime\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)\)/g, (match, year, month, day, hour, minute, second, millisecond) => {
        const date = new Date(Date.UTC(year, month - 1, day, hour, minute, second, millisecond / 1000));
        return `"${date.toISOString()}"`;
    });
      
    // 2. Replace 'None' with 'null'
    doc_dict = doc_dict.replace(/None/g, "null");
    
    // 3. Replace single quotes with double quotes
    doc_dict = doc_dict.replace(/'/g, '"');
    
    // Now parse the modified string into a JavaScript object
    const supplier_details = JSON.parse(doc_dict);

    let cbamHasFieldVals = true;;

    cbamSection.querySelectorAll(".tc-field").forEach(field => {
        if(!field.textContent) {
            cbamHasFieldVals = false;
        }
    })

    if(!cbamHasFieldVals) {
        cbamBtnCont.classList.remove("hidden");
    }

    company_contact.addEventListener("click", function(e){     
        e.preventDefault();   
        UpdateContactDetails();
    })

    commercial_contact.addEventListener("click", function(e) {
        e.preventDefault();
        UpdateCommericalDetails();
    })

    cbam_rep.addEventListener("click", function(e) {
        e.preventDefault();
        UpdateRepresentativeDetails();
    })

    const UpdateContactDetails = async function(){
            const cc_add = __("Company Contact and Address")
            let d = new frappe.ui.Dialog({
                title: __("Please Confrim your Operating Company Details"),
                fields: [
                    {
                        label: __("Operating Company Name"),
                        fieldname: "supplier_name",
                        fieldtype: "Data",
                        
                        default: supplier_details.supplier_name,
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
                        default: supplier_details.company_email,
                        options: "Email"
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
                        default: supplier_details.street_and_number,
                    },
                    {
                        label: __("Zip Code"),
                        fieldname: "zip_code",
                        fieldtype: "Data",
                        default: supplier_details.zip_code,
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
                        default: supplier_details.city,
                    },
                    {
                        label: __("Country"),
                        fieldname: "country",
                        fieldtype: "Autocomplete",
                        options: await cbam.utils.get_links("Country"),
                        default: supplier_details.country,
                    }    
                ],
                size: 'extra-large', // small, large, extra-large 
                primary_action_label: __('Confirm Details'),
                //secondary_action_label: '',
                primary_action(values) {
                    confirmDetails(values, d)                    
                },
                secondary_action(values) {                    
                    no+=1                    
                }
            });
            d.show()        
    }

    const UpdateCommericalDetails = async function(){
            const cc_details = __("Commercial Contact Details")
            let d = new frappe.ui.Dialog({
                title: __("Please Confirm your CBAM Representative Contact Details"),
                fields: [
                    {
                        label: __("Operating Company"),
                        fieldname: "supplier_name",
                        fieldtype: "Data",
                        
                        default: supplier_details.supplier_name,
                        read_only:1
                        //options: "\nSub Supplier\nCollegue"
                    },
                    {
                        label: `<strong>${cc_details}</strong>`,
                        fieldname: "sb1",
                        fieldtype: "Section Break",
                    },
                    {
                        label: __("Last Name"),
                        fieldname: "main_contact_employee_last_name",
                        fieldtype: "Data",
                        default: supplier_details.main_contact_employee_last_name,
                    },
                    {
                        label: __("Position"),
                        fieldname: "main_contact_employee_position",
                        fieldtype: "Data",
                        default: supplier_details.main_contact_employee_position
                    },
                    {
                        label: __(""),
                        fieldname: "cb1",
                        fieldtype: "Column Break",
                    },
                    {
                        label: __("First Name"),
                        fieldname: "main_contact_employee_first_name",
                        fieldtype: "Data",
                        default: supplier_details.main_contact_employee_first_name,
                    },
                    {
                        label: __("Phone Number"),
                        fieldname: "main_contact_employee_phone_number",
                        fieldtype: "Data",
                        default: supplier_details.main_contact_employee_phone_number
                    },
                    {
                        label: __(""),
                        fieldname: "cb1",
                        fieldtype: "Column Break",
                    },
                    {
                        label: __("Email"),
                        fieldname: "main_contact_employee_email",
                        fieldtype: "Data",
                        default: supplier_details.main_contact_employee_email,
                        options: "Email",
                        read_only: 1
                    },
                ],
                size: 'extra-large', // small, large, extra-large 
                primary_action_label: __('Confirm Details'),
                //secondary_action_label: '',
                primary_action(values) {
                    confirmDetails(values, d);
                },
                secondary_action(values) {                    
                    no+=1                    
                }
            });
            d.show()      
    }

    const UpdateRepresentativeDetails = async function(){

        const cbr_details = __("CBAM Representative Details")
        let d = new frappe.ui.Dialog({
            title: __("Please Confirm your Commercial Contact Details"),
            fields: [
                {
                    label: __("Operating Company"),
                    fieldname: "supplier_name",
                    fieldtype: "Data",
                    default: supplier_details.supplier_name,
                    read_only:1
                    //options: "\nSub Supplier\nCollegue"
                },
                {
                    label: `<strong>${cbr_details}</strong>`,
                    fieldname: "sb1",
                    fieldtype: "Section Break",
                },
                {
                    label: __("Last Name"),
                    fieldname: "cbam_representive_last_name",
                    fieldtype: "Data",
                    default: supplier_details.cbam_representive_last_name,
                },
                {
                    label: __("First Name"),
                    fieldname: "cbam_representive_employee_first_name",
                    fieldtype: "Data",
                    default: supplier_details.cbam_representive_employee_first_name,
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Email"),
                    fieldname: "cbam_representive_employee_email",
                    fieldtype: "Data",
                    default: supplier_details.cbam_representive_employee_email,
                    options: "Email",
                    read_only: supplier_details.cbam_representative_user ? 1 : 0
                },
                {
                    label: __("Phone Number"),
                    fieldname: "cbam_representive_employee_phone_number",
                    fieldtype: "Data",
                    default: supplier_details.cbam_representive_employee_phone_number,
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Position"),
                    fieldname: "cbam_representive_employee_position",
                    fieldtype: "Data",
                    default: supplier_details.cbam_representive_employee_position
                }
            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: __('Confirm Details'),
            //secondary_action_label: '',
            primary_action(values) {
                confirmDetails(values, d);
            },
            secondary_action(values) {                    
                no+=1                    
            }
        });
        d.show()      
    }    
}