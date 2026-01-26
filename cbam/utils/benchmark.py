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
		# Step 1: Get Country Default Values
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
		factor = 1.0

		details["indicator_used"] = indicator
		details["factor_used"] = factor

		if not indicator:
			warnings.append("Indicator missing in Country Default Values")
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
		details["cn_code_used"] = cbam_benchmark.get("cn_code_used") or cdb.get("cn_code_used")

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


def get_cn_code_hierarchy(cn_code):
	"""
	Get CN code hierarchy (8-digit → 6-digit → 4-digit) for fallback lookup

	Args:
		cn_code: CN Code (string, int, or Link name)

	Returns:
		list: CN code names in order of specificity (most specific first)
		Example: For 73181535, returns [73181535, 731815, 7318]
	"""
	hierarchy = []

	# Normalize CN code to string
	if isinstance(cn_code, str):
		# Check if it's a CN Code name (Link) or numeric value
		try:
			# Try to get CN code value from name
			cn_code_value = frappe.db.get_value("CN Code", cn_code, "cn_code")
			if cn_code_value:
				cn_code_str = str(cn_code_value)
				cn_code_name = cn_code
			else:
				# If not found, assume it's a numeric string
				cn_code_str = cn_code
				cn_code_name = frappe.db.get_value("CN Code", {"cn_code": int(cn_code_str)}, "name") or cn_code_str
		except (ValueError, TypeError):
			# If conversion fails, use as-is
			cn_code_str = cn_code
			cn_code_name = frappe.db.get_value("CN Code", {"cn_code": int(cn_code_str)}, "name") if cn_code_str.isdigit() else cn_code_str
	else:
		# Integer or other type
		cn_code_str = str(cn_code)
		cn_code_name = frappe.db.get_value("CN Code", {"cn_code": int(cn_code_str)}, "name") or cn_code_str

	cn_code_len = len(cn_code_str)

	# Add the original CN code first (most specific)
	if cn_code_name:
		hierarchy.append(cn_code_name)

	# If it's an 8-digit code, get parent hierarchy
	if cn_code_len == 8:
		# Get 6-digit parent (HS Subheading)
		six_digit_code = int(cn_code_str[:6])
		six_digit_name = frappe.db.get_value("CN Code", {"cn_code": six_digit_code, "is_group": 1}, "name")
		if six_digit_name and six_digit_name not in hierarchy:
			hierarchy.append(six_digit_name)

		# Get 4-digit parent (HS Heading)
		four_digit_code = int(cn_code_str[:4])
		four_digit_name = frappe.db.get_value("CN Code", {"cn_code": four_digit_code, "is_group": 1}, "name")
		if four_digit_name and four_digit_name not in hierarchy:
			hierarchy.append(four_digit_name)

	# If it's a 6-digit code, get 4-digit parent
	elif cn_code_len == 6:
		four_digit_code = int(cn_code_str[:4])
		four_digit_name = frappe.db.get_value("CN Code", {"cn_code": four_digit_code, "is_group": 1}, "name")
		if four_digit_name and four_digit_name not in hierarchy:
			hierarchy.append(four_digit_name)

	# Return hierarchy (most specific first)
	return hierarchy if hierarchy else [cn_code_name] if cn_code_name else [cn_code_str]


def get_country_default_benchmark(country, cn_code):
	"""
	Get Country Default Values for a specific country and CN code
	With fallback to parent CN code groups (6-digit → 4-digit)

	Returns:
		dict: {
			"cbam_benchmark_indicator": str,
			"benchmark_multiplication_factor": float,
			"cn_code_used": str  # Which CN code level was used
		} or None
	"""
	# Get CN code hierarchy for fallback lookup
	cn_code_hierarchy = get_cn_code_hierarchy(cn_code)

	# Get Country Default Values document
	cdb_docs = frappe.get_all("Country Default Values",
		filters={"country": country, "is_global_default": 0},
		fields=["name"]
	)

	if not cdb_docs:
		return None

	cdb_doc = frappe.get_doc("Country Default Values", cdb_docs[0].name)

	# Try each CN code in hierarchy (most specific first)
	for cn_code_to_try in cn_code_hierarchy:
		# Find matching CN code in table
		# CN code in table is a Link field, so compare with name
		for row in cdb_doc.benchmark_values:
			# row.cn_code is a Link field (name of CN Code doctype)
			if row.cn_code == cn_code_to_try:
				return {
					"cbam_benchmark_indicator": row.production_route_cbam_benchmark_indicator,
					"benchmark_multiplication_factor": 1.0,
					"cn_code_used": cn_code_to_try
				}

	return None


def get_global_default_benchmark(cn_code):
	"""
	Get Global Default Values (no country specified) for a CN code
	With fallback to parent CN code groups (6-digit → 4-digit)

	Returns:
		dict: {
			"cbam_benchmark_indicator": str,
			"benchmark_multiplication_factor": float,
			"cn_code_used": str  # Which CN code level was used
		} or None
	"""
	# Get CN code hierarchy for fallback lookup
	cn_code_hierarchy = get_cn_code_hierarchy(cn_code)

	# Get Global Default Values document
	cdb_docs = frappe.get_all("Country Default Values",
		filters={"is_global_default": 1},
		fields=["name"]
	)

	if not cdb_docs:
		return None

	cdb_doc = frappe.get_doc("Country Default Values", cdb_docs[0].name)

	# Try each CN code in hierarchy (most specific first)
	for cn_code_to_try in cn_code_hierarchy:
		# Find matching CN code in table
		# CN code in table is a Link field, so compare with name
		for row in cdb_doc.benchmark_values:
			# row.cn_code is a Link field (name of CN Code doctype)
			if row.cn_code == cn_code_to_try:
				return {
					"cbam_benchmark_indicator": row.production_route_cbam_benchmark_indicator,
					"benchmark_multiplication_factor": 1.0,
					"cn_code_used": cn_code_to_try
				}

	return None


def _serialize_default_emission_row(row):
	return {
		"cn_code": row.cn_code,
		"description": row.description,
		"default_value_direct_emissions": row.default_value_direct_emissions,
		"default_value_indirect_emissions": row.default_value_indirect_emissions,
		"default_value_total_emissions": row.default_value_total_emissions,
		"default_value_2026": row.default_value_2026,
		"default_value_2027": row.default_value_2027,
		"default_value_2028_onwards": row.default_value_2028_onwards,
		"production_route_cbam_benchmark_indicator": row.production_route_cbam_benchmark_indicator
	}


def resolve_report_year(report_year):
	"""Resolve report year from int, string, or Year link."""
	if not report_year:
		return None
	if isinstance(report_year, int):
		return report_year
	if isinstance(report_year, str):
		try:
			return int(report_year)
		except ValueError:
			year_value = frappe.db.get_value("Year", report_year, "year")
			return int(year_value) if year_value else None
	if hasattr(report_year, "year"):
		try:
			return int(report_year.year)
		except (TypeError, ValueError):
			return None
	return None


def pick_default_emission_value(row, report_year):
	"""Pick default emission value based on reporting year."""
	if not row:
		return None

	year_value = resolve_report_year(report_year)

	if year_value == 2026 and row.get("default_value_2026") is not None:
		return row.get("default_value_2026")
	if year_value == 2027 and row.get("default_value_2027") is not None:
		return row.get("default_value_2027")
	if year_value == 2028 and row.get("default_value_2028_onwards") is not None:
		return row.get("default_value_2028_onwards")

	return row.get("default_value_total_emissions")


def get_country_default_emission_values(country, cn_code):
	"""
	Get Default Emission Values for a specific country and CN code
	With fallback to parent CN code groups (6-digit → 4-digit) and global defaults.
	"""
	if not cn_code or not country:
		return [], {"source": None, "cn_code_used": None}

	cn_code_hierarchy = get_cn_code_hierarchy(cn_code)

	cdb_docs = frappe.get_all("Country Default Values",
		filters={"country": country, "is_global_default": 0},
		fields=["name"]
	)
	source = "country_specific"

	if not cdb_docs:
		cdb_docs = frappe.get_all("Country Default Values",
			filters={"is_global_default": 1},
			fields=["name"]
		)
		source = "global_default"

	if not cdb_docs:
		return [], {"source": None, "cn_code_used": None}

	cdb_doc = frappe.get_doc("Country Default Values", cdb_docs[0].name)

	for cn_code_to_try in cn_code_hierarchy:
		matching_rows = [
			_serialize_default_emission_row(row)
			for row in cdb_doc.benchmark_values
			if row.cn_code == cn_code_to_try
		]
		if matching_rows:
			return matching_rows, {"source": source, "cn_code_used": cn_code_to_try}

	return [], {"source": source, "cn_code_used": None}


def get_default_emission_value(country, cn_code, report_year):
	"""Get a single Default Emission Value when no Good selection exists."""
	rows, _details = get_country_default_emission_values(country, cn_code)
	if not rows:
		return None
	if len(rows) > 1:
		return None
	return pick_default_emission_value(rows[0], report_year)


def get_cbam_benchmark(cn_code, indicator, year):
	"""
	Get CBAM Benchmark value for a CN code, indicator, and year
	With fallback to parent CN code groups (6-digit → 4-digit)

	Returns:
		dict: {
			"emission_benchmark": float,
			"cn_code_used": str  # Which CN code level was used
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

	# Get CN code hierarchy for fallback lookup
	cn_code_hierarchy = get_cn_code_hierarchy(cn_code)

	# Try each CN code in hierarchy (most specific first)
	for cn_code_to_try in cn_code_hierarchy:
		# Find CBAM Benchmark with valid date range
		cbam_docs = frappe.get_all("CBAM Benchmark",
			filters={"cn_code": cn_code_to_try},
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
						"emission_benchmark": flt(row.emission_benchmark),
						"cn_code_used": cn_code_to_try
					}

	return None


def get_standard_emission_value(cn_code, country, year):
	"""
	Deprecated: use Default Emission Values from Country Default Values.
	"""
	return get_default_emission_value(country, cn_code, year)


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
def recalculate_good_default_emission_values(good_name):
	"""Recalculate default emission values for a Good"""
	try:
		good = frappe.get_doc("Good", good_name)
		good.calculate_default_emission_values()
		good.save(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		error_msg = str(e)[:500]
		title = f"Error recalculating default emissions for {good_name}"[:140]
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
def recalculate_external_good_default_emission_values(external_good_name):
	"""Recalculate default emission values for an External Good"""
	try:
		eg = frappe.get_doc("External Good", external_good_name)
		eg.calculate_default_emission_values()
		eg.save(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		error_msg = str(e)[:500]
		title = f"Error recalculating default emissions for {external_good_name}"[:140]
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
				recalculate_good_default_emission_values(good.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Good {good.name}"[:140]
				frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")

		for eg in external_goods:
			try:
				recalculate_external_good_benchmark(eg.name)
				recalculate_external_good_default_emission_values(eg.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Ext Good {eg.name}"[:140]
				frappe.log_error(title, f"External Good: {eg.name}\nError: {error_msg}")

		# Ensure all updates are committed
		frappe.db.commit()


def update_affected_goods_by_country(country):
	"""
	Update all goods and external goods with a specific country
	Called when Country Default Values change

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
				recalculate_good_default_emission_values(good.name)
			except Exception as e:
				error_msg = str(e)[:500]
				title = f"Error updating Good {good.name}"[:140]
				frappe.log_error(title, f"Good: {good.name}\nError: {error_msg}")

		for eg in external_goods:
			try:
				recalculate_external_good_benchmark(eg.name)
				recalculate_external_good_default_emission_values(eg.name)
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
			recalculate_good_default_emission_values(good.name)
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
			recalculate_external_good_default_emission_values(eg.name)
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
			recalculate_good_default_emission_values(good.name)
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
			recalculate_external_good_default_emission_values(eg.name)
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

