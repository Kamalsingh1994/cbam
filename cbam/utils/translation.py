import frappe
from frappe.utils import now
import json

def remove_duplicate_translations():
    # Step 1: Get duplicates to be deleted (all except latest per source_text)
    duplicates_query = """
        SELECT t1.name, t1.source_text, t1.language, t1.translated_text, t1.creation
        FROM `tabTranslation` t1
        LEFT JOIN (
            SELECT source_text, MAX(creation) AS latest
            FROM `tabTranslation`
            GROUP BY source_text
        ) t2 ON t1.source_text = t2.source_text AND t1.creation = t2.latest
        WHERE t2.latest IS NULL OR t1.creation != t2.latest
    """

    duplicates = frappe.db.sql(duplicates_query, as_dict=True)

    if not duplicates:
        frappe.msgprint("✅ No duplicate translations found.")
        return

    # Step 2: Log the deleted rows in Error Log
    for entry in duplicates:
        if entry.get("creation") and not isinstance(entry["creation"], str):
            entry["creation"] = entry["creation"].isoformat()

    frappe.get_doc({
        "doctype": "Error Log",
        "method": "deduplicate_translation_source_texts",
        "error": json.dumps(duplicates, indent=2),
        "error_type": "Translation Cleanup",
        "timestamp": now(),
    }).insert(ignore_permissions=True)

    # Step 3: Delete the duplicates
    names_to_delete = [d["name"] for d in duplicates]

    frappe.db.sql(
        """DELETE FROM `tabTranslation` WHERE name IN %(names)s""",
        {"names": names_to_delete}
    )

    frappe.msgprint(f"✅ Deleted {len(names_to_delete)} duplicate translation records. See Error Log for details.")
