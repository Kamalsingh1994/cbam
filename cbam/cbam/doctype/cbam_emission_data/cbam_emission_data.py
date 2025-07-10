# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBAMEmissionData(Document):
	def on_update(self):
		self.update_good_installation_name()
		
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
