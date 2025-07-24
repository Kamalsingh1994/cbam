import fitz  # PyMuPDF
import os
import re
import frappe

def extract_numeric_value(text):
    match = re.search(r'[-+]?\d*\.\d+|\d+', text)
    if match:
        return match.group(0)
    return None

def extract_field(label, lines):
    for i, l in enumerate(lines):
        if label.lower() in l.lower():
            # Look for the next non-empty line after the label
            for j in range(i + 1, len(lines)):
                value = lines[j].strip()
                if value:
                    return value
            return None
    return None

def get_section_value_from_title(section, label, prev_lines):
    # If the section title is a value and the previous section ended with the label
    if section and re.match(r'^\d+(\.\d+)?\s*\w+', section):
        if prev_lines and prev_lines[-1].strip().lower() == label.lower():
            return section
    return None

def extract_cbam_goods(pdf_path):
    doc = fitz.open(pdf_path)
    lines = []
    header_info = {"reporting_declarant": None, "importer": None}

    for page_num, page in enumerate(doc):
        page_lines = page.get_text("text").split("\n")  # Use 'text' option for better text extraction
        lines.extend(page_lines)

        # Extract header info from the first page
        if page_num == 0:
            for i, line in enumerate(page_lines):
                if "Reporting declarant" in line:
                    header_info["reporting_declarant"] = page_lines[i + 1].strip() if i + 1 < len(page_lines) else None
                
                # Handle Importer with debugging
                if "Importer" in line:
                    # Fetch the value directly below 'Importer', similar to 'Reporting declarant'
                    if i + 1 < len(page_lines):
                        importer_value = page_lines[i + 1].strip()
                        header_info["importer"] = importer_value
                        break  # Stop after finding the first importer

    # Match section headers like "1. 73181535 | CN"
    top_section_re = re.compile(r"^(\d+)\.\s+(\d+)\s+\|")  # e.g. "1. 73181535 | CN"
    sub_section_re = re.compile(r"^(\d+\.\d+)\s")  # e.g. "1.1 Some text"

    good_blocks = []
    current = {"Section": None, "CN Code": None, "Lines": []}

    for line in lines:
        line = line.strip()

        match_top = top_section_re.match(line)
        match_sub = sub_section_re.match(line)

        if match_top:
            if current["Section"]:
                good_blocks.append(current)
            current = {
                "Section": match_top.group(1),  # 1, 2, 3
                "CN Code": match_top.group(2),
                "Lines": [line]
            }
        elif match_sub and current["Section"]:
            if current["Lines"]:
                good_blocks.append(current)
            current = {
                "Section": match_sub.group(1),  # 1.1, 2.2, etc.
                "CN Code": None,
                "Lines": [line]
            }
        elif current["Section"]:
            current["Lines"].append(line)

    if current["Section"]:
        good_blocks.append(current)

    # Cache CN Code + Procedure Code from main sections like "1", "2", "3"
    parent_values = {}
    for block in good_blocks:
        section = block["Section"]
        if "." not in section:
            parent_values[section] = {
                "CN Code": block["CN Code"],
                "Requested Procedure Code": extract_field("Requested procedure code", block["Lines"])
            }

    # Final extraction
    extracted = []
    last_lines = None
    for idx, block in enumerate(good_blocks):
        section = block["Section"]
        lines = block["Lines"]
        parent_key = section.split(".")[0]

        declarant = header_info["reporting_declarant"]
        importer = header_info["importer"]
        declarant_acts_as_importer = (declarant == importer) if declarant and importer else False
        final_importer_value = declarant if declarant_acts_as_importer else importer

        # Get raw and numeric values for emissions fields, handling both structures
        sdee_raw = extract_field("Specific direct embedded emissions", lines)
        sdee_attached = False
        if not sdee_raw:
            sdee_raw = get_section_value_from_title(section, "Specific direct embedded emissions", last_lines)
            # If found, attach to previous row
            if sdee_raw and extracted:
                extracted[-1]["specific_direct_embedded_emissions"] = sdee_raw
                extracted[-1]["specific_direct_embedded_emissions_numeric"] = extract_numeric_value(sdee_raw)
                sdee_attached = True
        sdee_num = extract_numeric_value(sdee_raw) if sdee_raw and not sdee_attached else None

        sidee_raw = extract_field("Specific indirect embedded emissions", lines)
        sidee_attached = False
        if not sidee_raw:
            sidee_raw = get_section_value_from_title(section, "Specific indirect embedded emissions", last_lines)
            if sidee_raw and extracted:
                extracted[-1]["specific_indirect_embedded_emissions"] = sidee_raw
                extracted[-1]["specific_indirect_embedded_emissions_numeric"] = extract_numeric_value(sidee_raw)
                sidee_attached = True
        sidee_num = extract_numeric_value(sidee_raw) if sidee_raw and not sidee_attached else None

        data = {
            "section": section,
            "operator_name": extract_field("Operator Name", lines),
            "installation_name": extract_field("Installation name", lines),
            "country_of_production": extract_field("Country code", lines),
            "type_of_measurement_unit": extract_field("Type of measurement unit", lines),
            "quantity": extract_field("Quantity", lines),
            "specific_direct_embedded_emissions": sdee_raw if not sdee_attached else None,
            "specific_direct_embedded_emissions_numeric": sdee_num,
            "specific_indirect_embedded_emissions": sidee_raw if not sidee_attached else None,
            "specific_indirect_embedded_emissions_numeric": sidee_num,
            "type_of_determination": extract_field("Type of determination", lines),
            "requested_procedure_code": extract_field("Requested procedure code", lines) or parent_values.get(parent_key, {}).get("Requested Procedure Code"),
            "cn_code": block.get("CN Code") or parent_values.get(parent_key, {}).get("CN Code"),
            "reporting_declarant": declarant,
            "importer": final_importer_value,
            "declarant_acts_as_importer": declarant_acts_as_importer
        }

        # Only add rows with meaningful business data
        if (data["operator_name"] or data["installation_name"]):
            extracted.append(data)
        last_lines = lines
    return extracted


@frappe.whitelist()
def extract_cbam_pdf_flex(file_url):
    if file_url.startswith("/private/files/"):
        full_path = frappe.get_site_path("private", "files", os.path.basename(file_url))
    elif file_url.startswith("/files/"):
        full_path = frappe.get_site_path("public", "files", os.path.basename(file_url))
    else:
        raise ValueError("Invalid file URL")

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")

    extracted = extract_cbam_goods(full_path)

    return extracted
