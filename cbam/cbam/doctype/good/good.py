# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt
import json
import frappe
from frappe.model.document import Document
from cbam.send_email.create_email import create_email
from cbam.send_email.create_new_supplier_user import create_new_supplier_user
from frappe.model.naming import getseries
from cbam.utils.benchmark import calculate_country_specific_benchmark, get_country_default_emission_values


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

		self.update_name()
		self.calculate_default_emission_values()
		self.calculate_benchmark()
		self.update_rejection_flags()

	def update_name(self):
		for row in self.split_details:
			if not row.source_name:
				continue

			if row.source == "Operating Company":
				row.name_ = frappe.db.get_value("Operating Company", row.source_name, "supplier_name")
			elif row.source == "CBAM Installation":
				row.name_ = frappe.db.get_value("CBAM Installation", row.source_name, "name_of_the_installation")

	def set_countries(self):
		# Only set country_of_origin from code if code is provided and country_of_origin is not already set
		# This prevents resetting country_of_origin when user sets it directly
		if self.country_of_origin_code:
			country_from_code = frappe.db.get_value("Country", {"code": self.country_of_origin_code}, "name")
			if country_from_code:
				self.country_of_origin = country_from_code
		# If country_of_origin is set directly but code is not, try to get code from country
		elif self.country_of_origin and not self.country_of_origin_code:
			country_code = frappe.db.get_value("Country", self.country_of_origin, "code")
			if country_code:
				self.country_of_origin_code = country_code

		# Only set shipping_country from code if code is provided
		if self.shipping_country_code:
			shipping_from_code = frappe.db.get_value("Country", {"code": self.shipping_country_code}, "name")
			if shipping_from_code:
				self.shipping_country = shipping_from_code
		# If shipping_country is set directly but code is not, try to get code from country
		elif self.shipping_country and not self.shipping_country_code:
			shipping_code = frappe.db.get_value("Country", self.shipping_country, "code")
			if shipping_code:
				self.shipping_country_code = shipping_code

	def calculate_benchmark(self):
		"""Calculate and store country-specific CBAM benchmark"""
		# Use manual override if enabled
		if self.use_benchmark_override and self.benchmark_manual_override:
			self.country_specific_default_cbam_benchmark = self.benchmark_manual_override
			self.benchmark_calculation_status = "Manual Override"
			self.benchmark_calculation_details = json.dumps({
				"source": "manual_override",
				"override_value": self.benchmark_manual_override
			})
			self.benchmark_last_calculated_at = frappe.utils.now()
			return

		# Calculate benchmark if CN code and country are available
		if self.cn_code and self.country_of_origin:
			try:
				indicator_override = self._get_selected_benchmark_indicator()
				result = calculate_country_specific_benchmark(
					self.cn_code,
					self.country_of_origin,
					self.hand_over_date,
					indicator_override=indicator_override
				)

				self.country_specific_default_cbam_benchmark = result.get("benchmark_value")
				self.benchmark_calculation_status = result.get("status", "Error")
				self.benchmark_calculation_details = json.dumps(result.get("details", {}))
				self.benchmark_last_calculated_at = frappe.utils.now()

				# Log warnings if any (keep title short for error log)
				warnings = result.get("warnings", [])
				if warnings and self.benchmark_calculation_status != "Calculated":
					# Truncate warnings for title, full details in message
					warnings_str = ', '.join(warnings)
					message = f"Good: {self.name}\nCN Code: {self.cn_code}\nCountry: {self.country_of_origin}\nWarnings: {warnings_str}"
					title = f"Benchmark warnings: Good {self.name}"[:140]
					frappe.log_error(title, message)
			except Exception as e:
				error_msg = str(e)[:500]  # Limit error message length
				message = f"Good: {self.name}\nCN Code: {self.cn_code}\nCountry: {self.country_of_origin}\nError: {error_msg}"
				title = f"Benchmark calc error: Good {self.name}"[:140]
				frappe.log_error(title, message)
				self.country_specific_default_cbam_benchmark = None
				self.benchmark_calculation_status = "Error"
				self.benchmark_calculation_details = json.dumps({"error": str(e)})
				self.benchmark_last_calculated_at = frappe.utils.now()
		else:
			# Missing required fields
			self.country_specific_default_cbam_benchmark = None
			self.benchmark_calculation_status = "Missing Data"
			self.benchmark_calculation_details = json.dumps({
				"missing_fields": {
					"cn_code": not bool(self.cn_code),
					"country_of_origin": not bool(self.country_of_origin)
				}
			})

	def _get_selected_benchmark_indicator(self):
		"""Use applicable product's production route for benchmark selection."""
		for row in self.country_specific_default_emission_values or []:
			if row.applicable_product and row.production_route_cbam_benchmark_indicator:
				return row.production_route_cbam_benchmark_indicator
		return None

	def calculate_default_emission_values(self):
		"""Populate default emission values from Country Default Values"""
		if not self.cn_code or not self.country_of_origin:
			self.country_specific_default_emission_values = []
			self.select_applicable_product_for_cn_code = 0
			return

		should_refresh = self.is_new() or self.has_value_changed("cn_code") or self.has_value_changed("country_of_origin")
		selected_key = None
		if self.country_specific_default_emission_values:
			for row in self.country_specific_default_emission_values:
				if row.applicable_product:
					selected_key = (row.cn_code, row.production_route_cbam_benchmark_indicator)
					break

		if should_refresh or not self.country_specific_default_emission_values:
			rows, _details = get_country_default_emission_values(self.country_of_origin, self.cn_code)
			self.country_specific_default_emission_values = []
			for row in rows:
				child = self.append("country_specific_default_emission_values", {
					"cn_code": row.get("cn_code"),
					"description": row.get("description"),
					"default_value_direct_emissions": row.get("default_value_direct_emissions"),
					"default_value_indirect_emissions": row.get("default_value_indirect_emissions"),
					"default_value_total_emissions": row.get("default_value_total_emissions"),
					"default_value_2026": row.get("default_value_2026"),
					"default_value_2027": row.get("default_value_2027"),
					"default_value_2028_onwards": row.get("default_value_2028_onwards"),
					"production_route_cbam_benchmark_indicator": row.get("production_route_cbam_benchmark_indicator")
				})
				if selected_key and (child.cn_code, child.production_route_cbam_benchmark_indicator) == selected_key:
					child.applicable_product = 1

		self._sync_default_emission_selection_status()

	def update_rejection_flags(self):
		"""Set rejection flags for declarant visibility."""
		if self.status != "Rejected":
			self.rejected_within_supply_chain = 0
			self.rejected_to_declarant = 0
			return

		if not self.rejected_from_supplier or not self.operating_company:
			self.rejected_within_supply_chain = 0
			self.rejected_to_declarant = 0
			return

		if self.rejected_from_supplier == self.operating_company:
			self.rejected_within_supply_chain = 0
			self.rejected_to_declarant = 1
		else:
			self.rejected_within_supply_chain = 1
			self.rejected_to_declarant = 0

	def _sync_default_emission_selection_status(self):
		applicable_rows = [row for row in self.country_specific_default_emission_values if row.applicable_product]
		if len(applicable_rows) > 1:
			frappe.throw("Only one Applicable Product can be selected.")

		if applicable_rows:
			self.select_applicable_product_for_cn_code = 0
		else:
			self.select_applicable_product_for_cn_code = 1 if len(self.country_specific_default_emission_values) > 1 else 0


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

	def on_update(self):
		"""Called after document is saved to database"""
		# Only process if document has a name (is saved)
		if self.name:
			self.add_emission_attachment_to_sidebar()

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

	def add_emission_attachment_to_sidebar(self):
		"""Add/Update all files with same file_url from emission_data_attachment to sidebar"""
		if not self.name:
			return

		try:
			# Get old emission_data_attachment if document was updated
			old_attachment = None
			old_emission_data = None
			doc_before_save = self.get_doc_before_save()
			if doc_before_save:
				old_attachment = doc_before_save.get("emission_data_attachment")
				old_emission_data = doc_before_save.get("emission_data")

			# Check if emission_data has changed - if so, we need to update sidebar
			emission_data_changed = old_emission_data != self.emission_data

			# Get current emission_data_attachment
			# Always get from emission_data directly to ensure we have the latest value
			# This is important because fetch fields might not be updated yet when on_update runs
			current_attachment = None
			if self.emission_data:
				current_attachment = frappe.db.get_value("CBAM Emission Data", self.emission_data, "emission_attachment")

			# Fallback to fetch field value if emission_data not linked
			if not current_attachment:
				current_attachment = self.emission_data_attachment
				# If document is saved, fetch the latest value from DB to get updated fetch field
				if self.name:
					db_value = frappe.db.get_value("Good", self.name, "emission_data_attachment")
					if db_value:
						current_attachment = db_value

			# If emission_data changed, also check old attachment from old emission_data
			if emission_data_changed and old_emission_data:
				old_attachment = frappe.db.get_value("CBAM Emission Data", old_emission_data, "emission_attachment")

			# Remove all old files with the old file_url if attachment changed
			if old_attachment and old_attachment != current_attachment:
				# Get all files attached to Good document with the old file_url
				old_files = frappe.get_all("File", {
					"file_url": old_attachment,
					"attached_to_doctype": "Good",
					"attached_to_name": self.name
				}, ["name"])

				# Remove all old files
				for old_file in old_files:
					try:
						frappe.delete_doc("File", old_file.name, ignore_permissions=True, force=True)
					except Exception as e:
						frappe.log_error(f"Error removing old emission attachment: {str(e)}", "Good.add_emission_attachment_to_sidebar")

				if old_files:
					frappe.db.commit()

			# If no current attachment, return (old ones already removed above if they existed)
			if not current_attachment:
				return

			file_url = current_attachment

			# Get ALL files with this file_url (there can be multiple files with same URL but different filenames)
			all_files_with_url = frappe.get_all("File", {
				"file_url": file_url
			}, ["name", "file_name", "is_private"], order_by="creation desc")

			if not all_files_with_url:
				# No files found with this URL, try to create one from the URL
				file_name = file_url.split('/')[-1]
				if file_name and file_name != file_url:
					try:
						is_private = 1 if file_url.startswith("/private/files/") else 0
						new_file = frappe.get_doc({
							"doctype": "File",
							"file_name": file_name,
							"file_url": file_url,
							"attached_to_doctype": "Good",
							"attached_to_name": self.name,
							"is_private": is_private,
							"folder": "Home/Attachments"
						})
						new_file.insert(ignore_permissions=True)
						frappe.db.commit()
					except Exception as e:
						frappe.log_error(f"Error creating file from URL: {str(e)}", "Good.add_emission_attachment_to_sidebar")
				return

			# Get list of files already attached to this Good document with this file_url
			existing_files = frappe.get_all("File", {
				"file_url": file_url,
				"attached_to_doctype": "Good",
				"attached_to_name": self.name
			}, ["file_name"])

			existing_file_names = {f.file_name for f in existing_files}

			# Attach all files with this file_url that are not already attached
			for file_info in all_files_with_url:
				file_name = file_info.file_name

				# Skip if this file is already attached to this Good document
				if file_name in existing_file_names:
					continue

				# Create a new File record with the same file_url reference
				# Determine if file is private
				is_private = file_info.is_private if file_info.is_private is not None else (1 if file_url.startswith("/private/files/") else 0)

				# Create new File record attached to this Good document
				try:
					new_file = frappe.get_doc({
						"doctype": "File",
						"file_name": file_name,
						"file_url": file_url,
						"attached_to_doctype": "Good",
						"attached_to_name": self.name,
						"is_private": is_private,
						"folder": "Home/Attachments"
					})
					new_file.insert(ignore_permissions=True)
				except frappe.DuplicateEntryError:
					# File already exists, skip
					pass
				except Exception as e:
					frappe.log_error(f"Error adding emission attachment to sidebar: {str(e)}", "Good.add_emission_attachment_to_sidebar")

			frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Error in add_emission_attachment_to_sidebar: {str(e)}", "Good.add_emission_attachment_to_sidebar")

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
			frappe.throw("User not found")
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
		if op.cbam_representative_user:
			op.commercial_contact_user = op.cbam_representative_user
			op.main_contact_employee_last_name = op.cbam_representive_last_name
		email.send(op)
	for g in goods:
		if g.get('status') == "Draft":
			frappe.db.set_value("Good", g.get("name"), "status", "Data Requested")


@frappe.whitelist()
def get_supplier_snapshot():
    # Same method you use on frontend
    from cbam.utils.supplier import get_supplier
    return get_supplier()

def on_submit(doc, method):
    # Get supplier snapshot
    supplier = get_supplier_snapshot()

    # Set snapshot fields on Good
    doc.country = supplier.get("country")
    doc.city = supplier.get("city")
    doc.zip_code = supplier.get("zip_code")
    doc.street_and_number = supplier.get("street_and_number")
    doc.company_email = supplier.get("company_email")
    doc.company_phone_number = supplier.get("company_phone_number")

def update_good_sidebar_on_emission_data_update(emission_data_doc, method):
	"""Update Good document sidebar attachments when emission_data is updated"""
	if not emission_data_doc.emission_attachment:
		return

	# Find all Good documents linked to this emission_data
	good_docs = frappe.get_all("Good",
		filters={"emission_data": emission_data_doc.name},
		fields=["name"]
	)

	for good in good_docs:
		try:
			good_doc = frappe.get_doc("Good", good.name)
			# Update the sidebar attachment
			good_doc.add_emission_attachment_to_sidebar()
		except Exception as e:
			frappe.log_error(f"Error updating Good sidebar on emission_data update: {str(e)}", "update_good_sidebar_on_emission_data_update")
