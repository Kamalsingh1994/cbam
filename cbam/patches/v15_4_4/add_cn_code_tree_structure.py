# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""
	Migrate existing CN codes to tree structure.
	For each 8-digit CN code, creates parent 6-digit and 4-digit groups if they don't exist.
	"""

	# Get all existing CN codes
	all_cn_codes = frappe.get_all("CN Code", fields=["name", "cn_code"], order_by="cn_code")

	if not all_cn_codes:
		frappe.msgprint("No CN codes found to migrate")
		return

	created_4digit = 0
	created_6digit = 0
	updated_8digit = 0
	errors = []

	# Process each CN code
	for cn_code_doc in all_cn_codes:
		try:
			cn_code_str = str(cn_code_doc.cn_code)
			cn_code_len = len(cn_code_str)

			# Only process 8-digit codes for migration
			if cn_code_len != 8:
				continue

			# Extract parent codes
			six_digit_code = int(cn_code_str[:6])
			four_digit_code = int(cn_code_str[:4])

			# Step 1: Create or get 4-digit parent (if needed)
			four_digit_name = frappe.db.get_value("CN Code", {"cn_code": four_digit_code}, "name")
			if not four_digit_name:
				# Create 4-digit group
				four_digit_doc = frappe.new_doc("CN Code")
				four_digit_doc.cn_code = four_digit_code
				four_digit_doc.is_group = 1
				four_digit_doc.parent_cn_code = None  # Root level
				four_digit_doc.save(ignore_permissions=True)
				four_digit_name = four_digit_doc.name
				created_4digit += 1
				frappe.db.commit()
			else:
				# Ensure existing 4-digit is marked as group
				existing_is_group = frappe.db.get_value("CN Code", four_digit_name, "is_group")
				if not existing_is_group:
					frappe.db.set_value("CN Code", four_digit_name, "is_group", 1, update_modified=False)

			# Step 2: Create or get 6-digit parent (if needed)
			six_digit_name = frappe.db.get_value("CN Code", {"cn_code": six_digit_code}, "name")
			if not six_digit_name:
				# Create 6-digit group
				six_digit_doc = frappe.new_doc("CN Code")
				six_digit_doc.cn_code = six_digit_code
				six_digit_doc.is_group = 1
				six_digit_doc.parent_cn_code = four_digit_name
				six_digit_doc.save(ignore_permissions=True)
				six_digit_name = six_digit_doc.name
				created_6digit += 1
				frappe.db.commit()
			else:
				# Ensure existing 6-digit is marked as group and has correct parent
				existing_is_group = frappe.db.get_value("CN Code", six_digit_name, "is_group")
				existing_parent = frappe.db.get_value("CN Code", six_digit_name, "parent_cn_code")

				if not existing_is_group:
					frappe.db.set_value("CN Code", six_digit_name, "is_group", 1, update_modified=False)

				if existing_parent != four_digit_name:
					frappe.db.set_value("CN Code", six_digit_name, "parent_cn_code", four_digit_name, update_modified=False)

			# Step 3: Update 8-digit code to have 6-digit as parent
			current_parent = frappe.db.get_value("CN Code", cn_code_doc.name, "parent_cn_code")
			current_is_group = frappe.db.get_value("CN Code", cn_code_doc.name, "is_group")

			if current_parent != six_digit_name:
				frappe.db.set_value("CN Code", cn_code_doc.name, "parent_cn_code", six_digit_name, update_modified=False)
				updated_8digit += 1

			if current_is_group:
				frappe.db.set_value("CN Code", cn_code_doc.name, "is_group", 0, update_modified=False)

			frappe.db.commit()

		except Exception as e:
			error_msg = f"Error processing CN Code {cn_code_doc.name}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(error_msg, "CN Code Tree Migration Error")
			continue

	# Final commit
	frappe.db.commit()

	# Report results
	message = f"""
	CN Code Tree Migration Complete:
	- Created {created_4digit} four-digit groups
	- Created {created_6digit} six-digit groups
	- Updated {updated_8digit} eight-digit codes with parent relationships
	"""

	if errors:
		message += f"\n- {len(errors)} errors occurred (check Error Log for details)"

	frappe.msgprint(message)
