import frappe
import json
import os

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


def create_dynamic_web_templates_if_not_exists():
	"""Create Dynamic Web Templates only if they don't exist to avoid overwriting customer customizations"""
	# Use .json.template extension to avoid automatic import by Frappe's fixture system
	fixtures_path = frappe.get_app_path("cbam", "fixtures", "dynamic_web_template.json.template")
	
	if not os.path.exists(fixtures_path):
		return
	
	try:
		with open(fixtures_path, 'r') as f:
			templates = json.load(f)
		
		for template_data in templates:
			template_name = template_data.get("name")
			
			# Skip if template already exists
			if frappe.db.exists("Dynamic Web Template", template_name):
				continue
			
			# Create template only if it doesn't exist
			try:
				doc = frappe.get_doc(template_data)
				doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
				frappe.db.commit()
			except frappe.DuplicateEntryError:
				# Template was created by another process, skip
				pass
			except Exception as e:
				frappe.log_error(f"Error creating Dynamic Web Template {template_name}: {str(e)}", "create_dynamic_web_templates_if_not_exists")
	except Exception as e:
		frappe.log_error(f"Error loading Dynamic Web Template fixtures: {str(e)}", "create_dynamic_web_templates_if_not_exists")