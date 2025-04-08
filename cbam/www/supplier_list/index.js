let CreateSupplierDialog;

window.addEventListener("DOMContentLoaded", () => {
    executeJS();
    refreshElements(frappe)
    document.querySelector('.add-new').addEventListener('click', async function(e){
        CreateSupplierDialog()
    })
});

const refreshElements = function (frappe) {
    const contentContainer = document.querySelectorAll(".content-container");
    return new Promise((resolve, reject) => {
        frappe.call({
            method: "cbam.www.supplier_list.index.get_supplier_partial_html",
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

    


    const createSupplier = async function(values, d) {
        values.parent_operating_company = await cbam.supplier.get_supplier()
        frappe.call({
            method: "cbam.utils.create_new_doc",
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
    
    const updateSupplier = function(values, d) {
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

    const hideDropDown = function() {
        dropDownCont.forEach(dropDownEl => dropDownEl.classList.add("hidden"));
    }
    
    window.addEventListener('click', function(e){
        if(!e.target.classList.contains("action-btn")) {
            hideDropDown()
        }
    })
    

    CreateSupplierDialog = async function(docName="", docData=false, update=false){
        let d = new frappe.ui.Dialog({
            title: `${update ? __("Update Supplier") : __("Add New Supplier")}`,
            fields: [
                {
                    label: __("Supplier Number"),
                    fieldname: "supplier_number",
                    fieldtype: "Data",
                    default: docData ? docData.supplier_number : ""
                },
                {
                    label: __("Country"),
                    fieldname: "country",
                    fieldtype: "Autocomplete",
                    options: await cbam.utils.get_links("Country"),
                    default: docData ? docData.country : ""
                },
                {
                    label: __("Company Email"),
                    fieldname: "company_email",
                    fieldtype: "Data",
                    default: docData ? docData.company_email : ""
                },
                {
                    label: __(""),
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    label: __("Supplier Name"),
                    fieldname: "supplier_name",
                    fieldtype: "Data",
                    reqd: update ? 0 : 1,
                    //options: "Same contact person as Operating Company\nDifferent contact person\nNo contact person for this Installation"
                    default: docData ? docData.supplier_name : ""
                    
                },
                {
                    label: __("Zip Code"),
                    fieldname: "zip_code",
                    fieldtype: "Data",
                    default: docData ? docData.zip_code : ""
                },
                {
                    label: __("Phone No"),
                    fieldname: "company_phone_number",
                    fieldtype: "Data",
                    default: docData ? docData.company_phone_number : ""
                },
                {
                    label: __(""),
                    fieldname: "cb2",
                    fieldtype: "Column Break",
                },
                {
                    label: __("City"),
                    fieldname: "city",
                    fieldtype: "Data",
                    default: docData ? docData.city : ""   
                },                
                {
                    label: __("Street and Number"),
                    fieldname: "street_and_number",
                    fieldtype: "Data",
                    default: docData ? docData.street_and_number : ""
                },
                {
                    label: __("Main Contact"),
                    fieldname: "cb3",
                    fieldtype: "Section Break",
                    depends_on: ""
                },
                {
                    label: __("First Name"),
                    fieldname: "main_contact_employee_first_name",
                    fieldtype: "Data",
                    default: docData ? docData.main_contact_employee_first_name : ""
                },
                
                {
                    label: __("Last Name"),
                    fieldname: "main_contact_employee_last_name",
                    fieldtype: "Data",
                    reqd: update ? 0 : 1,
                    default: docData ? docData.main_contact_employee_last_name : ""
                },
                {
                    label: __("Main Contact Employee Position"),
                    fieldname: "main_contact_employee_position",
                    fieldtype: "Data",
                    default: docData ? docData.main_contact_employee_position : ""
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
                    reqd: update ? 0 : 1,
                    default: docData ? docData.main_contact_employee_email : ""
                    
                    
                },
                {
                    label: __("Commercial Contact Phone Number"),
                    fieldname: "main_contact_employee_phone_number",
                    fieldtype: "Data",
                    default: docData ? docData.company_phone_number : ""
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
            primary_action_label: `${update ? __("Update Supplier") : __("Create Supplier")}`,
            //secondary_action_label: '',
            primary_action(values) {
                values.doctype = "Operating Company"
                if (update) {
                    values.name = docName
                    updateSupplier(values, d);
                } else {
                    values.create_commercial_contact_user = 1
                    createSupplier(values, d);
                }
                // cbam.utils.new_doc(values)
                // d.hide();
            },
            secondary_action(values) {
                no+=1
            }
        });
        d.show();
    }

    contentContainer.forEach(container => {
        const absBtn = container.querySelectorAll(".abs-option-btn");

        absBtn.forEach(btn => {
            btn.addEventListener("click", function() {
                const docName = container.querySelector(".inv-name").dataset.number;
                const action = btn.dataset.action;
                if(action == "Split"){
                    CreateSplitDialog(docName)
                }
               
                
                    
                
            })
        })

        container.addEventListener("click", function(e) {
            if(e.target.classList.contains("edit-btn")) {
                const docName = container.querySelector(".inv-name").dataset.name;
                frappe.call({
                    method: "cbam.utils.supplier.get_supplier_details",
                    args: {
                        
                        sup: docName
                    },
                    callback: function(response) {
                        if (response.message) {
                            CreateSupplierDialog(docName, response.message, true);
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

       
    })

    if(document.querySelector(".list-container")) {
        const contentContainer = document.querySelectorAll(".content-container");
        const infoContainer = document.querySelectorAll(".info-container");
        const arrowEl = document.querySelectorAll(".arrow");

        const currentDomain = window.location.origin;

        let exPrintFormat = "";

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

        
    }
}