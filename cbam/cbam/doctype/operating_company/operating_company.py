# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OperatingCompany(Document):
	def validate(self):
		if self.create_commercial_contact_user and not self.commercial_contact_user:
			username = frappe.db.get_value("User", self.main_contact_employee_email, "name")
			if not username:
				user = frappe.new_doc("User")
				user.send_welcome_email = False
				user.first_name = self.main_contact_employee_first_name or self.main_contact_employee_last_name
				user.email = self.main_contact_employee_email
				user.append("roles",{
					"role": frappe.db.get_single_value("CBAM Settings", "commercial_contact_user_role")
				})
				user.save()
				username = user.name


			self.commercial_contact_user = username

	@frappe.whitelist()
	def send_signup_request(self):
		email = frappe.get_doc("Notification", "Commercial Contact Signup Request")
		email.send(self)