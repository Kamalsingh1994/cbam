# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBAMBenchmarkIndicator(Document):
	def autoname(self):
		"""Generate name from (code) + ' ' + description"""
		if self.code and self.description:
			self.name = f"({self.code}) {self.description}"
	
	def validate(self):
		# Validate code format (single character A-Z, 0-9)
		if self.code and len(self.code) > 1:
			frappe.throw("Code must be a single character (A-Z, 0-9)")
		
		if self.code and not self.code.isalnum():
			frappe.throw("Code must be alphanumeric (A-Z, 0-9)")
		
		# Ensure code is uppercase
		if self.code:
			self.code = self.code.upper()
		
		# Ensure name is set (in case autoname wasn't called)
		if not self.name and self.code and self.description:
			self.name = f"({self.code}) {self.description}"

