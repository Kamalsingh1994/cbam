# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class Declarant(Document):
    def validate(self):
        self.ensure_unique_user_across_declarants()

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
