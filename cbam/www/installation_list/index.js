let CreateInstallationDialog;



// This is to load the translations from the server
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
    // args?.forEach((val, idx) => {
    //     translated = translated.replace(`{${idx}}`, val);
    // });
    return translated;
    };
});
// end of translation
  

  

window.addEventListener("DOMContentLoaded", () => {
    executeJS();
    refreshElements(frappe)
    document.querySelector('.add-new').addEventListener('click', function(e){
        CreateInstallationDialog()
    })
});

const refreshElements = function (frappe) {
    const contentContainer = document.querySelectorAll(".content-container");
    return new Promise((resolve, reject) => {
        frappe.call({
            method: "cbam.www.installation_list.index.get_installation_partial_html",
            callback: function(r) {
                if(r.message) {
                    contentContainer.forEach(container => {
                        container.remove();
                    });
                    document.querySelector('.list-row-container').insertAdjacentHTML('beforeend', r.message);
                    executeJS();
                    resolve(true);
                }
            }
        })
    })
}


function executeJS() {
    // This condition is to stop the rest of the code from executing if the user is not authorized.
    // frappe.call({
    //     method: "paystack_integration.utils.ex_utils.clear_website_cache",
    //     callback: function(r) {
    //     }
    // });

    const contentContainer = document.querySelectorAll(".content-container");
    const infoContainer = document.querySelectorAll(".info-container");
    const arrowEl = document.querySelectorAll(".arrow");
    const totalCheckbox = document.querySelector(".total-checkbox");
    const checkboxes = document.querySelectorAll(".checkbox");
    const selectedEl = document.querySelector(".selected-no");
    const statusFilter = document.querySelector(".status-filter");
    const dropDownCont = document.querySelectorAll(".options-abs");

    let boxesLen = 0;
    let selected = 0;
    let amount = 0;

    selectedEl.textContent = selected;
    
    const hideDropDown = function() {
        dropDownCont.forEach(dropDownEl => dropDownEl.classList.add("hidden"));
    }

    const createEmission = function(values, d) {
        frappe.call({
            method: "cbam.utils.create_new_doc",
            args: {
                doc: values
            },
            callback: async function(r) {
                if(r.message) {
                    const refreshed = await refreshElements(frappe)
                    if(refreshed) {
                        d.hide();
                    }
                }
            }
        })
    }

    const updateDoc = function(values, d) {
        frappe.call({
            method: "cbam.utils.update_doc",
            args: {
                doc: values
            },
            callback: async function(r) {
                if(r.message) {
                    const refreshed = await refreshElements(frappe);
                    if(refreshed) {
                        d.hide();
                    }
                }
            }
        })
    }

    window.addEventListener('click', function(e){
        if(!e.target.classList.contains("action-btn")) {
            hideDropDown()
        }
    })
    
    CreateInstallationDialog = async function(docName, docData=false, update=false){
        let d = new frappe.ui.Dialog({
            title: `${update ? __("Update Installation") : __("Add New Installation")}`,
            fields: [
                {
                    label: __("Name of Installation"),
                    fieldname: "name_of_the_installation",
                    fieldtype: "Data",
                    reqd: update? 0 : 1,
                    default: docData ? docData.name_of_the_installation : ""
                    
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
                    reqd: update? 0 : 1,
                    default: docData ? docData.city : ""
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Zip Code"),
                    fieldname: "zip_code",
                    fieldtype: "Data",
                    reqd: update? 0 : 1,
                    default: docData ? docData.zip_code : ""
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Country Code"),
                    fieldname: "country",
                    fieldtype: "Autocomplete",
                    options: await cbam.utils.get_links("Country", {}, ["Upper(code) as label", 'name as value']),
                    reqd: update? 0 : 1,
                    default: docData ? docData.country : ""
                },               
                {
                    label: __("Contact Person Details"),
                    fieldname: "cb1",
                    fieldtype: "Section Break",
                    depends_on: "eval:doc.contact_person == 'Different contact person'"
                },
                {
                    label: __("First Name"),
                    fieldname: "first_name",
                    fieldtype: "Data"
                },
                
                {
                    label: __("Last Name"),
                    fieldname: "last_name",
                    fieldtype: "Data"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Email"),
                    fieldname: "email",
                    fieldtype: "Data",
                    options: "Email"
                },
                {
                    label: __("Phone No"),
                    fieldname: "phone_number",
                    fieldtype: "Data"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break"
                },
                {
                    label: __("Is the installation tracking emissions data?"),
                    fieldname: "is_the_installation_tracking_emissions_data",
                    fieldtype: "Select",
                    options: "\nYes\nNo",
                    default: docData ? docData.is_the_installation_tracking_emissions_data : ""
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break"
                },
                {
                    label: __("Is the installation subject to an emission trading system?"),
                    fieldname: "is_the_installation_subject_to_an_emission_trading_system",
                    fieldtype: "Select",
                    options: "\nYes\nNo",
                    default: docData ? docData.is_the_installation_subject_to_an_emission_trading_system : ""
                },
                {
                    label: __("Which emission trading system (link to legal act)?"),
                    fieldname: "which_emission_trading_system_link_to_legal_act",
                    fieldtype: "Data",
                    depends_on: "eval:doc.is_the_installation_subject_to_an_emission_trading_system == 'Yes'",
                    default: docData ? docData.which_emission_trading_system_link_to_legal_act : ""
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break"
                },
                {
                    
                    label: __("Define how emissions get monitored, reported and verified:"),
                    fieldname: "define_how_emissions_get_monitored_reported_and_verified",
                    fieldtype: "Small Text",
                    default: docData ? docData.define_how_emissions_get_monitored_reported_and_verified : "",
                    depends_on: "eval:doc.is_the_installation_tracking_emissions_data == 'Yes'"
                    //options: "\nSub Supplier\nCollegue"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break"
                },
                {
                    label: __("Parent Operating Company"),
                    fieldname: "parent_operating_company",
                    fieldtype: "Data",
                    read_only: 1,
                    default: await cbam.supplier.get_supplier()
                }

            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: `${update ? __("Update Installation") : __("Create Installation")}`,
            //secondary_action_label: '',
            primary_action(values) {
                values.doctype = "CBAM Installation"
                if (update) {
                    values.name = docName
                    updateDoc(values, d);
                } else {
                    // cbam.utils.new_doc(values);
                    // d.hide();
                    createEmission(values, d);
                }
            },
            secondary_action(values) {
                no+=1
            }
        });

                    
        d.show();
    }

    const CreateEmissionDialog = async function(docName, docData=false, update=false){
        let d = new frappe.ui.Dialog({
            title: __("Add New Emission"),
            fields: [
                {
                    label: __("Label"),
                    fieldname: "label",
                    fieldtype: "Data",
                    reqd: update ? 0 : 1,
                    default: docData ? docData.label : ""                  
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Specific (direct) embedded emissions [tCO2/t]"),
                    fieldname: "specific_direct_embedded_emissions",
                    fieldtype: "Float",
                    description: "Example: 1.67 tCO2/t (t = tonnes of product)",
                    reqd: update ? 0 : 1,
                    default: docData ? docData.specific_direct_embedded_emissions : "" 
                   
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break",
                },
                {
                    label: __("Source of electricity"),
                    fieldname: "source_of_electricity",
                    fieldtype: "Select",
                    options: await cbam.utils.get_field_options("CBAM Emission Data", "source_of_electricity", false),
                    reqd: update ? 0 : 1,
                    default: docData ? docData.source_of_electricity : ""
                   
                },
                {
                    label: __("Electricity consumed [MWh/t]"),
                    fieldname: "electricity_consumed",
                    fieldtype: "Float",
                    reqd: update ? 0 : 1,
                    default: docData ? docData.electricity_consumed : ""
                    
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Production Method"),
                    fieldname: "production_method",
                    fieldtype: "Select",
                    options: await cbam.utils.get_field_options("CBAM Emission Data", "production_method", false),
                    reqd: update ? 0 : 1,
                    default: docData ? docData.production_method : ""
                    
                },
                {
                    label: __("Installation"),
                    fieldname: "cbam_installation",
                    fieldtype: "Data",
                    default: docName,
                    hidden: 0,
                    read_only: 1
                },
                {
                    label: __(""),
                    fieldname: "cb2",
                    fieldtype: "Section Break",
                },
                {
                    label: __("Indirect Emission Factor [tCO2/MWh]"),
                    fieldname: "indirect_emission_factor",
                    fieldtype: "Float",
                    default: docData ? docData.indirect_emission_factor : "",
                    description: "Your specific indirect emission factor. If not set the national indirect emission factor defined by the IEA is used",
                },
                {
                    label: __("Source of Indirect Emission Factor"),
                    fieldname: "source_of_indirect_emission_factor",
                    fieldtype: "Data",
                    default: docData ? docData.source_of_indirect_emission_factor : "",
                    depends_on: "eval:doc.indirect_emission_factor",
                    mandatory_depends_on: "eval:doc.indirect_emission_factor"
                },
                {
                    label: __(""),
                    fieldname: "cb2",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Specific (indirect) embedded emissions [tCO2/t]"),
                    fieldname: "specific_indirect_embedded_emissions",
                    fieldtype: "Float",
                    default: docData ? docData.specific_indirect_embedded_emissions : "",
                    depends_on: "eval:doc.indirect_emission_factor",
                },
                {
                    label: __(""),
                    fieldname: "cb2",
                    fieldtype: "Section Break"
                },
                {
                    label: __("Emission Notes (sent to declarant when submitting goods)"),
                    fieldname: "emission_notes",
                    fieldtype: "Small Text",
                    mandatory_depends_on: "eval:!doc.specific_direct_embedded_emissions",
                    description: __("Explanation mandatory if no emission data entered"),
                },
                {
                    label: __(""),
                    fieldname: "cb2",
                    fieldtype: "Column Break",
                },


            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: `${update ? __("Update Emission") : __("Create Emission")}`,
            //secondary_action_label: '',
            primary_action(values) {
                values.doctype = "CBAM Emission Data"
                if (update) {
                    values.name = docName
                    updateDoc(values, d);
                } else {
                    // cbam.utils.new_doc(values)
                    createEmission(values, d);
                }      
            },
            secondary_action(values) {
                
                
                
                no+=1
                
            }
        });

                    
        d.show();
    }

    
    contentContainer.forEach(container => {
        const absBtn = container.querySelectorAll(".add-newemission");
        const editBtn = container.querySelectorAll(".edit-btn");

        absBtn.forEach(btn => {
            btn.addEventListener("click", function() {
                const docName = container.querySelector(".inv-name").dataset.name;
                CreateEmissionDialog(docName);
                
            })
        })

        container.addEventListener("click", function(e) {
            if(e.target.classList.contains("action-btn")) {
                // Hide all the visible drop downs
                const curDropDown = container.querySelector(".options-abs");

                if(!curDropDown.classList.contains("hidden")) {
                    curDropDown.classList.add("hidden");
                    return;
                }

                hideDropDown();

                // Show only the drop down which is clicked

                if(curDropDown.classList.contains("hidden")) {
                    curDropDown.classList.remove("hidden");
                }
            }

            if(e.target.classList.contains("edit-btn")) {
                const docName = container.querySelector(".inv-name").dataset.name;
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "CBAM Installation",
                        name: docName  // Replace with the actual document name
                    },
                    callback: function(response) {
                        if (response.message) {
                            CreateInstallationDialog(docName, response.message, true);
                        }
                    }
                });
            }
            
            if(e.target.classList.contains("edit-emission")) {
                const docName = container.querySelector(".edit-emission").dataset.emission;
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "CBAM Emission Data",
                        name: docName  // Replace with the actual document name
                    },
                    callback: function(response) {
                        if (response.message) {
                            CreateEmissionDialog(docName, response.message, true);
                        }
                    }
                });
                
            }
        })
    })

    const setTotalCheckBoxes = (value) => {
        totalCheckbox.checked  = value;
    }
    
    // To apply the filter on the Invoices Content Container
    const setStatusFilter = function (status) {
        // Reset the values
        totalCheckbox.checked = false;
        selected = 0;
        selectedEl.textContent = selected;
        
        contentContainer.forEach(container => {
            // Show all the elements before checking for the filter condition
            container.classList.remove("hidden");
            
            container.querySelector(".checkbox").checked = false;
            const curStatus = container.querySelector(".status").textContent.toLowerCase();
            
            // The first condition is incase no filter is applied we want to show all the goods
            if(!status) {
                container.classList.remove("hidden");
                // To hide the invoices which are not the same as filter
            } else if(status.toLowerCase() != curStatus) {
                container.classList.add("hidden");
            }
        })
    };

    statusFilter.addEventListener("change", function() {
        const selectedValue = this.value;
        
        setStatusFilter(selectedValue);
    })

    // This checks the visible checkboxes in set the boxes lenght value (This is in case filter is applied an some invoices are hidden)
    const checkVisibleBoxes = function() {
        boxesLen = 0;
        contentContainer.forEach(container => {
            const status = container.querySelector(".status").dataset.status;
            if(!container.classList.contains("hidden") && status.toLowerCase() != "verifying payment") {
                boxesLen++;
            }
        })
    };

    totalCheckbox.addEventListener("click", function() {
        if(totalCheckbox.checked) {
            //checkVisibleBoxes();
            selected = boxesLen;
            selectedEl.textContent = selected;
            contentContainer.forEach(container => {
                const status = container.querySelector(".status").dataset.status;
                if(!container.classList.contains("hidden")) {
                    const box = container.querySelector(".checkbox");
                    box.checked = true;
                }
            });
        } else {
            selected = 0;
            amount = 0;
            selectedEl.textContent = selected;
            checkboxes.forEach(box => {
                box.checked = false;
            });
        }
    });

    contentContainer.forEach(container => {
        // Checkbox logic
        //checkVisibleBoxes();
        
        const box = container.querySelector(".checkbox");
        box.addEventListener("click", function() {
            if(box.checked) {
                selected++;
            } else {
                selected--;
            }

            selectedEl.textContent = selected;
            
            if(selected === boxesLen) {
                setTotalCheckBoxes(true);
            }
            
            checkboxes.forEach(b => {
                if(!b.checked) {
                    setTotalCheckBoxes(false);
                    return;
                }
            })

        })

        // container.addEventListener("click", function(e) {
        //     if (e.target.classList.contains("arr-icon")) {
        //         const childInfoCon = container.querySelector(".info-container");
        //         const isCurrentlyHidden = childInfoCon.classList.contains("hidden");
                
        //         infoContainer.forEach(c => c.classList.add("hidden"));
        //         arrowEl.forEach(arrow => arrow.setAttribute("href", "#es-line-down"));
                
        //         if (isCurrentlyHidden) {
        //             childInfoCon.classList.remove("hidden");
        //             container.querySelector(".arrow").setAttribute("href", "#es-line-up");
        //         } else {
        //             childInfoCon.classList.add("hidden");
        //             container.querySelector(".arrow").setAttribute("href", "#es-line-down");
        //         }
        //     }
        // });
    })

    if(document.querySelector(".list-container")) {
        const contentContainer = document.querySelectorAll(".content-container");
        const infoContainer = document.querySelectorAll(".info-container");
        const arrowEl = document.querySelectorAll(".arrow");

        const currentDomain = window.location.origin;

        let exPrintFormat = "";

        // frappe.call({
        //     method: 'paystack_integration.utils.ex_utils.get_print_format',
        //     callback: function(r) {
        //         if(r.message) {
        //             exPrintFormat = r.message;
        //         }
        //     }
        // });

        contentContainer.forEach(parentContainer => {
            parentContainer.addEventListener("click", function(e) {
                if (e.target.classList.contains("arr-icon")) {
                    const childInfoCon = parentContainer.querySelector(".info-container");
                    const isCurrentlyHidden = childInfoCon.classList.contains("hidden");
                    
                    infoContainer.forEach(c => c.classList.add("hidden"));
                    arrowEl.forEach(arrow => arrow.setAttribute("href", "#es-line-down"));
                    
                    if (isCurrentlyHidden) {
                        childInfoCon.classList.remove("hidden");
                        parentContainer.querySelector(".arrow").setAttribute("href", "#es-line-up");
                    } else {
                        childInfoCon.classList.add("hidden");
                        parentContainer.querySelector(".arrow").setAttribute("href", "#es-line-down");
                    }
                }
            });
        });

        contentContainer.forEach(container => {
            container.addEventListener("click", function(e) {
                if(e.target.classList.contains("print-btn")) {
                    const invName = container.querySelector(".inv-name").dataset.name;
                    window.open(`${currentDomain}/printview?doctype=Sales%20Invoice&name=${invName}&trigger_print=1&format=${exPrintFormat || "Standard"}r&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en`);
                    // window.open(`${currentDomain}/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name=${invName}&&format=${exPrintFormat || "Standard"}&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en`, '_blank');
                }
            })
        })
    }
}