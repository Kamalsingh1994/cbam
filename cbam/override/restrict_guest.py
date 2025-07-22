import frappe

def block_guest():
    path = frappe.request.path
    public_pages = ["/login", "/signup", "/about", "/contact", "/"]

    if frappe.session.user == "Guest" and path not in public_pages:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
