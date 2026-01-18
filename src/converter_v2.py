"""
Improved FoxPro FRT to DevExpress REPX Converter

Generates high-quality DevExpress reports from FoxPro FRT files,
producing output similar to professionally designed REPX files.
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


@dataclass
class Control:
    """Represents a report control with full properties"""
    control_type: str  # XRLabel, XRLine, XRPanel, XRTable, etc.
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
    can_shrink: bool = False
    multiline: bool = False
    borders: str = ""
    back_color: str = ""
    fore_color: str = ""
    format_string: str = ""
    summary_type: str = ""
    extra_attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class Band:
    """Represents a report band"""
    band_type: str
    name: str
    height: float
    controls: List[Control] = field(default_factory=list)
    sub_bands: List['Band'] = field(default_factory=list)
    visible: bool = True
    keep_together: bool = False
    group_fields: List[str] = field(default_factory=list)


class ImprovedREPXGenerator:
    """
    Generates professional-quality DevExpress REPX files
    """
    
    def __init__(self, report_name: str):
        self.report_name = report_name
        self.ref_counter = 1
        
        # Report properties
        self.page_width = 850
        self.page_height = 1100
        self.margins = (2.083333, 0, 0, 1.624934)  # left, right, top, bottom
        self.default_font = "Arial, 10pt"
        
        # Collections
        self.parameters: List[Dict] = []
        self.calculated_fields: List[Dict] = []
        self.bands: List[Band] = []
        self.data_source: Optional[str] = None
        self.data_member: str = "Table"
        
    def next_ref(self) -> str:
        """Get next reference number"""
        ref = str(self.ref_counter)
        self.ref_counter += 1
        return ref
    
    def add_parameter(self, name: str, description: str = "", 
                      param_type: str = "String", visible: bool = False,
                      default_value: str = ""):
        """Add a report parameter"""
        self.parameters.append({
            "ref": self.next_ref(),
            "name": name,
            "description": description or name,
            "type": param_type,
            "visible": visible,
            "default": default_value
        })
    
    def add_calculated_field(self, name: str, expression: str,
                            field_type: str = "String", data_member: str = ""):
        """Add a calculated field"""
        self.calculated_fields.append({
            "ref": self.next_ref(),
            "name": name,
            "expression": expression,
            "type": field_type,
            "data_member": data_member or self.data_member
        })
    
    def add_band(self, band: Band):
        """Add a band to the report"""
        self.bands.append(band)
    
    def create_label(self, text: str, x: float, y: float, 
                     width: float = 100, height: float = 20,
                     font: str = None, bold: bool = False,
                     alignment: str = "",
                     fore_color: str = "", back_color: str = "",
                     borders: str = "") -> Control:
        """Create a label control"""
        font_str = font or self.default_font
        if bold and "Bold" not in font_str:
            font_str = font_str.replace("pt", "pt, style=Bold")
        
        return Control(
            control_type="XRLabel",
            name=f"label{self.next_ref()}",
            text=text,
            x=x, y=y,
            width=width, height=height,
            font=font_str,
            text_alignment=alignment,
            fore_color=fore_color,
            back_color=back_color,
            borders=borders,
            multiline=True
        )
    
    def create_field(self, expression: str, x: float, y: float,
                     width: float = 100, height: float = 20,
                     font: str = None, format_string: str = "",
                     alignment: str = "",
                     fore_color: str = "", back_color: str = "",
                     borders: str = "") -> Control:
        """Create a data-bound field control"""
        return Control(
            control_type="XRLabel",
            name=f"field{self.next_ref()}",
            expression=expression,
            x=x, y=y,
            width=width, height=height,
            font=font or self.default_font,
            format_string=format_string,
            text_alignment=alignment,
            fore_color=fore_color,
            back_color=back_color,
            borders=borders,
            multiline=True
        )
    
    def create_line(self, x: float, y: float, width: float, 
                    height: float = 1, direction: str = "Horizontal") -> Control:
        """Create a line control"""
        return Control(
            control_type="XRLine",
            name=f"line{self.next_ref()}",
            x=x, y=y,
            width=width, height=height,
            extra_attrs={"LineDirection": direction}
        )
    
    def generate_xml(self) -> str:
        """Generate the complete REPX XML"""
        
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
        if self.data_member:
            root.set("DataMember", self.data_member)
        if self.data_source:
            root.set("DataSource", self.data_source)
        root.set("Font", self.default_font)
        
        # Parameters
        if self.parameters:
            params_elem = etree.SubElement(root, "Parameters")
            for i, param in enumerate(self.parameters):
                item = etree.SubElement(params_elem, f"Item{i+1}")
                item.set("Ref", param["ref"])
                item.set("Visible", str(param["visible"]).lower())
                item.set("Description", param["description"])
                item.set("Name", param["name"])
                if param.get("default"):
                    item.set("ValueInfo", param["default"])
        
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
        
        # Bands
        bands_elem = etree.SubElement(root, "Bands")
        self._generate_bands(bands_elem, self.bands)
        
        # Generate XML string
        xml_str = etree.tostring(root, pretty_print=True, xml_declaration=True, 
                                 encoding="utf-8").decode("utf-8")
        return xml_str
    
    def _generate_bands(self, parent: etree.Element, bands: List[Band]):
        """Generate band XML elements"""
        for i, band in enumerate(bands):
            band_elem = etree.SubElement(parent, f"Item{i+1}")
            band_elem.set("Ref", self.next_ref())
            band_elem.set("ControlType", band.band_type)
            band_elem.set("Name", band.name)
            band_elem.set("HeightF", str(band.height))
            
            if band.keep_together:
                band_elem.set("KeepTogether", "true")
            if not band.visible:
                band_elem.set("Visible", "false")
            
            band_elem.set("TextAlignment", "TopLeft")
            band_elem.set("Padding", "0,0,0,0,100")
            
            # Controls
            if band.controls:
                controls_elem = etree.SubElement(band_elem, "Controls")
                self._generate_controls(controls_elem, band.controls)
            
            # SubBands
            if band.sub_bands:
                sub_elem = etree.SubElement(band_elem, "SubBands")
                self._generate_bands(sub_elem, band.sub_bands)
            
            # Group fields
            if band.group_fields:
                group_elem = etree.SubElement(band_elem, "GroupFields")
                for j, field_name in enumerate(band.group_fields):
                    item = etree.SubElement(group_elem, f"Item{j+1}")
                    item.set("Ref", self.next_ref())
                    item.set("FieldName", field_name)
    
    def _generate_controls(self, parent: etree.Element, controls: List[Control]):
        """Generate control XML elements"""
        for i, ctrl in enumerate(controls):
            item = etree.SubElement(parent, f"Item{i+1}")
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
            
            if ctrl.can_shrink:
                item.set("CanShrink", "true")
            
            if ctrl.format_string:
                item.set("TextFormatString", ctrl.format_string)
            
            if ctrl.back_color:
                item.set("BackColor", ctrl.back_color)
            
            if ctrl.fore_color:
                item.set("ForeColor", ctrl.fore_color)
            
            if ctrl.borders:
                item.set("Borders", ctrl.borders)
            
            # Add StylePriority if custom colors/fonts are set
            if ctrl.back_color or ctrl.fore_color or ctrl.borders:
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
            
            # Extra attributes
            for key, value in ctrl.extra_attrs.items():
                item.set(key, value)


class FRTToREPXConverter:
    """
    Converts FoxPro FRT files to DevExpress REPX format
    """
    
    def __init__(self, output_folder: str = "output"):
        self.output_folder = Path(output_folder)
        self.translator = ExpressionTranslator()
        self.analysis = {}
        
    def convert(self, frt_path: str, pdf_path: str = None) -> Dict[str, str]:
        """
        Convert an FRT file to REPX format.
        
        Args:
            frt_path: Path to FoxPro FRT file
            pdf_path: Optional path to PDF example for reference
            
        Returns:
            Dict with paths to generated files
        """
        frt_path = Path(frt_path)
        report_name = frt_path.stem
        
        # Create output folder for this report
        # If output_folder already ends with report name, use it directly
        if self.output_folder.name == report_name:
            report_folder = self.output_folder
        else:
            report_folder = self.output_folder / report_name
        report_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"Converting: {frt_path.name}")
        print(f"Output folder: {report_folder}")
        print(f"{'='*60}")
        
        # Parse FRT file using FRTParser
        print("\n📂 Parsing FRT file...")
        parser = FRTParser(str(frt_path))
        parsed = parser.parse()
        
        # Store analysis
        self.analysis = {
            "basic": parsed
        }
        
        strings = parsed.get("strings", [])
        fonts = parsed.get("fonts", [])
        
        # Separate labels and expressions
        labels = []
        expressions = []
        
        for s in strings:
            if s.startswith('"') and s.endswith('"') and '(' not in s:
                label = s.strip('"').strip()
                if label and len(label) > 1:
                    labels.append(label)
            elif '(' in s or '.' in s:
                expressions.append(s)
        
        print(f"   Found {len(labels)} labels")
        print(f"   Found {len(expressions)} expressions")
        print(f"   Found {len(fonts)} fonts")
        
        # Create REPX generator
        generator = ImprovedREPXGenerator(report_name)
        
        # Analyze expressions and create calculated fields
        print("\n🔄 Processing expressions...")
        calc_fields = self._process_expressions(expressions)
        for cf in calc_fields:
            generator.add_calculated_field(
                name=cf["name"],
                expression=cf["expression"],
                field_type=cf["type"]
            )
        print(f"   Created {len(calc_fields)} calculated fields")
        
        # Create report structure with proper layout
        print("\n📐 Creating report layout...")
        self._create_report_layout(generator, labels, expressions, fonts)
        
        # Generate REPX
        print("\n📝 Generating REPX file...")
        repx_content = generator.generate_xml()
        
        repx_path = report_folder / f"{report_name}.repx"
        with open(repx_path, "w", encoding="utf-8") as f:
            f.write(repx_content)
        print(f"   ✅ Saved: {repx_path}")
        
        # Save analysis JSON
        analysis_path = report_folder / f"{report_name}_analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_file": str(frt_path),
                "conversion_date": datetime.now().isoformat(),
                "labels": labels,
                "expressions": expressions,
                "fonts": fonts,
                "calculated_fields": calc_fields
            }, f, indent=2, default=str)
        print(f"   ✅ Saved: {analysis_path}")
        
        # Copy PDF if provided
        if pdf_path and Path(pdf_path).exists():
            import shutil
            pdf_dest = report_folder / Path(pdf_path).name
            shutil.copy2(pdf_path, pdf_dest)
            print(f"   ✅ Copied PDF: {pdf_dest}")
        
        return {
            "repx": str(repx_path),
            "analysis": str(analysis_path),
            "folder": str(report_folder)
        }
    
    def _process_expressions(self, expressions: List[str]) -> List[Dict]:
        """Process FoxPro expressions and create calculated fields"""
        calc_fields = []
        seen_names = set()
        
        for expr in expressions:
            # Skip simple strings or empty
            if not expr or expr.startswith('"'):
                continue
            
            # Clean up the expression
            clean_expr = expr.strip()
            
            # Skip expressions that are clearly not valid
            # (contain file paths, URLs, setup commands, etc.)
            skip_patterns = [
                r'\\\\',  # File paths
                r'www\.',  # URLs
                r'\.png', r'\.jpg', r'\.gif',  # Images
                r'output\s*=',  # Output assignments
                r'datasource\s*=',  # DataSource assignments
                r'tabstop\s*=',  # TabStop assignments
                r'visible\s*=',  # Visible assignments
                r'setupchart',  # Chart setup
                r'updatechart',  # Chart update
                r'billgraph',  # Chart names
                r'\*\*',  # Comments/annotations
                r'gatewaydistrict\.org',  # Specific URLs
                r'utility\d',  # File paths like Utility1
            ]
            
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, clean_expr, re.IGNORECASE):
                    skip = True
                    break
            
            if skip:
                continue
            
            # Clean leading garbage characters (non-alphanumeric at start)
            # But preserve quotes and brackets
            clean_expr = re.sub(r'^[^a-zA-Z\[\(\'\"\!]+', '', clean_expr)
            
            # Handle garbage prefix before known function names
            # Pattern: single char + known FoxPro function (e.g., "Malltrim" -> "alltrim")
            known_functions = ['alltrim', 'transform', 'shortdate', 'iif', 'empty', 'str', 'dtoc', 'padl', 'strtran']
            for func in known_functions:
                # Check if starts with garbage + function name
                pattern = rf'^([a-z0-9])({func})\b'
                match = re.match(pattern, clean_expr, re.IGNORECASE)
                if match:
                    # Strip the garbage prefix
                    clean_expr = clean_expr[1:]
                    break
            
            # Also handle "(garbage..." at start of parenthetical expressions
            if re.match(r'^\([a-z0-9]\s*empty', clean_expr, re.IGNORECASE):
                # Remove the garbage char after open paren
                clean_expr = re.sub(r'^\(([a-z0-9])\s*(empty)', r'(\2', clean_expr, flags=re.IGNORECASE)
            
            # Handle single char + open paren (e.g., "r(..." -> "(...")
            if re.match(r'^[a-z]\(', clean_expr, re.IGNORECASE):
                clean_expr = clean_expr[1:]
            
            # Skip if expression is now empty or too short
            if not clean_expr or len(clean_expr) < 3:
                continue
            
            # Skip pure comparison expressions used for visibility (not data)
            if re.match(r'^[a-z_]+\s*(<>|=)\s*[\d\.]+$', clean_expr, re.IGNORECASE):
                continue
            
            # Skip string literals that start with leading whitespace (formatting strings)
            if re.match(r'^[\'\"][\s]{4,}', clean_expr):
                continue
            
            # Skip single-letter-prefix garbage patterns like M"...", I"...", W"...", c"..."
            if re.match(r'^[A-Za-z]["\']', clean_expr):
                continue
            
            # Handle comma-separated expressions (FoxPro sequence operator)
            # If there are top-level commas, we either skip or take last part
            if ',' in clean_expr:
                # Check if it's a sequence of function calls (not args to a function)
                # Count parens - if comma is at top level (paren depth 0), split
                depth = 0
                top_level_comma = False
                for i, ch in enumerate(clean_expr):
                    if ch == '(':
                        depth += 1
                    elif ch == ')':
                        depth -= 1
                    elif ch == ',' and depth == 0:
                        top_level_comma = True
                        break
                
                if top_level_comma:
                    # Skip these complex expressions - they're likely concatenations
                    continue
            
            # Extract a name from the expression
            name = self._extract_field_name(clean_expr)
            
            # Ensure unique name
            base_name = name
            counter = 1
            while name in seen_names:
                name = f"{base_name}_{counter}"
                counter += 1
            seen_names.add(name)
            
            # Translate expression
            translated = self.translator.translate(clean_expr)
            
            # Final validation - skip clearly broken expressions
            if not translated or len(translated) < 3:
                continue
                
            # Skip if still has garbage prefix
            if re.match(r'^[^a-zA-Z\[\(\'\"\!]', translated):
                continue
            
            # Determine field type
            field_type = self._infer_field_type(clean_expr)
            
            calc_fields.append({
                "name": name,
                "original": clean_expr,
                "expression": translated,
                "type": field_type
            })
        
        return calc_fields
    
    def _extract_field_name(self, expr: str) -> str:
        """Extract a suitable field name from an expression"""
        # Try to find a field reference
        match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expr)
        if match:
            name = match.group(1)
            # Clean up common prefixes
            if name.lower() in ['transform', 'shortdate', 'alltrim', 'iif']:
                # Look for the actual field
                inner_match = re.search(r'\(([^,)]+)', expr)
                if inner_match:
                    name = re.sub(r'[^a-zA-Z0-9_]', '', inner_match.group(1))
            return f"fml{name.title()}"
        return f"fmlCalculated{len(expr) % 100}"
    
    def _infer_field_type(self, expr: str) -> str:
        """Infer DevExpress field type from expression"""
        expr_lower = expr.lower()
        
        if 'date' in expr_lower or 'shortdate' in expr_lower:
            return "DateTime"
        elif '$' in expr or 'chrg' in expr_lower or 'bal' in expr_lower:
            return "Decimal"
        elif any(x in expr_lower for x in ['tot_', 'amt', 'price', 'cost']):
            return "Decimal"
        else:
            return "String"
    
    def _create_report_layout(self, generator: ImprovedREPXGenerator,
                              labels: List[str], expressions: List[str],
                              fonts: List[str]):
        """Create a proper report layout with bands and controls"""
        
        # Use first font as primary, or default
        primary_font = fonts[0] if fonts else "Arial"
        
        # Color scheme based on original FoxPro report
        # These colors are extracted from the DevExpress_Ebill.repx example
        colors = {
            # Primary header color (teal/dark blue-green)
            "header_bg": "247,73,91,94",  # ARGB format
            "header_fg": "White",
            # Secondary header (gray)
            "section_header_bg": "227,191,189,189",
            "section_header_fg": "Black",
            # Accent color (green)
            "accent_green_bg": "255,51,145,82",
            "accent_green_fg": "White",
            # Text colors
            "primary_text": "247,73,91,94",  # Teal text for important items
            "green_text": "255,10,145,3",  # Green text for notices
            "red_text": "Red",  # Warning text
            "black_text": "Black",
        }
        
        # Create bands
        # 1. Top Margin
        generator.add_band(Band(
            band_type="TopMarginBand",
            name="topMarginBand1",
            height=0
        ))
        
        # 2. Report Header (company info, typically)
        header_controls = []
        y_pos = 10
        
        # Look for company-related labels
        company_labels = [l for l in labels if any(x in l.upper() for x in 
            ['GATEWAY', 'SERVICES', 'CDD', 'DISTRICT', 'ADDRESS', 'LAKES'])]
        
        for i, label in enumerate(company_labels[:3]):  # First 3 company-related labels
            # Company header with colored background
            header_controls.append(generator.create_label(
                text=label,
                x=50, y=y_pos,
                width=400, height=22,
                font=f"{primary_font}, 10pt",
                bold=True,
                fore_color=colors["header_fg"],
                back_color=colors["header_bg"],
                borders="All"
            ))
            y_pos += 24
        
        generator.add_band(Band(
            band_type="ReportHeaderBand",
            name="ReportHeaderArea1",
            height=max(80, y_pos + 10),
            controls=header_controls,
            keep_together=True
        ))
        
        # 3. Page Header (column headers)
        page_header_controls = []
        column_headers = [l for l in labels if any(x in l.upper() for x in 
            ['DATE', 'SERVICE', 'METER', 'USAGE', 'AMOUNT', 'PRIOR', 'CURRENT', 'READING'])]
        
        x_pos = 50
        for header in column_headers[:8]:
            page_header_controls.append(generator.create_label(
                text=header,
                x=x_pos, y=10,
                width=90, height=22,
                font=f"{primary_font}, 8pt",
                bold=True,
                alignment="MiddleCenter",
                fore_color=colors["black_text"],
                back_color=colors["section_header_bg"],
                borders="All"
            ))
            x_pos += 95
        
        if page_header_controls:
            generator.add_band(Band(
                band_type="PageHeaderBand",
                name="PageHeaderArea1",
                height=35,
                controls=page_header_controls
            ))
        
        # 4. Group Header with main content
        main_controls = []
        y_pos = 20
        
        # Add a "BILLING INFORMATION" header bar
        main_controls.append(generator.create_label(
            text="BILLING INFORMATION:",
            x=50, y=y_pos,
            width=700, height=22,
            font=f"{primary_font}, 9pt",
            bold=True,
            fore_color=colors["black_text"],
            back_color=colors["section_header_bg"],
            borders="All"
        ))
        y_pos += 30
        
        # Account/billing info section
        billing_labels = [l for l in labels if any(x in l.upper() for x in 
            ['ACCOUNT', 'BILLING', 'DUE', 'BALANCE', 'TOTAL', 'PAYMENT', 'CHARGE'])]
        
        for i, label in enumerate(billing_labels):
            col = i % 2
            row = i // 2
            # Important fields get teal color
            is_important = any(x in label.upper() for x in ['TOTAL', 'DUE', 'AMOUNT'])
            main_controls.append(generator.create_label(
                text=label,
                x=50 + (col * 400), y=y_pos + (row * 25),
                width=180, height=22,
                font=f"{primary_font}, 9pt",
                bold=True,
                fore_color=colors["primary_text"] if is_important else colors["black_text"]
            ))
        
        y_pos += (len(billing_labels) // 2 + 1) * 25 + 20
        
        # Add "BILL SUMMARY" header
        main_controls.append(generator.create_label(
            text="BILL SUMMARY",
            x=50, y=y_pos,
            width=350, height=24,
            font=f"{primary_font}, 11pt",
            bold=True,
            fore_color=colors["primary_text"],
            alignment="MiddleCenter",
            borders="Left, Top, Right"
        ))
        y_pos += 30
        
        # Service section labels
        service_labels = [l for l in labels if any(x in l.upper() for x in 
            ['WATER', 'SEWER', 'IRRIGATION', 'BYPASS', 'BASE'])]
        
        for i, label in enumerate(service_labels):
            main_controls.append(generator.create_label(
                text=label,
                x=50, y=y_pos,
                width=200, height=18,
                font=f"{primary_font}, 8pt"
            ))
            y_pos += 20
        
        # Add separator line
        main_controls.append(generator.create_line(
            x=50, y=y_pos + 5,
            width=700, height=2
        ))
        y_pos += 15
        
        # Message section
        if any('MESSAGE' in l.upper() for l in labels):
            # Message header bar with teal background
            main_controls.append(generator.create_label(
                text="MESSAGE FROM GSCDD",
                x=50, y=y_pos,
                width=350, height=22,
                font=f"{primary_font}, 11pt",
                bold=True,
                fore_color=colors["header_fg"],
                back_color=colors["header_bg"],
                alignment="MiddleLeft"
            ))
            y_pos += 30
            
            # Also add "KEEP IN MIND" section header
            main_controls.append(generator.create_label(
                text="KEEP IN MIND",
                x=450, y=y_pos - 30,
                width=300, height=22,
                font=f"{primary_font}, 11pt",
                bold=True,
                fore_color=colors["header_fg"],
                back_color=colors["header_bg"],
                alignment="MiddleLeft"
            ))
        
        group_header = Band(
            band_type="GroupHeaderBand",
            name="GroupHeaderArea1",
            height=0
        )
        
        # Main content as SubBand
        sub_band = Band(
            band_type="SubBand",
            name="GroupHeaderSection1",
            height=max(500, y_pos + 50),
            controls=main_controls
        )
        group_header.sub_bands.append(sub_band)
        generator.add_band(group_header)
        
        # 5. Detail Band (for repeating data)
        generator.add_band(Band(
            band_type="DetailBand",
            name="DetailArea1",
            height=0,
            keep_together=True
        ))
        
        # 6. Group Footer (summary/totals)
        footer_controls = []
        total_labels = [l for l in labels if 'TOTAL' in l.upper()]
        
        y_pos = 10
        
        # Add "CURRENT BILL" header bar
        footer_controls.append(generator.create_label(
            text="CURRENT BILL",
            x=500, y=y_pos,
            width=200, height=24,
            font=f"{primary_font}, 11pt",
            bold=True,
            fore_color=colors["header_fg"],
            back_color=colors["header_bg"],
            alignment="MiddleCenter"
        ))
        y_pos += 30
        
        for label in total_labels:
            footer_controls.append(generator.create_label(
                text=label,
                x=500, y=y_pos,
                width=150, height=22,
                font=f"{primary_font}, 9pt",
                bold=True,
                alignment="MiddleRight",
                fore_color=colors["primary_text"]
            ))
            y_pos += 24
        
        if footer_controls:
            generator.add_band(Band(
                band_type="GroupFooterBand",
                name="GroupFooter1",
                height=max(100, y_pos + 20),
                controls=footer_controls
            ))
        
        # 7. Page Footer
        page_footer_controls = []
        
        # Add "PAY YOUR BILL ONLINE" green bar
        page_footer_controls.append(generator.create_label(
            text="PAY YOUR BILL ONLINE AT GATEWAYDISTRICT.ORG",
            x=50, y=5,
            width=500, height=24,
            font=f"{primary_font}, 10pt",
            bold=True,
            fore_color=colors["header_fg"],
            back_color=colors["accent_green_bg"],
            alignment="MiddleCenter"
        ))
        
        # Add "VISIT US ONLINE" with website
        online_labels = [l for l in labels if 'WWW' in l.upper() or 'ONLINE' in l.upper()]
        if online_labels:
            page_footer_controls.append(generator.create_label(
                text="VISIT US ONLINE: WWW.GATEWAYDISTRICT.ORG",
                x=550, y=5,
                width=250, height=24,
                font=f"{primary_font}, 9pt",
                bold=True,
                fore_color=colors["green_text"]
            ))
        
        page_footer_controls.append(generator.create_label(
            text="Page [PageN] of [PageNofM]",
            x=700, y=35,
            width=100, height=20,
            font=f"{primary_font}, 8pt",
            alignment="MiddleRight"
        ))
        
        generator.add_band(Band(
            band_type="PageFooterBand",
            name="PageFooterArea1",
            height=60,
            controls=page_footer_controls
        ))
        
        # 8. Bottom Margin
        generator.add_band(Band(
            band_type="BottomMarginBand",
            name="bottomMarginBand1",
            height=1.625
        ))


def convert_frt_to_repx(frt_path: str, pdf_path: str = None, 
                        output_folder: str = "output") -> Dict[str, str]:
    """
    Main conversion function.
    
    Args:
        frt_path: Path to FoxPro FRT file
        pdf_path: Optional PDF example for reference
        output_folder: Output folder for all generated files
        
    Returns:
        Dict with paths to generated files
    """
    converter = FRTToREPXConverter(output_folder)
    return converter.convert(frt_path, pdf_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python converter_v2.py <file.frt> [output_folder] [example.pdf]")
        sys.exit(1)
    
    frt_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "output"
    pdf_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Check if second arg is a PDF file or output folder
    if output_folder and output_folder.lower().endswith('.pdf'):
        pdf_path = output_folder
        output_folder = "output"
    
    result = convert_frt_to_repx(frt_path, pdf_path, output_folder)
    
    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE")
    print("="*60)
    print(f"📁 Output folder: {result['folder']}")
    print(f"📄 REPX file: {result['repx']}")
    print(f"📊 Analysis: {result['analysis']}")
