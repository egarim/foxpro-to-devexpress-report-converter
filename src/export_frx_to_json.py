"""
export_frx_to_json.py

Reads FoxPro FRX report files directly using Python and exports to JSON.
This eliminates the need for FoxPro runtime.

Usage:
    python export_frx_to_json.py <report.frx> [output.json]
"""

import json
import sys
import os
from datetime import datetime
from dbfread import DBF


# ObjType mapping
OBJTYPE_NAMES = {
    1: "Report Header",
    2: "Page Header", 
    3: "Column Header",
    4: "Group Header",
    5: "Detail",
    6: "Group Footer",
    7: "Column Footer",
    8: "Page Footer",
    9: "Summary/Report Footer",
    5: "Label",  # Control types start here
    6: "Line",
    7: "Rectangle",
    8: "Field/Expression",
    17: "Picture",
    23: "OLE Object",
}


def export_frx_to_json(frx_path: str, output_path: str = None) -> dict:
    """
    Export FRX file to JSON format.
    
    Args:
        frx_path: Path to the FRX file
        output_path: Optional output JSON path
        
    Returns:
        Dictionary with report data
    """
    if not os.path.exists(frx_path):
        raise FileNotFoundError(f"FRX file not found: {frx_path}")
    
    # Try to read with memo file, fall back to ignoring it
    try:
        db = DBF(frx_path, encoding='latin-1')
    except Exception:
        print("Warning: Could not read memo file, expressions may be truncated")
        db = DBF(frx_path, encoding='latin-1', ignore_missing_memofile=True)
    
    records = list(db)
    
    # Build report structure
    report_name = os.path.splitext(os.path.basename(frx_path))[0]
    
    data = {
        "report": {
            "name": report_name,
            "source_file": os.path.abspath(frx_path),
            "exported_at": datetime.now().isoformat(),
            "record_count": len(records),
            "exported_by": "Python dbfread"
        },
        "bands": [],
        "controls": []
    }
    
    # Process records
    for idx, rec in enumerate(records):
        objtype = rec.get('OBJTYPE', 0)
        
        # Extract common fields
        item = {
            "id": idx + 1,
            "objtype": objtype,
            "objcode": rec.get('OBJCODE', 0),
            "name": str(rec.get('NAME', '') or '').strip(),
            "position": {
                "left_fru": rec.get('HPOS', 0) or 0,
                "top_fru": rec.get('VPOS', 0) or 0,
                "width_fru": rec.get('WIDTH', 0) or 0,
                "height_fru": rec.get('HEIGHT', 0) or 0,
            },
            "expression": str(rec.get('EXPR', '') or '').strip(),
            "picture": str(rec.get('PICTURE', '') or '').strip(),
            "font": {
                "name": str(rec.get('FONTFACE', 'Arial') or 'Arial').strip(),
                "size": rec.get('FONTSIZE', 10) or 10,
                "style": rec.get('FONTSTYLE', 0) or 0,
                "bold": bool((rec.get('FONTSTYLE', 0) or 0) & 1),
                "italic": bool((rec.get('FONTSTYLE', 0) or 0) & 2),
                "underline": bool((rec.get('FONTSTYLE', 0) or 0) & 4),
            },
            "colors": {
                "pen_rgb": [
                    rec.get('PENRED', 0) or 0,
                    rec.get('PENGREEN', 0) or 0,
                    rec.get('PENBLUE', 0) or 0
                ],
                "fill_rgb": [
                    rec.get('FILLRED', 255) or 255,
                    rec.get('FILLGREEN', 255) or 255,
                    rec.get('FILLBLUE', 255) or 255
                ]
            },
            "offset": rec.get('OFFSET', 0) or 0,  # Alignment
            "stretch": bool(rec.get('STRETCH', False)),
            "print_when": str(rec.get('SUPEXPR', '') or '').strip(),
        }
        
        # Band definition (OBJTYPE 0 with OBJCODE indicating band type)
        # First record is usually report definition
        if objtype == 1:
            # Page/report settings
            data["page"] = {
                "width_fru": rec.get('WIDTH', 85000) or 85000,
                "height_fru": rec.get('HEIGHT', 110000) or 110000,
            }
        elif objtype in (0, 9) or (objtype >= 1 and objtype <= 9 and not item["expression"]):
            # Band definitions
            item["band_type"] = get_band_type_name(objtype, rec.get('OBJCODE', 0))
            if item["band_type"]:
                data["bands"].append(item)
        else:
            # Controls (labels, fields, lines, etc.)
            item["objtype_name"] = get_objtype_name(objtype)
            data["controls"].append(item)
    
    # Output
    if output_path is None:
        output_path = frx_path.replace('.frx', '.json')
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Exported: {output_path}")
    print(f"Bands: {len(data['bands'])}")
    print(f"Controls: {len(data['controls'])}")
    
    return data


def get_band_type_name(objtype: int, objcode: int) -> str:
    """Map FoxPro band type codes to names."""
    band_map = {
        0: "Title",
        1: "Page Header",
        2: "Column Header", 
        3: "Group Header",
        4: "Detail",
        5: "Group Footer",
        6: "Column Footer",
        7: "Page Footer",
        8: "Summary",
        9: "Detail Header",
    }
    return band_map.get(objtype, "") or band_map.get(objcode, "")


def get_objtype_name(objtype: int) -> str:
    """Map FoxPro OBJTYPE to control name."""
    objtype_map = {
        5: "Label",
        6: "Line",
        7: "Rectangle",
        8: "Field",
        17: "Picture",
        23: "OLE",
        25: "ActiveX",
    }
    return objtype_map.get(objtype, f"Unknown_{objtype}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python export_frx_to_json.py <report.frx> [output.json]")
        sys.exit(1)
    
    frx_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    export_frx_to_json(frx_path, output_path)


if __name__ == "__main__":
    main()
