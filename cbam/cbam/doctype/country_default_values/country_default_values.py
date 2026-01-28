# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CountryDefaultValues(Document):
	def autoname(self):
		"""Generate name based on country or global default"""
		if self.is_global_default:
			# For global default, use format: CDV-GLOBAL-####
			from frappe.model.naming import make_autoname
			self.name = make_autoname("CDV-GLOBAL-.####")
		elif self.country:
			# For country-specific, use format: CDV-{country}-####
			# Clean country name for use in name (remove special chars)
			country_clean = self.country.replace(" ", "-").replace("/", "-")
			from frappe.model.naming import make_autoname
			series = f"CDV-{country_clean}-.####"
			self.name = make_autoname(series)
		else:
			# Fallback to default series
			from frappe.model.naming import make_autoname
			self.name = make_autoname("CDV-.####")

	def validate(self):
		# Validate that either country or is_global_default is set
		if not self.is_global_default and not self.country:
			frappe.throw("Either Country must be specified or Is Global Default must be checked")

		if self.is_global_default and self.country:
			frappe.throw("Cannot specify both Country and Is Global Default. If Is Global Default is checked, Country should be empty")

		# Allow multiple production routes per CN code, but avoid exact duplicates
		seen = set()
		for row in self.benchmark_values:
			if not row.cn_code:
				continue
			key = (row.cn_code, row.production_route_cbam_benchmark_indicator)
			if key in seen:
				frappe.throw(
					f"Duplicate CN Code {row.cn_code} with the same Production Route found in Default Values table"
				)
			seen.add(key)


	def on_update(self):
		"""Update all affected goods when country default values change"""
		from cbam.utils.benchmark import update_affected_goods_by_country
		if self.is_global_default:
			# For global default, update all goods (no specific country)
			# We'll update goods that don't have country-specific defaults
			# For simplicity, we can update all goods, or skip if too many
			pass  # Global default affects all, so we skip auto-update (too many records)
		elif self.country:
			update_affected_goods_by_country(self.country)

