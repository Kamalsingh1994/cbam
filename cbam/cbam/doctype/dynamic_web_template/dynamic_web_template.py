# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.website.utils import clear_cache


class DynamicWebTemplate(Document):
	def on_update(self):
		"""Clear website cache when template is updated"""
		# Map template names to their routes
		template_route_map = {
			"CBAM Home": "home",
			"Privacy Policy": "privacy-policy",
			"Impressum": "imprint"
		}
		
		# Clear cache for the specific route if it exists
		if self.template in template_route_map:
			route = template_route_map[self.template]
			clear_cache(route)
		
		# Also clear general website cache to ensure all changes are reflected
		clear_cache()
		frappe.clear_cache(user="Guest")
