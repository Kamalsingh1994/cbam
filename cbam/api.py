import frappe
from frappe.model.document import Document


@frappe.whitelist()
def set_user_language(lang):
    user = frappe.session.user
    if user != "Guest":
        frappe.db.set_value("User", user, "language", lang)


