# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBAMReport(Document):
	pass

@frappe.whitelist()
def get_declarant_by_user(user):
	"""Get declarant name for a user from declarant_user child table"""
	try:
		# Check if user exists in declarant_user child table
		declarant = frappe.db.sql("""
			SELECT parent 
			FROM `tabDeclarant User` 
			WHERE user = %s 
			LIMIT 1
		""", user, as_dict=True)
		
		if declarant:
			return {"declarant": declarant[0].parent}
		else:
			return {"declarant": None}
			
	except Exception as e:
		frappe.log_error(f"Error in get_declarant_by_user: {str(e)}")
		return {"declarant": None}
