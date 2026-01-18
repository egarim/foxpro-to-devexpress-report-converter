"""
Explore FRT file structure - FoxPro Report files are DBF format
This script helps us understand the structure of FRT files
"""

from dbfread import DBF
import json
from pathlib import Path


def explore_frt(frt_path: str):
    """Read FRT file as DBF and explore its structure"""
    
    print(f"=" * 80)
    print(f"Exploring FRT file: {frt_path}")
    print(f"=" * 80)
    
    try:
        # Open the FRT file as a DBF
        # Try different encodings - FoxPro often uses cp1252 or latin1
        table = DBF(frt_path, load=True, ignore_missing_memofile=True, encoding='cp1252')
        
        # Print field information
        print("\n📋 FIELD DEFINITIONS:")
        print("-" * 60)
        for field in table.fields:
            print(f"  {field.name:20} | Type: {field.type:10} | Length: {field.length}")
        
        print(f"\n📊 TOTAL RECORDS: {len(table)}")
        print("-" * 60)
        
        # Analyze record types
        record_types = {}
        for record in table:
            # Try to identify the record type - FoxPro uses OBJTYPE field
            obj_type = record.get('OBJTYPE', record.get('objtype', 'UNKNOWN'))
            if obj_type not in record_types:
                record_types[obj_type] = []
            record_types[obj_type].append(record)
        
        print("\n📦 RECORD TYPES FOUND:")
        print("-" * 60)
        for obj_type, records in sorted(record_types.items(), key=lambda x: str(x[0])):
            print(f"  Type {obj_type}: {len(records)} records")
        
        # Print sample records for each type
        print("\n📝 SAMPLE RECORDS BY TYPE:")
        print("=" * 80)
        
        for obj_type, records in sorted(record_types.items(), key=lambda x: str(x[0])):
            print(f"\n--- Type {obj_type} ({len(records)} records) ---")
            # Show first record of each type
            if records:
                sample = records[0]
                for key, value in sample.items():
                    if value is not None and value != '' and value != 0:
                        # Truncate long values
                        str_val = str(value)
                        if len(str_val) > 100:
                            str_val = str_val[:100] + "..."
                        print(f"    {key}: {str_val}")
        
        return table, record_types
        
    except Exception as e:
        print(f"❌ Error reading FRT file: {e}")
        raise


def extract_report_structure(frt_path: str) -> dict:
    """
    Extract structured report data from FRT file
    
    FoxPro FRT Object Types:
    1 = Report header/title band
    2 = Page header band
    3 = Column header band
    4 = Group header band
    5 = Detail band
    6 = Group footer band
    7 = Column footer band
    8 = Page footer band
    9 = Report footer/summary band
    17 = Data environment
    18 = Cursor (data source reference)
    19 = Relation
    23 = Field/Label object
    25 = Line object
    26 = Rectangle/Box object
    27 = Picture/Image object
    """
    
    table = DBF(frt_path, load=True, ignore_missing_memofile=True, encoding='cp1252')
    
    report = {
        "source_file": str(frt_path),
        "bands": [],
        "objects": [],
        "data_environment": None,
        "fonts": [],
        "raw_records": []
    }
    
    band_type_map = {
        0: "Title",
        1: "PageHeader", 
        2: "ColumnHeader",
        3: "GroupHeader",
        4: "Detail",
        5: "GroupFooter",
        6: "ColumnFooter",
        7: "PageFooter",
        8: "Summary",
        9: "DetailHeader"
    }
    
    object_type_map = {
        5: "Label",
        6: "InputField",
        7: "Line",
        8: "Rectangle",
        17: "Picture",
        23: "OLEObject"
    }
    
    for record in table:
        obj_type = record.get('OBJTYPE', 0)
        
        # Store raw record for analysis
        raw_record = {k: v for k, v in record.items() if v is not None and v != '' and v != 0}
        report["raw_records"].append(raw_record)
        
        # Band records (type 0 in OBJTYPE, with OBJCODE indicating band type)
        if obj_type == 0:
            obj_code = record.get('OBJCODE', 0)
            band_info = {
                "type": band_type_map.get(obj_code, f"Unknown_{obj_code}"),
                "height": record.get('HEIGHT', 0),
                "vpos": record.get('VPOS', 0),
                "hpos": record.get('HPOS', 0),
                "width": record.get('WIDTH', 0)
            }
            report["bands"].append(band_info)
            
        # Object records
        elif obj_type in [5, 6, 7, 8, 17, 23]:
            obj_info = {
                "type": object_type_map.get(obj_type, f"Unknown_{obj_type}"),
                "name": record.get('NAME', ''),
                "expr": record.get('EXPR', ''),
                "vpos": record.get('VPOS', 0),
                "hpos": record.get('HPOS', 0),
                "height": record.get('HEIGHT', 0),
                "width": record.get('WIDTH', 0),
                "fontface": record.get('FONTFACE', ''),
                "fontsize": record.get('FONTSIZE', 0),
                "fontstyle": record.get('FONTSTYLE', 0),
            }
            report["objects"].append(obj_info)
    
    return report


if __name__ == "__main__":
    frt_path = Path(__file__).parent.parent / "FoxPro_Ebill.frt"
    
    # First, explore the raw structure
    table, record_types = explore_frt(str(frt_path))
    
    print("\n" + "=" * 80)
    print("📄 EXTRACTING STRUCTURED REPORT DATA")
    print("=" * 80)
    
    # Extract structured data
    report_data = extract_report_structure(str(frt_path))
    
    # Save to JSON for analysis
    output_path = Path(__file__).parent.parent / "frt_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n✅ Report structure saved to: {output_path}")
    print(f"   - Bands found: {len(report_data['bands'])}")
    print(f"   - Objects found: {len(report_data['objects'])}")
