import frappe


def execute():
    """
    Update user permissions for users linked in Declarant User child table.
    
    For each user in the Declarant User child table:
    - Create user permission to allow access to Declarant doctype
    - For value: the declarant name (parent of the Declarant User record)
    - Apply to all doctypes
    
    This patch ensures that users linked in the Declarant User child table
    have proper user permissions to access their assigned declarant records.
    """
    
    # Check if required tables exist
    if not frappe.db.table_exists("Declarant User"):
        print("Declarant User table does not exist, skipping patch.")
        return
        
    if not frappe.db.table_exists("User Permission"):
        print("User Permission table does not exist, skipping patch.")
        return
    
    # Get all users from Declarant User child table with their parent declarant
    declarant_users = frappe.db.sql("""
        SELECT 
            du.user,
            du.parent as declarant_name
        FROM `tabDeclarant User` du
        WHERE du.user IS NOT NULL 
        AND du.parent IS NOT NULL
        AND du.user != ''
        AND du.parent != ''
    """, as_dict=True)
    
    if not declarant_users:
        print("No Declarant User records found.")
        return
    
    print(f"Found {len(declarant_users)} Declarant User records to process.")
    
    created_permissions = 0
    skipped_permissions = 0
    error_count = 0
    
    for record in declarant_users:
        user = record.user
        declarant_name = record.declarant_name
        
        # Check if user exists and is not disabled
        if not frappe.db.exists("User", user):
            print(f"User {user} does not exist, skipping...")
            continue
            
        user_doc = frappe.get_doc("User", user)
        if user_doc.enabled == 0:
            print(f"User {user} is disabled, skipping...")
            continue
            
        # Check if declarant exists
        if not frappe.db.exists("Declarant", declarant_name):
            print(f"Declarant {declarant_name} does not exist, skipping...")
            continue
            
        # Check if user permission already exists
        existing_permission = frappe.db.exists("User Permission", {
            "user": user,
            "allow": "Declarant",
            "for_value": declarant_name,
            "apply_to_all_doctypes": 1
        })
        
        if existing_permission:
            print(f"User permission already exists for user {user} and declarant {declarant_name}, skipping...")
            skipped_permissions += 1
            continue
        
        try:
            # Create user permission
            user_permission = frappe.get_doc({
                "doctype": "User Permission",
                "user": user,
                "allow": "Declarant",
                "for_value": declarant_name,
                "apply_to_all_doctypes": 1,
                "is_default": 0
            })
            
            user_permission.insert(ignore_permissions=True)
            created_permissions += 1
            print(f"Created user permission for user {user} to access declarant {declarant_name}")
            
        except frappe.DuplicateEntryError:
            print(f"User permission already exists for user {user} and declarant {declarant_name}, skipping...")
            skipped_permissions += 1
        except Exception as e:
            frappe.log_error(f"Error creating user permission for user {user} and declarant {declarant_name}", str(e))
            error_count += 1
            continue
    
    print(f"User permission update completed:")
    print(f"- Created: {created_permissions} permissions")
    print(f"- Skipped: {skipped_permissions} permissions (already exist)")
    print(f"- Errors: {error_count} permissions failed")
    
    # Clear user permissions cache for all affected users
    affected_users = list(set([record.user for record in declarant_users]))
    for user in affected_users:
        try:
            frappe.cache.hdel("user_permissions", user)
        except Exception as e:
            print(f"Error clearing cache for user {user}: {str(e)}")
    
    print("User permissions cache cleared for all affected users.")
    
    # Commit the changes
    frappe.db.commit()
    print("Changes committed to database.")
