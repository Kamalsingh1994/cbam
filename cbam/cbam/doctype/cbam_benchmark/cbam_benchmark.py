# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBAMBenchmark(Document):
	def validate(self):
		# Validate unique indicators in benchmark_values table
		indicators = []
		for row in self.benchmark_values:
			if row.cbam_benchmark_indicator:
				if row.cbam_benchmark_indicator in indicators:
					frappe.throw(f"Duplicate CBAM Benchmark Indicator '{row.cbam_benchmark_indicator}' found in Benchmark Values table")
				indicators.append(row.cbam_benchmark_indicator)
	
	def on_update(self):
		"""Update all affected goods when benchmark changes"""
		from cbam.utils.benchmark import update_affected_goods_by_cn_code
		if self.cn_code:
			update_affected_goods_by_cn_code(self.cn_code)
