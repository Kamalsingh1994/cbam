// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("CN Code", {
	cn_code(frm) {
		// Auto-set is_group based on CN code length
		if (frm.doc.cn_code) {
			const cn_code_str = String(frm.doc.cn_code);
			const cn_code_len = cn_code_str.length;

			if (cn_code_len === 8) {
				// 8-digit codes cannot be groups
				frm.set_value("is_group", 0);
				frm.set_df_property("is_group", "read_only", 1);
			} else if (cn_code_len === 4 || cn_code_len === 6) {
				// 4 and 6-digit codes must be groups
				frm.set_value("is_group", 1);
				frm.set_df_property("is_group", "read_only", 1);
			} else {
				// Invalid length - allow editing
				frm.set_df_property("is_group", "read_only", 0);
			}
		}
	},

	refresh(frm) {
		// Set read-only state based on CN code length
		if (frm.doc.cn_code) {
			const cn_code_str = String(frm.doc.cn_code);
			const cn_code_len = cn_code_str.length;

			if (cn_code_len === 8 || cn_code_len === 4 || cn_code_len === 6) {
				frm.set_df_property("is_group", "read_only", 1);
			}
		}
	}
});
