import frappe


def execute():
    for r in frappe.get_all("Operating Company", {"cbam_representative_user": ["is", "set"]}, ["cbam_representive_last_name", "cbam_representative_user", "cbam_representive_employee_first_name"]):
        if r.cbam_representative_user:
            user = frappe.get_doc("User", r.cbam_representative_user)
            full_name = user.full_name
            user.first_name = r.cbam_representive_employee_first_name if r.cbam_representive_employee_first_name else r.cbam_representive_last_name
            user.last_name = r.cbam_representive_last_name if r.cbam_representive_employee_first_name else ""
            user.save()

            print(f"Changing {full_name} to {user.full_name} for {user.name}")