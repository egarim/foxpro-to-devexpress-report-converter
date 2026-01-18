"""
converter_foxpro_json.py

Converts FoxPro report JSON (exported by export_frt_to_json.prg) to DevExpress REPX format.

This is the "hybrid approach" - using FoxPro runtime for accurate FRX extraction
and Python for REPX generation.

Usage:
    python converter_foxpro_json.py <report.json> [output_folder]
"""

import json
import os
import sys
from pathlib import Path
from lxml import etree
from expression_translator import ExpressionTranslator


class FoxProJsonConverter:
    """Converts FoxPro-exported JSON to DevExpress REPX format."""
    
    # FoxPro Report Units to DevExpress conversion
    # FoxPro: 10,000 FRU = 1 inch
    # DevExpress: 100 units = 1 inch
    # Scale factor: 10000 / 100 = 100
    FRU_SCALE = 100
    
    # Band type mapping: FoxPro band type -> DevExpress band class
    BAND_MAPPING = {
        "Title": "ReportHeaderBand",
        "Page Header": "PageHeaderBand",
        "Column Header": "PageHeaderBand",  # Map to page header
        "Group Header": "GroupHeaderBand",
        "Detail": "DetailBand",
        "Group Footer": "GroupFooterBand",
        "Column Footer": "PageFooterBand",  # Map to page footer
        "Page Footer": "PageFooterBand",
        "Summary": "ReportFooterBand",
    }
    
    # ObjType mapping: FoxPro objtype -> DevExpress control type
    OBJTYPE_MAPPING = {
        5: "XRLabel",      # Label (static text)
        6: "XRLine",       # Line
        7: "XRShape",      # Rectangle/Box
        8: "XRLabel",      # Field/Expression (bound label)
        17: "XRPictureBox", # Picture
    }
    
    # Alignment mapping
    ALIGNMENT_MAPPING = {
        0: "Near",    # Left
        1: "Far",     # Right
        2: "Center",  # Center
    }
    
    def __init__(self, json_path: str):
        """Initialize converter with JSON file path."""
        self.json_path = json_path
        self.translator = ExpressionTranslator()
        self.calculated_fields = []
        self.control_count = 0
        
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def convert(self, output_folder: str = None) -> str:
        """
        Convert JSON to REPX format.
        
        Args:
            output_folder: Output folder path. If None, uses same folder as JSON.
            
        Returns:
            Path to generated REPX file.
        """
        # Determine output path
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
        
        # Page settings
        page_info = self.data.get("page", {})
        width_fru = page_info.get("width_fru", 85000)
        height_fru = page_info.get("height_fru", 110000)
        
        root.set("PageWidth", str(int(width_fru / self.FRU_SCALE)))
        root.set("PageHeight", str(int(height_fru / self.FRU_SCALE)))
        root.set("Margins", "100, 100, 100, 100")  # Default margins
        root.set("PaperKind", "Letter")
        root.set("SnapGridSize", "25")
        
        # Add bands
        bands_elem = etree.SubElement(root, "Bands")
        self._add_bands(bands_elem)
        
        # Add calculated fields
        if self.calculated_fields:
            calc_elem = etree.SubElement(root, "CalculatedFields")
            for field in self.calculated_fields:
                self._add_calculated_field(calc_elem, field)
        
        # Version info
        etree.SubElement(root, "Version").text = "24.2"
        
        return root
    
    def _add_bands(self, parent: etree.Element):
        """Add all bands and their controls."""
        bands_data = self.data.get("bands", [])
        controls_data = self.data.get("controls", [])
        
        # Create bands
        band_refs = {}
        ref_counter = 2  # Start after root ref
        
        for band in bands_data:
            band_type = band.get("band_type", "")
            dx_band_type = self.BAND_MAPPING.get(band_type)
            
            if not dx_band_type:
                continue
            
            # Create band element
            band_elem = etree.SubElement(parent, "Item1")
            band_elem.set("Ref", str(ref_counter))
            band_elem.set("ControlType", f"DevExpress.XtraReports.UI.{dx_band_type}, DevExpress.XtraReports.v24.2")
            band_elem.set("Name", dx_band_type.replace("Band", "1"))
            
            # Band height
            height_fru = band.get("height_fru", 2500)
            height_dx = int(height_fru / self.FRU_SCALE)
            band_elem.set("HeightF", str(height_dx))
            
            band_refs[band_type] = (band_elem, ref_counter)
            ref_counter += 1
        
        # If no bands were created, create default Detail band
        if not band_refs:
            band_elem = etree.SubElement(parent, "Item1")
            band_elem.set("Ref", str(ref_counter))
            band_elem.set("ControlType", "DevExpress.XtraReports.UI.DetailBand, DevExpress.XtraReports.v24.2")
            band_elem.set("Name", "Detail1")
            band_elem.set("HeightF", "100")
            band_refs["Detail"] = (band_elem, ref_counter)
            ref_counter += 1
        
        # Add controls to bands
        # Group controls by their vertical position to determine band
        for control in controls_data:
            band_elem = self._get_band_for_control(control, band_refs, bands_data)
            if band_elem is not None:
                self._add_control(band_elem[0], control, ref_counter)
                ref_counter += 1
    
    def _get_band_for_control(self, control: dict, band_refs: dict, bands: list) -> tuple:
        """Determine which band a control belongs to based on its position."""
        # Try to match control to band based on vertical position
        # This is a simplified approach - FoxPro stores band association differently
        
        top_fru = control.get("position", {}).get("top_fru", 0)
        
        # Calculate cumulative band heights to find which band this control is in
        cumulative_height = 0
        for band in bands:
            band_type = band.get("band_type", "")
            band_height = band.get("height_fru", 0)
            
            if top_fru >= cumulative_height and top_fru < cumulative_height + band_height:
                if band_type in band_refs:
                    return band_refs[band_type]
            
            cumulative_height += band_height
        
        # Default to Detail band
        return band_refs.get("Detail") or list(band_refs.values())[0] if band_refs else None
    
    def _add_control(self, band_elem: etree.Element, control: dict, ref: int):
        """Add a control to a band."""
        objtype = control.get("objtype", 8)
        dx_control_type = self.OBJTYPE_MAPPING.get(objtype, "XRLabel")
        
        # Create Controls element if not exists
        controls_elem = band_elem.find("Controls")
        if controls_elem is None:
            controls_elem = etree.SubElement(band_elem, "Controls")
        
        # Create control element
        ctrl_elem = etree.SubElement(controls_elem, "Item1")
        ctrl_elem.set("Ref", str(ref))
        ctrl_elem.set("ControlType", f"DevExpress.XtraReports.UI.{dx_control_type}, DevExpress.XtraReports.v24.2")
        
        control_name = control.get("name", f"Control{self.control_count}")
        ctrl_elem.set("Name", self._sanitize_name(control_name))
        
        # Position and size
        pos = control.get("position", {})
        left = int(pos.get("left_fru", 0) / self.FRU_SCALE)
        top = int(pos.get("top_fru", 0) / self.FRU_SCALE)
        width = int(pos.get("width_fru", 1000) / self.FRU_SCALE)
        height = int(pos.get("height_fru", 250) / self.FRU_SCALE)
        
        # Adjust top position relative to band
        # TODO: Calculate relative position within band
        
        ctrl_elem.set("LocationFloat", f"{left}, {top}")
        ctrl_elem.set("SizeF", f"{max(width, 10)}, {max(height, 15)}")
        
        # Expression/Text
        expression = control.get("expression", "")
        if expression and objtype == 8:  # Field
            # Translate FoxPro expression to DevExpress
            translated = self.translator.translate(expression)
            
            if translated:
                # Create calculated field
                field_name = f"calcField{len(self.calculated_fields) + 1}"
                self.calculated_fields.append({
                    "name": field_name,
                    "expression": translated,
                    "original": expression
                })
                
                # Bind control to calculated field
                etree.SubElement(ctrl_elem, "ExpressionBindings").text = (
                    f'<Item1 Ref="0" Expression="[{field_name}]" PropertyName="Text" />'
                )
        elif expression:
            # Static text (Label)
            # Remove quotes from string literals
            text = expression.strip('"\'')
            ctrl_elem.set("Text", text)
        
        # Font
        font_info = control.get("font", {})
        font_name = font_info.get("name", "Arial")
        font_size = font_info.get("size", 10)
        font_bold = font_info.get("bold", False)
        font_italic = font_info.get("italic", False)
        
        font_style = []
        if font_bold:
            font_style.append("Bold")
        if font_italic:
            font_style.append("Italic")
        
        style_str = ", ".join(font_style) if font_style else "Regular"
        ctrl_elem.set("Font", f"{font_name}, {font_size}pt, style={style_str}")
        
        # Colors
        colors = control.get("colors", {})
        pen_rgb = colors.get("pen_rgb", [0, 0, 0])
        fill_rgb = colors.get("fill_rgb", [255, 255, 255])
        
        if pen_rgb != [0, 0, 0]:
            ctrl_elem.set("ForeColor", f"{pen_rgb[0]}, {pen_rgb[1]}, {pen_rgb[2]}")
        
        if fill_rgb != [255, 255, 255]:
            ctrl_elem.set("BackColor", f"{fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}")
        
        # Alignment
        alignment = control.get("alignment", 0)
        dx_alignment = self.ALIGNMENT_MAPPING.get(alignment, "Near")
        ctrl_elem.set("TextAlignment", f"Top{dx_alignment}")
        
        self.control_count += 1
    
    def _add_calculated_field(self, parent: etree.Element, field: dict):
        """Add a calculated field definition."""
        field_elem = etree.SubElement(parent, "Item1")
        field_elem.set("Ref", str(100 + self.calculated_fields.index(field)))
        field_elem.set("Name", field["name"])
        field_elem.set("Expression", field["expression"])
        
        # Add comment with original expression
        field_elem.set("Description", f"Original: {field['original']}")
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize control name for DevExpress."""
        # Remove invalid characters
        result = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        # Ensure starts with letter or underscore
        if result and result[0].isdigit():
            result = '_' + result
        
        return result or f"Control{self.control_count}"
    
    def _save_analysis(self, output_folder: str, report_name: str):
        """Save conversion analysis to JSON."""
        analysis = {
            "report_name": report_name,
            "source_json": self.json_path,
            "controls_count": self.control_count,
            "calculated_fields": self.calculated_fields,
            "bands": self.data.get("bands", []),
            "conversion_notes": [
                "Converted using hybrid FoxPro+Python approach",
                "Positions converted from FRU (10000/inch) to DevExpress (100/inch)",
                "Expressions translated using expression_translator.py"
            ]
        }
        
        analysis_path = os.path.join(output_folder, f"{report_name}_analysis.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"Analysis: {analysis_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python converter_foxpro_json.py <report.json> [output_folder]")
        print()
        print("Arguments:")
        print("  report.json    JSON file exported by FoxPro export_frt_to_json.prg")
        print("  output_folder  Output folder for REPX (optional)")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    
    converter = FoxProJsonConverter(json_path)
    converter.convert(output_folder)


if __name__ == "__main__":
    main()
