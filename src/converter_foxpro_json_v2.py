"""
converter_foxpro_json_v2.py

Improved converter that reads FoxPro-exported JSON and generates DevExpress REPX.
Creates a simple report structure with all controls in a single Detail band.

Usage:
    python converter_foxpro_json_v2.py <report.json> [output_folder]
"""

import json
import os
import sys
from pathlib import Path
from lxml import etree
from expression_translator import ExpressionTranslator


class FoxProJsonConverterV2:
    """Converts FoxPro-exported JSON to DevExpress REPX format (v2)."""
    
    # FoxPro Report Units to DevExpress conversion
    # FoxPro: 10,000 FRU = 1 inch
    # DevExpress: 100 units = 1 inch
    FRU_SCALE = 100
    
    def __init__(self, json_path: str):
        """Initialize converter with JSON file path."""
        self.json_path = json_path
        self.translator = ExpressionTranslator()
        self.calculated_fields = []
        self.control_count = 0
        
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def convert(self, output_folder: str = None) -> str:
        """Convert JSON to REPX format."""
        if output_folder is None:
            output_folder = os.path.dirname(self.json_path)
        
        os.makedirs(output_folder, exist_ok=True)
        
        report_name = self.data.get("report", {}).get("name", "Report")
        output_path = os.path.join(output_folder, f"{report_name}.repx")
        
        # Build REPX XML
        root = self._build_repx()
        
        # Write to file
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
        # Root element
        root = etree.Element("XtraReportsLayoutSerializer")
        root.set("SerializerVersion", "24.2.3.0")
        root.set("Ref", "1")
        root.set("ControlType", "DevExpress.XtraReports.UI.XtraReport, DevExpress.XtraReports.v24.2")
        root.set("Name", self.data.get("report", {}).get("name", "XtraReport1"))
        
        # Page settings - use full page
        root.set("PageWidth", "850")
        root.set("PageHeight", "1100")
        root.set("Margins", "0, 0, 0, 0")  # No margins to use full page
        root.set("PaperKind", "Letter")
        root.set("SnapGridSize", "25")
        
        # Add bands
        bands_elem = etree.SubElement(root, "Bands")
        self._add_bands(bands_elem)
        
        # Add calculated fields
        if self.calculated_fields:
            calc_elem = etree.SubElement(root, "CalculatedFields")
            for idx, field in enumerate(self.calculated_fields):
                self._add_calculated_field(calc_elem, field, idx)
        
        # Version info
        etree.SubElement(root, "Version").text = "24.2"
        
        return root
    
    def _add_bands(self, parent: etree.Element):
        """Add bands and all controls."""
        controls_data = self.data.get("controls", [])
        
        # Calculate page height based on controls
        max_y = 0
        for ctrl in controls_data:
            pos = ctrl.get("position", {})
            y = pos.get("top_fru", 0) + pos.get("height_fru", 0)
            if y > max_y:
                max_y = y
        
        # Convert to DevExpress units
        page_height = int(max_y / self.FRU_SCALE) + 50
        
        # Create a single Detail band that spans the full page
        detail_band = etree.SubElement(parent, "Item1")
        detail_band.set("Ref", "2")
        detail_band.set("ControlType", "DevExpress.XtraReports.UI.DetailBand, DevExpress.XtraReports.v24.2")
        detail_band.set("Name", "Detail")
        detail_band.set("HeightF", str(max(page_height, 1100)))
        
        # Add all controls to the detail band
        controls_elem = etree.SubElement(detail_band, "Controls")
        
        ref_counter = 3
        for ctrl in controls_data:
            self._add_control(controls_elem, ctrl, ref_counter)
            ref_counter += 1
    
    def _add_control(self, parent: etree.Element, control: dict, ref: int):
        """Add a control element."""
        objtype = control.get("objtype", 8)
        
        # Create control element
        ctrl_elem = etree.SubElement(parent, "Item1")
        ctrl_elem.set("Ref", str(ref))
        ctrl_elem.set("ControlType", "DevExpress.XtraReports.UI.XRLabel, DevExpress.XtraReports.v24.2")
        
        self.control_count += 1
        control_name = control.get("name") or f"label{self.control_count}"
        ctrl_elem.set("Name", self._sanitize_name(control_name))
        
        # Position and size
        pos = control.get("position", {})
        left = int(pos.get("left_fru", 0) / self.FRU_SCALE)
        top = int(pos.get("top_fru", 0) / self.FRU_SCALE)
        width = int(pos.get("width_fru", 1000) / self.FRU_SCALE)
        height = int(pos.get("height_fru", 250) / self.FRU_SCALE)
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{max(width, 10)}, {max(height, 15)}")
        
        # Font
        font_info = control.get("font", {})
        font_name = font_info.get("name", "Arial") or "Arial"
        font_size = font_info.get("size", 10) or 10
        font_bold = font_info.get("bold", False)
        font_italic = font_info.get("italic", False)
        
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
        
        # Colors
        colors = control.get("colors", {})
        pen_rgb = colors.get("pen_rgb", [0, 0, 0])
        if pen_rgb and pen_rgb != [0, 0, 0] and pen_rgb != [-1, -1, -1]:
            ctrl_elem.set("ForeColor", f"{pen_rgb[0]}, {pen_rgb[1]}, {pen_rgb[2]}")
        
        # Expression/Text
        expression = control.get("expression", "")
        if expression:
            expr_stripped = expression.strip()
            
            # Skip invalid/metadata expressions
            if self._is_invalid_expression(expr_stripped):
                return
            
            # Check if it's a string literal
            if (expr_stripped.startswith('"') and expr_stripped.endswith('"')) or \
               (expr_stripped.startswith("'") and expr_stripped.endswith("'")):
                # Static text
                text = expr_stripped[1:-1]
                ctrl_elem.set("Text", text)
            else:
                # Translate expression
                translated = self.translator.translate(expression)
                
                if translated and not self._is_invalid_expression(translated):
                    # Check if translated is also a string literal
                    trans_stripped = translated.strip()
                    if (trans_stripped.startswith('"') and trans_stripped.endswith('"')) or \
                       (trans_stripped.startswith("'") and trans_stripped.endswith("'")):
                        text = trans_stripped[1:-1]
                        ctrl_elem.set("Text", text)
                    else:
                        # Create calculated field
                        field_name = f"calcField{len(self.calculated_fields) + 1}"
                        self.calculated_fields.append({
                            "name": field_name,
                            "expression": translated,
                            "original": expression
                        })
                        
                        # Bind to calculated field
                        bindings = etree.SubElement(ctrl_elem, "ExpressionBindings")
                        binding = etree.SubElement(bindings, "Item1")
                        binding.set("Ref", "0")
                        binding.set("Expression", f"[{field_name}]")
                        binding.set("PropertyName", "Text")
    
    def _is_invalid_expression(self, expr: str) -> bool:
        """Check if expression is invalid/metadata that should be skipped."""
        if not expr:
            return True
        
        # Skip multiline expressions (usually metadata)
        if '\n' in expr or '\r' in expr:
            return True
        
        # Skip expressions that look like property assignments
        skip_patterns = [
            'Top =', 'Left =', 'Width =', 'Height =',
            'Visible =', 'TabStop =', 'DataSource =',
            'Name =', '.NULL.', '= .F.', '= .T.',
            'Dataenvironment', 'PLATFORMLIST',
        ]
        for pattern in skip_patterns:
            if pattern.lower() in expr.lower():
                return True
        
        return False
    
    def _add_calculated_field(self, parent: etree.Element, field: dict, idx: int):
        """Add a calculated field definition."""
        field_elem = etree.SubElement(parent, "Item1")
        field_elem.set("Ref", str(100 + idx))
        field_elem.set("Name", field["name"])
        field_elem.set("Expression", field["expression"])
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize control name for DevExpress."""
        if not name:
            return f"label{self.control_count}"
        
        result = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(name))
        if result and result[0].isdigit():
            result = '_' + result
        
        return result or f"label{self.control_count}"
    
    def _save_analysis(self, output_folder: str, report_name: str):
        """Save conversion analysis to JSON."""
        analysis = {
            "report_name": report_name,
            "source_json": self.json_path,
            "controls_count": self.control_count,
            "calculated_fields": self.calculated_fields,
        }
        
        analysis_path = os.path.join(output_folder, f"{report_name}_analysis.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"Analysis: {analysis_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python converter_foxpro_json_v2.py <report.json> [output_folder]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    
    converter = FoxProJsonConverterV2(json_path)
    converter.convert(output_folder)


if __name__ == "__main__":
    main()
