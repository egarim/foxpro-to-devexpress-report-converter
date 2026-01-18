# Hybrid Approach Plan: FoxPro Runtime + Python

## 📋 Overview

This plan outlines a **two-step conversion process** that leverages FoxPro runtime for accurate report extraction and Python for REPX generation.

### Why Hybrid?

| Approach | Pros | Cons |
|----------|------|------|
| **Pure Python** | No FoxPro needed | Limited FRT parsing, relies on PDF |
| **Pure FoxPro** | Full FRT access | Complex XML generation |
| **Hybrid** ✅ | Best of both worlds | Requires FoxPro runtime |

The hybrid approach gives us:
- **100% accurate** control positions, sizes, and properties
- **Native expressions** exactly as defined in FoxPro
- **Complete band structure** with all properties
- **Python's power** for XML/REPX generation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     STEP 1: FoxPro Runtime                       │
│                                                                 │
│  ┌──────────┐    ┌────────────────────┐    ┌──────────────┐    │
│  │ FRT/FRX  │───▶│ export_frt.prg     │───▶│ report.json  │    │
│  │ file     │    │ (FoxPro script)    │    │ (full data)  │    │
│  └──────────┘    └────────────────────┘    └──────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STEP 2: Python Converter                     │
│                                                                 │
│  ┌──────────────┐    ┌────────────────────┐    ┌───────────┐   │
│  │ report.json  │───▶│ converter_hybrid.py│───▶│ .repx     │   │
│  │              │    │ (Python)           │    │ file      │   │
│  └──────────────┘    └────────────────────┘    └───────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 JSON Schema Design

The FoxPro script will export a JSON file with this structure:

```json
{
  "report": {
    "name": "FoxPro_Ebill",
    "source_file": "FoxPro_Ebill.frx",
    "exported_at": "2026-01-18T10:30:00",
    "page": {
      "width": 85000,
      "height": 110000,
      "left_margin": 0,
      "top_margin": 0,
      "right_margin": 0,
      "bottom_margin": 0,
      "orientation": 0
    }
  },
  "data_environment": {
    "tables": [
      {
        "alias": "CUSTOMER",
        "source": "customer.dbf"
      }
    ]
  },
  "bands": [
    {
      "band_type": "Title",
      "band_code": 0,
      "height": 5000,
      "visible": true
    },
    {
      "band_type": "Page Header",
      "band_code": 1,
      "height": 10000,
      "visible": true
    },
    {
      "band_type": "Detail",
      "band_code": 4,
      "height": 2500,
      "visible": true
    }
  ],
  "controls": [
    {
      "id": 1,
      "objtype": 8,
      "objtype_name": "Field",
      "band": "Detail",
      "name": "Field1",
      "position": {
        "left": 1000,
        "top": 500,
        "width": 15000,
        "height": 2000
      },
      "expression": "ALLTRIM(customer.name)",
      "format": "",
      "font": {
        "name": "Arial",
        "size": 10,
        "bold": false,
        "italic": false,
        "underline": false
      },
      "colors": {
        "foreground": 0,
        "background": 16777215
      },
      "alignment": 0,
      "stretch": false,
      "print_when": ".T."
    },
    {
      "id": 2,
      "objtype": 5,
      "objtype_name": "Label",
      "band": "Page Header",
      "name": "Label1",
      "position": {
        "left": 1000,
        "top": 100,
        "width": 8000,
        "height": 2000
      },
      "expression": "\"Customer Name\"",
      "font": {
        "name": "Arial",
        "size": 10,
        "bold": true,
        "italic": false,
        "underline": false
      },
      "colors": {
        "foreground": 0,
        "background": 16777215
      },
      "alignment": 0
    }
  ],
  "variables": [
    {
      "name": "_PAGENO",
      "expression": "_PAGENO",
      "reset_on": "Page"
    }
  ]
}
```

---

## 🦊 FoxPro FRX/FRT Structure

### ObjType Codes (OBJTYPE field)

| Code | Name | DevExpress Equivalent |
|------|------|----------------------|
| 0 | Comment | (ignored) |
| 1 | Title Band | ReportHeaderBand |
| 2 | Page Header Band | PageHeaderBand |
| 3 | Column Header | (not common) |
| 4 | Group Header | GroupHeaderBand |
| 5 | Label | XRLabel (static text) |
| 6 | Line | XRLine |
| 7 | Rectangle/Box | XRShape or XRPanel |
| 8 | Field/Expression | XRLabel with binding |
| 9 | Detail Band | DetailBand |
| 10 | Group Footer | GroupFooterBand |
| 11 | Column Footer | (not common) |
| 12 | Page Footer | PageFooterBand |
| 13 | Summary Band | ReportFooterBand |
| 17 | Picture | XRPictureBox |
| 23 | OLE Object | (not supported) |

### Band Type Codes

| Code | Band Name | DevExpress Equivalent |
|------|-----------|----------------------|
| 0 | Title | ReportHeaderBand |
| 1 | Page Header | PageHeaderBand |
| 2 | Column Header | (rare) |
| 3 | Group Header | GroupHeaderBand |
| 4 | Detail | DetailBand |
| 5 | Group Footer | GroupFooterBand |
| 6 | Column Footer | (rare) |
| 7 | Page Footer | PageFooterBand |
| 8 | Summary | ReportFooterBand |

### Coordinate System

FoxPro uses **FRUs (FoxPro Report Units)**:
- **10,000 FRUs = 1 inch**
- To convert to DevExpress (100 units/inch): `value / 100`

### Key FRX Fields

| Field | Description |
|-------|-------------|
| `OBJTYPE` | Control/band type code |
| `OBJCODE` | Sub-type code |
| `NAME` | Control name |
| `EXPR` | Expression for field/calculated |
| `HPOS` | Horizontal position (FRUs) |
| `VPOS` | Vertical position (FRUs) |
| `WIDTH` | Width (FRUs) |
| `HEIGHT` | Height (FRUs) |
| `PENRED/GREEN/BLUE` | Foreground color RGB |
| `FILLRED/GREEN/BLUE` | Background color RGB |
| `FONTFACE` | Font name |
| `FONTSIZE` | Font size |
| `FONTSTYLE` | Bitmask: 1=Bold, 2=Italic, 4=Underline |
| `PICTURE` | Format string |
| `STRETCH` | Stretch to fit |
| `TAG` | Additional properties |
| `TAG2` | More properties |
| `SUPEXPR` | Print-when expression |

---

## 🔧 Implementation Steps

### Step 1: Create FoxPro PRG Script

**File:** `foxpro/export_frt_to_json.prg`

```foxpro
* export_frt_to_json.prg
* Exports FRX/FRT report structure to JSON
* Usage: DO export_frt_to_json WITH "myreport.frx", "output.json"

LPARAMETERS tcFrxFile, tcJsonFile

LOCAL loJson, lcJson, lnRecNo

* Open the FRX as a table
USE (tcFrxFile) ALIAS frxdata IN 0 SHARED AGAIN

SELECT frxdata

* Build JSON structure
lcJson = '{'
lcJson = lcJson + '"report": ' + GetReportInfo(tcFrxFile) + ','
lcJson = lcJson + '"bands": ' + GetBands() + ','
lcJson = lcJson + '"controls": ' + GetControls()
lcJson = lcJson + '}'

* Write to file
STRTOFILE(lcJson, tcJsonFile)

USE IN frxdata

RETURN .T.

* ----------------------------------------
FUNCTION GetBands
* Returns JSON array of band definitions
* ----------------------------------------
LOCAL lcBands, lcBand
lcBands = '['
SELECT frxdata
SCAN FOR OBJTYPE IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
  * ... build band JSON
ENDSCAN
lcBands = lcBands + ']'
RETURN lcBands

* ----------------------------------------
FUNCTION GetControls
* Returns JSON array of all controls
* ----------------------------------------
LOCAL lcControls
lcControls = '['
SELECT frxdata
SCAN FOR OBJTYPE IN (5, 6, 7, 8, 17, 23)
  * ... build control JSON with all properties
ENDSCAN
lcControls = lcControls + ']'
RETURN lcControls
```

### Step 2: Create Python JSON Consumer

**File:** `src/converter_foxpro_json.py`

```python
"""
Converter that reads FoxPro-exported JSON and generates REPX
"""
import json
from lxml import etree

class FoxProJsonConverter:
    # FRU to DevExpress unit conversion
    FRU_SCALE = 100  # 10000 FRU = 1 inch; DevExpress uses 100 units/inch
    
    BAND_MAPPING = {
        "Title": "ReportHeaderBand",
        "Page Header": "PageHeaderBand",
        "Detail": "DetailBand",
        "Group Header": "GroupHeaderBand",
        "Group Footer": "GroupFooterBand",
        "Page Footer": "PageFooterBand",
        "Summary": "ReportFooterBand",
    }
    
    def __init__(self, json_path: str):
        with open(json_path, 'r') as f:
            self.data = json.load(f)
    
    def convert(self) -> str:
        # Build REPX XML from JSON data
        ...
```

### Step 3: Update CLI

Add new command for hybrid workflow:

```bash
# Using FoxPro JSON export
python cli.py convert-json <report.json> --output <folder>
```

---

## 📋 Task Breakdown

### Phase 1: FoxPro Script (2-3 hours)
- [ ] Create `foxpro/export_frt_to_json.prg`
- [ ] Handle all ObjTypes (5, 6, 7, 8, 17)
- [ ] Extract font properties correctly
- [ ] Handle color conversion (RGB)
- [ ] Export expressions with proper escaping
- [ ] Handle special characters in JSON

### Phase 2: Python Consumer (3-4 hours)
- [ ] Create `src/converter_foxpro_json.py`
- [ ] Implement band creation
- [ ] Implement control creation
- [ ] Coordinate conversion (FRU → DevExpress)
- [ ] Expression translation (reuse existing)
- [ ] Font/color mapping

### Phase 3: Integration (1-2 hours)
- [ ] Add CLI command for JSON conversion
- [ ] Create batch script for two-step process
- [ ] Error handling and validation
- [ ] Progress reporting

### Phase 4: Testing & Documentation (1-2 hours)
- [ ] Test with FoxPro_Ebill.frt
- [ ] Compare accuracy with PDF-based approach
- [ ] Update README with hybrid workflow
- [ ] Document troubleshooting

---

## 🚀 Usage (After Implementation)

### Manual Two-Step Process

```bash
# Step 1: Run FoxPro script (in FoxPro IDE or runtime)
DO export_frt_to_json WITH "FoxPro_Ebill.frx", "FoxPro_Ebill.json"

# Step 2: Run Python converter
cd src
python converter_foxpro_json.py ../FoxPro_Ebill.json ../output/FoxPro_Ebill
```

### Automated with VFP9 Runtime

```batch
@echo off
REM convert_report.bat - Full conversion pipeline

SET FRX_FILE=%1
SET OUTPUT_FOLDER=%2

REM Step 1: Export to JSON using FoxPro runtime
vfp9.exe -c foxpro\config.fpw foxpro\export_frt_to_json.prg %FRX_FILE% temp\report.json

REM Step 2: Convert JSON to REPX
python src\converter_foxpro_json.py temp\report.json %OUTPUT_FOLDER%

REM Step 3: Generate preview (optional)
tools\RepxPreview\bin\Release\net8.0\win-x64\RepxPreview.exe %OUTPUT_FOLDER%\*.repx %OUTPUT_FOLDER%\preview.png
```

---

## ✅ Expected Improvements

| Metric | Pure Python | Hybrid Approach |
|--------|-------------|-----------------|
| Control Positions | ~85% | **100%** |
| Expression Extraction | ~70% | **100%** |
| Font Properties | ~80% | **100%** |
| Band Structure | ~75% | **100%** |
| Color Accuracy | ~90% | **100%** |
| **Overall** | **7/10** | **9-10/10** |

---

## ⚠️ Prerequisites

1. **FoxPro Runtime** - VFP9 runtime or IDE
2. **Python 3.11+** - With required packages
3. **.NET 8.0** - For preview tool (optional)

---

## 🔜 Next Steps

1. **Create the FoxPro PRG script** - Start with basic structure
2. **Test JSON export** - Verify all fields are captured
3. **Build Python consumer** - Leverage existing expression translator
4. **Compare results** - Validate improvement over PDF approach
