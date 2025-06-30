import frappe
import json
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import now

@frappe.whitelist()
def get_supplier():
    filters = {"contact_person": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles() and not "Commercial Contact" in frappe.get_roles():
        filters = {"contact_person": frappe.session.user}

    return frappe.db.get_value("Contact Person", filters, "parent")

@frappe.whitelist()
def confirm_details(values):
    values = json.loads(values)
    doc = frappe.get_doc("Operating Company", get_supplier())
    doc.update(values)
    if values.get('varify'):
        doc.status = "Company Verified"
    doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_supplier_details(sup=None):
    if not sup:
        sup = get_supplier()
    if frappe.db.exists("Operating Company", sup):
        return frappe.get_doc("Operating Company", sup).as_dict()

@frappe.whitelist()
def get_child_suppliers(filters={}):
    parent_company = get_supplier()
    _filters = {"parent_operating_company": parent_company}
    if filters:
        _filters.update(json.loads(filters))
   
    return frappe.db.get_all("Operating Company", _filters, ["name as value", "supplier_name as label"])

@frappe.whitelist()
def update_contact_person(contact_email, updated_values):
    """
    Update Contact Person in Operating Company child table using ORM + QB.
    """
    try:
        updated_values = json.loads(updated_values)
        ContactPerson = DocType("Contact Person")

        # Get the parent Operating Company using query builder
        parent_record = (
            frappe.qb.from_(ContactPerson)
            .select(ContactPerson.parent)
            .where(ContactPerson.contact_email == contact_email)
            .limit(1)
        ).run(as_dict=True)

        if not parent_record:
            frappe.throw(_("No Contact Person found with email {0}").format(contact_email))

        parent = parent_record[0]["parent"]
        doc = frappe.get_doc("Operating Company", parent)

        contact_row = next((row for row in doc.contact_persons if row.contact_email == contact_email and row.contact_type == updated_values.get("contact_type")), None)

        frappe.log_error("contact_row", str(contact_row))
        if not contact_row:
            frappe.throw(_("Contact Person not found in the Operating Company."))

        # Update fields from values
        contact_row.first_name = updated_values.get("first_name", contact_row.first_name)
        contact_row.last_name = updated_values.get("last_name", contact_row.last_name)
        contact_row.phone_no = updated_values.get("phone_no", contact_row.phone_no)
        contact_row.position = updated_values.get("position", contact_row.position)

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return "success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_contact_person_error")
        return {"error": str(e)}

@frappe.whitelist()
def add_cbam_representative(values):
    if isinstance(values, str):
        values = json.loads(values)

    user = frappe.session.user

    # Find Operating Company where this user is already a contact (from child table)
    opcos = frappe.get_all(
        "Operating Company",
        filters={},
        fields=["name"]
    )

    target_opco = None
    for opco in opcos:
        doc = frappe.get_doc("Operating Company", opco.name)
        for row in doc.contact_persons:
            if row.contact_person == user:
                target_opco = doc
                break
        if target_opco:
            break

    if not target_opco:
        frappe.throw("Operating Company not found for the current user.")

    # Ensure only one CBAM Representative exists
    for row in target_opco.contact_persons:
        if row.contact_type == "CBAM Representative":
            frappe.throw("CBAM Representative already exists.")

    # Create new row
    target_opco.append("contact_persons", {
        "contact_type": "CBAM Representative",
        "contact_email": values.get("contact_email"),
        "first_name": values.get("first_name"),
        "last_name": values.get("last_name"),
        "phone_no": values.get("phone_no"),
        "position": values.get("position"),
        "contact_person": user,  # assuming current user is creating themselves
    })

    target_opco.save(ignore_permissions=True)
    return "success"

