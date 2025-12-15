// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Country Default Benchmark", {
	refresh: function(frm) {
		// Update field visibility based on is_global_default
		frm.toggle_display("country", !frm.doc.is_global_default);
	},
	
	is_global_default: function(frm) {
		// Clear country if global default is checked
		if (frm.doc.is_global_default) {
			frm.set_value("country", "");
		}
		frm.toggle_display("country", !frm.doc.is_global_default);
	},
	
	country: function(frm) {
		// Uncheck global default if country is set
		if (frm.doc.country) {
			frm.set_value("is_global_default", 0);
		}
	}
});

