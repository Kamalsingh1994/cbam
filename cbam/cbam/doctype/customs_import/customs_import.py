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
		self.update_year()
		if self.current:
			existing = frappe.db.get_value("Customs Import", {"current": 1, "name": ["!=", self.name]}, "name")

			if existing:
				frappe.db.sql("""
					UPDATE `tabCustoms Import`
					SET current = 0
					WHERE name = %s
				""", (existing,))

				frappe.msgprint(f"Customs Import <b>{self.name}</b> is now current, current status removed from <b>{existing}</b>.")

	def update_year(self):
		"""Extract year from from_date and update the year field"""
		if self.from_date:
			# Extract year from from_date
			if isinstance(self.from_date, str):
				# If from_date is a string, parse it
				from datetime import datetime
				try:
					date_obj = datetime.strptime(self.from_date, '%Y-%m-%d')
					self.year = date_obj.year
				except ValueError:
					# Try different date format if needed
					try:
						date_obj = datetime.strptime(self.from_date, '%Y-%m-%d %H:%M:%S')
						self.year = date_obj.year
					except ValueError:
						frappe.msgprint(f"Invalid date format for from_date: {self.from_date}")
			else:
				# If from_date is already a date object
				self.year = self.from_date.year
		