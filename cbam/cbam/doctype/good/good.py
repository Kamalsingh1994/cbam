# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt
import json
import frappe
from frappe.model.document import Document
from cbam.send_email.create_email import create_email
from cbam.send_email.create_new_supplier_user import create_new_supplier_user
from frappe.model.naming import getseries


class Good(Document):
	def autoname(self):
		if self.parent_good:
			prefix = self.parent_good
			self.name = f'{prefix}-{getseries(prefix, 2)}'


	def validate(self):
		self.set_countries()
		if self.supplier_number and self.supplier_name:
			operating_company = frappe.db.get_value("Operating Company", {"supplier_number": self.supplier_number, "declarant":self.declarant}, "name")
			if operating_company:
				self.operating_company = operating_company
		if self.operating_company:
			self.supplier_number, self.supplier_name = frappe.db.get_values("Operating Company", self.operating_company, ['supplier_number', 'supplier_name'])[0]

	def set_countries(self):
		self.country_of_origin = frappe.db.get_value("Country", {"code": self.country_of_origin_code}, "name")
		self.shipping_country = frappe.db.get_value("Country", {"code": self.shipping_country_code}, "name")


	def _before_save(self):
		self.delete_old_employee_if_supplier_changed()
		self.get_main_contact_employee()
		if self.is_data_confirmed == True and self.manufacture == "I am able to provide the emission data of this product":
			self.status = "Done"
		self.add_to_supplier_cht()
		self.add_to_employee_cht()
		self.add_to_customs_import_cht()

	def _1validate(self):
		if self.manufacture == "The mass of this product needs to be split into several parts, due to shared responsibilities. I will assign the responsible parties" and not self.good_splitted:
			self.split_good()
		elif self.manufacture == "I am not able to provide emission data and will delegate this request":
			self.forward_goods()
		elif self.manufacture == "This item was not purchased from us. I want to reject this request back to the sender.":
			self.reject_goods()

	def reject_goods(self):
		self.status = "Rejected"
		#send email alert to the owner of good
		self.send_email("Rejected")


	def forward_goods(self):
		
		self.forwarded_from_employee = self.employee
		if self.forward_to == "Another Supplier":
			self.forwarded_from_supplier = self.supplier
			self.supplier = self.forward_to_supplier
			self.set_main_contact()
			self.send_email("Another supplier is responsible")
		else:
			self.employee = self.forward_to_employee
			self.send_email("Another employee is responsible")
		self.forward_to_supplier = ""
		self.forward_to_employee = ""
		self.manufacture = "I am able to provide the emission data of this product"
		self.is_data_confirmed = False
	def on_trash(self):
		self.delete_all_good_item()

	def delete_old_employee_if_supplier_changed(self):
		return
		has_supplier_changed = self.has_value_changed("supplier")
		if has_supplier_changed and not self.is_new():
			self.employee = None

	def get_main_contact_employee(self):
		if self.supplier and not self.employee:
			self.set_main_contact()


	def set_main_contact(self):
		supplier_doc = frappe.get_doc("Supplier", self.supplier)
		for child in supplier_doc.employees:
			if child.is_main_contact in ["1", 1, True]:
				main_contact = child.employee_number
				self.employee = main_contact

	def handle_total_raw_mass(self):
		total_raw_mass = sum(
			getattr(self, attr, 0) or 0
			for attr in [
				'split_raw_mass_1',
				'split_raw_mass_2',
				'split_raw_mass_3',
				'split_raw_mass_4',
				'split_raw_mass_5'
			]
		)
		if total_raw_mass != self.raw_mass:
			original_raw_mass = self.raw_mass

			frappe.throw(f"The raw mass total of the components is not equal to the raw mass of the original good. <br><br> The total should be {original_raw_mass}, not {total_raw_mass}. <br><br> Please change the raw masses of the components and ensure that they add up to a total of {original_raw_mass}.")

	def split_goods(self):
		
		for i in self.split_details:
			self.create_new_good_doc(i.source, i.source_name, i.qty_to_split)

		self.status = "Split"
		self.save(ignore_permissions=True)
		


	def create_new_good_doc(self, source, source_name, qty):
		new_good = frappe.copy_doc(self)
		new_good.parent_good = self.name
		new_good.raw_mass = qty
		new_good.split_details = []
		new_good.rejected_from_supplier = ""
		new_good.forwarded_from_supplier = ""
		new_good.installation = ""
		new_good.emission_data = ""
		if source == "CBAM Installation":
			new_good.installation = source_name
		else:
			new_good.supplier_name, new_good.supplier_number = frappe.db.get_values("Operating Company", source_name, ["supplier_name", "supplier_number"])[0]
		new_good.insert(ignore_permissions=True)
		if not new_good.installation:
			new_good.send_data_request()
		
		#new_good.send_email(responsiblity)

	def add_to_supplier_cht(self):
		if self.has_value_changed("supplier") and not self.is_new():
			delete_good_item(self.name, "Supplier")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Supplier"}):
			supplier = frappe.get_doc("Supplier", self.supplier)
			supplier.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			supplier.save()
		else:
			self.update_good_items()

	def add_to_employee_cht(self):
		if self.has_value_changed("employee") and not self.is_new():
			delete_good_item(self.name, "Supplier Employee")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Supplier Employee"}):
			employee = frappe.get_doc("Supplier Employee", self.employee)
			employee.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			employee.save()
		else:
			self.update_good_items()

	def add_to_customs_import_cht(self):
		if self.has_value_changed("internal_customs_import_number") and not self.is_new():
			delete_good_item(self.name, "Customs Import")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Customs Import"}):
			customs_import = frappe.get_doc("Customs Import", self.internal_customs_import_number)
			customs_import.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			customs_import.save()
		else:
			self.update_good_items()

	def update_good_items(self):
		frappe.db.set_value("Good Item", {"good_number": self.name}, {
			"supplier": self.supplier,
			"employee": self.employee,
			"status": self.status
			})

	def delete_all_good_item(self):
		good_items = frappe.get_all("Good Item", filters={'good_number': self.name}, fields=["name"], pluck="name")
		for good_item in good_items:
			frappe.db.delete("Good Item", {
				"name": good_item
			})
		frappe.db.commit()

	def check_confirmation_checkbox(self):
		user_email = frappe.session.user
		try:
			user = frappe.get_doc("User", user_email)
		except frappe.DoesNotExistError:
			frappe.throw(_("User not found"))
		role_list = [r.role for r in user.roles]
		if "Supplier" in role_list and self.confirmation_web_form == "true" and self.is_data_confirmed != True:
			frappe.throw("Please check the 'Data Confirmed' checkbox before submitting the form.")

	def set_confirmation_web_form_to_none(self):
		has_value_changed = self.has_value_changed("confirmation_web_form")
		if not has_value_changed and self.confirmation_web_form:
			self.confirmation_web_form = None

	def send_email(self, responsiblity=None, employee=None):
		if responsiblity and responsiblity != "I'm the responsible Person":
			template = ""
			employee_email = frappe.db.get_value("Supplier Employee", self.employee, "email")
			user_exists = frappe.db.exists("User", employee_email)
			settings = frappe.get_single("CBAM Settings")

			if responsiblity == "Another employee is responsible":
				template = settings.tier_1_registered_employee_template
				if not user_exists:
					template = settings.tier_1_unregistered_employee_template
					create_new_supplier_user(self.employee)

			elif responsiblity == "Another supplier is responsible":
				template = settings.tier_n1_registered_template
				if not user_exists:
					create_new_supplier_user(self.employee)
					template = settings.tier_n1_unregistered_template
			elif responsiblity == "Rejected":
				template = settings.supplier_good_rejection_notification_template
			else:
				template = settings.tier_n1_registered_template #! Just for testing reason

			notification = frappe.get_doc("Notification", template)
			notification.send(self)

	@frappe.whitelist()
	def send_data_request(self):
		if self.status in ["Data Submitted", "Rejected"]:
			return
		email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "data_request_template"))
		
		if not email:
			frappe.throw("Please setup Data Request Notification Template in CBAM Settings")
		opp = frappe.get_doc("Operating Company", self.operating_company)
		opp.declarant = opp.declarant
		email.send(opp)
		self.status = "Data Requested"
		self.save()



	def add_split_good_details(self, details):
		for d in details:
			self.append("split_details", {
				"source": "CBAM Installation" if d.get("source") == "Installation" else "Operating Company",
				"source_name": d.get("source_name"),
				"qty_to_split": d.get("qty")
			})
		self.save(ignore_permissions=True)




def delete_good_item(good, parenttype):
	good_item_list = frappe.get_all("Good Item", filters={'good_number': good, 'parenttype': parenttype}, fields=["name"], pluck="name")
	good_item = ', '.join(good_item_list)
	frappe.db.delete("Good Item", {
		"name": good_item
	})
	frappe.db.commit()









@frappe.whitelist()
def send_data_request(goods):
	goods = json.loads(goods)
	supp = []
	for g in goods:
		if g.get('status') != "Data Submitted":
			if not g.get("operating_company") in supp:
				supp.append(g.get("operating_company"))

	email = frappe.get_doc("Notification", frappe.db.get_single_value("CBAM Settings", "data_request_template"))
	if not email:
		frappe.throw("Please setup Data Request Notification Template in CBAM Settings")
		
	for s in supp:
		op = frappe.get_doc("Operating Company", s)
		op.declarant = op.declarant
		if not op.commercial_contact_user:
			op.commercial_contact_user = op.cbam_representative_user
		email.send(op)
	for g in goods:
		if g.get('status') == "Draft":
			frappe.db.set_value("Good", g.get("name"), "status", "Data Requested")


