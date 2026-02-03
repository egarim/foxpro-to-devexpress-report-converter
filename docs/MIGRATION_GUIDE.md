# FoxPro FRX to DevExpress REPX Migration Guide

This document captures the key learnings from converting Visual FoxPro report files (FRX/FRT) to DevExpress XtraReports (REPX) format.

## Table of Contents
- [Coordinate Systems](#coordinate-systems)
- [FoxPro Object Types](#foxpro-object-types)
- [DevExpress Control Mapping](#devexpress-control-mapping)
- [Expression Translation](#expression-translation)
- [Color Handling](#color-handling)
- [Z-Order and Layering](#z-order-and-layering)
- [Common Issues and Solutions](#common-issues-and-solutions)

---

## Coordinate Systems

### FoxPro FRU (FoxPro Report Units)
- **Scale**: 10,000 FRU = 1 inch
- **Origin**: Top-left of report
- **Fields**: `VPOS` (vertical), `HPOS` (horizontal), `HEIGHT`, `WIDTH`

### DevExpress Units
- **Scale**: 100 units = 1 inch (default)
- **Origin**: Top-left of band/control

### Conversion Formula
```python
FRU_SCALE = 100  # 10,000 FRU / 100 DX units = 100
dx_position = fru_position / FRU_SCALE
```

### Y-Offset Adjustment
FoxPro positions have an inherent offset that needs correction:
```python
Y_OFFSET = 20  # DevExpress units
top = max(0, raw_top - Y_OFFSET)
```

---

## FoxPro Object Types (OBJTYPE)

| OBJTYPE | Name | Description |
|---------|------|-------------|
| 5 | Label | Static text labels |
| 6 | Line | Lines and borders |
| 7 | Rectangle | Filled rectangles/boxes |
| 8 | Field | Data-bound fields with expressions |
| 9 | Band | Report bands (header, detail, footer) |
| 17 | Picture | Images, charts, OLE objects |
| 18 | Variable | Report variables |
| 23 | Data Environment | Data source definitions |
| 25 | Cursor | Data cursor definitions |

### Important Note on Data Location
- **Labels, Fields, Pictures** (objtype 5, 8, 17) → stored in `controls` array
- **Rectangles, Lines** (objtype 7, 6) → stored in `bands` array (not controls!)

This is a critical discovery - visual elements like rectangles and lines are stored alongside band definitions in FoxPro, not with other controls.

---

## DevExpress Control Mapping

### Rectangles: Use XRPanel, NOT XRShape

**❌ XRShape with ShapeRectangle renders as ELLIPSE by default!**

```xml
<!-- WRONG - renders as ellipse -->
<Item1 ControlType="DevExpress.XtraReports.UI.XRShape, DevExpress.XtraReports.v24.2"
       Shape="DevExpress.XtraPrinting.Shape.ShapeRectangle" />
```

**✅ Use XRPanel for rectangular backgrounds:**

```xml
<!-- CORRECT - renders as rectangle -->
<Item1 ControlType="DevExpress.XtraReports.UI.XRPanel, DevExpress.XtraReports.v24.2"
       BackColor="255,71,109,126"
       LocationFloat="44, 120"
       SizeF="726, 30" />
```

### Control Type Mapping Summary

| FoxPro | DevExpress | Notes |
|--------|------------|-------|
| Label (5) | XRLabel | Static text |
| Field (8) | XRLabel + CalculatedField | Dynamic expressions |
| Rectangle (7) | **XRPanel** | Use BackColor for fill |
| Line (6) | XRLine | LineDirection: Horizontal/Vertical |
| Picture (17) | XRPictureBox | Placeholder with border |

---

## Expression Translation

### String Literals
- FoxPro uses double quotes: `"Hello World"`
- DevExpress uses single quotes: `'Hello World'`

### Comma Concatenation
FoxPro allows comma for string concatenation:
```foxpro
ALLTRIM(field1), ALLTRIM(field2)
```
DevExpress requires `+` operator:
```csharp
Trim([field1]) + Trim([field2])
```

### Function Mapping

| FoxPro | DevExpress |
|--------|------------|
| `ALLTRIM()` | `Trim()` |
| `IIF()` | `Iif()` |
| `DTOC()` | `ToStr()` |
| `STR()` | `ToStr()` |
| `UPPER()` | `Upper()` |
| `LOWER()` | `Lower()` |
| `SUBSTR()` | `Substring()` |

### Field References
DevExpress requires brackets around field names:
```
TOT_CHRG08  →  [TOT_CHRG08]
billdate    →  [billdate]
```

### Invalid Expressions to Skip
- `updatechart()` - FoxPro chart update function
- `thisform.` / `thisreport.` - Form/report references
- `_pageno` / `_pageof` - Page number variables
- File paths containing `:\` 

---

## Color Handling

### FoxPro Color Format
RGB stored as array: `[R, G, B]`
- `pen_rgb`: Border/foreground color
- `fill_rgb`: Background/fill color
- Value of `-1` indicates transparent

### DevExpress Color Format
ARGB string: `"Alpha,R,G,B"`

```python
def rgb_to_argb(rgb):
    if rgb[0] < 0:  # -1 = transparent
        return None
    return f"255,{rgb[0]},{rgb[1]},{rgb[2]}"
```

### Key Colors Found in Sample Report
| Color | RGB | Usage |
|-------|-----|-------|
| Teal | [71,109,126] | Header backgrounds |
| Gray | [240,240,238] | Table cell backgrounds |
| Dark Gray | [79,89,78] | Lines/borders |
| Yellow | [254,245,184] | Highlight areas |

---

## Z-Order and Layering

DevExpress renders controls in XML order. For proper layering:

1. **Backgrounds first** (XRPanel) - bottom layer
2. **Lines second** (XRLine) - borders
3. **Pictures third** (XRPictureBox) - images/charts
4. **Labels last** (XRLabel) - text on top

```python
def sort_controls_for_layering(controls):
    layer_order = {
        OBJTYPE_RECTANGLE: 0,  # Bottom
        OBJTYPE_LINE: 1,
        OBJTYPE_PICTURE: 2,
        OBJTYPE_LABEL: 3,      # Top
        OBJTYPE_FIELD: 3,
    }
    return sorted(controls, key=lambda c: layer_order.get(c["objtype"], 3))
```

---

## Common Issues and Solutions

### Issue 1: "Single criterion expected" error
**Cause**: Comma concatenation in expressions
**Solution**: Replace top-level commas with `+` operator

### Issue 2: "Invalid symbols at character 0" error
**Cause**: Double quotes in string literals
**Solution**: Convert `"text"` to `'text'`

### Issue 3: Shapes render as ellipses
**Cause**: XRShape defaults to ellipse rendering
**Solution**: Use XRPanel instead of XRShape for rectangles

### Issue 4: Position offset (~14-20 points)
**Cause**: FoxPro internal coordinate offset
**Solution**: Apply Y_OFFSET correction (20 units)

### Issue 5: Missing rectangles and lines
**Cause**: These are in `bands` array, not `controls`
**Solution**: Extract objtype 6 and 7 from bands array

### Issue 6: Text appears behind backgrounds
**Cause**: Incorrect Z-order in XML
**Solution**: Sort controls by layer before generating XML

### Issue 7: Duplicate/overlapping text
**Cause**: FoxPro FRX files often contain duplicate entries for the same visual element
**Solution**: Deduplicate controls based on position and expression before generating XML

```python
def deduplicate_controls(controls):
    seen = set()
    deduplicated = []
    for control in controls:
        pos = control.get("position", {})
        top = int((pos.get("top_fru", 0) or 0) / 100)
        left = int((pos.get("left_fru", 0) or 0) / 100)
        expr = (control.get("expression", "") or "").strip()[:30]
        objtype = control.get("objtype", 0)
        key = (objtype, top, left, expr)
        if key not in seen:
            seen.add(key)
            deduplicated.append(control)
    return deduplicated
```

---

## REPX File Structure

```xml
<?xml version='1.0' encoding='UTF-8'?>
<XtraReportsLayoutSerializer SerializerVersion="24.2.3.0" Ref="1"
    ControlType="DevExpress.XtraReports.UI.XtraReport, DevExpress.XtraReports.v24.2"
    Name="ReportName"
    PageWidth="850"
    PageHeight="1100"
    Margins="0, 0, 0, 0"
    PaperKind="Letter">
  <Bands>
    <Item1 ControlType="DevExpress.XtraReports.UI.DetailBand, DevExpress.XtraReports.v24.2"
           Name="Detail1" HeightF="1100">
      <Controls>
        <!-- Panels (rectangles) first -->
        <Item1 ControlType="DevExpress.XtraReports.UI.XRPanel..." />
        <!-- Lines second -->
        <Item2 ControlType="DevExpress.XtraReports.UI.XRLine..." />
        <!-- Pictures third -->
        <Item3 ControlType="DevExpress.XtraReports.UI.XRPictureBox..." />
        <!-- Labels last -->
        <Item4 ControlType="DevExpress.XtraReports.UI.XRLabel..." />
      </Controls>
    </Item1>
  </Bands>
  <CalculatedFields>
    <Item1 Name="calcField1" Expression="Trim([fieldname])" />
  </CalculatedFields>
</XtraReportsLayoutSerializer>
```

---

## Tools Created

1. **converter_frx_v3.py** - Main converter from FRX JSON to REPX
2. **expression_translator.py** - Translates FoxPro expressions to DevExpress
3. **export_frx_to_json.py** - Exports FRX binary to JSON
4. **RepxPreview** (.NET) - Renders REPX to PNG for visual comparison

---

## Version Information

- DevExpress XtraReports: v24.2
- Visual FoxPro: 9.0
- Python: 3.x with lxml

---

*Document created: February 2026*
*Based on: Gateway Services CDD eBill report migration*
