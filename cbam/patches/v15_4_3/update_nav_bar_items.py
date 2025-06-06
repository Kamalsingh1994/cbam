import frappe

def execute():
    doc = frappe.get_doc("Website Settings")

    existing_labels = {item.label for item in doc.top_bar_items}

    if "Help" not in existing_labels:
        print("updating Website Settings...")
        doc.append("top_bar_items", {
            "label": "Help"
        })

    if "Contact Myconet Support" not in existing_labels:
        doc.append("top_bar_items", {
            "label": "Contact Myconet Support",
            "url": "/helpdesk",
            "parent_label": "Help",
            "open_in_new_tab": 1
        })

    doc.save()
    frappe.db.commit()
    print("updated Website Settings")

