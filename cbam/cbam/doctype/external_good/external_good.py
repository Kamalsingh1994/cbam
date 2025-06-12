# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExternalGood(Document):
	def validate(self):
		if self.declarant and not self.is_user_allowed_declarant(self.declarant, frappe.session.user):
			self.declarant = None
	
	def is_user_allowed_declarant(self, declarant, user):
		return frappe.db.exists("Declarant User", {
			"parent": declarant,
			"user": user
		})