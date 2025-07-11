import os
import re
import fitz  # PyMuPDF
import frappe
import pandas as pd


def extract_cbam_goods(pdf_path):
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        lines.extend(page.get_text().split("\n"))

    section_re = re.compile(r"^(\d+(?:\.\d+)?)\s+[\w\d]")
    good_blocks = []
    current = {"Section": None, "Lines": []}

    for line in lines:
        line = line.strip()
        match = section_re.match(line)
        if match:
            if current["Section"]:
                good_blocks.append(current)
            current = {"Section": match.group(1), "Lines": [line]}
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

    # Step: Cache parent fields from sections like "1", "2", "3"
    parent_values = {}

    for block in good_blocks:
        section = block["Section"]
        if "." not in section:  # It's a parent
            parent_values[section] = {
                "Requested Procedure Code": extract_field("Requested procedure code", block["Lines"], numeric=True),
                "CN Code": extract_field("| CN", block["Lines"])  # fallback via section header line
            }

    # Step: Extract per-section values
    extracted = []
    for block in good_blocks:
        section = block["Section"]
        lines = block["Lines"]

        # Determine parent section ID (e.g., 1.1 → 1)
        parent_key = section.split(".")[0]

        data = {
            "Section": section,
            "Operator Name": extract_field("Operator Name", lines),
            "Installation Name": extract_field("Installation name", lines),
            "Country of Production": extract_field("Country code", lines),
            "Type of Measurement Unit": extract_field("Type of measurement unit", lines),
            "Quantity": extract_field("Quantity", lines, numeric=True),
            "Specific Direct Embedded Emissions": extract_field("Specific direct embedded emissions", lines, numeric=True),
            "Specific Indirect Embedded Emissions": extract_field("Specific indirect embedded emissions", lines, numeric=True),
            "Type of Determination": extract_field("Type of determination", lines),
            "Requested Procedure Code": extract_field("Requested procedure code", lines, numeric=True) or parent_values.get(parent_key, {}).get("Requested Procedure Code"),
            "CN Code": parent_values.get(parent_key, {}).get("CN Code")
        }

        if data["Operator Name"] or data["Installation Name"]:
            extracted.append(data)

    return extracted


@frappe.whitelist()
def extract_cbam_pdf_flex1(file_url="/files/PDF_export.pdf"):
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



import fitz  # PyMuPDF
import os
import re
import frappe

def extract_cbam_goods(pdf_path):
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        lines.extend(page.get_text().split("\n"))

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

        data = {
            "Section": section,
            "Operator Name": extract_field("Operator Name", lines),
            "Installation Name": extract_field("Installation name", lines),
            "Country of Production": extract_field("Country code", lines),
            "Type of Measurement Unit": extract_field("Type of measurement unit", lines),
            "Quantity": extract_field("Quantity", lines, numeric=True),
            "Specific Direct Embedded Emissions": extract_field("Specific direct embedded emissions", lines, numeric=True),
            "Specific indirect embedded emissions": extract_field("Specific indirect embedded emissions", lines, numeric=True),
            "Type of Determination": extract_field("Type of determination", lines),
            "Requested Procedure Code": extract_field("Requested procedure code", lines, numeric=True) or parent_values.get(parent_key, {}).get("Requested Procedure Code"),
            "CN Code": block.get("CN Code") or parent_values.get(parent_key, {}).get("CN Code")
        }

        if data["Operator Name"] or data["Installation Name"]:
            extracted.append(data)

    return extracted


@frappe.whitelist()
def extract_cbam_pdf_flex(file_url="/files/PDF_export.pdf"):
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
