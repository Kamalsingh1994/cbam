# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.utils import flt, today, getdate


@frappe.whitelist()
def calculate_country_specific_benchmark(cn_code, country, reference_date=None):
	"""
	Calculate country-specific CBAM benchmark with multi-tier fallback
	
	Args:
		cn_code: CN Code (string or Link)
		country: Country name (string or Link)
		reference_date: Date for benchmark lookup (defaults to today)
	
	Returns:
		dict: {
			"benchmark_value": float or None,
			"status": str,  # "Calculated" | "Missing Data" | "Error"
			"details": dict,
			"warnings": list
		}
	"""
	warnings = []
	details = {
		"cn_code": cn_code,
		"country": country,
		"indicator_used": None,
		"factor_used": None,
		"base_value": None,
		"source": None
	}
	
	if not cn_code or not country:
		return {
			"benchmark_value": None,
			"status": "Missing Data",
			"details": details,
			"warnings": ["CN Code or Country is missing"]
		}
	
	# Determine reference year
	from datetime import date as date_class
	
	if reference_date:
		try:
			ref_date = getdate(reference_date)
			# Ensure we have a date object (not a string)
			if isinstance(ref_date, date_class):
				reference_year = ref_date.year
			else:
				# If getdate returned something unexpected, use current year
				reference_year = date_class.today().year
		except (ValueError, TypeError, AttributeError) as e:
			# If date parsing fails, use current year
			reference_year = date_class.today().year
	else:
		reference_year = date_class.today().year
	
	details["reference_year"] = reference_year
	
	try:
		# Step 1: Get Country Default Benchmark
		cdb = get_country_default_benchmark(country, cn_code)
		
		if not cdb:
			# Fallback: Try global default
			cdb = get_global_default_benchmark(cn_code)
			if not cdb:
				warnings.append(f"No Country Default for {country} / CN {cn_code}")
				warnings.append(f"No Global Default for CN {cn_code}")
				return {
					"benchmark_value": None,
					"status": "Missing Data",
					"details": details,
					"warnings": warnings
				}
			details["source"] = "global_default"
		else:
			details["source"] = "country_specific"
		
		indicator = cdb.get("cbam_benchmark_indicator")
		factor = cdb.get("benchmark_multiplication_factor", 1.0)
		
		details["indicator_used"] = indicator
		details["factor_used"] = factor
		
		if not indicator:
			warnings.append("Indicator missing in Country Default Benchmark")
			return {
				"benchmark_value": None,
				"status": "Missing Data",
				"details": details,
				"warnings": warnings
			}
		
		# Step 2: Get CBAM Benchmark
		cbam_benchmark = get_cbam_benchmark(cn_code, indicator, reference_year)
		
		if not cbam_benchmark:
			warnings.append(f"No CBAM Benchmark: CN {cn_code}, Indicator {indicator}, Year {reference_year}")
			return {
				"benchmark_value": None,
				"status": "Missing Data",
				"details": details,
				"warnings": warnings
			}
		
		base_value = cbam_benchmark.get("emission_benchmark")
		details["base_value"] = base_value
		
		if base_value is None:
			warnings.append("Emission Benchmark value is None in CBAM Benchmark")
			return {
				"benchmark_value": None,
				"status": "Missing Data",
				"details": details,
				"warnings": warnings
			}
		
		# Step 3: Calculate
		result = flt(base_value) * flt(factor)
		details["calculated_value"] = result
		
		return {
			"benchmark_value": result,
			"status": "Calculated",
			"details": details,
			"warnings": warnings
		}
	
	except Exception as e:
		error_msg = str(e)[:500]  # Limit error message length
		frappe.log_error("Benchmark Calculation Error", f"Error calculating benchmark: {error_msg}")
		return {
			"benchmark_value": None,
			"status": "Error",
			"details": details,
			"warnings": [f"Error during calculation: {str(e)}"]
		}


def get_country_default_benchmark(country, cn_code):
	"""
	Get Country Default Benchmark for a specific country and CN code
	
	Returns:
		dict: {
			"cbam_benchmark_indicator": str,
			"benchmark_multiplication_factor": float
		} or None
	"""
	# Normalize CN code - handle both Link and string formats
	if isinstance(cn_code, str):
		# If it's a string, it might be the CN code value or the name
		# Try to get the CN Code name if it's a numeric value
		try:
			cn_code_int = int(cn_code)
			cn_code_name = frappe.db.get_value("CN Code", {"cn_code": cn_code_int}, "name")
			if cn_code_name:
				cn_code = cn_code_name
		except (ValueError, TypeError):
			# If it's already a name or can't convert, use as is
			pass
	
	# Get Country Default Benchmark document
	cdb_docs = frappe.get_all("Country Default Benchmark",
		filters={"country": country, "is_global_default": 0},
		fields=["name"]
	)
	
	if not cdb_docs:
		return None
	
	cdb_doc = frappe.get_doc("Country Default Benchmark", cdb_docs[0].name)
	
	# Find matching CN code in table
	# CN code in table is a Link field, so compare with name
	for row in cdb_doc.benchmark_values:
		# row.cn_code is a Link field (name of CN Code doctype)
		# Compare with the normalized cn_code
		if row.cn_code == cn_code:
			return {
				"cbam_benchmark_indicator": row.cbam_benchmark_indicator,
				"benchmark_multiplication_factor": flt(row.benchmark_multiplication_factor)
			}
	
	return None


def get_global_default_benchmark(cn_code):
	"""
	Get Global Default Benchmark (no country specified) for a CN code
	
	Returns:
		dict: {
			"cbam_benchmark_indicator": str,
			"benchmark_multiplication_factor": float
		} or None
	"""
	# Normalize CN code - handle both Link and string formats
	if isinstance(cn_code, str):
		# If it's a string, it might be the CN code value or the name
		# Try to get the CN Code name if it's a numeric value
		try:
			cn_code_int = int(cn_code)
			cn_code_name = frappe.db.get_value("CN Code", {"cn_code": cn_code_int}, "name")
			if cn_code_name:
				cn_code = cn_code_name
		except (ValueError, TypeError):
			# If it's already a name or can't convert, use as is
			pass
	
	# Get Global Default Benchmark document
	cdb_docs = frappe.get_all("Country Default Benchmark",
		filters={"is_global_default": 1},
		fields=["name"]
	)
	
	if not cdb_docs:
		return None
	
	cdb_doc = frappe.get_doc("Country Default Benchmark", cdb_docs[0].name)
	
	# Find matching CN code in table
	# CN code in table is a Link field, so compare with name
	for row in cdb_doc.benchmark_values:
		# row.cn_code is a Link field (name of CN Code doctype)
		# Compare with the normalized cn_code
		if row.cn_code == cn_code:
			return {
				"cbam_benchmark_indicator": row.cbam_benchmark_indicator,
				"benchmark_multiplication_factor": flt(row.benchmark_multiplication_factor)
			}
	
	return None


def get_cbam_benchmark(cn_code, indicator, year):
	"""
	Get CBAM Benchmark value for a CN code, indicator, and year
	
	Returns:
		dict: {
			"emission_benchmark": float
		} or None
	"""
	# Get year value
	year_value = None
	if isinstance(year, str):
		year_value = frappe.db.get_value("Year", year, "year")
	else:
		year_value = year
	
	if not year_value:
		return None
	
	# Find CBAM Benchmark with valid date range
	cbam_docs = frappe.get_all("CBAM Benchmark",
		filters={"cn_code": cn_code},
		fields=["name", "valid_from_year", "valid_to_year"]
	)
	
	for cbam_doc in cbam_docs:
		from_year = frappe.db.get_value("Year", cbam_doc.valid_from_year, "year") if cbam_doc.valid_from_year else None
		to_year = frappe.db.get_value("Year", cbam_doc.valid_to_year, "year") if cbam_doc.valid_to_year else None
		
		# Check if year is in range
		if from_year and year_value < from_year:
			continue
		if to_year and year_value > to_year:
			continue
		
		# Year is in range, get the benchmark document
		cbam = frappe.get_doc("CBAM Benchmark", cbam_doc.name)
		
		# Find matching indicator
		for row in cbam.benchmark_values:
			if row.cbam_benchmark_indicator == indicator:
				return {
					"emission_benchmark": flt(row.emission_benchmark)
				}
	
	return None


@frappe.whitelist()
def recalculate_good_benchmark(good_name):
	"""Recalculate benchmark for a Good"""
	try:
		good = frappe.get_doc("Good", good_name)
		result = calculate_country_specific_benchmark(
			good.cn_code,
			good.country_of_origin,
			good.hand_over_date
		)
		
		# Use db.set_value to update directly (bypasses read-only restrictions on submitted docs)
		if good.use_benchmark_override and good.benchmark_manual_override:
			benchmark_value = good.benchmark_manual_override
			status = "Manual Override"
			details = json.dumps({
				"source": "manual_override",
				"override_value": good.benchmark_manual_override
			})
		else:
			benchmark_value = result.get("benchmark_value")
			status = result.get("status", "Error")
			details = json.dumps(result.get("details", {}))
		
		# Update directly in database to bypass read-only restrictions
		frappe.db.set_value("Good", good_name, {
			"country_specific_default_cbam_benchmark": benchmark_value,
			"benchmark_calculation_status": status,
			"benchmark_calculation_details": details,
			"benchmark_last_calculated_at": frappe.utils.now()
		}, update_modified=False)
		
		frappe.db.commit()
		
		return {"success": True, "benchmark": benchmark_value}
	except Exception as e:
		error_msg = str(e)[:500]  # Limit error message length
		title = f"Error recalculating Good {good_name}"[:140]
		frappe.log_error(title, f"Good: {good_name}\nError: {error_msg}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def recalculate_external_good_benchmark(external_good_name):
	"""Recalculate benchmark for an External Good"""
	try:
		eg = frappe.get_doc("External Good", external_good_name)
		
		# Use year field if available, otherwise use None
		reference_date = None
		if eg.year:
			# Get year value from Year doctype and create a date
			year_value = frappe.db.get_value("Year", eg.year, "year")
			if year_value:
				from datetime import date
				reference_date = date(year_value, 1, 1)  # Use January 1st of the year
		
		result = calculate_country_specific_benchmark(
			eg.cn_code,
			eg.installation_country,
			reference_date
		)
		
		# Use db.set_value to update directly (bypasses read-only restrictions on submitted docs)
		if eg.use_benchmark_override and eg.benchmark_manual_override:
			benchmark_value = eg.benchmark_manual_override
			status = "Manual Override"
			details = json.dumps({
				"source": "manual_override",
				"override_value": eg.benchmark_manual_override
			})
		else:
			benchmark_value = result.get("benchmark_value")
			status = result.get("status", "Error")
			details = json.dumps(result.get("details", {}))
		
		# Update directly in database to bypass read-only restrictions
		frappe.db.set_value("External Good", external_good_name, {
			"country_specific_default_cbam_benchmark": benchmark_value,
			"benchmark_calculation_status": status,
			"benchmark_calculation_details": details,
			"benchmark_last_calculated_at": frappe.utils.now()
		}, update_modified=False)
		
		frappe.db.commit()
		
		return {"success": True, "benchmark": benchmark_value}
	except Exception as e:
		error_msg = str(e)[:500]  # Limit error message length
		title = f"Error recalculating Ext Good {external_good_name}"[:140]
		frappe.log_error(title, f"External Good: {external_good_name}\nError: {error_msg}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def batch_update_benchmarks(cn_code=None, country=None):
	"""
	Batch update benchmarks for all goods
	
	Args:
		cn_code: Optional CN code filter
		country: Optional country filter
	"""
	filters = {}
	if cn_code:
		filters["cn_code"] = cn_code
	if country:
		filters["country_of_origin"] = country
	
	goods = frappe.get_all("Good", filters=filters, fields=["name"])
	
	updated = 0
	errors = 0
	
	for good in goods:
		try:
			result = recalculate_good_benchmark(good.name)
			if result.get("success"):
				updated += 1
			else:
				errors += 1
		except Exception as e:
			errors += 1
			error_msg = str(e)[:500]
			title = f"Error updating Good {good.name}"[:140]
			frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")
	
	return {
		"updated": updated,
		"errors": errors,
		"total": len(goods)
	}


def update_affected_goods_by_cn_code(cn_code):
	"""
	Update all goods and external goods with a specific CN code
	Called when CBAM Benchmark changes
	
	Args:
		cn_code: CN Code to update goods for
	"""
	if not cn_code:
		return
	
	# Get all goods with this CN code (exclude submitted and cancelled)
	goods = frappe.get_all("Good",
		filters={
			"cn_code": cn_code,
			"status": ["not in", ["Data Submitted", "Cancelled"]],
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		},
		fields=["name"]
	)
	
	# Get all external goods with this CN code (exclude submitted and cancelled)
	external_goods = frappe.get_all("External Good",
		filters={
			"cn_code": cn_code,
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		},
		fields=["name"]
	)
	
	total_count = len(goods) + len(external_goods)
	
	if total_count == 0:
		return
	
	# Use background job for large updates
	if total_count > 100:
		frappe.enqueue(
			"cbam.utils.benchmark.batch_update_benchmarks_by_cn_code",
			cn_code=cn_code,
			queue="long"
		)
		frappe.msgprint(f"Updating {total_count} goods ({len(goods)} Goods, {len(external_goods)} External Goods) in background. This may take a few minutes.")
	else:
		# Update immediately for small sets
		for good in goods:
			try:
				recalculate_good_benchmark(good.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Good {good.name}"[:140]
				frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")
		
		for eg in external_goods:
			try:
				recalculate_external_good_benchmark(eg.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Ext Good {eg.name}"[:140]
				frappe.log_error(title, f"External Good: {eg.name}\nError: {error_msg}")
		
		# Ensure all updates are committed
		frappe.db.commit()


def update_affected_goods_by_country(country):
	"""
	Update all goods and external goods with a specific country
	Called when Country Default Benchmark changes
	
	Args:
		country: Country to update goods for
	"""
	if not country:
		return
	
	# Get all goods with this country of origin (exclude submitted and cancelled)
	goods = frappe.get_all("Good",
		filters={
			"country_of_origin": country,
			"status": ["not in", ["Data Submitted", "Cancelled"]],
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		},
		fields=["name"]
	)
	
	# Get all external goods with this installation country (exclude submitted and cancelled)
	external_goods = frappe.get_all("External Good",
		filters={
			"installation_country": country,
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		},
		fields=["name"]
	)
	
	total_count = len(goods) + len(external_goods)
	
	if total_count == 0:
		return
	
	# Use background job for large updates
	if total_count > 100:
		frappe.enqueue(
			"cbam.utils.benchmark.batch_update_benchmarks_by_country",
			country=country,
			queue="long"
		)
		frappe.msgprint(f"Updating {total_count} goods in background. This may take a few minutes.")
	else:
		# Update immediately for small sets
		for good in goods:
			try:
				recalculate_good_benchmark(good.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Good {good.name}"[:140]
				frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")
		
		for eg in external_goods:
			try:
				recalculate_external_good_benchmark(eg.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Ext Good {eg.name}"[:140]
				frappe.log_error(title, f"External Good: {eg.name}\nError: {error_msg}")


@frappe.whitelist()
def batch_update_benchmarks_by_cn_code(cn_code):
	"""Background job to update benchmarks for a CN code"""
	goods = frappe.get_all("Good", 
		filters={
			"cn_code": cn_code,
			"status": ["not in", ["Data Submitted", "Cancelled"]],
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		}, 
		fields=["name"]
	)
	external_goods = frappe.get_all("External Good", 
		filters={
			"cn_code": cn_code,
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		}, 
		fields=["name"]
	)
	
	updated = 0
	errors = 0
	
	for good in goods:
		try:
			result = recalculate_good_benchmark(good.name)
			if result.get("success"):
				updated += 1
		except Exception as e:
			errors += 1
			error_msg = str(e)[:500]
			title = f"Error updating Good {good.name}"[:140]
			frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")
	
	for eg in external_goods:
		try:
			result = recalculate_external_good_benchmark(eg.name)
			if result.get("success"):
				updated += 1
		except Exception as e:
			errors += 1
			error_msg = str(e)[:500]
			title = f"Error updating Ext Good {eg.name}"[:140]
			frappe.log_error(title, f"External Good: {eg.name}\nError: {error_msg}")
	
	# Ensure all updates are committed
	frappe.db.commit()
	
	return {"updated": updated, "errors": errors, "total": len(goods) + len(external_goods)}


@frappe.whitelist()
def batch_update_benchmarks_by_country(country):
	"""Background job to update benchmarks for a country"""
	goods = frappe.get_all("Good", 
		filters={
			"country_of_origin": country,
			"status": ["not in", ["Data Submitted", "Cancelled"]],
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		}, 
		fields=["name"]
	)
	external_goods = frappe.get_all("External Good", 
		filters={
			"installation_country": country,
			"docstatus": ["not in", [1, 2]]  # Not submitted (1) or cancelled (2)
		}, 
		fields=["name"]
	)
	
	updated = 0
	errors = 0
	
	for good in goods:
		try:
			result = recalculate_good_benchmark(good.name)
			if result.get("success"):
				updated += 1
		except Exception as e:
			errors += 1
			error_msg = str(e)[:500]
			title = f"Error updating Good {good.name}"[:140]
			frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")
	
	for eg in external_goods:
		try:
			result = recalculate_external_good_benchmark(eg.name)
			if result.get("success"):
				updated += 1
		except Exception as e:
			errors += 1
			error_msg = str(e)[:500]
			title = f"Error updating Ext Good {eg.name}"[:140]
			frappe.log_error(title, f"External Good: {eg.name}\nError: {error_msg}")
	
	# Ensure all updates are committed
	frappe.db.commit()
	
	return {"updated": updated, "errors": errors, "total": len(goods) + len(external_goods)}

