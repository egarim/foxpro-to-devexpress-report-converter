"""
converter_frx_v3.py

Improved converter that reads FRX JSON and generates proper DevExpress REPX.
This version adds support for rectangles, lines, and picture placeholders.

Key features:
- Labels (objtype 5) and Fields (objtype 8) -> XRLabel
- Rectangles (objtype 7) -> XRShape with background color
- Lines (objtype 6) -> XRLine
- Pictures (objtype 17) -> XRPictureBox placeholder
- Proper Z-order layering (shapes first, then lines, then text)

Usage:
    python converter_frx_v3.py <report.json> [output_folder]
"""

import json
import os
import sys
import re
from lxml import etree
from expression_translator import ExpressionTranslator


class FrxToRepxConverter:
    """Converts FRX JSON to DevExpress REPX with proper band structure."""
    
    # FoxPro: 10,000 FRU = 1 inch, DevExpress: 100 units = 1 inch
    FRU_SCALE = 100
    
    # Y offset adjustment (FRX positions are offset from PDF by ~20 DX units)
    Y_OFFSET = 20
    
    # FoxPro objtype codes
    OBJTYPE_LABEL = 5
    OBJTYPE_LINE = 6
    OBJTYPE_RECTANGLE = 7
    OBJTYPE_FIELD = 8
    OBJTYPE_BAND = 9
    OBJTYPE_PICTURE = 17
    
    # FoxPro band objcode to DevExpress band type
    BAND_TYPE_MAP = {
        0: ("ReportHeaderBand", "ReportHeader"),
        1: ("PageHeaderBand", "PageHeader"),
        4: ("DetailBand", "Detail"),
        7: ("PageFooterBand", "PageFooter"),
        8: ("ReportFooterBand", "ReportFooter"),
    }
    
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.translator = ExpressionTranslator()
        self.calculated_fields = []
        self.control_count = 0
        self.ref_counter = 1
        
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def convert(self, output_folder: str = None) -> str:
        """Convert JSON to REPX."""
        if output_folder is None:
            output_folder = os.path.dirname(self.json_path) or '.'
        
        os.makedirs(output_folder, exist_ok=True)
        
        report_name = self.data.get("report", {}).get("name", "Report")
        output_path = os.path.join(output_folder, f"{report_name}.repx")
        
        # Build REPX
        root = self._build_repx()
        
        # Write file
        tree = etree.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)
        
        print(f"Generated: {output_path}")
        print(f"Controls: {self.control_count}")
        print(f"Calculated Fields: {len(self.calculated_fields)}")
        
        # Save analysis
        self._save_analysis(output_folder, report_name)
        
        return output_path
    
    def _build_repx(self) -> etree.Element:
        """Build the REPX XML structure."""
        self.ref_counter = 1
        
        # Root element
        root = etree.Element("XtraReportsLayoutSerializer")
        root.set("SerializerVersion", "24.2.3.0")
        root.set("Ref", str(self.ref_counter))
        self.ref_counter += 1
        
        root.set("ControlType", "DevExpress.XtraReports.UI.XtraReport, DevExpress.XtraReports.v24.2")
        root.set("Name", self.data.get("report", {}).get("name", "XtraReport1"))
        root.set("PageWidth", "850")
        root.set("PageHeight", "1100")
        root.set("Margins", "0, 0, 0, 0")  # No margins for accurate positioning
        root.set("PaperKind", "Letter")
        root.set("SnapGridSize", "25")
        
        # Organize controls by band
        bands_data = self._organize_controls_by_band()
        
        # Add bands
        bands_elem = etree.SubElement(root, "Bands")
        self._add_bands(bands_elem, bands_data)
        
        # Add calculated fields
        if self.calculated_fields:
            calc_elem = etree.SubElement(root, "CalculatedFields")
            for idx, field in enumerate(self.calculated_fields):
                field_elem = etree.SubElement(calc_elem, f"Item{idx + 1}")
                field_elem.set("Ref", str(self.ref_counter))
                self.ref_counter += 1
                field_elem.set("Name", field["name"])
                field_elem.set("Expression", field["expression"])
        
        return root
    
    def _organize_controls_by_band(self) -> dict:
        """Organize controls into bands based on vertical position."""
        bands = self.data.get("bands", [])
        controls = self.data.get("controls", [])
        
        # In FoxPro FRX, rectangles and lines are stored in the "bands" array
        # with objtype 7 (rectangles) and 6 (lines) - extract them as controls
        visual_elements = []
        actual_bands = []
        
        for item in bands:
            objtype = item.get("objtype", 9)
            if objtype == self.OBJTYPE_RECTANGLE:
                visual_elements.append(item)
            elif objtype == self.OBJTYPE_LINE:
                visual_elements.append(item)
            elif objtype == self.OBJTYPE_BAND:
                actual_bands.append(item)
        
        # Merge visual elements with controls
        all_controls = visual_elements + controls
        
        # Build band ranges from VPOS
        band_ranges = []
        cumulative_height = 0
        
        # Sort actual bands by their vertical position
        sorted_bands = sorted(actual_bands, key=lambda b: b.get("position", {}).get("top_fru", 0))
        
        for band in sorted_bands:
            height_fru = band.get("position", {}).get("height_fru", 0) or 0
            objcode = band.get("objcode", 4)
            
            band_ranges.append({
                "objcode": objcode,
                "start": cumulative_height,
                "end": cumulative_height + height_fru,
                "height": height_fru,
                "controls": []
            })
            cumulative_height += height_fru
        
        # If no bands found, create a default Detail band
        if not band_ranges:
            band_ranges.append({
                "objcode": 4,
                "start": 0,
                "end": 1000000,
                "height": 100000,
                "controls": []
            })
        
        # Assign all_controls to bands
        for control in all_controls:
            vpos = control.get("position", {}).get("top_fru", 0) or 0
            
            # Find which band this control belongs to
            assigned = False
            for band in band_ranges:
                if band["start"] <= vpos < band["end"]:
                    # Adjust control position relative to band
                    control["relative_vpos"] = vpos - band["start"]
                    band["controls"].append(control)
                    assigned = True
                    break
            
            # If not assigned, put in last band
            if not assigned and band_ranges:
                control["relative_vpos"] = 0
                band_ranges[-1]["controls"].append(control)
        
        return band_ranges
    
    def _add_bands(self, parent: etree.Element, bands_data: list):
        """Add bands with their controls."""
        # Group bands by type and keep only one of each
        band_by_type = {}
        
        for band in bands_data:
            objcode = band["objcode"]
            if objcode not in band_by_type:
                band_by_type[objcode] = {
                    "height": band["height"],
                    "controls": []
                }
            # Merge controls
            band_by_type[objcode]["controls"].extend(band["controls"])
            # Use max height
            if band["height"] > band_by_type[objcode]["height"]:
                band_by_type[objcode]["height"] = band["height"]
        
        # Create bands in DevExpress order
        # For absolute positioning, we just need a Detail band that spans the page
        band_order = [4]  # Just Detail band for absolute positioning
        
        item_num = 1
        for objcode in band_order:
            if objcode in band_by_type:
                band_info = self.BAND_TYPE_MAP.get(objcode)
                if band_info:
                    band_class, band_name = band_info
                    band_data = band_by_type[objcode]
                    
                    band_elem = etree.SubElement(parent, f"Item{item_num}")
                    item_num += 1
                    
                    band_elem.set("Ref", str(self.ref_counter))
                    self.ref_counter += 1
                    band_elem.set("ControlType", f"DevExpress.XtraReports.UI.{band_class}, DevExpress.XtraReports.v24.2")
                    band_elem.set("Name", f"{band_name}1")
                    
                    # Use full page height for absolute positioning
                    band_elem.set("HeightF", "1100")  # Full page height
                    
                    # Add controls to band
                    if band_data["controls"]:
                        self._add_controls_to_band(band_elem, band_data["controls"])
        
        # Ensure we have at least a Detail band
        if 4 not in band_by_type:
            band_elem = etree.SubElement(parent, f"Item{item_num}")
            band_elem.set("Ref", str(self.ref_counter))
            self.ref_counter += 1
            band_elem.set("ControlType", "DevExpress.XtraReports.UI.DetailBand, DevExpress.XtraReports.v24.2")
            band_elem.set("Name", "Detail1")
            band_elem.set("HeightF", "100")
    
    def _sort_controls_for_layering(self, controls: list) -> list:
        """
        Sort controls for proper Z-order layering.
        Order: Rectangles (backgrounds) -> Lines -> Pictures -> Labels/Fields (text on top)
        """
        layer_order = {
            self.OBJTYPE_RECTANGLE: 0,  # Bottom layer - backgrounds
            self.OBJTYPE_LINE: 1,        # Borders
            self.OBJTYPE_PICTURE: 2,     # Images
            self.OBJTYPE_LABEL: 3,       # Text
            self.OBJTYPE_FIELD: 3,       # Text fields
        }
        
        return sorted(controls, key=lambda c: layer_order.get(c.get("objtype", 5), 3))
    
    def _add_controls_to_band(self, band_elem: etree.Element, controls: list):
        """Add controls to a band element with proper layering."""
        controls_elem = etree.SubElement(band_elem, "Controls")
        
        # Sort controls for proper Z-order
        sorted_controls = self._sort_controls_for_layering(controls)
        
        idx = 1
        for control in sorted_controls:
            objtype = control.get("objtype", 5)
            
            # Skip band records (objtype 9)
            if objtype == self.OBJTYPE_BAND:
                continue
            
            # Skip controls with no valid position (vpos and hpos both 0 or very small)
            pos = control.get("position", {})
            vpos = pos.get("top_fru", 0) or 0
            hpos = pos.get("left_fru", 0) or 0
            
            # For labels/fields, skip if position is essentially at origin
            if objtype in (self.OBJTYPE_LABEL, self.OBJTYPE_FIELD):
                if vpos < 1000 and hpos < 1000:
                    expr = control.get("expression", "")
                    if not expr or expr.startswith('"\\\\') or 'updatechart' in expr.lower():
                        continue
            
            # Route to appropriate handler
            if objtype == self.OBJTYPE_RECTANGLE:
                self._add_rectangle(controls_elem, control, idx)
            elif objtype == self.OBJTYPE_LINE:
                self._add_line(controls_elem, control, idx)
            elif objtype == self.OBJTYPE_PICTURE:
                self._add_picture(controls_elem, control, idx)
            elif objtype in (self.OBJTYPE_LABEL, self.OBJTYPE_FIELD):
                self._add_label(controls_elem, control, idx)
            
            idx += 1
    
    def _rgb_to_argb(self, rgb: list) -> str:
        """
        Convert RGB array to ARGB hex string for DevExpress.
        Format: Alpha,R,G,B (e.g., "255,71,109,126")
        """
        if not rgb or len(rgb) < 3:
            return "255,255,255,255"  # Default white
        
        r, g, b = rgb[0], rgb[1], rgb[2]
        
        # Handle invalid values (-1 means transparent/no fill)
        if r < 0 or g < 0 or b < 0:
            return None  # Transparent
        
        return f"255,{r},{g},{b}"
    
    def _get_position(self, control: dict) -> tuple:
        """Extract and convert position from FRU to DevExpress units."""
        pos = control.get("position", {})
        left = int((pos.get("left_fru", 0) or 0) / self.FRU_SCALE)
        raw_top = int((pos.get("top_fru", 0) or 0) / self.FRU_SCALE)
        top = max(0, raw_top - self.Y_OFFSET)
        width = max(int((pos.get("width_fru", 1000) or 1000) / self.FRU_SCALE), 1)
        height = max(int((pos.get("height_fru", 250) or 250) / self.FRU_SCALE), 1)
        
        return left, top, width, height
    
    def _add_rectangle(self, parent: etree.Element, control: dict, item_num: int):
        """Add a rectangle using XRPanel (background box)."""
        left, top, width, height = self._get_position(control)
        
        # Skip very small rectangles (likely just spacers)
        if width < 5 or height < 5:
            return
        
        ctrl_elem = etree.SubElement(parent, f"Item{item_num}")
        ctrl_elem.set("Ref", str(self.ref_counter))
        self.ref_counter += 1
        
        # Use XRPanel instead of XRShape - it's a simple rectangular container
        ctrl_elem.set("ControlType", "DevExpress.XtraReports.UI.XRPanel, DevExpress.XtraReports.v24.2")
        ctrl_elem.set("Name", f"Panel{self.control_count}")
        self.control_count += 1
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{width}, {height}")
        
        # Fill color from fill_rgb - use BackColor for panel
        colors = control.get("colors", {})
        fill_rgb = colors.get("fill_rgb", [255, 255, 255])
        fill_color = self._rgb_to_argb(fill_rgb)
        
        if fill_color:
            ctrl_elem.set("BackColor", fill_color)
        
        # Border color from pen_rgb
        pen_rgb = colors.get("pen_rgb", [0, 0, 0])
        pen_color = self._rgb_to_argb(pen_rgb)
        
        if pen_color and pen_rgb != fill_rgb:
            # Only add border if pen color differs from fill
            ctrl_elem.set("BorderColor", pen_color)
            ctrl_elem.set("Borders", "All")
            ctrl_elem.set("BorderWidth", "1")
    
    def _add_line(self, parent: etree.Element, control: dict, item_num: int):
        """Add a line control."""
        left, top, width, height = self._get_position(control)
        
        ctrl_elem = etree.SubElement(parent, f"Item{item_num}")
        ctrl_elem.set("Ref", str(self.ref_counter))
        self.ref_counter += 1
        
        ctrl_elem.set("ControlType", "DevExpress.XtraReports.UI.XRLine, DevExpress.XtraReports.v24.2")
        ctrl_elem.set("Name", f"Line{self.control_count}")
        self.control_count += 1
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{width}, {height}")
        
        # Determine line direction based on dimensions
        # Horizontal lines have small height, vertical lines have small width
        if width > height:
            # Horizontal line
            ctrl_elem.set("LineDirection", "Horizontal")
        else:
            # Vertical line or diagonal (default to slant)
            ctrl_elem.set("LineDirection", "Vertical")
        
        # Line color from pen_rgb
        colors = control.get("colors", {})
        pen_rgb = colors.get("pen_rgb", [0, 0, 0])
        pen_color = self._rgb_to_argb(pen_rgb)
        
        if pen_color:
            ctrl_elem.set("ForeColor", pen_color)
        
        # Line width (default 1pt)
        ctrl_elem.set("LineWidth", "1")
    
    def _add_picture(self, parent: etree.Element, control: dict, item_num: int):
        """Add a picture placeholder."""
        left, top, width, height = self._get_position(control)
        
        ctrl_elem = etree.SubElement(parent, f"Item{item_num}")
        ctrl_elem.set("Ref", str(self.ref_counter))
        self.ref_counter += 1
        
        ctrl_elem.set("ControlType", "DevExpress.XtraReports.UI.XRPictureBox, DevExpress.XtraReports.v24.2")
        ctrl_elem.set("Name", f"Picture{self.control_count}")
        self.control_count += 1
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{width}, {height}")
        ctrl_elem.set("Sizing", "ZoomImage")
        
        # Add a border to make placeholder visible
        ctrl_elem.set("BorderColor", "128,128,128,128")  # Gray border
        ctrl_elem.set("Borders", "All")
        ctrl_elem.set("BorderWidth", "1")
        
        # Add placeholder text via tag to identify what this was
        name = control.get("name", "")
        if name:
            ctrl_elem.set("Tag", f"Placeholder: {name}")
    
    def _add_label(self, parent: etree.Element, control: dict, item_num: int):
        """Add a label control (for text and fields)."""
        ctrl_elem = etree.SubElement(parent, f"Item{item_num}")
        ctrl_elem.set("Ref", str(self.ref_counter))
        self.ref_counter += 1
        
        ctrl_elem.set("ControlType", "DevExpress.XtraReports.UI.XRLabel, DevExpress.XtraReports.v24.2")
        ctrl_elem.set("Name", f"Label{self.control_count}")
        self.control_count += 1
        
        # Position
        left, top, width, height = self._get_position(control)
        # Ensure minimum readable size for labels
        width = max(width, 10)
        height = max(height, 15)
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{width}, {height}")
        
        # Font
        font = control.get("font", {})
        font_name = font.get("name", "Arial") or "Arial"
        font_size = font.get("size", 10) or 10
        font_bold = font.get("bold", False)
        font_italic = font.get("italic", False)
        
        style_parts = []
        if font_bold:
            style_parts.append("Bold")
        if font_italic:
            style_parts.append("Italic")
        style_str = ", ".join(style_parts) if style_parts else ""
        
        if style_str:
            ctrl_elem.set("Font", f"{font_name}, {font_size}pt, style={style_str}")
        else:
            ctrl_elem.set("Font", f"{font_name}, {font_size}pt")
        
        # Text/Foreground color
        colors = control.get("colors", {})
        pen_rgb = colors.get("pen_rgb", [0, 0, 0])
        text_color = self._rgb_to_argb(pen_rgb)
        if text_color:
            ctrl_elem.set("ForeColor", text_color)
        
        # Background color (if fill_rgb is set and not transparent)
        fill_rgb = colors.get("fill_rgb", [-1, -1, -1])
        fill_color = self._rgb_to_argb(fill_rgb)
        if fill_color:
            ctrl_elem.set("BackColor", fill_color)
        
        # Expression or text
        expression = control.get("expression", "")
        
        if expression:
            # Check if it's a string literal
            if self._is_string_literal(expression):
                # Static text
                text = expression.strip('"\'')
                ctrl_elem.set("Text", text)
            elif self._is_valid_expression(expression):
                # Create calculated field
                translated = self.translator.translate(expression)
                # Fix field references to be bracketed
                translated = self._fix_field_references(translated)
                
                if translated and self._is_valid_translated(translated):
                    field_name = f"calcField{len(self.calculated_fields) + 1}"
                    self.calculated_fields.append({
                        "name": field_name,
                        "expression": translated,
                        "original": expression
                    })
                    
                    bindings = etree.SubElement(ctrl_elem, "ExpressionBindings")
                    bindings.text = f'<Item1 Ref="0" Expression="[{field_name}]" PropertyName="Text" />'
                else:
                    # Couldn't translate, use as static text
                    ctrl_elem.set("Text", expression[:50])
            else:
                # Invalid expression, skip or use as text
                ctrl_elem.set("Text", "")
        
        # Alignment
        offset = control.get("offset", 0)
        alignment = {0: "Near", 1: "Far", 2: "Center"}.get(offset, "Near")
        ctrl_elem.set("TextAlignment", f"Top{alignment}")
    
    def _is_string_literal(self, expr: str) -> bool:
        """Check if expression is a string literal."""
        expr = expr.strip()
        return (expr.startswith('"') and expr.endswith('"')) or \
               (expr.startswith("'") and expr.endswith("'"))
    
    def _is_valid_expression(self, expr: str) -> bool:
        """Check if expression is valid for conversion."""
        if not expr or len(expr) < 2:
            return False
        
        # Skip binary/garbage data
        if '\x00' in expr or '\x01' in expr:
            return False
        
        # Skip if too many non-printable characters
        non_printable = sum(1 for c in expr if ord(c) < 32 or ord(c) > 126)
        if non_printable > len(expr) * 0.1:
            return False
        
        # Skip data environment entries
        if 'DBSETPROP' in expr.upper() or 'CURSORSETPROP' in expr.upper():
            return False
        
        # Skip if looks like file paths
        if '\\' in expr and ':' in expr:
            return False
        
        return True
    
    def _is_valid_translated(self, translated: str) -> bool:
        """Check if translated expression is valid."""
        if not translated:
            return False
        
        # Skip if it's just a quoted string
        if translated.startswith('"') and translated.endswith('"'):
            return False
        
        # Must have some content
        if len(translated.strip()) < 2:
            return False
        
        # Check for invalid patterns
        # Comma-separated expressions not inside function call parentheses
        paren_depth = 0
        for i, c in enumerate(translated):
            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
            elif c == ',' and paren_depth == 0:
                # Comma at top level - invalid expression syntax
                return False
        
        # Skip unknown/custom FoxPro functions
        unknown_functions = ['updatechart', 'refreshform', 'thisform', 'thisreport', 
                            'report_', '_pageno', '_pageof']
        for func in unknown_functions:
            if func.lower() in translated.lower():
                return False
        
        return True
    
    def _fix_field_references(self, expr: str) -> str:
        """
        Ensure all field references are wrapped in brackets.
        E.g., TOT_CHRG08 -> [TOT_CHRG08]
        """
        if not expr:
            return expr
        
        # Skip if inside quotes
        # First, protect quoted strings
        quoted_strings = []
        def save_quoted(match):
            quoted_strings.append(match.group(0))
            return f"__QUOTED_{len(quoted_strings)-1}__"
        
        # Save single and double quoted strings
        result = re.sub(r"'[^']*'", save_quoted, expr)
        result = re.sub(r'"[^"]*"', save_quoted, result)
        
        # Pattern to match field names that aren't already bracketed
        pattern = r'(?<!\[)\b([a-zA-Z][a-zA-Z0-9_]*)\b(?!\s*\()(?!\])'
        
        # Known functions and keywords to skip
        skip_words = {
            'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE', 
            'Iif', 'Trim', 'Abs', 'Max', 'Min', 'Sum', 'Avg', 'Count',
            'FormatString', 'ToStr', 'ToDecimal', 'ToDateTime',
            'Upper', 'Lower', 'Substring', 'Replace', 'Len',
            'IsNull', 'IsNullOrEmpty', 'GetYear', 'GetMonth', 'GetDay',
            'Today', 'Now', 'Round', 'Floor', 'Ceiling',
            'TrimStart', 'TrimEnd', 'PadLeft', 'PadRight',
            'style', 'pt', 'Ref', 'Expression', 'PropertyName', 'Text'
        }
        
        def replace(match):
            word = match.group(1)
            # Skip if it's a known function/keyword
            if word in skip_words or word.lower() in [w.lower() for w in skip_words]:
                return word
            # Skip very short words that are likely operators
            if len(word) <= 1:
                return word
            return f'[{word}]'
        
        result = re.sub(pattern, replace, result)
        
        # Restore quoted strings
        for idx, qs in enumerate(quoted_strings):
            result = result.replace(f"__QUOTED_{idx}__", qs)
        
        return result
    
    def _save_analysis(self, output_folder: str, report_name: str):
        """Save conversion analysis."""
        analysis = {
            "report_name": report_name,
            "source_json": self.json_path,
            "controls_count": self.control_count,
            "calculated_fields_count": len(self.calculated_fields),
            "calculated_fields": self.calculated_fields[:20],  # First 20 for brevity
        }
        
        path = os.path.join(output_folder, f"{report_name}_analysis.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"Analysis: {path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python converter_frx_v3.py <report.json> [output_folder]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    converter = FrxToRepxConverter(json_path)
    converter.convert(output_folder)


if __name__ == "__main__":
    main()
