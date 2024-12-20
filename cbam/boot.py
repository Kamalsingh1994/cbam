import frappe
from frappe.boot import get_bootinfo as boot_info
def update_boot_context(context):
    context.update({
        "cbam": {
            "admin_role": frappe.db.get_single_value("CBAM Settings", "admin_role"),
            "test": "testset"
        }
    })




def update_website_context(context):
    
    
    
    context.update({
        "test": "sfd"
    })

    