# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from cbam.utils.benchmark import calculate_country_specific_benchmark, get_country_default_emission_values


class ExternalGood(Document):
	def validate(self):
		self.set_year_from_report()
		self.calculate_benchmark()
		self.calculate_default_emission_values()

	def set_year_from_report(self):
		"""Set year field from CBAM Report's from_date/to_date if not already set"""
		if self.report_id and not self.year:
			try:
				cbam_report = frappe.get_doc("CBAM Report", self.report_id)
				# Extract year from from_date (preferred) or to_date
				date_to_use = cbam_report.from_date or cbam_report.to_date
				if date_to_use:
					from frappe.utils import getdate
					from datetime import datetime
					if isinstance(date_to_use, str):
						date_obj = datetime.strptime(date_to_use.split()[0], '%Y-%m-%d')
					else:
						date_obj = getdate(date_to_use)
					year_value = date_obj.year
					# Get or create Year record
					self.year = get_or_create_year(year_value)
			except Exception as e:
				# Log error but don't fail validation
				frappe.log_error(f"Error setting year from CBAM Report {self.report_id}: {str(e)}", "External Good Year Error")

	def calculate_benchmark(self):
		"""Calculate and store country-specific CBAM benchmark"""
		# Use manual override if enabled
		if self.use_benchmark_override and self.benchmark_manual_override:
			self.country_specific_default_cbam_benchmark = self.benchmark_manual_override
			self.benchmark_calculation_status = "Manual Override"
			self.benchmark_calculation_details = json.dumps({
				"source": "manual_override",
				"override_value": self.benchmark_manual_override
			})
			self.benchmark_last_calculated_at = frappe.utils.now()
			return

		# Calculate benchmark if CN code and installation country are available
		if self.cn_code and self.installation_country:
			try:
				# Use year field if available, otherwise use None
				reference_date = None
				if self.year:
					# Get year value from Year doctype and create a date
					year_value = frappe.db.get_value("Year", self.year, "year")
					if year_value:
						from datetime import date
						reference_date = date(year_value, 1, 1)  # Use January 1st of the year

				result = calculate_country_specific_benchmark(
					self.cn_code,
					self.installation_country,
					reference_date
				)

				self.country_specific_default_cbam_benchmark = result.get("benchmark_value")
				self.benchmark_calculation_status = result.get("status", "Error")
				self.benchmark_calculation_details = json.dumps(result.get("details", {}))
				self.benchmark_last_calculated_at = frappe.utils.now()

				# Log warnings if any (keep title short for error log)
				warnings = result.get("warnings", [])
				if warnings and self.benchmark_calculation_status != "Calculated":
					# Truncate warnings for title, full details in message
					warnings_str = ', '.join(warnings)
					message = f"External Good: {self.name}\nCN Code: {self.cn_code}\nCountry: {self.installation_country}\nWarnings: {warnings_str}"
					title = f"Benchmark warnings: Ext Good {self.name}"[:140]
					frappe.log_error(title, message)
			except Exception as e:
				error_msg = str(e)[:500]  # Limit error message length
				message = f"External Good: {self.name}\nCN Code: {self.cn_code}\nCountry: {self.installation_country}\nError: {error_msg}"
				title = f"Benchmark calc error: Ext Good {self.name}"[:140]
				frappe.log_error(title, message)
				self.country_specific_default_cbam_benchmark = None
				self.benchmark_calculation_status = "Error"
				self.benchmark_calculation_details = json.dumps({"error": str(e)})
				self.benchmark_last_calculated_at = frappe.utils.now()
		else:
			# Missing required fields
			self.country_specific_default_cbam_benchmark = None
			self.benchmark_calculation_status = "Missing Data"
			self.benchmark_calculation_details = json.dumps({
				"missing_fields": {
					"cn_code": not bool(self.cn_code),
					"installation_country": not bool(self.installation_country)
				}
			})

	def calculate_default_emission_values(self):
		"""Populate default emission values from Country Default Values"""
		if not self.cn_code or not self.installation_country:
			self.country_specific_default_emission_values = []
			self.select_applicable_product_for_cn_code = 0
			return

		should_refresh = self.is_new() or self.has_value_changed("cn_code") or self.has_value_changed("installation_country")
		selected_key = None
		if self.country_specific_default_emission_values:
			for row in self.country_specific_default_emission_values:
				if row.applicable_product:
					selected_key = (row.cn_code, row.production_route_cbam_benchmark_indicator)
					break

		if should_refresh or not self.country_specific_default_emission_values:
			rows, _details = get_country_default_emission_values(self.installation_country, self.cn_code)
			self.country_specific_default_emission_values = []
			for row in rows:
				child = self.append("country_specific_default_emission_values", {
					"cn_code": row.get("cn_code"),
					"description": row.get("description"),
					"default_value_direct_emissions": row.get("default_value_direct_emissions"),
					"default_value_indirect_emissions": row.get("default_value_indirect_emissions"),
					"default_value_total_emissions": row.get("default_value_total_emissions"),
					"default_value_2026": row.get("default_value_2026"),
					"default_value_2027": row.get("default_value_2027"),
					"default_value_2028_onwards": row.get("default_value_2028_onwards"),
					"production_route_cbam_benchmark_indicator": row.get("production_route_cbam_benchmark_indicator")
				})
				if selected_key and (child.cn_code, child.production_route_cbam_benchmark_indicator) == selected_key:
					child.applicable_product = 1

		self._sync_default_emission_selection_status()

	def _sync_default_emission_selection_status(self):
		applicable_rows = [row for row in self.country_specific_default_emission_values if row.applicable_product]
		if len(applicable_rows) > 1:
			frappe.throw("Only one Applicable Product can be selected.")

		if applicable_rows:
			self.select_applicable_product_for_cn_code = 0
		else:
			self.select_applicable_product_for_cn_code = 1 if len(self.country_specific_default_emission_values) > 1 else 0

		year_value = None
		if self.year:
			year_value = frappe.db.get_value("Year", self.year, "year")

		return


@frappe.whitelist()
def bulk_create_external_goods(rows, declarant=None, cbam_report=None, reporting_period=None, declarant_acts_as_importer=None, importer=None):
    if isinstance(rows, str):
        rows = json.loads(rows)

    created = []

    for row in rows:
        try:
            # Clean + resolve linked fields
            raw_country = row.get("country")
            country_name = raw_country.split(" - ")[-1].strip() if raw_country else None

            cn_code = get_or_create_linked_value("CN Code", "cn_code", row.get("cn_code"))
            customs_procedure = get_or_create_linked_value("Customs Procedure", "name", row.get("requested_procedure_code"))
            installation_country = get_or_create_linked_value("Country", "country_name", country_name)

            # Create External Good
            doc = frappe.new_doc("External Good")
            doc.update({
                "position_number": row.get("section"),
                "cn_code": cn_code,
                "supplier": row.get("operator_name"),
                "installation_name": row.get("installation_name"),
                "installation_country": installation_country,
                "raw_mass_tonne": row.get("quantity"),
                "raw_mass": float(row.get("quantity")) * 1000,  # Convert to kg
                "specific_direct_embedded_emissions": row.get("direct_embedded_emissions"),
                "specific_indirect_embedded_emissions": row.get("indirect_embedded_emissions"),
                "customs_procedure": customs_procedure,
                "calculate": "Quantity of Articles",
                "declarant": declarant,
                "report_id": cbam_report,
                "reporting_period": reporting_period,
                "declarant_acts_as_importer": declarant_acts_as_importer,
                "importer": importer
            })
            doc.insert(ignore_permissions=True)

            # Link back to child table if possible
            if row.get("parent") and row.get("idx"):
                frappe.db.set_value(
                    "CBAM Report Data",
                    {"parent": row["parent"], "idx": row["idx"]},
                    {
						"external_good": doc.name,
						"imported": 1
					}
                )

            created.append({
                "external_good": doc.name,
                "idx": row.get("idx")
            })

        except Exception:
            frappe.log_error(frappe.get_traceback(), "External Good Import Error")

    return {"created": created}


def get_or_create_linked_value(doctype, fieldname, value):
    if not value:
        return None

    # Check if value exists
    existing = frappe.db.get_value(doctype, {fieldname: value})
    if existing:
        return existing

    # Try to create new record
    try:
        doc = frappe.get_doc({
            "doctype": doctype,
            fieldname: value
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Auto-create failed for {doctype}: {value}")
        return None


def get_or_create_year(year_value):
    """Get or create Year record for a given year value"""
    if not year_value:
        return None

    # Year doctype uses autoname: field:year, so name is the year value itself
    year_name = str(year_value)

    # Check if Year exists
    if frappe.db.exists("Year", year_name):
        return year_name

    # Create Year record
    try:
        year_doc = frappe.get_doc({
            "doctype": "Year",
            "year": int(year_value)
        })
        year_doc.insert(ignore_permissions=True)
        return year_doc.name
    except Exception as e:
        frappe.log_error(f"Error creating Year {year_value}: {str(e)}", "Year Creation Error")
        return None


