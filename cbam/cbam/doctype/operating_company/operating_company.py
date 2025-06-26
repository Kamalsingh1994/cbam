# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document

MISSING_CONTACT_MESSAGE = """The contact email provided already exists for another Operating Company. 
		The System Manager will look into it and get back to you. Please wait before using this Supplier."""

class OperatingCompany(Document):

	def validate(self):
		self.validate_duplicate_contacts()
		self.validate_contact_users()
		self.validate_conflict()
		self.set_title()

	def after_insert(self):
		for contact in self.contact_persons:
			if contact.contact_person:
				self.create_permissions(contact.contact_person)
		if self.parent_operating_company:
			self.send_signup_request()

	def validate_contact_users(self):
		for contact in self.contact_persons:
			if not contact.contact_email or not contact.contact_type:
				continue

			if not self.check_user_exists(contact.contact_email):
				frappe.msgprint(MISSING_CONTACT_MESSAGE)
				
			if contact.contact_type == "Commercial Contact":
				self.status = "Missing Commercial Contact"
			elif contact.contact_type == "CBAM Representative":
				self.status = "CBAM Rep User Conflict"

			user = self.create_or_update_user(contact)
			contact.contact_person = user.name

			# Always reassign roles and permissions even if updated later
			self.create_permissions(user.name)

	def check_user_exists(self, user_email):
		contact_exists = frappe.db.exists(
			"Contact Person",
			{
				"contact_email": user_email,
				"parenttype": "Operating Company",
				"parent": ["!=", self.name]
			}
		)
		return not contact_exists

	def create_or_update_user(self, contact):
		existing_user = frappe.db.exists("User", {"email": contact.contact_email})
		if existing_user:
			user = frappe.get_doc("User", existing_user)
		else:
			user = frappe.new_doc("User")
			user.first_name = contact.first_name or ""
			user.last_name = contact.last_name or ""
			user.email = contact.contact_email
			user.enabled = 1
			user.send_welcome_email = False

		role_key = (
			"commercial_contact_user_role"
			if contact.contact_type == "Commercial Contact"
			else "cbam_representative_user_role"
		)
		role_name = frappe.db.get_single_value("CBAM Settings", role_key)

		if role_name and role_name not in [r.role for r in user.roles]:
			user.append("roles", {"role": role_name})

		user.save(ignore_permissions=True)
		return user

	def create_permissions(self, user):
		if not user or not self.name or self.name.startswith("New"):
			return

		# Operating Company permission
		if not frappe.db.exists("User Permission", {
			"user": user,
			"allow": "Operating Company",
			"for_value": self.name
		}):
			frappe.get_doc({
				"doctype": "User Permission",
				"user": user,
				"allow": "Operating Company",
				"for_value": self.name,
				"is_default": 1
			}).insert(ignore_permissions=True)

		# Declarant(s) permission
		for declarant in self.get("declarants", []):
			if declarant.declarant and not frappe.db.exists("User Permission", {
				"user": user,
				"allow": "Declarant",
				"for_value": declarant.declarant
			}):
				frappe.get_doc({
					"doctype": "User Permission",
					"user": user,
					"allow": "Declarant",
					"for_value": declarant.declarant,
					"is_default": 1
				}).insert(ignore_permissions=True)

	@frappe.whitelist()
	def send_signup_request(self):
		email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "signup_template"))
		email.send(self)
		self.status = "Pending Verification"
		self.save(ignore_permissions=True)

	def validate_conflict(self):
		if self.status not in [
			"Missing Commercial Contact",
			"CBAM Rep User Conflict",
			"Verification Needed",
			"Pending Verification",
			"Contact Verified",
			"Company Verified"
		]:
			raise frappe.ValidationError("Invalid status. Please use a valid status value.")

		self.user_conflict = 1 if self.status == "Verification Needed" else 0

	def set_title(self):
		self.title = f"{self.supplier_name}-{self.supplier_number}"

	def validate_duplicate_contacts(self):
		seen = set()
		for row in self.contact_persons:
			key = (row.contact_person, row.contact_type)
			if key in seen:
				frappe.throw(
					f"Duplicate entry: User <b>{row.contact_person}</b> already exists as <b>{row.contact_type}</b>."
				)
			seen.add(key)

@frappe.whitelist()
def send_bulk_signup_request(operating_companys):
	operating_companys = json.loads(operating_companys)
	if len(operating_companys) > 0:
		for company in operating_companys:
			operating_company = frappe.get_doc("Operating Company", company.get("name"))
			operating_company.send_signup_request()
