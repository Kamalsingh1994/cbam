# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class OperatingCompany(Document):
	def validate(self):
		self.create_commercial_contact()
		self.create_cbam_user()	
		self.set_title()

	def set_title(self):
		self.title = f"{self.supplier_name}-{self.supplier_number}"

	def create_commercial_contact(self):
		username = ""
		self.flags.new_flag = True
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
				user.save(ignore_permissions=True)
				
				username = user.name


			self.commercial_contact_user = username
		if not self.is_new():
			self.flags.new_flag = False
			self.create_permissions(username)

	def create_cbam_user(self):
		username = ""
		self.flags.new_flag = True
		if self.cbam_representive_employee_email and not self.cbam_representative_user:
			username = frappe.db.get_value("User", self.cbam_representive_employee_email, "name")
			if not username:
				user = frappe.new_doc("User")
				user.send_welcome_email = False
				user.first_name = self.cbam_representive_last_name or self.cbam_representive_employee_first_name
				user.email = self.cbam_representive_employee_email
				user.append("roles",{
					"role": frappe.db.get_single_value("CBAM Settings", "commercial_contact_user_role")
				})
				user.append("roles",{
					"role": frappe.db.get_single_value("CBAM Settings", "cbam_representative_user_role")
				})
				user.save(ignore_permissions=True)
				
				username = user.name


			self.cbam_representative_user = username
		if not self.is_new():
			self.flags.new_flag = False
			self.create_permissions(username)

	def after_insert(self):
		if self.flags.new_flag:
			self.create_permissions()
		if self.parent_operating_company:
			self.send_signup_request()

	@frappe.whitelist()
	def send_signup_request(self):
		email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "signup_template"))
		
		#self.declarent = self.declarent if not self.parent_operating_company else frappe.db.get_value("Operating Company", self.parent_operating_company, "supplier_name")
		
		email.send(self)
		self.status = "Pending Verification"
		self.save(ignore_permissions=True)


	def create_permissions(self, user=None):
		if self.commercial_contact_user and self.create_commercial_contact_user:
			if not frappe.db.exists("User Permission", {"user": self.commercial_contact_user, "for_value":self.name}):
				us_pem = frappe.new_doc("User Permission")
				us_pem.user = user or self.commercial_contact_user
				us_pem.allow = "Operating Company"
				us_pem.for_value = self.name
				us_pem.save(ignore_permissions=True)

			if not frappe.db.exists("User Permission", {"user": self.commercial_contact_user, "for_value":self.declarant}):
				aus_pem = frappe.new_doc("User Permission")
				aus_pem.user = user or self.commercial_contact_user
				aus_pem.allow = "Declarant"
				aus_pem.for_value = self.declarant
				aus_pem.save(ignore_permissions=True)
    
@frappe.whitelist()
def send_bulk_signup_request(operating_companys):
	operating_companys = json.loads(operating_companys)
	if len(operating_companys) > 0:
		for company in operating_companys:
			operating_company = frappe.get_doc("Operating Company", company.get("name"))
			operating_company.send_signup_request()