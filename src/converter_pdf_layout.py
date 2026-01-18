"""
PDF-Based FoxPro FRT to DevExpress REPX Converter

Uses PDF layout extraction to create accurate REPX layouts
by extracting actual positions, fonts, and colors from PDF examples.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from lxml import etree
from dataclasses import dataclass, field

# Import existing modules
from frt_parser import FRTParser
from expression_translator import ExpressionTranslator, normalize_field_name
from pdf_layout_extractor import PDFLayoutExtractor


@dataclass
class REPXControl:
    """Represents a report control with full properties"""
    control_type: str
    name: str
    text: str = ""
    expression: str = ""
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 20
    font: str = "Arial, 10pt"
    text_alignment: str = ""
    padding: str = "2,2,0,0,100"
    visible: bool = True
    multiline: bool = True
    borders: str = ""
    back_color: str = ""
    fore_color: str = ""
    format_string: str = ""


class PDFBasedREPXGenerator:
    """
    Generates REPX files based on PDF layout extraction.
    Uses actual positions from PDF for accurate layout matching.
    """
    
    def __init__(self, report_name: str):
        self.report_name = report_name
        self.ref_counter = 1
        
        # Report properties
        self.page_width = 850
        self.page_height = 1100
        self.margins = (2.083333, 0, 0, 1.624934)
        self.default_font = "Arial, 10pt"
        
        # Collections
        self.calculated_fields: List[Dict] = []
        self.controls: List[REPXControl] = []
        self.data_member = "Table"
        
    def next_ref(self) -> str:
        ref = str(self.ref_counter)
        self.ref_counter += 1
        return ref
    
    def add_calculated_field(self, name: str, expression: str,
                            field_type: str = "String", data_member: str = ""):
        self.calculated_fields.append({
            "ref": self.next_ref(),
            "name": name,
            "expression": expression,
            "type": field_type,
            "data_member": data_member or self.data_member
        })
    
    def add_control(self, ctrl: REPXControl):
        self.controls.append(ctrl)
    
    def add_label(self, text: str, x: float, y: float,
                  width: float, height: float,
                  font: str = None, bold: bool = False,
                  fore_color: str = "", back_color: str = "",
                  borders: str = "", alignment: str = "") -> REPXControl:
        """Add a label control"""
        font_str = font or self.default_font
        if bold and "Bold" not in font_str:
            # Parse font and add bold style
            parts = font_str.split(',')
            if len(parts) >= 2:
                font_str = f"{parts[0].strip()}, {parts[1].strip()}, style=Bold"
            else:
                font_str += ", style=Bold"
        
        ctrl = REPXControl(
            control_type="XRLabel",
            name=f"label{self.next_ref()}",
            text=text,
            x=x, y=y,
            width=width, height=height,
            font=font_str,
            text_alignment=alignment,
            fore_color=fore_color,
            back_color=back_color,
            borders=borders
        )
        self.controls.append(ctrl)
        return ctrl
    
    def generate_xml(self) -> str:
        """Generate the REPX XML using PDF-based positions"""
        
        # Root element
        root = etree.Element("XtraReportsLayoutSerializer")
        root.set("SerializerVersion", "24.2.10.0")
        root.set("Ref", self.next_ref())
        root.set("ControlType", "DevExpress.XtraReports.UI.XtraReport, DevExpress.XtraReports.v24.2")
        root.set("Name", self.report_name)
        root.set("SnappingMode", "None")
        root.set("Margins", f"{self.margins[0]}, {self.margins[1]}, {self.margins[2]}, {self.margins[3]}")
        root.set("PageWidth", str(self.page_width))
        root.set("PageHeight", str(self.page_height))
        root.set("Version", "24.2")
        root.set("RequestParameters", "false")
        root.set("DataMember", self.data_member)
        root.set("Font", self.default_font)
        
        # Calculated fields
        if self.calculated_fields:
            calc_elem = etree.SubElement(root, "CalculatedFields")
            for i, field in enumerate(self.calculated_fields):
                item = etree.SubElement(calc_elem, f"Item{i+1}")
                item.set("Ref", field["ref"])
                item.set("Name", field["name"])
                item.set("FieldType", field["type"])
                item.set("Expression", field["expression"])
                if field.get("data_member"):
                    item.set("DataMember", field["data_member"])
        
        # Create bands structure
        bands_elem = etree.SubElement(root, "Bands")
        
        # Top Margin
        top_margin = etree.SubElement(bands_elem, "Item1")
        top_margin.set("Ref", self.next_ref())
        top_margin.set("ControlType", "TopMarginBand")
        top_margin.set("Name", "topMarginBand1")
        top_margin.set("HeightF", "0")
        top_margin.set("TextAlignment", "TopLeft")
        top_margin.set("Padding", "0,0,0,0,100")
        
        # Group Header with SubBand containing all controls
        group_header = etree.SubElement(bands_elem, "Item2")
        group_header.set("Ref", self.next_ref())
        group_header.set("ControlType", "GroupHeaderBand")
        group_header.set("Name", "GroupHeaderArea1")
        group_header.set("HeightF", "0")
        group_header.set("TextAlignment", "TopLeft")
        group_header.set("Padding", "0,0,0,0,100")
        
        # SubBand with all controls
        sub_bands = etree.SubElement(group_header, "SubBands")
        sub_band = etree.SubElement(sub_bands, "Item1")
        sub_band.set("Ref", self.next_ref())
        sub_band.set("ControlType", "SubBand")
        sub_band.set("Name", "GroupHeaderSection1")
        
        # Calculate max height from controls
        max_y = max((c.y + c.height for c in self.controls), default=100)
        sub_band.set("HeightF", str(max_y + 50))
        sub_band.set("TextAlignment", "TopLeft")
        sub_band.set("Padding", "0,0,0,0,100")
        
        # Add all controls
        if self.controls:
            controls_elem = etree.SubElement(sub_band, "Controls")
            for i, ctrl in enumerate(self.controls):
                self._add_control_xml(controls_elem, i + 1, ctrl)
        
        # Detail Band (empty, for data binding)
        detail = etree.SubElement(bands_elem, "Item3")
        detail.set("Ref", self.next_ref())
        detail.set("ControlType", "DetailBand")
        detail.set("Name", "DetailArea1")
        detail.set("HeightF", "0")
        detail.set("TextAlignment", "TopLeft")
        detail.set("Padding", "0,0,0,0,100")
        
        # Bottom Margin
        bottom_margin = etree.SubElement(bands_elem, "Item4")
        bottom_margin.set("Ref", self.next_ref())
        bottom_margin.set("ControlType", "BottomMarginBand")
        bottom_margin.set("Name", "bottomMarginBand1")
        bottom_margin.set("HeightF", "1.625")
        bottom_margin.set("TextAlignment", "TopLeft")
        bottom_margin.set("Padding", "0,0,0,0,100")
        
        # Generate XML string
        xml_str = etree.tostring(root, pretty_print=True, xml_declaration=True,
                                 encoding="utf-8").decode("utf-8")
        return xml_str
    
    def _add_control_xml(self, parent: etree.Element, index: int, ctrl: REPXControl):
        """Add a control element to the XML"""
        item = etree.SubElement(parent, f"Item{index}")
        item.set("Ref", self.next_ref())
        item.set("ControlType", ctrl.control_type)
        item.set("Name", ctrl.name)
        
        if ctrl.multiline:
            item.set("Multiline", "true")
        
        if ctrl.text:
            item.set("Text", ctrl.text)
        
        if ctrl.text_alignment:
            item.set("TextAlignment", ctrl.text_alignment)
        
        item.set("SizeF", f"{ctrl.width},{ctrl.height}")
        item.set("LocationFloat", f"{ctrl.x},{ctrl.y}")
        item.set("Font", ctrl.font)
        item.set("Padding", ctrl.padding)
        
        if ctrl.back_color:
            item.set("BackColor", ctrl.back_color)
        
        if ctrl.fore_color:
            item.set("ForeColor", ctrl.fore_color)
        
        if ctrl.borders:
            item.set("Borders", ctrl.borders)
        
        # Add StylePriority if custom styling
        if ctrl.back_color or ctrl.fore_color or ctrl.borders or ctrl.text_alignment:
            style_priority = etree.SubElement(item, "StylePriority")
            style_priority.set("Ref", self.next_ref())
            if ctrl.fore_color:
                style_priority.set("UseForeColor", "false")
            if ctrl.back_color:
                style_priority.set("UseBackColor", "false")
            if ctrl.borders:
                style_priority.set("UseBorders", "false")
            if ctrl.text_alignment:
                style_priority.set("UseTextAlignment", "false")
        
        # Expression binding
        if ctrl.expression:
            bindings = etree.SubElement(item, "ExpressionBindings")
            binding = etree.SubElement(bindings, "Item1")
            binding.set("Ref", self.next_ref())
            binding.set("EventName", "BeforePrint")
            binding.set("PropertyName", "Text")
            binding.set("Expression", ctrl.expression)


class PDFBasedConverter:
    """
    Converts FoxPro FRT files to REPX using PDF layout as reference.
    """
    
    def __init__(self, output_folder: str = "output"):
        self.output_folder = Path(output_folder)
        self.translator = ExpressionTranslator()
    
    def convert(self, frt_path: str, pdf_path: str) -> Dict[str, str]:
        """
        Convert FRT to REPX using PDF layout as reference.
        
        Args:
            frt_path: Path to FoxPro FRT file
            pdf_path: Path to PDF example (required for layout)
            
        Returns:
            Dict with paths to generated files
        """
        frt_path = Path(frt_path)
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF required for conversion: {pdf_path}")
        
        report_name = frt_path.stem
        
        # Create output folder
        if self.output_folder.name == report_name:
            report_folder = self.output_folder
        else:
            report_folder = self.output_folder / report_name
        report_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"PDF-Based REPX Conversion")
        print(f"{'='*60}")
        print(f"FRT: {frt_path.name}")
        print(f"PDF: {pdf_path.name}")
        print(f"Output: {report_folder}")
        
        # 1. Parse FRT for expressions
        print("\n📂 Parsing FRT file...")
        parser = FRTParser(str(frt_path))
        parsed = parser.parse()
        expressions = [s for s in parsed.get("strings", []) 
                      if '(' in s or '.' in s]
        
        # 2. Extract PDF layout
        print("\n📐 Extracting PDF layout...")
        extractor = PDFLayoutExtractor(str(pdf_path))
        pdf_data = extractor.extract_all()
        repx_layout = extractor.get_layout_for_repx()
        
        print(f"   Found {len(repx_layout['controls'])} text blocks")
        
        # 3. Create REPX generator
        generator = PDFBasedREPXGenerator(report_name)
        
        # 4. Process expressions into calculated fields
        print("\n🔄 Processing expressions...")
        calc_fields = self._process_expressions(expressions)
        for cf in calc_fields:
            generator.add_calculated_field(
                name=cf["name"],
                expression=cf["expression"],
                field_type=cf["type"]
            )
        print(f"   Created {len(calc_fields)} calculated fields")
        
        # 5. Add controls from PDF layout
        print("\n📍 Creating controls from PDF positions...")
        self._create_controls_from_pdf(generator, repx_layout)
        print(f"   Created {len(generator.controls)} controls")
        
        # 6. Generate REPX
        print("\n📝 Generating REPX file...")
        repx_content = generator.generate_xml()
        
        repx_path = report_folder / f"{report_name}.repx"
        with open(repx_path, "w", encoding="utf-8") as f:
            f.write(repx_content)
        print(f"   ✅ Saved: {repx_path}")
        
        # 7. Save layout JSON
        layout_path = report_folder / f"{report_name}_pdf_layout.json"
        with open(layout_path, "w", encoding="utf-8") as f:
            json.dump(repx_layout, f, indent=2)
        
        # 8. Save analysis
        analysis_path = report_folder / f"{report_name}_analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_file": str(frt_path),
                "pdf_source": str(pdf_path),
                "conversion_date": datetime.now().isoformat(),
                "control_count": len(generator.controls),
                "calculated_fields": calc_fields,
                "color_palette": pdf_data.get("color_palette", [])
            }, f, indent=2, default=str)
        
        return {
            "repx": str(repx_path),
            "layout": str(layout_path),
            "analysis": str(analysis_path),
            "folder": str(report_folder)
        }
    
    def _process_expressions(self, expressions: List[str]) -> List[Dict]:
        """Process FoxPro expressions into calculated fields"""
        calc_fields = []
        seen_names = set()
        
        skip_patterns = [
            r'\\\\', r'www\.', r'\.png', r'\.jpg', r'output\s*=',
            r'datasource\s*=', r'setupchart', r'updatechart', r'billgraph',
            r'\*\*', r'gatewaydistrict\.org', r'utility\d',
            r'tabstop\s*=', r'visible\s*=', r'enabled\s*=',  # Property assignments
            r'^\s*Top\s*=', r'^\s*Left\s*=', r'^\s*Width\s*=', r'^\s*Height\s*=',  # Position props
            r'cursor\s*=', r'name\s*=.*cursor',  # Cursor assignments
        ]
        
        for expr in expressions:
            if not expr or expr.startswith('"'):
                continue
            
            clean_expr = expr.strip()
            
            # Skip invalid patterns
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, clean_expr, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue
            
            # Clean garbage prefixes
            clean_expr = re.sub(r'^[^a-zA-Z\[\(\'\"\!]+', '', clean_expr)
            
            # Handle Malltrim -> alltrim etc.
            known_funcs = ['alltrim', 'transform', 'shortdate', 'iif', 'empty', 'str', 'dtoc', 'padl', 'trans']
            for func in known_funcs:
                pattern = rf'^([a-z0-9])({func})\b'
                if re.match(pattern, clean_expr, re.IGNORECASE):
                    clean_expr = clean_expr[1:]
                    break
            
            # Skip single letter + quote patterns
            if re.match(r'^[A-Za-z]["\']', clean_expr):
                continue
            
            if not clean_expr or len(clean_expr) < 3:
                continue
            
            # Extract name
            match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', clean_expr)
            name = f"fml{match.group(1).title()}" if match else f"fmlCalc{len(clean_expr) % 100}"
            
            # Ensure unique
            base_name = name
            counter = 1
            while name in seen_names:
                name = f"{base_name}_{counter}"
                counter += 1
            seen_names.add(name)
            
            # Translate
            translated = self.translator.translate(clean_expr)
            if not translated or len(translated) < 3:
                continue
            
            # Clean up the translated expression
            # Remove leading garbage like "r(" or single letters before parenthesis
            translated = re.sub(r'^[a-z]\(', '(', translated, flags=re.IGNORECASE)
            # Ensure balanced parentheses - if starts with extra close paren, skip
            if translated.startswith(')'):
                continue
            # Skip if has clearly broken pattern
            if re.match(r'^[^a-zA-Z\[\(\'\"\!]', translated):
                continue
            
            # Skip boolean expressions (visibility conditions, not display data)
            # These are comparisons that return true/false, not displayable values
            translated_lower = translated.lower()
            if ' and ' in translated_lower or ' or ' in translated_lower:
                # Check if it's purely a boolean condition (no IIF wrapper)
                if not translated_lower.startswith('iif('):
                    # Skip pure boolean expressions like "x <> 0 And y <> 0"
                    if '<>' in translated or '=' in translated or 'isnullorempty' in translated_lower:
                        continue
            
            # Skip standalone boolean check expressions like "IsNullOrEmpty(x)" or "x <> 0"
            if re.match(r'^(Not\s+)?IsNullOrEmpty\(', translated, re.IGNORECASE):
                continue
            if re.match(r'^[a-zA-Z_][\w]*\s*<>\s*[\d\.]+$', translated):
                continue
            if re.match(r'^\[[^\]]+\]\s*<>\s*[\d\.]+$', translated):
                continue
            
            # Skip expressions with top-level commas (FoxPro sequences, not valid in DevExpress)
            paren_depth = 0
            has_top_comma = False
            for ch in translated:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
                elif ch == ',' and paren_depth == 0:
                    has_top_comma = True
                    break
            if has_top_comma:
                continue
            
            # Determine type
            expr_lower = clean_expr.lower()
            if 'date' in expr_lower or 'shortdate' in expr_lower:
                field_type = "DateTime"
            elif '$' in clean_expr or 'chrg' in expr_lower or 'bal' in expr_lower:
                field_type = "Decimal"
            else:
                field_type = "String"
            
            calc_fields.append({
                "name": name,
                "original": clean_expr,
                "expression": translated,
                "type": field_type
            })
        
        return calc_fields
    
    def _create_controls_from_pdf(self, generator: PDFBasedREPXGenerator,
                                  layout: Dict[str, Any]):
        """Create REPX controls from PDF layout data"""
        
        # Define color mapping for styling
        # DevExpress ARGB format: "Alpha,R,G,B"
        
        # Known colors from PDF that need background styling
        header_colors = [
            ("255,71,109,126", "255,255,255,255"),  # Teal header
            ("255,79,89,78", "255,255,255,255"),     # Green header
            ("255,2,117,83", "255,255,255,255"),     # Accent green
        ]
        
        for ctrl_data in layout.get("controls", []):
            text = ctrl_data.get("text", "").strip()
            if not text or text == ",":  # Skip empty or single punctuation
                continue
            
            x = ctrl_data.get("x", 0)
            y = ctrl_data.get("y", 0)
            width = max(ctrl_data.get("width", 50), len(text) * 6)
            height = max(ctrl_data.get("height", 20), 18)
            font = ctrl_data.get("font", "Arial, 10pt")
            fore_color = ctrl_data.get("fore_color", "")
            is_bold = ctrl_data.get("is_bold", False)
            
            # Determine if this needs special styling
            back_color = ""
            borders = ""
            alignment = ""
            
            # Check text content for special styling
            text_upper = text.upper()
            
            # Header row styling (colored backgrounds)
            if any(x in text_upper for x in ["SERVICE DATE", "METER READING", "BILLING DATE", "SERVICE ADDRESS"]):
                # Section headers get gray background
                back_color = "227,191,189,189"
                fore_color = ""  # Black text
                borders = "All"
                alignment = "MiddleCenter"
            elif any(x in text_upper for x in ["BILL SUMMARY", "CURRENT BILL"]):
                # Important headers
                fore_color = "255,71,109,126"  # Teal
                alignment = "MiddleCenter"
                borders = "Left, Top, Right"
            elif any(x in text_upper for x in ["TOTAL", "AMOUNT DUE"]):
                # Totals
                is_bold = True
                if "DUE" in text_upper:
                    fore_color = "255,71,109,126"  # Teal for important
            elif "PAY" in text_upper and "ONLINE" in text_upper:
                # Call to action
                back_color = "255,51,145,82"  # Green
                fore_color = "255,255,255,255"  # White
                alignment = "MiddleCenter"
            
            # Skip white-on-white text (invisible)
            if fore_color == "255,255,255,255" and not back_color:
                continue
            
            # Add the control
            generator.add_label(
                text=text,
                x=x, y=y,
                width=width, height=height,
                font=font,
                bold=is_bold,
                fore_color=fore_color,
                back_color=back_color,
                borders=borders,
                alignment=alignment
            )


def convert_with_pdf_layout(frt_path: str, pdf_path: str,
                           output_folder: str = "output") -> Dict[str, str]:
    """
    Main conversion function using PDF layout.
    
    Args:
        frt_path: Path to FoxPro FRT file
        pdf_path: Path to PDF example
        output_folder: Output folder
        
    Returns:
        Dict with paths to generated files
    """
    converter = PDFBasedConverter(output_folder)
    return converter.convert(frt_path, pdf_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python converter_pdf_layout.py <file.frt> <example.pdf> [output_folder]")
        sys.exit(1)
    
    frt_path = sys.argv[1]
    pdf_path = sys.argv[2]
    output_folder = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    result = convert_with_pdf_layout(frt_path, pdf_path, output_folder)
    
    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE")
    print("="*60)
    print(f"📁 Output folder: {result['folder']}")
    print(f"📄 REPX file: {result['repx']}")
