# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class CNCode(Document):
	def validate(self):
		cn_code_str = str(self.cn_code) if self.cn_code else ""
		cn_code_len = len(cn_code_str)

		# Validate length (must be 4, 6, or 8 digits)
		if cn_code_len not in [4, 6, 8]:
			frappe.throw(_("CN Code must be 4, 6, or 8 digits"))

		# Force is_group based on length (mandatory rule)
		if cn_code_len == 8:
			# 8-digit codes are always leaf nodes (not groups)
			if self.is_group:
				frappe.throw(_("8-digit CN Codes cannot be groups. Only 4-digit and 6-digit codes can be groups."))
			self.is_group = 0
		elif cn_code_len in [4, 6]:
			# 4 and 6-digit codes must be groups
			if not self.is_group:
				frappe.throw(_("{0}-digit CN Codes must be groups. Please check 'Is Group'.").format(cn_code_len))
			self.is_group = 1

		# Validate parent relationship
		if self.parent_cn_code:
			parent_doc = frappe.get_doc("CN Code", self.parent_cn_code)
			parent_code_str = str(parent_doc.cn_code)
			parent_code_len = len(parent_code_str)

			# Parent must be a group
			if not parent_doc.is_group:
				frappe.throw(_("Parent CN Code must be a group (is_group must be checked)"))

			# Parent must be shorter than child
			if parent_code_len >= cn_code_len:
				frappe.throw(_("Parent CN Code must be shorter than child CN Code"))

			# Parent must be a prefix of child
			if not cn_code_str.startswith(parent_code_str):
				frappe.throw(_("Parent CN Code '{0}' must be a prefix of child CN Code '{1}'").format(
					parent_code_str, cn_code_str
				))

			# Validate hierarchy: 4-digit → 6-digit → 8-digit
			if cn_code_len == 6 and parent_code_len != 4:
				frappe.throw(_("6-digit CN Code must have a 4-digit parent"))
			elif cn_code_len == 8 and parent_code_len != 6:
				frappe.throw(_("8-digit CN Code must have a 6-digit parent"))

		# Validate: 8-digit codes cannot have children (they are leaf nodes)
		if cn_code_len == 8 and self.is_group:
			frappe.throw(_("8-digit CN Codes cannot be groups. Only 4-digit and 6-digit codes can be groups."))
