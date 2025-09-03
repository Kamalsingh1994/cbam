import frappe

def execute():
    """Add System Manager role to all workspaces if not exists"""
    
    # Get all workspaces
    workspaces = frappe.get_all("Workspace", fields=["name"])
    
    for workspace in workspaces:
        try:
            # Get the workspace document
            ws_doc = frappe.get_doc("Workspace", workspace.name)
            
            # Check if System Manager role already exists in roles child table
            existing_roles = [role.role for role in ws_doc.roles]
            
            if "System Manager" not in existing_roles:
                # Add System Manager role to the roles child table
                ws_doc.append("roles", {
                    "role": "System Manager"
                })
                
                # Save the workspace
                ws_doc.save(ignore_permissions=True)
                
                print(f"Added System Manager role to workspace: {workspace.name}")
                
        except Exception as e:
            print(f"Error processing workspace {workspace.name}: {str(e)}")
            frappe.log_error(f"Patch Error: {str(e)}")
            continue
    
    print("Patch completed: System Manager role added to all workspaces")
