# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document

MISSING_CONTACT_MESSAGE = """The contact email provided already exists for another Operating Company. 
		The System Manager will look into it and get back to you. Please wait before using this Supplier."""

class OperatingCompany(Document):
	
	def check_user_exists(self, user):
		cc_filters = {
			"commercial_contact_user": user, 
			"name": ["!=", self.name]
		}
		cr_filters = {
			"cbam_representative_user": user, 
			"name": ["!=", self.name]
		}
		
		if (not frappe.db.exists("Operating Company", cc_filters) 
	  		and not frappe.db.exists("Operating Company", cr_filters)):
			return True
		return False




	def validate_cc_user(self):
		if self.main_contact_employee_email:
			if self.check_user_exists(self.main_contact_employee_email):
				self.create_commercial_contact()
				self.status = "Pending Verification"		
			else:
				frappe.msgprint(MISSING_CONTACT_MESSAGE)
				# Only send email once
				if not getattr(self.flags, "conflict_notified", False):
					notify_system_manager_of_conflict(self.main_contact_employee_email, self.name)
					self.flags.conflict_notified = True

				self.create_commercial_contact_user = 0
				self.commercial_contact_user = ""
				self.status = "Missing Commercial Contact"


	def validate(self):
		self.validate_cc_user()
		self.validate_cr_user()
		self.validate_conflict()


	


	def validate_cr_user(self):
		if self.cbam_representive_employee_email:	
			if self.check_user_exists(self.cbam_representive_employee_email):
				
				self.create_cbam_user()
				self.status = "Pending Verification"
			else:
				frappe.msgprint(MISSING_CONTACT_MESSAGE)
				# Only send email once
				if not getattr(self.flags, "conflict_notified", False):
					notify_system_manager_of_conflict(self.cbam_representive_employee_email, self.name)
					self.flags.conflict_notified = True

				self.cbam_representative_user = ""
				self.status = "CBAM Rep User Conflict"



	def validate_conflict(self):
	
		if self.status in [
			"CBAM Rep User Conflict", 
			"Missing Commercial Contact"
		]:
			self.user_conflict = 1
		else:
			self.user_conflict = 0

		self.set_title()

	def set_title(self):
		self.title = f"{self.supplier_name}-{self.supplier_number}"

	def create_commercial_contact(self):
		username = self.main_contact_employee_email
		self.flags.new_flag = True
		if username:
			username = frappe.db.get_value("User", username, "name")
			if not username:
				user = frappe.new_doc("User")
				user.send_welcome_email = False
				user.first_name = self.main_contact_employee_first_name if (
					self.main_contact_employee_first_name) else self.main_contact_employee_last_name
				user.last_name = self.main_contact_employee_last_name if (
					self.main_contact_employee_first_name) else ""
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
		user = None
		if self.cbam_representive_employee_email == self.commercial_contact_user:
			user = frappe.get_doc("User", self.commercial_contact_user)
		
			
		elif frappe.db.exists("User", self.cbam_representive_employee_email):
			existing_username = frappe.db.get_value("User", self.cbam_representive_employee_email, "name")
			user = frappe.get_doc("User", existing_username)

		else:
			user = frappe.new_doc("User")
			user.send_welcome_email = False
			user.first_name = self.cbam_representive_employee_first_name if (
				self.cbam_representive_employee_first_name) else self.cbam_representive_last_name
			user.last_name = self.cbam_representive_last_name if (
				self.cbam_representive_employee_first_name) else ""
			user.email = self.cbam_representive_employee_email
			user.enabled = 1

		if user:
			user.append("roles",{
				"role": frappe.db.get_single_value("CBAM Settings", "cbam_representative_user_role")
			})
			user.save(ignore_permissions=True)
					
			self.cbam_representative_user = user.name
			self.create_permissions(user.name)


	def after_insert(self):
		if self.flags.new_flag:
			if self.commercial_contact_user:
				self.create_permissions(self.commercial_contact_user)

		# Only send signup request if no conflict
		if self.parent_operating_company and not self.user_conflict:
			self.send_signup_request()

	def on_update(self):
		update_user_from_operating_company(self, method="on_update")


	@frappe.whitelist()
	def send_signup_request(self):
		email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "signup_template"))
		
		
		email.send(self)
		self.status = "Pending Verification"
		self.save(ignore_permissions=True)


	def create_permissions(self, user):
		if not user:
			return
		if not frappe.db.exists("User Permission", {"user": user, "allow":"Operating Company"}):
			us_pem = frappe.new_doc("User Permission")
			us_pem.user = user 
			us_pem.allow = "Operating Company"
			us_pem.for_value = self.name
			us_pem.is_default = 1
			us_pem.save(ignore_permissions=True)

		if not frappe.db.exists("User Permission", {"user":user, "allow":"Declarant"}):
			aus_pem = frappe.new_doc("User Permission")
			aus_pem.user = user
			aus_pem.allow = "Declarant"
			aus_pem.for_value = self.declarant
			aus_pem.is_default = 1
			aus_pem.save(ignore_permissions=True)
	
	@frappe.whitelist()
	def update_contact(self, values):
		values = frappe._dict(values)
		old_user = ''
		if values.type == "Commercial Contact":
			if not self.check_user_exists(values.email):
				frappe.throw("This user is already associated with another Operating Company.")
			self.main_contact_employee_last_name = values.last_name
			self.main_contact_employee_first_name = values.first_name
			self.main_contact_employee_phone_number = values.phone_no
			self.main_contact_employee_position = values.position
			self.main_contact_employee_email = values.email
			old_user = self.commercial_contact_user
		elif values.type == "CBAM Representative":
			
			if not self.check_user_exists(values.email):
				frappe.throw("This user is already associated with another Operating Company.")
			self.cbam_representive_last_name = values.last_name
			self.cbam_representive_employee_first_name = values.first_name
			self.cbam_representive_employee_phone_number = values.phone_no
			self.cbam_representive_employee_position = values.position
			self.cbam_representive_employee_email = values.email
			old_user = self.cbam_representative_user
		self.save()

		user = frappe.get_all("User", filters={"email": values.email}, fields=["name"])
		if user:
			user_doc = frappe.get_doc("User", user[0].name)
			user_doc.first_name = values.first_name
			user_doc.last_name = values.last_name
			user_doc.phone = values.phone_no
			user_doc.save()

		# Disable old user if different
		if old_user not in [self.cbam_representative_user, self.commercial_contact_user]:
			frappe.db.set_value("User", old_user, "enabled", 0)

@frappe.whitelist()
def update_user_from_operating_company(doc, method=None):
	# Update the user linked in commercial_contact_user
	if doc.commercial_contact_user:
		try:
			user = frappe.get_doc("User", doc.commercial_contact_user)
			user.first_name = doc.main_contact_employee_first_name
			user.last_name = doc.main_contact_employee_last_name
			user.email = doc.main_contact_employee_email
			user.phone = doc.main_contact_employee_phone_number
			user.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error updating commercial contact User")

	# Update the user linked in cbam_representative_user
	if doc.cbam_representative_user:
		try:
			user = frappe.get_doc("User", doc.cbam_representative_user)
			user.first_name = doc.cbam_representive_employee_first_name
			user.last_name = doc.cbam_representive_last_name
			user.email = doc.cbam_representive_employee_email
			user.phone = doc.cbam_representive_employee_phone_number
			user.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error updating CBAM representative User")

@frappe.whitelist()
def send_bulk_signup_request(operating_companys):
	operating_companys = json.loads(operating_companys)
	if len(operating_companys) > 0:
		for company in operating_companys:
			operating_company = frappe.get_doc("Operating Company", company.get("name"))
			operating_company.send_signup_request()




def update_goods_on_operating_company_change(doc, method):
    # Fetch all Goods records linked to this Operating Company and not "Data Submitted"
    goods_list = frappe.get_all("Good", 
        filters={
            "operating_company": doc.name,
            "status": ["!=", "Data Submitted"]
        },
        fields=["name"]
    )

    for good in goods_list:
        good_doc = frappe.get_doc("Good", good.name)
        good_doc.country = doc.country
        good_doc.city = doc.city
        good_doc.zip_code = doc.zip_code
        good_doc.street_and_number = doc.street_and_number
        good_doc.company_email = doc.company_email
        good_doc.company_phone_number = doc.company_phone_number
        good_doc.supplier_name = doc.supplier_name
        good_doc.save(ignore_permissions=True)

def notify_system_manager_of_conflict(email, oc_name):
	subject = "User Conflict on Operating Company Assignment"
	message = f"""
		<p>Dear System Manager,</p>
		<p>An attempt was made to assign the email <b>{email}</b> to Operating Company <b>{oc_name}</b>,</p>
		<p>but this email is already associated with another Operating Company.</p>
		<p>Please resolve this conflict by checking user permissions and assignments.</p>
	"""

	system_managers = frappe.get_all("User", filters={"role": "System Manager", "enabled": 1}, pluck="email")

	frappe.sendmail(
		recipients=system_managers,
		subject=subject,
		message=message
	)
