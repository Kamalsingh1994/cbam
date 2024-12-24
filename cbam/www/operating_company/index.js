window.addEventListener("DOMContentLoaded", function() {
    const contentContainer = document.querySelectorAll(".content-container");
    const infoContainer = document.querySelectorAll(".info-container");
    const company_contact = document.querySelector("#company_contact");
    let doc_dict = document.querySelector("#doc_dict").textContent;
    console.log(doc_dict)
   
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



    company_contact.addEventListener("click", function(e){
       
      
        
        UpdateContactDetails()
    })

    const UpdateContactDetails = function(){
        
            
            let d = new frappe.ui.Dialog({
                title: `Please Confrim your Operating Company Details`,
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
                        label: __("<strong>Company Contact and Address</strong>"),
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
                        label: __("Zip code"),
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
                primary_action_label: 'Confirm Details',
                //secondary_action_label: '',
                primary_action(values) {
                    cbam.supplier.confirm_details(values)
                    d.hide();
                    
                },
                secondary_action(values) {
                    
                    
                    
                    no+=1
                    
                }
            });
            d.show()
       
        
        
    }


    

 

   

    
});