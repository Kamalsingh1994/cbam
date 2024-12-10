window.addEventListener("DOMContentLoaded", function() {
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
    window.addEventListener('click', function(e){
        if(!e.target.classList.contains("action-btn")) {
            hideDropDown()
        }
    })

    const CreateForwardDialog = function(docName){
        let d = new frappe.ui.Dialog({
            title: `Forwarding Request`,
            fields: [
                {
                    label: __("Forward to"),
                    fieldname: "forward_to_party",
                    fieldtype: "Select",
                    default: "",
                    options: "\nSub Supplier\nCollegue"
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Sub Supplier"),
                    fieldname: "supplier",
                    fieldtype: "Link",
                    default: "",
                    options: "Supplier",
                    depends_on: "eval:doc.forward_to_party == 'Sub Supplier'"
                },
                {
                    label: __("Employee"),
                    fieldname: "employee",
                    fieldtype: "Link",
                    default: "",
                    options: "Supplier Employee",
                    depends_on: "eval:doc.forward_to_party == 'Collegue'"
                },

            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: 'Submit',
            primary_action(values) {
                console.log(values);
                d.hide();
            }
        });

                   
        d.show();
    }

    const CreateRejectDialog = function(docName){
        let d = new frappe.ui.Dialog({
            title: `Rejecting Request`,
            fields: [
                {
                    label: __("Reason to Reject"),
                    fieldname: "reason",
                    fieldtype: "Small Text",
                    default: "",
                    //options: "\nSub Supplier\nCollegue"
                }

            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: 'Reject Goods',
            //secondary_action_label: '',
            primary_action(values) {
                console.log(values);
                d.hide();
            },
            secondary_action(values) {
                
               
                
                no+=1
                
            }
        });

                   
        d.show();
    }

    

    const split_fields = function(no){
        return [
            {
                label: __("Split with"),
                fieldname: `forward_to_party_${no}`,
                fieldtype: "Select",
                default: "",
                options: "\nSub Supplier\nInstallation",
                change: () =>{
                   console.log("Chanfe")
                    cur_dialog.refresh()
                }
            },
            {
                label: __(""),
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Sub Supplier"),
                fieldname: `supplier_${no}`,
                fieldtype: "Link",
                default: "",
                //options: "Supplier",
                depends_on: `eval:doc.forward_to_party_${no} == 'Sub Supplier'`
            },
            {
                label: __("Installation"),
                fieldname: `installation_${no}`,
                fieldtype: "Link",
                default: "",
                //options: "Installation",
                depends_on: `eval:doc.forward_to_party_${no} == 'Installation'`
            },
            {
                label: __(""),
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Qty to Split"),
                fieldname: `qty_${no}`,
                fieldtype: "Float",
                depends_on: `eval:doc.forward_to_party_${no}`
            },
            
            
        ]
    }
    



   const CreateEmissionDialog = async function(){
    let d = new frappe.ui.Dialog({
        title: `Rejecting Request`,
        fields: [
            {
                label: __("Emission"),
                fieldname: "emission_data",
                fieldtype: "Autocomplete",
                default: "",
                options: await cbam.utils.get_links("CBAM Emission Data")
                //options: "\nSub Supplier\nCollegue"
            }

        ],
        size: 'extra-large', // small, large, extra-large 
        primary_action_label: 'Reject Goods',
        //secondary_action_label: '',
        primary_action(values) {
            console.log(values);
            d.hide();
        },
        secondary_action(values) {
            
           
            
            no+=1
            
        }
    });

               
    d.show();
    }



    const CreateSplitDialog = function(docName){
        let fields = split_fields(1);
        let no = 1;
        let d = new frappe.ui.Dialog({
            title: `Spliting Goods`,
            fields: fields,
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: 'Split Goods',
            secondary_action_label: 'Add More',
            primary_action(values) {
                console.log(values);
                d.hide();
            },
            secondary_action(values) {
                
                d.add_fields(split_fields(no+1))
                d.refresh()
                no+=1
                
            }
        });

                   
        d.show();
    }

 

    contentContainer.forEach(container => {
        const absBtn = container.querySelectorAll(".abs-option-btn");

        absBtn.forEach(btn => {
            btn.addEventListener("click", function() {
                const docName = container.querySelector(".inv-name").dataset.name;
                const action = btn.dataset.action;
                if(action == "Split"){
                    CreateSplitDialog(docName)
                }
                else if(action == "Forward"){
                    CreateForwardDialog(docName)
                }
                else if(action == "Reject"){
                    CreateRejectDialog(docName)
                }
                else if(action == "Add Emission Data"){
                    CreateEmissionDialog(docName)
                }
                else if(action == "Add Installation"){
                    CreateInstallationDialog(docName)
                }
                
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
            checkVisibleBoxes();
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
        checkVisibleBoxes();
        
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
});