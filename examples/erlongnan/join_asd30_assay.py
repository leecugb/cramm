#!/usr/bin/env python
"""Join the 30 traced ASD samples to the original assay XLSX, without pickle.

The source workbook headers do not state units. Output therefore preserves the
original numeric values under ``*_source_value`` names and leaves unit status
explicit rather than inferring ppb, ppm, or µg/g from a figure label.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN, "r": DOC_REL, "p": PKG_REL}
ELEMENTS = ["Ag", "Au", "Co", "Cu", "Ni", "Pb", "Sb", "Zn"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {reference!r}")
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def first_sheet_rows(path: Path) -> List[List[str]]:
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships.findall("p:Relationship", NS)}
        sheet = workbook.find("m:sheets/m:sheet", NS)
        if sheet is None:
            raise ValueError("Workbook has no sheets")
        target = targets[sheet.attrib[f"{{{DOC_REL}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        root = ET.fromstring(archive.read(target))
        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values: Dict[int, str] = {}
            for cell in row.findall("m:c", NS):
                index = column_index(cell.attrib.get("r", ""))
                kind = cell.attrib.get("t")
                value_node = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                value = ""
                if kind == "s" and value_node is not None:
                    value = shared[int(value_node.text or "0")]
                elif kind == "inlineStr" and inline is not None:
                    value = "".join(node.text or "" for node in inline.findall(".//m:t", NS))
                elif value_node is not None:
                    value = value_node.text or ""
                values[index] = value
            width = max(values) + 1 if values else 0
            rows.append([values.get(index, "") for index in range(width)])
        return rows


def read_assay(path: Path) -> Dict[str, dict]:
    rows = first_sheet_rows(path)
    if not rows:
        raise ValueError("Assay workbook is empty")
    header = rows[0]
    required = ["分析编号", "样品原号"] + ELEMENTS
    missing = [name for name in required if name not in header]
    if missing:
        raise ValueError(f"Assay workbook lacks columns: {missing}")
    records = {}
    for row in rows[1:]:
        record = {name: row[index] if index < len(row) else "" for index, name in enumerate(header)}
        sample_id = record["样品原号"]
        if not sample_id:
            continue
        if sample_id in records:
            raise ValueError(f"Duplicate assay sample ID: {sample_id}")
        records[sample_id] = record
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="asd30_index.csv")
    parser.add_argument("--assay-xlsx", type=Path, required=True, help="Original Beishan assay workbook")
    parser.add_argument("--derived-csv", type=Path, help="Optional 30-row derived feature CSV for an Au order check")
    parser.add_argument("--output", type=Path, required=True, help="Output joined CSV")
    parser.add_argument("--summary", type=Path, help="Optional JSON audit summary")
    args = parser.parse_args()
    with args.index.open(encoding="utf-8", newline="") as stream:
        index_rows = list(csv.DictReader(stream))
    assay = read_assay(args.assay_xlsx)
    derived = None
    if args.derived_csv:
        with args.derived_csv.open(encoding="utf-8", newline="") as stream:
            derived = list(csv.DictReader(stream))
        if len(derived) != len(index_rows):
            raise ValueError("Derived table and ASD index have different row counts")
    fields = ["analysis_index_0based", "sample_id", "library_index_0based", "analysis_id"]
    fields += [f"{name}_source_value" for name in ELEMENTS]
    fields += ["source_unit_status"]
    output_rows = []
    au_differences = []
    for position, index_row in enumerate(index_rows):
        sample_id = index_row["sample_id"]
        if sample_id not in assay:
            raise ValueError(f"No original assay row for {sample_id}")
        source = assay[sample_id]
        row = {
            "analysis_index_0based": index_row["analysis_index_0based"],
            "sample_id": sample_id,
            "library_index_0based": index_row["library_index_0based"],
            "analysis_id": source["分析编号"],
            "source_unit_status": "not_stated_in_source_header",
        }
        for name in ELEMENTS:
            row[f"{name}_source_value"] = source[name]
        if derived is not None:
            au_differences.append(abs(float(source["Au"]) - float(derived[position]["Au"])))
        output_rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    summary = {
        "schema": "cramm.erlongnan.asd30-assay-join.v1",
        "joined_samples": len(output_rows),
        "assay_xlsx": str(args.assay_xlsx.resolve()),
        "assay_xlsx_sha256": sha256(args.assay_xlsx),
        "unit_status": "not_stated_in_source_header",
        "derived_csv_checked": derived is not None,
        "maximum_au_abs_difference": max(au_differences) if au_differences else None,
        "scope_note": "The join uses explicit sample IDs. Coordinates and EMIT pixels are not present in this workbook.",
    }
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Joined {len(output_rows)} samples by sample ID; max Au difference={summary['maximum_au_abs_difference']}")


if __name__ == "__main__":
    main()
