# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document


class ExternalGood(Document):
    pass


@frappe.whitelist()
def bulk_create_external_goods(rows, declarant=None, cbam_report=None, reporting_period=None, declarant_acts_as_importer=None, importer=None):
    if isinstance(rows, str):
        rows = json.loads(rows)

    created = []

    for row in rows:
        try:
            # Clean + resolve linked fields
            raw_country = row.get("country")
            country_name = raw_country.split(" - ")[-1].strip() if raw_country else None

            cn_code = get_or_create_linked_value("CN Code", "cn_code", row.get("cn_code"))
            customs_procedure = get_or_create_linked_value("Customs Procedure", "name", row.get("requested_procedure_code"))
            installation_country = get_or_create_linked_value("Country", "country_name", country_name)

            # Create External Good
            doc = frappe.new_doc("External Good")
            doc.update({
                "position_number": row.get("section"),
                "cn_code": cn_code,
                "supplier": row.get("operator_name"),
                "installation_name": row.get("installation_name"),
                "installation_country": installation_country,
                "raw_mass_tonne": row.get("quantity"),
                "raw_mass": float(row.get("quantity")) * 1000,  # Convert to kg
                "specific_direct_embedded_emissions": row.get("direct_embedded_emissions"),
                "specific_indirect_embedded_emissions": row.get("indirect_embedded_emissions"),
                "customs_procedure": customs_procedure,
                "calculate": "Quantity of Articles",
                "declarant": declarant,
                "report_id": cbam_report,
                "reporting_period": reporting_period,
                "declarant_acts_as_importer": declarant_acts_as_importer,
                "importer": importer
            })
            doc.insert(ignore_permissions=True)

            # Link back to child table if possible
            if row.get("parent") and row.get("idx"):
                frappe.db.set_value(
                    "CBAM Report Data",
                    {"parent": row["parent"], "idx": row["idx"]},
                    {
						"external_good": doc.name,
						"imported": 1
					}
                )

            created.append({
                "external_good": doc.name,
                "idx": row.get("idx")
            })

        except Exception:
            frappe.log_error(frappe.get_traceback(), "External Good Import Error")

    return {"created": created}


def get_or_create_linked_value(doctype, fieldname, value):
    if not value:
        return None

    # Check if value exists
    existing = frappe.db.get_value(doctype, {fieldname: value})
    if existing:
        return existing

    # Try to create new record
    try:
        doc = frappe.get_doc({
            "doctype": doctype,
            fieldname: value
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Auto-create failed for {doctype}: {value}")
        return None
