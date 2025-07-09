# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExternalGood(Document):
	def validate(self):
		if self.raw_mass:
			self.raw_mass_tonne = float(self.raw_mass) / 1000


