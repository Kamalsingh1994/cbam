// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("ETS Import Settings", {
	refresh: function(frm) {
		// Add custom buttons at the top of the form
		frm.add_custom_button(__('Test Google Drive Connection'), function() {
			frappe.call({
				method: 'cbam.cbam.doctype.ets_import_settings.ets_import_settings.test_google_drive_connection',
				args: {
					settings_name: frm.doc.name
				}
			});
		});

		frm.add_custom_button(__('Import ETS Prices'), function() {
			console.log('🚀 Import ETS Prices button clicked');
			console.log('📋 Form document name:', frm.doc.name);
			
			frappe.call({
				method: 'cbam.cbam.doctype.ets_import_settings.ets_import_settings.trigger_manual_import',
				args: {
					settings_name: frm.doc.name
				},
				callback: function(r) {
					console.log('✅ Import call completed successfully:', r);
				},
				error: function(r) {
					console.error('❌ Import call failed:', r);
					alert('Import failed: ' + JSON.stringify(r));
				}
			});
		});
	}
});

