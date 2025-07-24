import fitz  # PyMuPDF
import os
import re
import frappe

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
                        # Log for debugging
                        frappe.log_error(f"Found importer line: '{line}' -> value: '{importer_value}'", "CBAM Importer Debug")
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

    def extract_field(label, lines, numeric=False):
        for i, l in enumerate(lines):
            if label in l:
                if ":" in l:
                    return l.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    value = lines[i + 1].strip()
                    if numeric and not re.match(r"^[\d.]+$", value):
                        continue
                    return value
        return None

    # Cache CN Code + Procedure Code from main sections like "1", "2", "3"
    parent_values = {}
    for block in good_blocks:
        section = block["Section"]
        if "." not in section:
            parent_values[section] = {
                "CN Code": block["CN Code"],
                "Requested Procedure Code": extract_field("Requested procedure code", block["Lines"], numeric=True)
            }

    # Final extraction
    extracted = []
    for block in good_blocks:
        section = block["Section"]
        lines = block["Lines"]
        parent_key = section.split(".")[0]

        # Determine if declarant acts as importer
        declarant = header_info["reporting_declarant"]
        importer = header_info["importer"]
        declarant_acts_as_importer = (declarant == importer) if declarant and importer else False
        
        # Set importer value based on logic
        final_importer_value = declarant if declarant_acts_as_importer else importer
        
        data = {
            "section": section,
            "operator_name": extract_field("Operator Name", lines),
            "installation_name": extract_field("Installation name", lines),
            "country_of_production": extract_field("Country code", lines),
            "type_of_measurement_unit": extract_field("Type of measurement unit", lines),
            "quantity": extract_field("Quantity", lines, numeric=True),
            "specific_direct_embedded_emissions": extract_field("Specific direct embedded emissions", lines, numeric=True),
            "specific_indirect_embedded_emissions": extract_field("Specific indirect embedded emissions", lines, numeric=True),
            "type_of_determination": extract_field("Type of determination", lines),
            "requested_procedure_code": extract_field("Requested procedure code", lines, numeric=True) or parent_values.get(parent_key, {}).get("Requested Procedure Code"),
            "cn_code": block.get("CN Code") or parent_values.get(parent_key, {}).get("CN Code"),
            "reporting_declarant": declarant,
            "importer": final_importer_value,
            "declarant_acts_as_importer": declarant_acts_as_importer
        }

        if data["operator_name"] or data["installation_name"]:
            extracted.append(data)
            
    frappe.log_error("Extracted CBAM Goods Data", extracted)
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
