# Copyright (c) 2026, phamos GmbH and contributors
# See license.txt

from datetime import date

import frappe
from cbam.utils.benchmark import pick_default_emission_value
from frappe.tests.utils import FrappeTestCase


class TestDefaultEmissionValues(FrappeTestCase):
	def setUp(self):
		self.created_docs = []
		frappe.reload_doc("cbam", "doctype", "external_good")
		frappe.reload_doc("cbam", "doctype", "external_good_default_emission_value")

	def tearDown(self):
		for doctype, name in reversed(self.created_docs):
			try:
				frappe.delete_doc(doctype, name, force=True)
			except Exception:
				pass
		frappe.db.commit()

	def _create_doc(self, doctype, data):
		doc = frappe.get_doc({"doctype": doctype, **data})
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		self.created_docs.append((doctype, doc.name))
		return doc

	def _get_or_create_country(self, name, code):
		if frappe.db.exists("Country", name):
			return name
		doc = self._create_doc("Country", {"country_name": name, "code": code, "name": name})
		return doc.name

	def _get_or_create_year(self, year_value):
		year_name = str(year_value)
		if frappe.db.exists("Year", year_name):
			return year_name
		doc = self._create_doc("Year", {"year": year_value, "name": year_name})
		return doc.name

	def _create_cn_code(self, cn_code):
		name = str(cn_code)
		if frappe.db.exists("CN Code", name):
			return name
		code_len = len(name)
		is_group = 1 if code_len in (4, 6) else 0
		doc = self._create_doc("CN Code", {"name": name, "cn_code": cn_code, "is_group": is_group})
		return doc.name

	def _create_indicator(self, name):
		if frappe.db.exists("CBAM Benchmark Indicator", name):
			return name
		doc = self._create_doc("CBAM Benchmark Indicator", {"name": name})
		return doc.name

	def _create_country_default_values(self, country, cn_code_name, rows):
		doc = self._create_doc("Country Default Values", {
			"country": country,
			"is_global_default": 0,
			"benchmark_values": rows
		})
		return doc

	def _create_customs_import(self, import_name, year_value=None):
		data = {
			"import_name": import_name,
			"from_date": date(2026, 1, 1),
			"to_date": date(2026, 3, 31),
			"due_date": date(2026, 4, 30),
		}
		if year_value:
			data["year"] = self._get_or_create_year(year_value)
		return self._create_doc("Customs Import", data)

	def _create_customs_procedure(self, name):
		if frappe.db.exists("Customs Procedure", name):
			return frappe.get_doc("Customs Procedure", name)
		return self._create_doc("Customs Procedure", {"customs_procedure": name, "name": name})

	def _create_declarant(self, name):
		if frappe.db.exists("Declarant", name):
			return frappe.get_doc("Declarant", name)
		return self._create_doc("Declarant", {"declarant": name, "name": name})

	def test_good_default_emission_values_and_selection(self):
		country = self._get_or_create_country("Germany", "DE")
		cn_code_name = self._create_cn_code(12345678)
		indicator_a = self._create_indicator("Route A")
		indicator_b = self._create_indicator("Route B")
		self._create_country_default_values(country, cn_code_name, [
			{
				"cn_code": cn_code_name,
				"description": "Route A",
				"default_value_total_emissions": 10.0,
				"default_value_2026": 12.0,
				"production_route_cbam_benchmark_indicator": indicator_a,
			},
			{
				"cn_code": cn_code_name,
				"description": "Route B",
				"default_value_total_emissions": 20.0,
				"default_value_2026": 22.0,
				"production_route_cbam_benchmark_indicator": indicator_b,
			},
		])

		customs_import = self._create_customs_import("TEST-IMPORT-1", year_value=2026)
		customs_procedure = self._create_customs_procedure("TEST-CP")

		good = self._create_doc("Good", {
			"good_description": "Test Good",
			"internal_customs_import_number": customs_import.name,
			"raw_mass": 1000,
			"customs_procedure": customs_procedure.name,
			"cn_code": cn_code_name,
			"country_of_origin": country,
		})

		good.reload()
		self.assertEqual(len(good.country_specific_default_emission_values), 2)
		self.assertEqual(int(good.select_applicable_product_for_cn_code or 0), 1)

		good.country_specific_default_emission_values[0].applicable_product = 1
		good.save(ignore_permissions=True)
		good.reload()
		selected = [row for row in good.country_specific_default_emission_values if row.applicable_product]
		self.assertEqual(len(selected), 1)
		self.assertEqual(int(good.select_applicable_product_for_cn_code or 0), 0)

	def test_external_good_default_emission_value(self):
		country = self._get_or_create_country("China", "CN")
		cn_code_name = self._create_cn_code(65432100)
		indicator = self._create_indicator("Route C")
		self._create_country_default_values(country, cn_code_name, [
			{
				"cn_code": cn_code_name,
				"description": "Route C",
				"default_value_total_emissions": 15.0,
				"default_value_2026": 18.0,
				"production_route_cbam_benchmark_indicator": indicator,
			},
		])

		decl = self._create_declarant("TEST-DECLARANT")
		year_name = self._get_or_create_year(2026)

		eg = self._create_doc("External Good", {
			"cn_code": cn_code_name,
			"installation_country": country,
			"raw_mass": 100,
			"calculate": "Quantity of Articles",
			"declarant": decl.name,
			"year": year_name,
		})

		eg.reload()
		self.assertEqual(len(eg.country_specific_default_emission_values), 1)
		selected_value = pick_default_emission_value(eg.country_specific_default_emission_values[0], 2026)
		self.assertEqual(float(selected_value or 0.0), 18.0)

	def test_external_good_applicable_product_selection(self):
		country = self._get_or_create_country("France", "FR")
		cn_code_name = self._create_cn_code(99001100)
		indicator_a = self._create_indicator("Route X")
		indicator_b = self._create_indicator("Route Y")
		self._create_country_default_values(country, cn_code_name, [
			{
				"cn_code": cn_code_name,
				"description": "Route X",
				"default_value_total_emissions": 5.0,
				"default_value_2026": 7.0,
				"production_route_cbam_benchmark_indicator": indicator_a,
			},
			{
				"cn_code": cn_code_name,
				"description": "Route Y",
				"default_value_total_emissions": 9.0,
				"default_value_2026": 11.0,
				"production_route_cbam_benchmark_indicator": indicator_b,
			},
		])

		decl = self._create_declarant("TEST-DECLARANT-2")
		year_name = self._get_or_create_year(2026)

		eg = self._create_doc("External Good", {
			"cn_code": cn_code_name,
			"installation_country": country,
			"raw_mass": 100,
			"calculate": "Quantity of Articles",
			"declarant": decl.name,
			"year": year_name,
		})

		eg.reload()
		self.assertEqual(len(eg.country_specific_default_emission_values), 2)
		self.assertEqual(int(eg.select_applicable_product_for_cn_code or 0), 1)

		eg.country_specific_default_emission_values[1].applicable_product = 1
		eg.save(ignore_permissions=True)
		eg.reload()
		selected = [row for row in eg.country_specific_default_emission_values if row.applicable_product]
		self.assertEqual(len(selected), 1)
		self.assertEqual(int(eg.select_applicable_product_for_cn_code or 0), 0)
		selected_value = pick_default_emission_value(selected[0], 2026)
		self.assertEqual(float(selected_value or 0.0), 11.0)
