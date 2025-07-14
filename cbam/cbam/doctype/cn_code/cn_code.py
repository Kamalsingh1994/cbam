# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class CNCode(Document):
	def validate(self):
		if self.cn_code and len(str(self.cn_code)) > 8:
			frappe.throw(_("CN Code must be exactly 8 digits"))


 
