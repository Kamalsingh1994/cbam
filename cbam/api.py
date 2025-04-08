import frappe
from frappe.model.document import Document


@frappe.whitelist()
def set_user_language(lang):
    user = frappe.session.user
    if user != "Guest":
        frappe.db.set_value("User", user, "language", lang)


@frappe.whitelist(allow_guest=True)
def get_translations():
    
    """
    Accepts a list of translation keys, returns translated values
    from the Translation Doctype based on the current user's language.
    """

    # Grab keys from hook
    keys = frappe.get_hooks().get("web_translation_keys", [])

    if not keys:
        # If no keys are provided, return an empty dictionary
        return {}
    
    if isinstance(keys, str):
        keys = frappe.parse_json(keys)

    # Get user's preferred language or system default
    lang = frappe.local.lang or frappe.db.get_default("lang") or "en"

    # Fetch translations for the provided keys from the Translation Doctype
    translations = frappe.get_all(
        "Translation",
        filters={
            "source_text": ["in", keys],
            "language": lang
        },
        fields=["source_text", "translated_text"],
    )

    # Map source_text to translated_text
    translated_dict = {row.source_text: row.translated_text for row in translations}
    
    # Fallback to original keys if translation not found
    return {key: translated_dict.get(key, key) for key in keys}
