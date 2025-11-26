import frappe
import json
import os

def _link_and_prefix_emission_attachment(doc_dict, doc_obj):
    if doc_dict.get("doctype") == "CBAM Emission Data" and doc_dict.get("emission_attachment"):
        file_url = doc_dict["emission_attachment"]
        oc_ref = None
        supplier = "NOSUPPLIER"
        if hasattr(doc_obj, 'operating_company') and doc_obj.operating_company:
            oc_doc = frappe.get_doc("Operating Company", doc_obj.operating_company)
            oc_ref = oc_doc.name
            supplier = getattr(oc_doc, "supplier", None) or "NOSUPPLIER"
        else:
            oc_ref = "OC-UNKNOWN"

        file_doc = frappe.get_all("File", filters={"file_url": file_url}, fields=["name", "file_name", "file_url"])
        if file_doc:
            file_doc = frappe.get_doc("File", file_doc[0].name)
            expected_prefix = f"{oc_ref}_{supplier}_"
            if not file_doc.file_name.startswith(expected_prefix):
                new_name = f"{expected_prefix}{file_doc.file_name}"
                if file_doc.file_url and file_doc.file_url.startswith("/files/"):
                    old_url = file_doc.file_url
                    new_url = f"/files/{expected_prefix}{file_doc.file_name}"
                    # Get actual filesystem path to files directory
                    site_public = frappe.get_site_path("public")
                    old_path = os.path.join(site_public, old_url.lstrip("/"))
                    new_path = os.path.join(site_public, new_url.lstrip("/"))
                    os.rename(old_path, new_path)
                    file_doc.file_url = new_url
                file_doc.file_name = new_name
            file_doc.attached_to_doctype = "CBAM Emission Data"
            file_doc.attached_to_name = doc_obj.name
            file_doc.save(ignore_permissions=True)

@frappe.whitelist()
def create_new_doc(doc):
    doc = json.loads(doc)
    doc_obj = frappe.get_doc(doc).insert(ignore_permissions=True)
    _link_and_prefix_emission_attachment(doc, doc_obj)
    return doc_obj

@frappe.whitelist()
def update_doc(doc):
    doc = json.loads(doc)
    if not frappe.db.exists(doc.get("doctype"), doc.get("name")):
        frappe.throw("Document doesn't exist")
    existing_doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))
    existing_doc.update(doc)
    existing_doc.save(ignore_permissions=True)
    _link_and_prefix_emission_attachment(doc, existing_doc)
    # Reload to get any changes made in on_update hook (like renamed file attachments)
    existing_doc.reload()
    return existing_doc

@frappe.whitelist()
def get_roles(user):
    roles = frappe.get_roles(user)
    return roles

def require_website_user():
    """Redirect Guest users to login page. Call this at the start of get_context() for protected pages."""
    from urllib.parse import urlencode
    if frappe.session.user == "Guest":
        frappe.redirect(f"/login?{urlencode({'redirect-to': frappe.request.path})}")

@frappe.whitelist()
def get_supplier():
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}
    if frappe.db.exists("Operating Company", filters):
        return frappe.db.get_value("Operating Company", filters, "name")
    
@frappe.whitelist()
def get_field_options(doc, fieldname):
    meta = frappe.get_meta(doc)
    field = meta.get_field(fieldname)
    if field and field.options:
        return field.options.split("\n")
    return []

@frappe.whitelist()
def rename_any_file(file_url, new_file_name):
    """Rename a file (public or private) and update its File DocType record's file_url and file_name."""
    if not file_url or not new_file_name:
        frappe.throw('Both file_url and new_file_name are required.')

    # Get File document first to check if it's a remote file
    file_docs = frappe.get_all("File", filters={"file_url": file_url}, fields=["name"])
    if not file_docs:
        frappe.throw('File record not found for given URL.')
    
    file_doc = frappe.get_doc("File", file_docs[0].name)
    
    # Check if this is a remote file (stored in cloud like S3)
    # Remote files start with http:// or https://
    if file_doc.is_remote_file or file_url.startswith(("http://", "https://")):
        # For remote files, only update the File DocType record, don't rename on disk
        file_doc.file_name = new_file_name
        file_doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {'file_url': file_url, 'file_name': new_file_name}

    if file_url.startswith("/private/files/"):
        site_path = frappe.get_site_path("private")
        # both source and target in private
        old_path = os.path.join(site_path, "files", file_url.split("/")[-1])
        new_url = f"/private/files/{new_file_name}"
        new_path = os.path.join(site_path, "files", new_file_name)
    elif file_url.startswith("/files/"):
        site_path = frappe.get_site_path("public")
        old_path = os.path.join(site_path, file_url.lstrip('/'))
        new_url = f"/files/{new_file_name}"
        new_path = os.path.join(site_path, new_url.lstrip('/'))
    else:
        frappe.throw("File URL must be public (/files/) or private (/private/files/).")

    # Check if target path already exists (file already renamed for another emission)
    if os.path.exists(new_path):
        # Target file with desired name already exists
        # This is common when same file is used for multiple emissions
        # Just return the new URL without error
        return {'file_url': new_url, 'file_name': new_file_name}
    
    # Check if source file exists on disk before attempting rename
    if not os.path.exists(old_path):
        # Source file doesn't exist - might be uploaded to cloud, still uploading, or already renamed
        # Don't error out - just return current URL to allow emission creation
        frappe.log_error(
            "File Rename Skipped - Source Not Found",
            f"Source file not found: {old_path}. This may happen with cloud storage or if file was already renamed."
        )
        return {'file_url': file_url, 'file_name': file_doc.file_name}
    
    # Both source exists and target doesn't exist - safe to rename
    try:
        os.rename(old_path, new_path)
    except Exception as e:
        # If rename fails for any reason, log it but don't block the process
        frappe.log_error(
            "File Rename Failed",
            f"Failed to rename file from {old_path} to {new_path}: {str(e)}"
        )
        return {'file_url': file_url, 'file_name': file_doc.file_name}

    # Update File DocType after successful rename
    file_doc.file_name = new_file_name
    file_doc.file_url = new_url
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {'file_url': new_url, 'file_name': new_file_name}