// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("CBAM Benchmark Indicator", {
	refresh: function(frm) {
		// Auto-uppercase code field
		frm.set_df_property("code", "description", "Single character code (A-Z, 0-9). Will be stored as uppercase.");
	},
	
	code: function(frm) {
		// Auto-uppercase on input
		if (frm.doc.code) {
			frm.set_value("code", frm.doc.code.toUpperCase());
		}
	}
});

