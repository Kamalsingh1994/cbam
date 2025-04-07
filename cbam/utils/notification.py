
import frappe
from frappe.utils import today

def generate_alerts():
    owners = frappe.get_all("Operating Company", filters={"creation": ["between", [today(), today()]]}, fields=["distinct(owner) as owner"])
    for owner in owners:
        doc = frappe.get_doc("User", owner.owner)
        doc.items = frappe.get_all("Operating Company", filters= {"owner": owner.owner, "creation": ["between", [today(), today()]], "commercial_contact_user": ["is", "not set"]})
        notification = frappe.db.get_single_value("CBAM Settings", "duplicate_commercial_contact_notification_template")
        email = frappe.get_doc("Notification", notification)
        if doc.items:
            email.send(doc)