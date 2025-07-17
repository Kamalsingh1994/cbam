let CreateEmissionDialog;
let CreateRejectDialog;
let CreateForwardDialog;
let CreateEmissionSubmissionDialog;
let contentContainer;

window.addEventListener("DOMContentLoaded", () => {
    const bulkassign = document?.querySelector("#bulkassign-data");
    const bulksubmit = document?.querySelector("#bulksubmit-data");
    const bulkforward = document?.querySelector("#bulkforward-data");
    const bulkreject = document?.querySelector("#bulkreject-data");

    executeJS();


    bulkassign?.addEventListener("click", function(e){
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

    bulkreject?.addEventListener("click", function(e){
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

    bulkforward?.addEventListener("click", function(e){
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


    bulksubmit?.addEventListener("click", function(e){
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
});

function executeJS() {
    // This condition is to stop the rest of the code from executing if the user is not authorized.
    // frappe.call({
    //     method: "paystack_integration.utils.ex_utils.clear_website_cache",
    //     callback: function(r) {
    //     }
    // });
    
    contentContainer = document.querySelectorAll(".content-container");
    const infoContainer = document.querySelectorAll(".info-container");
    const arrowEl = document.querySelectorAll(".arrow");
    const totalCheckbox = document.querySelector(".total-checkbox");
    const checkboxes = document.querySelectorAll(".checkbox");
    const selectedEl = document.querySelector(".selected-no");
    const statusFilter = document.querySelector(".status-filter");
    const reportingFilter = document.querySelector(".reporting-filter");
    const dropDownCont = document.querySelectorAll(".options-abs");
    const dataBtnEl = document.querySelectorAll(".data-btn");
    const notAllowed = ["Split", "Data Submitted"];
    
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

    const performGoodsAction = function(fn, params, d) {
        if(!Array.isArray(params.goods)){
            params.goods = [params.goods]
        }

        frappe.call({
            method: `cbam.utils.goods.${fn}`,
            args: params,
            callback: function(r) {
                frappe.call({
                    method: "cbam.www.goods_list.index.get_goods_partial_html",
                    callback: function(r) {
                        contentContainer.forEach(container => {
                            container.remove();
                        });
                        document.querySelector('.list-row-container').insertAdjacentHTML('beforeend', r.message);
                        executeJS();
                    }
                })
                d.hide();
            }
        })
    }

    CreateForwardDialog = async function(goods){
        let d = new frappe.ui.Dialog({
            title: __('Forwarding Request'),
            fields: [
                {
                    label: __("Supplier"),
                    fieldname: "supplier",
                    fieldtype: "Autocomplete",
                    default: "",
                    options: await cbam.supplier.get_child_suppliers({"status": ["!=", "Missing Commercial Contact"]}),
                    //depends_on: "eval:doc.forward_to_party == 'Sub Supplier'"
                },
                
            ],
            size: 'large', // small, large, extra-large 
            primary_action_label: __('Submit'),
            primary_action(values) {
              
                if(!Array.isArray(goods)){
                    goods = [goods]
                }
                // cbam.goods.forward_goods(goods, values.supplier)
                performGoodsAction("forward_goods", {goods: goods, supplier: values.supplier}, d);
                d.hide()
            }
        });

                   
        d.show();
        d.$wrapper.find('.modal-dialog').css("height", "450px");
    }

    CreateRejectDialog = function(goods){
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
                // cbam.goods.reject_goods(goods, values.reason)
                performGoodsAction("reject_goods", {goods: goods, reason: values.reason}, d)
            },
            secondary_action(values) {
            }
        });

        d.show();
    }

    

    CreateEmissionDialog = async function(good, installation, emission) {
        const installationOptions = await cbam.utils.get_links("CBAM Installation", {}, ["name_of_the_installation as label", "name as value"]);
        const defaultEmissionOptions = await cbam.utils.get_links("CBAM Emission Data", {}, ["label as label", "name as value"]);
        console.log(emission)
        console.log(installation)
        let d = new frappe.ui.Dialog({
            title: __("Assigning Emission Data"),
            fields: [
                {
                    label: __("Installation"),
                    fieldname: "installation",
                    fieldtype: "Select",
                    options: installationOptions,
                    default: installation,
                    change: async () => {
                        const selectedInstallation = d.get_value("installation");
                        d.set_value("emission_data", null);
    
                        if (selectedInstallation) {
                            d.set_df_property("emission_data", "read_only", 0);
                            let emissionOptions = await cbam.utils.get_links("CBAM Emission Data", 
                                { cbam_installation: selectedInstallation }, 
                                ["label as label", "name as value"]);
                                console.log(`emission ${emissionOptions}`)
                            d.fields_dict.emission_data.df.options = emissionOptions;
                           
                            d.fields_dict.emission_data.refresh();
                        } else {
                            d.set_df_property("emission_data", "read_only", 1);
                            
                            d.fields_dict.emission_data.refresh();
                        }
                    }
                },
                {
                    label: __("Emission"),
                    fieldname: "emission_data",
                    fieldtype: "Select",
                    read_only: 1,
                    default: emission
                },
            ],
            size: 'large',
            primary_action_label: __('Assign Emission Data'),
            primary_action(values) {
                d.hide();
                if (!Array.isArray(good)) {
                    good = [good];
                }
                performGoodsAction("assign_emission", { goods: good, emission: values.emission_data }, d);
            }
        });
    
        // Ensure both fields are cleared before showing the dialog
        d.set_value("installation", null);
        d.set_value("emission_data", null);
        d.show();
        d.$wrapper.find('.modal-dialog').css("height", "350px");
    }
    
    
    
    



    const CreateSplitDialog = async function(docName, rawMass){
       
        let no = 1;
        let d = new frappe.ui.Dialog({
            title: __('Spliting Goods'),
            fields: [
                {
                    fieldtype: "Table",
                    fieldname: "table1",
                    editable_grid: 0,
                    fields: [
                        {
                            label: __("Source"),
                            fieldname: `source`,
                            fieldtype: "Select",
                            default: "",
                            reqd:1,
                            options: "Supplier\nInstallation",
                            onchange: async (event) => {
								if (event) {
									let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
                                    let row = d.fields_dict.table1.grid.grid_rows_by_docname[name];
									if(row.doc.source == "Supplier"){
                                        row.columns.source_name.df.options= await cbam.supplier.get_child_suppliers({"status": ["!=", "Missing Commercial Contact"]});
                                    }
                                    else{
                                        row.columns.source_name.df.options= await cbam.utils.get_links("CBAM Installation", {}, ["name_of_the_installation as label", "name as value"]);
                                        console.log(row.columns.source_name.df.options)
                                    }

									
									d.fields_dict.table1.grid.refresh();
								}
							},
                            in_list_view: 1
                            
                        },
                        {
                           
                            fieldname: "cb1",
                            fieldtype: "Column Break",
                        },
                        {
                            label: __("Source_name"),
                            fieldname: `source_name`,
                            fieldtype: "Select",
                            reqd: 1,  
                            in_list_view: 1,
                            onchange: (event) => {
                                const selectedOption = event.currentTarget.selectedOptions[0];
                                const label = selectedOption?.label || "";
                                const name = $(event.currentTarget).closest(".grid-row").attr("data-name");
                                let row = d.fields_dict.table1.grid.grid_rows_by_docname[name];
                                if (row) row.doc.name_ = label;
                                d.fields_dict.table1.grid.refresh();
                            }
                        },
                        {
                            label: __("Name"),
                            fieldname: "name_",
                            fieldtype: "Data", 
                            read_only: 1,
                            in_list_view: 1
                        },
                        {
                          
                            fieldname: "cb1",
                            fieldtype: "Column Break",
                        },
                        {
                            label: __("Qty to Split [kg]"),
                            fieldname: `qty`,
                            fieldtype: "Float",
                            in_list_view: 1,
                            onchange: (event) => {
                                let total_raw_mass = 0;
                                let table = d.get_value("table1");
                                for(var i in table){
                                    total_raw_mass += table[i].qty;
                                }
                                d.set_value("total_raw_mass", total_raw_mass)
                                d.set_value("total_remaining_qty", flt(d.get_value("raw_mass")) - flt(total_raw_mass, 3))
                            }
                        },
                    ],
                    
                },
                {
                    fieldtype: 'Section Break'
                },
                {
                    fieldtype: "Float",
                    fieldname: "raw_mass",
                    label: __("Total Qty [kg]"),
                    default: rawMass,
                    read_only: 1,

                },
                {
                          
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    fieldtype: "Float",
                    fieldname: "total_raw_mass",
                    label: __("Split Qty [kg]"),
                    read_only: 1,
                    default: "0.00"
                },
                {
                          
                    fieldname: "cb1",
                    fieldtype: "Column Break",
                },
                {
                    fieldtype: "Float",
                    fieldname: "total_remaining_qty",
                    label: __("Remaining Qty to Split [kg]"),
                    read_only: 1,
                    default: "0.00"
                }
            ],
            size: 'extra-large', // small, large, extra-large 
            primary_action_label: __('Split Goods'),
            secondary_action_label: '',
            primary_action(values) {
                let validation_flag = true
                if(values.raw_mass != flt(values.total_raw_mass, 3)){
                    msgprint(__("Total Qty to Split must be equal to Total Qty."))
                    validation_flag = false
                }
                else {
                    for(var i in values.table1){
                        if(!values.table1[i].source_name){
                            msgprint(`Please setup Source Name in row# ${Number(i)+1}`)
                            validation_flag = false
                        }
                    }
                }
                if (validation_flag){
                    // cbam.goods.split_goods(docName, values.table1)
                    performGoodsAction("split_goods", {good: docName, values: values.table1}, d);
                }

                
            },
            secondary_action(values) {
                
              
                
            }
        });

                   
        d.show();
        //Patch click event on rows to update source_name options on click
        d.fields_dict.table1.grid.wrapper.on('click', '.grid-row', async function (e) {
            const name = $(this).attr('data-name');
            const row = d.fields_dict.table1.grid.grid_rows_by_docname[name];

            if (!row || !row.doc.source) return;

            let options = [];
            if (row.doc.source === "Supplier") {
                row.columns.source_name.df.options= await cbam.supplier.get_child_suppliers({"status": ["!=", "Missing Commercial Contact"]});
            } else if (row.doc.source === "Installation") {
                row.columns.source_name.df.options= await cbam.utils.get_links("CBAM Installation", {}, ["name_of_the_installation as label", "name as value"]);
            }
            // row.columns.source_name.df.options = options;
            d.fields_dict.table1.grid.refresh();
        });
        
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
        const invEl = container.querySelector(".inv-name");
        const installation = invEl.dataset.installation;
        const emission = invEl.dataset.emission;

        absBtn.forEach(btn => {
            btn.addEventListener("click", function() {
                const docName = container.querySelector(".inv-name").dataset.name;
                const rawMass = container.querySelector(".inv-rawmass").dataset.rawmass;
                const action = btn.dataset.action;
                if(action == "Split"){
                   
                    CreateSplitDialog(docName, rawMass)
                }
                else if(action == "Forward"){
                    CreateForwardDialog(docName)
                }
                else if(action == "Reject"){
                    CreateRejectDialog(docName)
                }
                else if(action == "Add Emission Data"){
                    CreateEmissionDialog(docName, installation, emission)
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
    

 const applyCombinedFilter = function () {
    const selectedStatus = statusFilter?.value?.toLowerCase() || "all";
    const selectedReporting = reportingFilter?.value?.toLowerCase() || "all";

    totalCheckbox.checked = false;
    selected = 0;
    selectedEl.textContent = selected;

    contentContainer.forEach(container => {
        const curStatus = container.querySelector(".status").textContent.toLowerCase();
        const reportingEl = container.querySelector(".reporting");
        const curReporting = reportingEl ? (reportingEl.dataset.reporting || "").toLowerCase() : "";

        let show = true;

        // Check status filter
        if (selectedStatus && selectedStatus !== "all" && selectedStatus !== curStatus) {
            show = false;
        }

        // Check reporting filter
        if (selectedReporting && selectedReporting !== "all" && selectedReporting !== curReporting) {
            show = false;
        }

        // Apply visibility
        container.classList.toggle("hidden", !show);

        const checkbox = container.querySelector(".checkbox");
        if (checkbox) checkbox.checked = false;
    });
};



    statusFilter.addEventListener("change", applyCombinedFilter);
    reportingFilter.addEventListener("change", applyCombinedFilter);

    window.addEventListener("DOMContentLoaded", () => {
        applyCombinedFilter();
    });


    // This checks the visible checkboxes in set the boxes lenght value (This is in case filter is applied an some invoices are hidden)
    const checkVisibleBoxes = function() {
        boxesLen = 0;
        contentContainer.forEach(container => {
            const status = container.querySelector(".status").dataset.status;
            if(!container.classList.contains("hidden") && !notAllowed.includes(status)) {
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
                if(!container.classList.contains("hidden") && !notAllowed.includes(status)) {
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
            if(notAllowed.includes(box.dataset.status.toLowerCase())) return;

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
                if(notAllowed.includes(b.dataset.status)) return;
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
                // cbam.goods.submit_goods(goods)
                // d.hide();
                performGoodsAction("submit_goods", {goods: goods}, d);
            }
           
        });
        d.show()
        
    }


const CreateEmissionSubmissionDialog = async function(goods) {
    let current_user_email = frappe.session.user;

    // Get last submitted Good by this user
    let existing_good = await frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Good",
            filters: {
                cbam_representative_email: current_user_email,
                status: "Data Submitted"
            },
            fields: ["name"],
            order_by: "modified desc",
            limit_page_length: 1
        }
    });

    // Get supplier details ONCE
    let supplier_details = await cbam.supplier.get_supplier_details();

    if (existing_good.message && existing_good.message.length > 0) {
        let last_good_response = await frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Good",
                name: existing_good.message[0].name,
                fields: [
                    "country",
                    "city",
                    "zip_code",
                    "street_and_number",
                    "company_email",
                    "company_phone_number"
                ]
            }
        });

        let last_good = last_good_response.message;

        // Normalize helper
        function normalize(val) {
            return (val || '').toString().trim().toLowerCase();
        }

        // Actual comparison
        let has_changed = (
            normalize(last_good.country) !== normalize(supplier_details.country) ||
            normalize(last_good.city) !== normalize(supplier_details.city) ||
            normalize(last_good.zip_code) !== normalize(supplier_details.zip_code) ||
            normalize(last_good.street_and_number) !== normalize(supplier_details.street_and_number) ||
            normalize(last_good.company_email) !== normalize(supplier_details.company_email) ||
            normalize(last_good.company_phone_number) !== normalize(supplier_details.company_phone_number)
        );

        if (!has_changed) {
            SubmissionDialog(goods);
            return;
        } else {
            console.log(" Change detected — showing confirmation popup.");
        }
    }

    // Show popup
    if (supplier_details.status !== "Company Verified") {
        const cc_add = __("Company Contact and Address");
        let d = new frappe.ui.Dialog({
            title: __("Please Confirm your Operating Company Details"),
            fields: [
                    {
                        label: __("Operating Company Name"),
                        fieldname: "supplier_name",
                        fieldtype: "Data",
                        
                        default: supplier_details.supplier_name,
                        read_only: 1
                    },
                    {
                        label: `<strong>${__("Company Contact and Address")}</strong>`,
                        fieldname: "sb1",
                        fieldtype: "Section Break"
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
                        default: supplier_details.zip_code,
                        reqd: 1
                    },
                    {
                        label: __(""),
                        fieldname: "cb2",
                        fieldtype: "Column Break"
                    },
                    {
                        label: __("City"),
                        fieldname: "city",
                        fieldtype: "Data",
                        default: supplier_details.city,
                        reqd: 1
                    },
                    {
                        label: __("Country"),
                        fieldname: "country",
                        fieldtype: "Data",
                        default: supplier_details.country,
                        reqd: 1
                    },
                    {
                        label: `<strong>${__("CBAM Representative Details")}</strong>`,
                        fieldname: "sb3",
                        fieldtype: "Section Break"
                    },
                    {
                        label: __("CBAM Representative First Name"),
                        fieldname: "cbam_representive_employee_first_name",
                        fieldtype: "Data",
                        default: supplier_details.cbam_representive_employee_first_name,
                        reqd: 1
                    },
                    {
                        label: __("CBAM Representative Email"),
                        fieldname: "cbam_representive_employee_email",
                        fieldtype: "Data",
                        default: supplier_details.cbam_representive_employee_email,
                        reqd: supplier_details.cbam_representative_user ? 0 : 1,
                        read_only: supplier_details.cbam_representative_user ? 1 : 0
                    },
                    {
                        label: __("CBAM Representative Position"),
                        fieldname: "cbam_representive_employee_position",
                        fieldtype: "Data",
                        default: supplier_details.cbam_representive_employee_position
                        
                    },
                    {
                        label: __(""),
                        fieldname: "cb4",
                        fieldtype: "Column Break"
                    },
                    {
                        label: __("CBAM Representative Last Name"),
                        fieldname: "cbam_representive_last_name",
                        fieldtype: "Data",
                        default: supplier_details.cbam_representive_last_name,
                        reqd: 1
                    },
                    {
                        label: __("CBAM Representative Phone Number"),
                        fieldname: "cbam_representive_employee_phone_number",
                        fieldtype: "Data",
                        default: supplier_details.cbam_representive_employee_phone_number,
                        reqd: 1
                    }
                ],
            size: 'extra-large',
            primary_action_label: __('Confirm Details'),
            primary_action(values) {
                cbam.supplier.confirm_details(values);
                d.hide();
                SubmissionDialog(goods);
            }
        });
        d.show();
    } else {
        SubmissionDialog(goods);
    }
};




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
   applyCombinedFilter();     
}