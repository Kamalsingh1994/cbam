import frappe

def update_workspace_for_helpdesk():
    """
    Updates the Workspace Doctype for Helpdesk entry if it exists.
    Sets the field is_hidden to 1.
    """
    try:
        # Check if the Workspace entry for Helpdesk exists
        workspace = frappe.get_doc("Workspace", "Helpdesk")
        if workspace and not workspace.is_hidden:
            # Update the is_hidden field
            workspace.is_hidden = 1
            workspace.save()
            frappe.db.commit()
            frappe.msgprint("Workspace for Helpdesk updated successfully.")
    except Exception as e:
        frappe.log_error(f"Error updating Workspace for Helpdesk: {str(e)}", "Workspace Update Error")


def add_helpdesk_navbar_item():
	import frappe

	navbar_settings = frappe.get_single("Navbar Settings")
	help_item_exists = any(
		item.item_label == "Helpdesk" or item.route == "/helpdesk"
		for item in navbar_settings.help_dropdown or []
	)

	if not help_item_exists:
		navbar_settings.append("help_dropdown", {
			"item_label": "Helpdesk",
			"route": "/helpdesk",
			"item_type": "Route",
		})
		navbar_settings.save()
		frappe.db.commit()


def remove_user_access_for_desk_user():
    perms = frappe.get_all(
        "Custom DocPerm",
        filters={
            "parent": "User",
            "role": "Desk User"
        },
        fields=["name"]
    )

    for perm in perms:
        frappe.delete_doc("Custom DocPerm", perm.name, force=1)
        print(f"Removed permission: {perm.name}")

    frappe.db.commit()


def update_helpdesk_workspace_roles():
    # Check if "Helpdesk" workspace exists
    if not frappe.db.exists("Workspace", "Helpdesk"):
        return

    # Fetch the document
    ws = frappe.get_doc("Workspace", "Helpdesk")

    # Get current roles already assigned (as a set for fast lookup)
    existing_roles = {r.role for r in ws.roles}

    # Define required roles
    required_roles = ["System Manager", "Administrator"]

    # Track if we make changes
    updated = False

    # Append roles only if not already present
    for role in required_roles:
        if role not in existing_roles:
            ws.append("roles", {"role": role})
            updated = True

    # Save and commit only if any change
    if updated:
        ws.is_hidden = 0
        ws.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated roles in 'Helpdesk' workspace.")
