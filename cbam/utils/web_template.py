import frappe


@frappe.whitelist()
def get_content(template):
    # preferred_lang = frappe.request.cookies.get("preferred_language") 
    user_lang = frappe.db.get_value("User", frappe.session.user, "language") 
    lang = user_lang or "en" 

    content = ""
    if frappe.db.exists("Dynamic Web Template", {"template": template, "is_active": 1, "language": lang}):
        content = frappe.db.get_value(
            "Dynamic Web Template",
            {"template": template, "is_active": 1, "language": lang},
            "content"
        )
    else:
       content = frappe.db.get_value(
            "Dynamic Web Template",
            {"template": template, "is_active": 1, "language": "en"},
            "content"
        )

    return content
