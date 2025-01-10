import frappe
def after_install():
    frappe.db.set_value("System Settings", "System Settings", "apply_strict_permissions", 1)
    frappe.db.set_values("Website Settings", "Website Settings", {"app_name": "CBAM-Myconet", "disable_signup":1})