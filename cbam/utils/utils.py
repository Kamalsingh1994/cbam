import frappe
from frappe import _

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


def update_workspace_roles():
    update_roles("Helpdesk", ["System Manager", "Administrator"])
    update_roles("Users", ["System Manager", "Administrator"])

def update_user_workspace_roles():
    update_workspace_roles("User", ["System Manager", "Administrator"])

def update_roles(workspace_name, required_roles):
    # Check if workspace exists
    if not frappe.db.exists("Workspace", workspace_name):
        return

    ws = frappe.get_doc("Workspace", workspace_name)
    existing_roles = {r.role for r in ws.roles}

    # Append only missing roles
    for role in required_roles:
        if role not in existing_roles:
            ws.append("roles", {"role": role})

    # Always unhide the workspace if hidden
    if ws.is_hidden:
        ws.is_hidden = 0
    
    ws.save(ignore_permissions=True)
    frappe.db.commit()

def user_permission_query(user):
    # Hide all user documents from everyone except admins
    if "System Manager" in frappe.get_roles(user) or user == "Administrator":
        return ""
    return "1=0"  # deny all rows

@frappe.whitelist()
def get_declarant_for_user(doctype, txt, searchfield, start, page_len, filters):
    user = filters.get("user")

    declarants = frappe.db.sql("""
        SELECT parent
        FROM `tabDeclarant Users`
        WHERE user = %s
    """, (user,))

    if not declarants:
        return []

    return [
        (d[0],) for d in declarants
        if txt.lower() in d[0].lower()
    ]
