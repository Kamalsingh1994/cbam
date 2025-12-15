# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CountryDefaultBenchmark(Document):
	def autoname(self):
		"""Generate name based on country or global default"""
		if self.is_global_default:
			# For global default, use format: CDB-GLOBAL-####
			from frappe.model.naming import make_autoname
			self.name = make_autoname("CDB-GLOBAL-.####")
		elif self.country:
			# For country-specific, use format: CDB-{country}-####
			# Clean country name for use in name (remove special chars)
			country_clean = self.country.replace(" ", "-").replace("/", "-")
			from frappe.model.naming import make_autoname
			series = f"CDB-{country_clean}-.####"
			self.name = make_autoname(series)
		else:
			# Fallback to default series
			from frappe.model.naming import make_autoname
			self.name = make_autoname("CDB-.####")
	
	def validate(self):
		# Validate that either country or is_global_default is set
		if not self.is_global_default and not self.country:
			frappe.throw("Either Country must be specified or Is Global Default must be checked")
		
		if self.is_global_default and self.country:
			frappe.throw("Cannot specify both Country and Is Global Default. If Is Global Default is checked, Country should be empty")
		
		# Validate unique CN codes in table
		cn_codes = []
		for row in self.benchmark_values:
			if row.cn_code:
				if row.cn_code in cn_codes:
					frappe.throw(f"Duplicate CN Code {row.cn_code} found in Benchmark Values table")
				cn_codes.append(row.cn_code)
		
		# Validate multiplication factor > 0
		for row in self.benchmark_values:
			if row.benchmark_multiplication_factor and row.benchmark_multiplication_factor <= 0:
				frappe.throw(f"Benchmark Multiplication Factor must be greater than 0 for CN Code {row.cn_code}")
	
	def on_update(self):
		"""Update all affected goods when country default benchmark changes"""
		from cbam.utils.benchmark import update_affected_goods_by_country
		if self.is_global_default:
			# For global default, update all goods (no specific country)
			# We'll update goods that don't have country-specific defaults
			# For simplicity, we can update all goods, or skip if too many
			pass  # Global default affects all, so we skip auto-update (too many records)
		elif self.country:
			update_affected_goods_by_country(self.country)

