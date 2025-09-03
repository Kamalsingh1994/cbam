# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class Declarant(Document):
    def validate(self):
        self.ensure_unique_user_across_declarants()

    def after_insert(self):
        self.create_user_permissions()

    def on_update(self):
        self.create_user_permissions()

    def create_user_permissions(self):
        """Create user permissions for users in declarant_user child table"""
        for user_row in self.get("declarant_user"):
            user = user_row.user
            if not user:
                continue
            
            # Check if user permission already exists
            existing_permission = frappe.db.exists(
                "User Permission",
                {
                    "user": user,
                    "allow": "Declarant",
                    "for_value": self.name
                }
            )
            
            if not existing_permission:
                try:
                    # Create user permission
                    user_permission = frappe.get_doc({
                        "doctype": "User Permission",
                        "user": user,
                        "allow": "Declarant",
                        "for_value": self.name,
                        "apply_to_all_doctypes": 1,
                    })
                    user_permission.insert(ignore_permissions=True)
                    frappe.msgprint(
                        _("User permission created for user <b>{0}</b>").format(user),
                        title=_("Success")
                    )
                except Exception as e:
                    frappe.log_error(
                        f"Failed to create user permission for user {user} in declarant {self.name}: {str(e)}",
                        "Declarant User Permission Creation Error"
                    )
                    frappe.msgprint(
                        _("Failed to create user permission for user <b>{0}</b>: {1}").format(user, str(e)),
                        title=_("Error"),
                        indicator="red"
                    )

    def ensure_unique_user_across_declarants(self):
        for user_row in self.get("declarant_user"):
            user = user_row.user
            if not user:
                continue

            existing = frappe.db.exists(
                "Declarant User",
                {
                    "user": user,
                    "parent": ["!=", self.name]
                }
            )

            if existing:
                linked_doc = frappe.db.get_value("Declarant User", existing, "parent")
                frappe.throw(
                    _("User <b>{0}</b> is already linked to another Declarant: <b>{1}</b>").format(user, linked_doc),
                    title=_("Validation Error")
                )
