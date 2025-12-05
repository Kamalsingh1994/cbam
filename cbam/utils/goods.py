import frappe
import json

@frappe.whitelist()
def assign_emission(goods, emission):
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        doc.emission_data = emission
        doc.status = "Data Assigned"
        doc.save(ignore_permissions=True)

@frappe.whitelist()
def forward_goods(goods, supplier):
    doc = {}
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        doc.forwarded_from_supplier = doc.operating_company
        doc.supplier_name, doc.supplier_number = frappe.db.get_values("Operating Company", supplier, ["supplier_name", "supplier_number"])[0]
        doc.operating_company = supplier
        doc.status = "Forwarded"
        doc.save(ignore_permissions=True)
    if doc:
        doc.send_data_request()

@frappe.whitelist()
def submit_goods(goods):
    goods = json.loads(goods)
    for g in goods:
        doc = frappe.get_doc("Good", g)
        if doc.status == "Data Assigned":
            doc.status = "Data Submitted"
            doc.save(ignore_permissions=True)
            doc.submit()


@frappe.whitelist()
def reject_goods(goods, reason=None):
    # Handle both JSON string and list/array inputs
    if isinstance(goods, str):
        goods = json.loads(goods)
    
    rejected_goods_info = []
    declarant_emails = set()
    supplier_emails = set()
    
    for g in goods:
        parent_operating_company = {}
        doc = frappe.get_doc("Good", g)
        doc.rejected_from_supplier = doc.operating_company
        doc.rejection_reason = reason
        _parent_operating_company = frappe.db.get_value("Operating Company", doc.operating_company, "parent_operating_company")
        
        if _parent_operating_company: #if tier n+1 supplier
            parent_operating_company = frappe.get_doc("Operating Company", _parent_operating_company)
            doc.supplier_name, doc.supplier_number = parent_operating_company.supplier_name , parent_operating_company.supplier_number
            doc.status = "Data Requested"
        else:    
            doc.supplier_name, doc.supplier_number = "", ""
            doc.rejection_reason = reason
            doc.status = "Rejected"
        doc.save(ignore_permissions=True)
        
        # Collect good information for email
        article_num = doc.article_number or doc.name or doc.cn_code or "N/A"
        rejected_goods_info.append(article_num)
        
        # Collect email recipients
        # Requester (declarant email)
        declarant_doc = frappe.get_doc("Declarant", doc.declarant)
        if declarant_doc.email:
            declarant_emails.add(declarant_doc.email)
        
        # Supplier (operating company email)
        if doc.rejected_from_supplier:
            oc_doc = frappe.get_doc("Operating Company", doc.rejected_from_supplier)
            supplier_email = oc_doc.company_email or oc_doc.main_contact_employee_email
            if supplier_email:
                supplier_emails.add(supplier_email)
    
    # Format goods list for email
    goods_list_str = ", ".join(rejected_goods_info)
    
    # Get email template
    email_template_name = frappe.db.get_single_value("CBAM Settings", "supplier_good_rejection_notification_template")
    if not email_template_name:
        frappe.throw("Please setup Supplier Good Rejection Notification Template in CBAM Settings")
    
    email_template = frappe.get_doc("Notification", email_template_name)
    
    # Send to Declarant (Requester) - primary recipient
    for declarant_email in declarant_emails:
        try:
            # Get the first good's declarant for the template
            first_good = frappe.get_doc("Good", goods[0])
            declarant_doc = frappe.get_doc("Declarant", first_good.declarant)
            declarant_doc.goods = goods_list_str
            declarant_doc.email = declarant_email
            email_template.send(declarant_doc)
        except Exception as e:
            frappe.log_error(f"Failed to send rejection email to declarant {declarant_email}: {str(e)}")
    
    # Send to Supplier
    for supplier_email in supplier_emails:
        try:
            # Create a temporary document for supplier email
            supplier_doc = frappe._dict({
                "goods": goods_list_str,
                "email": supplier_email,
                "parent_operating_company": parent_operating_company
            })
            # Use frappe.sendmail for suppliers since they're not Declarants
            frappe.sendmail(
                recipients=[supplier_email],
                subject=email_template.subject,
                message=frappe.render_template(email_template.message, {"doc": supplier_doc}),
                reference_doctype="Good",
                reference_name=goods[0] if goods else None
            )
        except Exception as e:
            frappe.log_error(f"Failed to send rejection email to supplier {supplier_email}: {str(e)}")
    
    # Send to System Manager
    try:
        system_managers = frappe.get_all("User", 
            filters={"enabled": 1, "user_type": "System User"}, 
            fields=["email"],
            or_filters=[["role_profile_name", "like", "%System Manager%"]]
        )
        # Also get users with System Manager role directly
        system_manager_emails = [m.email for m in system_managers if m.email]
        role_users = frappe.get_all("Has Role", 
            filters={"role": "System Manager", "parenttype": "User"},
            fields=["parent"],
            pluck="parent"
        )
        for user in role_users:
            user_email = frappe.db.get_value("User", user, "email")
            if user_email and user_email not in system_manager_emails:
                system_manager_emails.append(user_email)
        
        if system_manager_emails:
            manager_doc = frappe._dict({
                "goods": goods_list_str,
                "email": system_manager_emails[0]
            })
            frappe.sendmail(
                recipients=system_manager_emails,
                subject=email_template.subject,
                message=frappe.render_template(email_template.message, {"doc": manager_doc}),
                reference_doctype="Good",
                reference_name=goods[0] if goods else None
            )
    except Exception as e:
        frappe.log_error(f"Failed to send rejection email to system managers: {str(e)}")

@frappe.whitelist()
def split_goods(good, values):
    details = json.loads(values)
    good_doc = frappe.get_doc("Good", good)
    good_doc.add_split_good_details(details)
    good_doc.split_goods()
    frappe.msgprint("Goods splitted successfully.")