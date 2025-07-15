# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomsImport(Document):
	def on_trash(self):
		self.delete_all_goods()

	def delete_all_goods(self):
		for good in self.goods:
			frappe.db.set_value("Good", good.name, "internal_customs_import_number", None)
			frappe.db.delete("Good", {
				"name": good.name
			})

	def validate(self):
		if self.current:
			existing = frappe.db.get_value("Customs Import", {"current": 1, "name": ["!=", self.name]}, "name")

			if existing:
				frappe.db.sql("""
					UPDATE `tabCustoms Import`
					SET current = 0
					WHERE name = %s
				""", (existing,))

				frappe.msgprint(f"Customs Import <b>{self.name}</b> is now current, current status removed from <b>{existing}</b>.")

