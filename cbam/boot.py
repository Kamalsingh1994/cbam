import frappe

def update_boot_context(context):
    context.update({
        "cbam": {
            "admin_role": frappe.db.get_single_value("CBAM Settings", "admin_role"),
            "test": "testset"
        }
    })




def update_website_context(bootinfo):
    
    
    
    bootinfo.update({
        "test": "sfd"
    })

    