// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.query_reports["ETS Pricing Prediction"] = {
	"filters": [
		{
			"label": "From Date",
			"fieldname": "from_date",
			"fieldtype": "Date"
		},
		{
		"label": "To Date",
		"fieldname": "to_date",
		"fieldtype": "Date"
		}
	]
};
