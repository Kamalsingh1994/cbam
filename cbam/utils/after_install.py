import frappe
def after_install():
    frappe.db.set_value("System Settings", "System Settings", "apply_strict_permissions", 1)
    frappe.db.set_value("Website Settings", "Website Settings", {"app_name": "CBAM-Myconet", "disable_signup":1})
    frappe.db.set_value("CBAM Settings", "CBAM Settings", {
        "admin_role": "System Manager",
        "commercial_contact_user_role": "Commercial Contact",
        "cbam_representative_user_role": "CBAM Representative",
        "declarent_user_role": "Declarent",
        "supplier_good_rejection_notification_template": "Supplier Good Rejection Notification Template",
        "data_request_template": "Request for Submission of Emission Data",
        "goods_forwarding_template": "Request for Submission of Emission Data",
        "signup_template": "Commercial Contact Signup Request"
    })