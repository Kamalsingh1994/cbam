// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('CBAM Report', {
    declarant_acts_as_importer(frm) {
        if (frm.doc.declarant_acts_as_importer) {
            // Copy Declarant to Importer
            frm.set_value('importer', frm.doc.declarant);
        } else {
            // Clear Importer if unchecked (optional)
            frm.set_value('importer', '');
        }
    },

    declarant(frm) {
        // If checkbox is already checked, keep importer in sync
        if (frm.doc.declarant_acts_as_importer) {
            frm.set_value('importer', frm.doc.declarant);
        }
    }
});
