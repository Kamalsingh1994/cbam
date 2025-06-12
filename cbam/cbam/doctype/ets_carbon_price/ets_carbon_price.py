# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import today, formatdate

class ETSCarbonPrice(Document):
	def autoname(self):
		if not self.ets_price_type:
			frappe.throw("ETS Price Type (Actual or Prediction) is required.")

		if not self.price_date:
			frappe.throw("ETS Carbon Price Date is required.")

        # Map Actual / Prediction to A / P
		type_code = "A" if self.ets_price_type == "Actual" else "P"
		price_date_str = formatdate(self.price_date, "yyyy-MM-dd")

        # Use Frappe's counter mechanism with date series
		creation_date_str = formatdate(self.creation, "yyyy-MM-dd")


		counter_prefix = f"ETS-{creation_date_str}-.####"
		counter_id = make_autoname(counter_prefix)

		self.creation_date = self.creation or today()
		self.name = f"{counter_id}-{type_code}-{price_date_str}"

		