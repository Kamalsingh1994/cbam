let CreateInstallationDialog;

window.addEventListener("DOMContentLoaded", () => {
    executeJS();

    document.querySelector('.add-new').addEventListener('click', function(e){
        CreateInstallationDialog()
    })
});

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
            callback: function(r) {
                console.log(r.message);
                if(r.message) {
                    frappe.call({
                        method: "cbam.www.installation_list.index.get_installation_partial_html",
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
            }
        })
    }

    window.addEventListener('click', function(e){
        if(!e.target.classList.contains("action-btn")) {
            hideDropDown()
        }
    })
    
    CreateInstallationDialog = async function(docName){
        let d = new frappe.ui.Dialog({
            title: `Add New Installation`,
            fields: [
                {
                    label: __("Name of Installation"),
                    fieldname: "name_of_the_installation",
                    fieldtype: "Data",
                    reqd:1
                   
                    
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
                    reqd:1
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
                    fieldtype: "Data",
                },
                
                {
                    label: __("Last Name"),
                    fieldname: "last_name",
                    fieldtype: "Data",
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
                    options: "Email",
                },
                {
                    label: __("Phone No"),
                    fieldname: "phone_number",
                    fieldtype: "Data",
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break",
                },
                {
                    label: __("Is the installation tracking emissions data?"),
                    fieldname: "is_the_installation_tracking_emissions_data",
                    fieldtype: "Select",
                    options: "\nYes\nNo"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Is the installation subject to an emission trading system?"),
                    fieldname: "is_the_installation_subject_to_an_emission_trading_system",
                    
                    fieldtype: "Select",
                    options: "\nYes\nNo"
                },
                
                {
                    label: __("Which emission trading system (link to legal act)?"),
                    fieldname: "which_emission_trading_system_link_to_legal_act",
                    fieldtype: "Data",
                    depends_on: "eval:doc.is_the_installation_subject_to_an_emission_trading_system == 'Yes'"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Section Break",
                },
                {
                    
                    label: __("Define how emissions get monitored, reported and verified:"),
                    fieldname: "reason",
                    fieldtype: "Small Text",
                    default: "",
                    depends_on: "eval:doc.is_the_installation_tracking_emissions_data == 'Yes'"
                    //options: "\nSub Supplier\nCollegue"
                }

            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: 'Create Installation',
            //secondary_action_label: '',
            primary_action(values) {
                values.doctype = "CBAM Installation"
                // cbam.utils.new_doc(values);
                // d.hide();
                createEmission(values, d);
            },
            secondary_action(values) {
                no+=1
            }
        });

                    
        d.show();
    }

    const CreateEmissionDialog = function(docName){
        let d = new frappe.ui.Dialog({
            title: `Add New Emission`,
            fields: [
                
                {
                    label: __("Label"),
                    fieldname: "label",
                    fieldtype: "Data",
                    reqd:1
                   
                    
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
                    description: "Example: 1.67 tCO2/t (t = tonnes of product)"
                   
                    
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
                    options: 'Direct technical link to electricity generator\n(Bilateral) power purchase agreement\nReceived from the grid'
                   
                    
                },
                {
                    label: __("Attach"),
                    fieldname: "cb1",
                    fieldtype: "Attach",
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Electricity consumed [MWh/t]"),
                    fieldname: "electricity_consumed",
                    fieldtype: "Float",
                   
                    
                },
                {
                    label: __("Installation"),
                    fieldname: "cbam_installation",
                    fieldtype: "Data",
                    default: docName,
                    hidden: 1
                }
            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: 'Create Emission',
            //secondary_action_label: '',
            primary_action(values) {
                values.doctype = "CBAM Emission Data"
                // cbam.utils.new_doc(values)
                createEmission(values, d);                
            },
            secondary_action(values) {
                
                
                
                no+=1
                
            }
        });

                    
        d.show();
    }

    document.querySelector('.add-newemission').addEventListener('click', function(e){
        
    })

    contentContainer.forEach(container => {
        const absBtn = container.querySelectorAll(".add-newemission");

        absBtn.forEach(btn => {
            btn.addEventListener("click", function() {
                const docName = container.querySelector(".inv-name").dataset.name;
                console.log(docName)
                CreateEmissionDialog(docName)
                
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