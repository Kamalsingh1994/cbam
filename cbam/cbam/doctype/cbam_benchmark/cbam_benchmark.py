# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBAMBenchmark(Document):
	def validate(self):
		# Validate date range
		if self.valid_from_year and self.valid_to_year:
			from_year = frappe.db.get_value("Year", self.valid_from_year, "year")
			to_year = frappe.db.get_value("Year", self.valid_to_year, "year")
			
			if from_year and to_year and from_year > to_year:
				frappe.throw("Valid From Year must be less than or equal to Valid To Year")
		
		# Validate unique indicators in benchmark_values table
		indicators = []
		for row in self.benchmark_values:
			if row.cbam_benchmark_indicator:
				if row.cbam_benchmark_indicator in indicators:
					frappe.throw(f"Duplicate CBAM Benchmark Indicator '{row.cbam_benchmark_indicator}' found in Benchmark Values table")
				indicators.append(row.cbam_benchmark_indicator)
		
		# Validate no overlapping date ranges for same CN code
		if self.cn_code and self.valid_from_year:
			from_year = frappe.db.get_value("Year", self.valid_from_year, "year")
			to_year = frappe.db.get_value("Year", self.valid_to_year, "year") if self.valid_to_year else None
			
			existing = frappe.get_all("CBAM Benchmark",
				filters={"cn_code": self.cn_code, "name": ["!=", self.name]},
				fields=["name", "valid_from_year", "valid_to_year"]
			)
			
			for existing_bm in existing:
				existing_from = frappe.db.get_value("Year", existing_bm.valid_from_year, "year") if existing_bm.valid_from_year else None
				existing_to = frappe.db.get_value("Year", existing_bm.valid_to_year, "year") if existing_bm.valid_to_year else None
				
				if self._ranges_overlap(from_year, to_year, existing_from, existing_to):
					frappe.throw(f"Date range overlaps with existing benchmark {existing_bm.name}")
	
	def _ranges_overlap(self, from1, to1, from2, to2):
		"""Check if two date ranges overlap"""
		# If either range is None (open-ended), they overlap if they start before the other ends
		if to1 is None and to2 is None:
			return True  # Both open-ended, they overlap
		if to1 is None:
			return from1 <= to2  # Range 1 is open-ended
		if to2 is None:
			return from2 <= to1  # Range 2 is open-ended
		
		# Both have end dates, check overlap
		return from1 <= to2 and from2 <= to1
	
	def on_update(self):
		"""Update all affected goods when benchmark changes"""
		from cbam.utils.benchmark import update_affected_goods_by_cn_code
		if self.cn_code:
			update_affected_goods_by_cn_code(self.cn_code)
