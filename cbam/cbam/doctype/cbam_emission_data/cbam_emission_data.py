# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os

from cbam.utils import rename_any_file
class CBAMEmissionData(Document):
	def on_update(self):
		self.update_good_installation_name()
		
		# Check if emission_attachment has actually changed (new file uploaded)
		has_attachment_changed = self.has_value_changed("emission_attachment")
		
		if self.emission_attachment and has_attachment_changed:
			oc = self.operating_company or "OC-UNKNOWN"
			emission_id = self.name or "EMISSION-UNKNOWN"
			original_file = self.emission_attachment.split('/')[-1]
			expected_prefix = f"{oc}_{emission_id}_"

			# If file already starts with "OC", don't rename it - use as is
			if original_file.upper().startswith("OC"):
				return

			# Only rename if current filename does not match target pattern exactly once
			already_correct = original_file.startswith(expected_prefix)
			prefix_count = original_file.count(expected_prefix)
			if already_correct and prefix_count == 1:
				return

			# Remove all leading known prefixes before applying target prefix
			base_name = original_file
			# Remove new emission prefix if already present (to handle renames)
			while base_name.startswith(expected_prefix):
				base_name = base_name[len(expected_prefix):]
			
			# Remove old supplier-based prefix if present (migration from old format)
			# Old format: OC-xxx_supplier_... -> remove everything up to second underscore
			if base_name.startswith(f"{oc}_") and not base_name.startswith(expected_prefix):
				# Check if it's old format (OC-xxx_supplier_)
				parts_after_oc = base_name[len(f"{oc}_"):].split('_', 1)
				if len(parts_after_oc) > 1:
					# This is old format: OC-xxx_supplier_filename -> extract just filename
					base_name = parts_after_oc[1]
			
			new_file_name = f"{expected_prefix}{base_name}"
			if original_file == new_file_name:
				return  # exactly same name--nothing to do
			
			# Check if source file exists before attempting rename
			file_url = self.emission_attachment
			if file_url.startswith("/private/files/"):
				site_path = frappe.get_site_path("private")
				source_path = os.path.abspath(os.path.join(site_path, "files", original_file))
			elif file_url.startswith("/files/"):
				site_path = frappe.get_site_path("public")
				source_path = os.path.abspath(os.path.join(site_path, "files", original_file))
			else:
				# Remote file or invalid URL - skip rename
				return
			
			# Only attempt rename if source file actually exists
			if not os.path.exists(source_path):
				frappe.log_error(
					"File Rename Skipped - Source Not Found",
					f"Source file does not exist: {source_path}. File might be used by another emission or stored remotely."
				)
				return
				
			result = rename_any_file(self.emission_attachment, new_file_name)
			if result and isinstance(result, dict) and "file_url" in result:
				# Update the field value if file URL changed
				if result["file_url"] != self.emission_attachment:
					self.emission_attachment = result["file_url"]
					# Update the database directly to persist the new filename
					frappe.db.set_value(self.doctype, self.name, "emission_attachment", result["file_url"], update_modified=False)
					frappe.db.commit()
		
	def after_insert(self):
		self.add_to_installation_cht()
		self.update_good_installation_name()


	def on_trash(self):
		self.delete_child_from_installation_cht()
		self.delete_link_in_good()


	def add_to_installation_cht(self):
		has_cbam_installation_changed = self.has_value_changed("cbam_installation")
		if has_cbam_installation_changed:
			installation = frappe.get_doc("CBAM Installation", self.cbam_installation)
			installation.append("emission_datas", {
				"emission_data": self.name
			})
			installation.save(ignore_permissions=True)

	def delete_child_from_installation_cht(self):
		if self.cbam_installation:
			installation = frappe.get_doc("CBAM Installation", self.cbam_installation)
			for child in installation.emission_datas:
				if child.emission_data == self.name:
					child.delete()

	def delete_link_in_good(self):
		linked_goods_list = frappe.get_all("Good", filters={"emission_data": self.name}, fields=["name"], pluck="name")
		for good in linked_goods_list:
			frappe.db.set_value("Good", good, "emission_data", None)


	def update_good_installation_name(self):
		if self.operating_company and self.installation_name:
			good_docs = frappe.get_all("Good", 
                filters={"operating_company": self.operating_company},
                fields=["name"]
            )
			for good in good_docs:
				frappe.db.set_value("Good", good.name, "installation_name", self.installation_name)
