


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
    const dataBtnEl = document.querySelectorAll(".data-btn");
    const bulkassign = document.querySelector("#bulkassign-data");
    const bulksubmit = document.querySelector("#bulksubmit-data");
    const bulkforward = document.querySelector("#bulkforward-data");
    const bulkreject = document.querySelector("#bulkreject-data");

    
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

    bulkassign.addEventListener("click", function(e){
        e.preventDefault();
        //const doc_list = document.querySelectorAll("#doc-name")
        const doc_list = []
        contentContainer.forEach(container =>{
            var index = container.querySelector('#index');
            if(index.querySelector("#list_check").checked){
                doc_list.push(index.querySelector('#doc-name').dataset.name)
            }
        })
        
        CreateEmissionDialog(doc_list)
    })

    bulkreject.addEventListener("click", function(e){
        e.preventDefault();
        //const doc_list = document.querySelectorAll("#doc-name")
        const doc_list = []
        contentContainer.forEach(container =>{
            var index = container.querySelector('#index');
            if(index.querySelector("#list_check").checked){
                doc_list.push(index.querySelector('#doc-name').dataset.name)
            }
        })
        
        CreateRejectDialog(doc_list)
    })

    bulkforward.addEventListener("click", function(e){
        e.preventDefault();
        //const doc_list = document.querySelectorAll("#doc-name")
        const doc_list = []
        contentContainer.forEach(container =>{
            var index = container.querySelector('#index');
            if(index.querySelector("#list_check").checked){
                doc_list.push(index.querySelector('#doc-name').dataset.name)
            }
        })
        CreateForwardDialog(doc_list)
    })


    bulksubmit.addEventListener("click", function(e){
        e.preventDefault();
        //const doc_list = document.querySelectorAll("#doc-name")
        const doc_list = []
        contentContainer.forEach(container =>{
            var index = container.querySelector('#index');
            if(index.querySelector("#list_check").checked){
                doc_list.push(index.querySelector('#doc-name').dataset.name)
            }
        })
        
        CreateEmissionSubmissionDialog(doc_list)
    })
    



    const CreateForwardDialog = async function(goods){
        let d = new frappe.ui.Dialog({
            title: `Forwarding Request`,
            fields: [
                {
                    label: __("Supplier"),
                    fieldname: "supplier",
                    fieldtype: "Autocomplete",
                    default: "",
                    options: await cbam.utils.get_links("Operating Company", ["supplier_name as label", "name as value"]),
                    //depends_on: "eval:doc.forward_to_party == 'Sub Supplier'"
                },
                
            ],
            size: 'large', // small, large, extra-large 
            primary_action_label: 'Submit',
            primary_action(values) {
              
                if(!Array.isArray(goods)){
                    goods = [goods]
                }
                cbam.goods.forward_goods(values.supplier, goods)
                d.hide()
            }
        });

                   
        d.show();
        d.$wrapper.find('.modal-dialog').css("height", "350px");
    }

    const CreateRejectDialog = function(goods){
        let d = new frappe.ui.Dialog({
            title: __('Rejecting Request'),
            fields: [
                {
                    label: __("Reason to Reject"),
                    fieldname: "reason",
                    fieldtype: "Small Text",
                    default: "",
                    //options: "\nSub Supplier\nCollegue"
                }

            ],
            size: 'small', // small, large, extra-large 
            primary_action_label: __('Reject Goods'),
            //secondary_action_label: '',
            primary_action(values) {
                cbam.goods.reject_goods(goods, values.reason)
                d.hide();
            },
            secondary_action(values) {
                
               
                
                
                
            }
        });

                   
        d.show();
    }

    

    const  split_fields =  function(no){
        
        return [
            {
                label: __("Source"),
                fieldname: `source_${no}`,
                fieldtype: "Select",
                default: "",
                options: "Supplier\nInstallation",
                change: async () =>{
                    cur_dialog.fields_dict[`source_name_${no}`].df.options = await cbam.utils.get_links("Operating Company", ["supplier_name as label", "name as value"])
                    cur_dialog.fields_dict[`source_name_${no}`].refresh()
                },
                in_list_view: 1
                
            },
            {
               
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Source Name"),
                fieldname: `source_name_${no}`,
                fieldtype: "Select",
                //default: "",
                //options: "Supplier",
                //depends_on: `eval:doc.forward_to_party_${no} == 'Sub Supplier'`,
                in_list_view: 1
            },
            // {
            //     label: __("Installation"),
            //     fieldname: `installation_${no}`,
            //     fieldtype: "Link",
            //     default: "",
            //     //options: "Installation",
            //     depends_on: `eval:doc.forward_to_party_${no} == 'Installation'`,
            //     in_list_view: 1
            // },
            {
              
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Qty to Split"),
                fieldname: `qty_${no}`,
                fieldtype: "Float",
                //depends_on: `eval:doc.forward_to_party_${no}`,
                in_list_view: 1
            },
            
            
        ]
        return [
            {
                label: __("Split with"),
                fieldname: `split_with`,
                fieldtype: "Select",
                default: "Supplier",
                options: "\nSupplier\nInstallation",
                change: () =>{
                    cur_dialog.refresh()
                },
                in_list_view: 1
                
            },
            {
               
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Split with Name"),
                fieldname: `split_with_name`,
                fieldtype: "Autocomplete",
                default: "",
                
                
                in_list_view: 1
            },
            {
              
                fieldname: "cb1",
                fieldtype: "Column Break",
            },
            {
                label: __("Qty to Split"),
                fieldname: `qty_${no}`,
                fieldtype: "Float",
                in_list_view: 1
            },
            
            
        ]
    }
    



   const CreateEmissionDialog = async function(good){
    let d = new frappe.ui.Dialog({
        title: `Assigning Emission Data`,
        fields: [
            {
                label: __("Emission"),
                fieldname: "emission_data",
                fieldtype: "Autocomplete",
                default: "",
                options: await cbam.utils.get_links("CBAM Emission Data"),
                change: async () =>{
                    let installation =  await cbam.utils.get_installation(d.get_value("emission_data"));
                    d.set_value("installation", installation)
                 }
                //options: "\nSub Supplier\nCollegue"
            },
            {
                label: __("Installation"),
                fieldname: "installation",
                fieldtype: "Data",
                default: "",
                read_only: 1
                //options: "\nSub Supplier\nCollegue"
            },


        ],
        size: 'large', // small, large, extra-large 
        primary_action_label: 'Assign Emission Data',
        //secondary_action_label: '',
        primary_action(values) {
            d.hide();
            if(!Array.isArray(good)){
                good = [good]
            }
            cbam.goods.assign_emission(values.emission_data, good)
        }
        
    });

               
    d.show();
    d.$wrapper.find('.modal-dialog').css("height", "350px");
    
    }



    const CreateSplitDialog = function(docName){
        let fields = split_fields(1);
        let no = 1;
        let d = new frappe.ui.Dialog({
            title: `Spliting Goods`,
            fields: fields, 
            //[
            //     {
            //         fieldtype: "Table",
            //         fieldname: "table1",
            //         editable_grid: 0,
            //         fields: [
            //             {
            //                 label: __("Split with"),
            //                 fieldname: `split_with`,
            //                 fieldtype: "Select",
            //                 default: "Supplier",
            //                 options: "\nSupplier\nInstallation",
            //                 onchange: (event) => {
			// 					if (event) {
			// 						let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
			// 						let item_row =
			// 							d.fields_dict.table1.grid.grid_rows_by_docname[name].columns.split_with_name.df.options=["AAA"];

									
			// 						d.fields_dict.table1.grid.refresh();
			// 					}
			// 				},
            //                 in_list_view: 1
                            
            //             },
            //             {
                           
            //                 fieldname: "cb1",
            //                 fieldtype: "Column Break",
            //             },
            //             {
            //                 label: __("Split with Name"),
            //                 fieldname: `split_with_name`,
            //                 fieldtype: "Autocomplete",
            //                 default: "",
            //                 options: ["BB"],
                            
            //                 reqd: 1,  
            //                 in_list_view: 1
            //             },
            //             {
                          
            //                 fieldname: "cb1",
            //                 fieldtype: "Column Break",
            //             },
            //             {
            //                 label: __("Qty to Split"),
            //                 fieldname: `qty`,
            //                 fieldtype: "Float",
            //                 in_list_view: 1
            //             },
            //         ]
            //     }
            // ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: __('Split Goods'),
            secondary_action_label: __('Add More'),
            primary_action(values) {
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

    const toggleDataBtn = function(toggle) {
        if(toggle) {
            dataBtnEl.forEach(btn => btn.classList.add("hidden"));
        } else {
            dataBtnEl.forEach(btn => btn.classList.remove("hidden"));
        }
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
                else if(action == "Submit Emission Data"){
                    CreateEmissionSubmissionDialog(docName)
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
            toggleDataBtn(false);
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
            toggleDataBtn(true);
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

            if(selected > 0) {
                toggleDataBtn(false);
            } else {
                toggleDataBtn(true);
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
    const SubmissionDialog = function(goods){
        
        
        let d = new frappe.ui.Dialog({
            title: 'Are you sure you want to proceed?',
            fields: [
                {
                    fieldtype: "HTML",
                    options: "This will submit the Emission data for the goods and will not be reverted."
                }
            ],
            primary_action_label: 'Submit',
            size: 'large', // small, large, extra-large 
            primary_action(values) {
                cbam.goods.submit_goods(goods)
                d.hide();
            }
           
        });
        d.show()
        
    }


    const CreateEmissionSubmissionDialog = async function(goods){
        let supplier_details = await cbam.supplier.get_supplier();
        if (supplier_details.status!="Company Verified"){
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
                    cbam.supplier.confirm_details(values)
                    d.hide();
                    SubmissionDialog(goods)
                },
                secondary_action(values) {
                    
                    
                    
                    no+=1
                    
                }
            });
            d.show()
        }
        else{
            SubmissionDialog(goods)    
        }
        
        
    }

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
    }
        
})