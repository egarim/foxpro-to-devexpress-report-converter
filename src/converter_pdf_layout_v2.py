"""
PDF-Based FoxPro FRT to DevExpress REPX Converter - Version 2

Enhanced version with:
1. Table detection and XRTable generation
2. Better row grouping and alignment
3. Improved section organization
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from lxml import etree
from dataclasses import dataclass, field
from collections import defaultdict

# Import existing modules
from frt_parser import FRTParser
from expression_translator import ExpressionTranslator
from pdf_layout_extractor import PDFLayoutExtractor


@dataclass
class TextItem:
    """Represents a text item from PDF"""
    text: str
    x: float
    y: float
    width: float
    height: float
    font: str = "Arial, 8pt"
    fore_color: str = ""
    is_bold: bool = False
    page: int = 0


@dataclass
class RowGroup:
    """Group of items on the same row (similar Y position)"""
    y: float
    height: float
    items: List[TextItem] = field(default_factory=list)
    
    def add_item(self, item: TextItem):
        self.items.append(item)
        self.items.sort(key=lambda i: i.x)  # Keep sorted by X
    
    @property
    def min_x(self) -> float:
        return min(i.x for i in self.items) if self.items else 0
    
    @property
    def max_x(self) -> float:
        return max(i.x + i.width for i in self.items) if self.items else 0
    
    @property
    def total_width(self) -> float:
        return self.max_x - self.min_x


class TableDetector:
    """Detects table-like structures in the extracted layout"""
    
    def __init__(self, y_tolerance: float = 5.0, x_tolerance: float = 20.0):
        self.y_tolerance = y_tolerance  # Items within this Y range are on same row
        self.x_tolerance = x_tolerance  # Gap between columns
    
    def group_into_rows(self, items: List[TextItem]) -> List[RowGroup]:
        """Group text items into rows based on Y position"""
        if not items:
            return []
        
        # Sort by Y position
        sorted_items = sorted(items, key=lambda i: i.y)
        
        rows = []
        current_row = None
        
        for item in sorted_items:
            if current_row is None:
                current_row = RowGroup(y=item.y, height=item.height)
                current_row.add_item(item)
            elif abs(item.y - current_row.y) <= self.y_tolerance:
                # Same row
                current_row.add_item(item)
            else:
                # New row
                rows.append(current_row)
                current_row = RowGroup(y=item.y, height=item.height)
                current_row.add_item(item)
        
        if current_row and current_row.items:
            rows.append(current_row)
        
        return rows
    
    def detect_tables(self, rows: List[RowGroup]) -> List[List[RowGroup]]:
        """Detect table structures from consecutive rows with similar column patterns"""
        if len(rows) < 2:
            return []
        
        tables = []
        current_table = []
        
        for i, row in enumerate(rows):
            if len(row.items) >= 3:  # Table rows usually have multiple columns
                if not current_table:
                    current_table.append(row)
                else:
                    # Check if columns roughly align with previous row
                    prev_row = current_table[-1]
                    if self._columns_align(prev_row, row):
                        current_table.append(row)
                    else:
                        if len(current_table) >= 2:
                            tables.append(current_table)
                        current_table = [row]
            else:
                if len(current_table) >= 2:
                    tables.append(current_table)
                current_table = []
        
        if len(current_table) >= 2:
            tables.append(current_table)
        
        return tables
    
    def _columns_align(self, row1: RowGroup, row2: RowGroup) -> bool:
        """Check if two rows have similar column positions"""
        if abs(len(row1.items) - len(row2.items)) > 2:
            return False
        
        # Compare X positions of items
        x1 = [i.x for i in row1.items]
        x2 = [i.x for i in row2.items]
        
        matches = 0
        for x in x1:
            for other_x in x2:
                if abs(x - other_x) < self.x_tolerance:
                    matches += 1
                    break
        
        return matches >= min(len(x1), len(x2)) * 0.5


class EnhancedREPXGenerator:
    """
    Enhanced REPX generator with table support.
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
        self.controls_xml: List[etree.Element] = []
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
    
    def add_label(self, index: int, text: str, x: float, y: float,
                  width: float, height: float,
                  font: str = None, bold: bool = False,
                  fore_color: str = "", back_color: str = "",
                  borders: str = "", alignment: str = ""):
        """Add a label control and return the XML element"""
        item = etree.Element(f"Item{index}")
        item.set("Ref", self.next_ref())
        item.set("ControlType", "XRLabel")
        item.set("Name", f"label{index}")
        item.set("Multiline", "true")
        item.set("Text", text)
        
        if alignment:
            item.set("TextAlignment", alignment)
        
        item.set("SizeF", f"{width},{height}")
        item.set("LocationFloat", f"{x},{y}")
        
        font_str = font or self.default_font
        if bold and "Bold" not in font_str:
            parts = font_str.split(',')
            if len(parts) >= 2:
                font_str = f"{parts[0].strip()}, {parts[1].strip()}, style=Bold"
        item.set("Font", font_str)
        item.set("Padding", "2,2,0,0,100")
        
        if fore_color:
            item.set("ForeColor", fore_color)
        
        if back_color:
            item.set("BackColor", back_color)
        
        if borders:
            item.set("Borders", borders)
        
        # Add StylePriority if custom styling
        if back_color or fore_color or borders or alignment:
            style = etree.SubElement(item, "StylePriority")
            style.set("Ref", self.next_ref())
            if fore_color:
                style.set("UseForeColor", "false")
            if back_color:
                style.set("UseBackColor", "false")
            if borders:
                style.set("UseBorders", "false")
            if alignment:
                style.set("UseTextAlignment", "false")
        
        self.controls_xml.append(item)
        return item
    
    def add_table(self, index: int, rows: List[RowGroup], 
                  x: float, y: float, width: float):
        """Add an XRTable control from row groups"""
        table = etree.Element(f"Item{index}")
        table.set("Ref", self.next_ref())
        table.set("ControlType", "XRTable")
        table.set("Name", f"table{index}")
        
        # Calculate table dimensions
        total_height = sum(r.height for r in rows) if rows else 25 * len(rows)
        total_height = max(total_height, len(rows) * 20)
        
        table.set("SizeF", f"{width},{total_height}")
        table.set("LocationFloat", f"{x},{y}")
        table.set("Font", "Arial, 8pt")
        table.set("Padding", "2,2,0,0,100")
        
        # Create rows container
        rows_container = etree.SubElement(table, "Rows")
        
        for row_idx, row in enumerate(rows):
            row_elem = etree.SubElement(rows_container, f"Item{row_idx + 1}")
            row_elem.set("Ref", self.next_ref())
            row_elem.set("ControlType", "XRTableRow")
            row_elem.set("Name", f"tableRow{index}_{row_idx}")
            row_elem.set("Weight", "1")
            
            # Create cells container
            cells_container = etree.SubElement(row_elem, "Cells")
            
            # Calculate column widths based on item positions
            items = row.items
            for cell_idx, item in enumerate(items):
                cell = etree.SubElement(cells_container, f"Item{cell_idx + 1}")
                cell.set("Ref", self.next_ref())
                cell.set("ControlType", "XRTableCell")
                cell.set("Name", f"cell{index}_{row_idx}_{cell_idx}")
                
                # Calculate weight based on width proportion
                cell_width = item.width if cell_idx < len(items) - 1 else width - item.x + x
                weight = max(1, cell_width / 100)
                cell.set("Weight", str(round(weight, 2)))
                cell.set("Multiline", "true")
                cell.set("Text", item.text)
                
                if item.font:
                    cell.set("Font", item.font)
                
                if item.fore_color:
                    cell.set("ForeColor", item.fore_color)
        
        self.controls_xml.append(table)
        return table
    
    def generate_xml(self) -> str:
        """Generate the full REPX XML"""
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
            calc_fields = etree.SubElement(root, "CalculatedFields")
            for i, cf in enumerate(self.calculated_fields, 1):
                item = etree.SubElement(calc_fields, f"Item{i}")
                item.set("Ref", cf["ref"])
                item.set("Name", cf["name"])
                item.set("FieldType", cf["type"])
                item.set("Expression", cf["expression"])
                if cf.get("data_member"):
                    item.set("DataMember", cf["data_member"])
        
        # Bands
        bands = etree.SubElement(root, "Bands")
        
        # Top margin
        top_margin = etree.SubElement(bands, "Item1")
        top_margin.set("Ref", self.next_ref())
        top_margin.set("ControlType", "TopMarginBand")
        top_margin.set("Name", "topMarginBand1")
        top_margin.set("HeightF", "0")
        
        # Detail band with all controls
        detail = etree.SubElement(bands, "Item2")
        detail.set("Ref", self.next_ref())
        detail.set("ControlType", "DetailBand")
        detail.set("Name", "detailBand1")
        detail.set("HeightF", str(self.page_height))
        detail.set("TextAlignment", "TopLeft")
        detail.set("Padding", "0,0,0,0,100")
        
        # Add controls
        controls = etree.SubElement(detail, "Controls")
        for ctrl in self.controls_xml:
            controls.append(ctrl)
        
        # Bottom margin
        bottom_margin = etree.SubElement(bands, "Item3")
        bottom_margin.set("Ref", self.next_ref())
        bottom_margin.set("ControlType", "BottomMarginBand")
        bottom_margin.set("Name", "bottomMarginBand1")
        bottom_margin.set("HeightF", "0")
        bottom_margin.set("TextAlignment", "TopLeft")
        bottom_margin.set("Padding", "0,0,0,0,100")
        
        xml_str = etree.tostring(root, pretty_print=True, xml_declaration=True,
                                 encoding="utf-8").decode("utf-8")
        return xml_str


class PDFBasedConverterV2:
    """
    Enhanced converter with table detection and better layout.
    """
    
    def __init__(self, output_folder: str = "output"):
        self.output_folder = Path(output_folder)
        self.translator = ExpressionTranslator()
        self.table_detector = TableDetector()
    
    def convert(self, frt_path: str, pdf_path: str) -> Dict[str, str]:
        """Convert FRT to REPX using PDF layout with table detection"""
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
        print(f"PDF-Based REPX Conversion V2 (Enhanced)")
        print(f"{'='*60}")
        print(f"FRT: {frt_path.name}")
        print(f"PDF: {pdf_path.name}")
        
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
        
        # 3. Convert to TextItem objects
        items = []
        for ctrl in repx_layout.get("controls", []):
            text = ctrl.get("text", "").strip()
            if not text or text == ",":
                continue
            items.append(TextItem(
                text=text,
                x=ctrl.get("x", 0),
                y=ctrl.get("y", 0),
                width=max(ctrl.get("width", 50), len(text) * 6),
                height=max(ctrl.get("height", 18), 18),
                font=ctrl.get("font", "Arial, 8pt"),
                fore_color=ctrl.get("fore_color", ""),
                is_bold=ctrl.get("is_bold", False),
                page=ctrl.get("page", 0)
            ))
        
        # 4. Group into rows
        print("\n📊 Analyzing layout structure...")
        rows = self.table_detector.group_into_rows(items)
        print(f"   Found {len(rows)} rows")
        
        # 5. Detect tables
        tables = self.table_detector.detect_tables(rows)
        print(f"   Detected {len(tables)} table structures")
        
        # 6. Create generator
        generator = EnhancedREPXGenerator(report_name)
        
        # 7. Process expressions
        print("\n🔄 Processing expressions...")
        calc_fields = self._process_expressions(expressions)
        for cf in calc_fields:
            generator.add_calculated_field(
                name=cf["name"],
                expression=cf["expression"],
                field_type=cf["type"]
            )
        print(f"   Created {len(calc_fields)} calculated fields")
        
        # 8. Create controls
        print("\n📍 Creating controls...")
        self._create_controls(generator, rows, tables)
        print(f"   Created {len(generator.controls_xml)} controls")
        
        # 9. Generate REPX
        print("\n📝 Generating REPX file...")
        repx_content = generator.generate_xml()
        
        repx_path = report_folder / f"{report_name}.repx"
        with open(repx_path, "w", encoding="utf-8") as f:
            f.write(repx_content)
        print(f"   ✅ Saved: {repx_path}")
        
        # Save layout JSON
        layout_path = report_folder / f"{report_name}_pdf_layout.json"
        with open(layout_path, "w", encoding="utf-8") as f:
            json.dump(repx_layout, f, indent=2)
        
        return {
            "repx": str(repx_path),
            "layout": str(layout_path),
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
            r'tabstop\s*=', r'visible\s*=', r'enabled\s*=',
            r'^\s*Top\s*=', r'^\s*Left\s*=', r'^\s*Width\s*=', r'^\s*Height\s*=',
            r'cursor\s*=', r'name\s*=.*cursor',
        ]
        
        for expr in expressions:
            if not expr or expr.startswith('"'):
                continue
            
            clean_expr = expr.strip()
            
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, clean_expr, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue
            
            clean_expr = re.sub(r'^[^a-zA-Z\[\(\'\"\!]+', '', clean_expr)
            
            known_funcs = ['alltrim', 'transform', 'shortdate', 'iif', 'empty', 'str', 'dtoc', 'padl', 'trans']
            for func in known_funcs:
                pattern = rf'^([a-z0-9])({func})\b'
                if re.match(pattern, clean_expr, re.IGNORECASE):
                    clean_expr = clean_expr[1:]
                    break
            
            if re.match(r'^[A-Za-z]["\']', clean_expr):
                continue
            
            if not clean_expr or len(clean_expr) < 3:
                continue
            
            match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', clean_expr)
            name = f"fml{match.group(1).title()}" if match else f"fmlCalc{len(clean_expr) % 100}"
            
            base_name = name
            counter = 1
            while name in seen_names:
                name = f"{base_name}_{counter}"
                counter += 1
            seen_names.add(name)
            
            translated = self.translator.translate(clean_expr)
            if not translated or len(translated) < 3:
                continue
            
            translated = re.sub(r'^[a-z]\(', '(', translated, flags=re.IGNORECASE)
            if translated.startswith(')'):
                continue
            if re.match(r'^[^a-zA-Z\[\(\'\"\!]', translated):
                continue
            
            translated_lower = translated.lower()
            if ' and ' in translated_lower or ' or ' in translated_lower:
                if not translated_lower.startswith('iif('):
                    if '<>' in translated or '=' in translated or 'isnullorempty' in translated_lower:
                        continue
            
            if re.match(r'^(Not\s+)?IsNullOrEmpty\(', translated, re.IGNORECASE):
                continue
            if re.match(r'^[a-zA-Z_][\w]*\s*<>\s*[\d\.]+$', translated):
                continue
            if re.match(r'^\[[^\]]+\]\s*<>\s*[\d\.]+$', translated):
                continue
            
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
    
    def _create_controls(self, generator: EnhancedREPXGenerator,
                        rows: List[RowGroup],
                        tables: List[List[RowGroup]]):
        """Create REPX controls from rows, using tables where detected"""
        
        # Identify which rows are part of tables
        table_rows = set()
        for table in tables:
            for row in table:
                table_rows.add(id(row))
        
        control_idx = 1
        
        # Process each row
        for row in rows:
            if id(row) in table_rows:
                continue  # Will be handled as part of table
            
            # Create individual labels for non-table rows
            for item in row.items:
                # Determine styling
                back_color, fore_color, borders, alignment, is_bold = self._determine_styling(item)
                
                generator.add_label(
                    index=control_idx,
                    text=item.text,
                    x=item.x, y=item.y,
                    width=item.width, height=item.height,
                    font=item.font,
                    bold=is_bold or item.is_bold,
                    fore_color=fore_color or item.fore_color,
                    back_color=back_color,
                    borders=borders,
                    alignment=alignment
                )
                control_idx += 1
        
        # Process tables
        for table_rows_list in tables:
            if not table_rows_list:
                continue
            
            # Calculate table position and size
            x = min(row.min_x for row in table_rows_list)
            y = min(row.y for row in table_rows_list)
            width = max(row.total_width for row in table_rows_list)
            
            generator.add_table(
                index=control_idx,
                rows=table_rows_list,
                x=x, y=y, width=width
            )
            control_idx += 1
    
    def _determine_styling(self, item: TextItem) -> Tuple[str, str, str, str, bool]:
        """Determine styling based on text content"""
        text_upper = item.text.upper()
        
        back_color = ""
        fore_color = ""
        borders = ""
        alignment = ""
        is_bold = False
        
        # Section headers
        if any(x in text_upper for x in ["SERVICE DATE", "METER READING", "BILLING DATE", "SERVICE ADDRESS"]):
            back_color = "227,191,189,189"
            borders = "All"
            alignment = "MiddleCenter"
        
        # Important headers
        elif any(x in text_upper for x in ["BILL SUMMARY", "CURRENT BILL"]):
            fore_color = "255,71,109,126"
            alignment = "MiddleCenter"
        
        # Totals
        elif "TOTAL" in text_upper or "AMOUNT DUE" in text_upper:
            is_bold = True
            if "DUE" in text_upper:
                fore_color = "255,71,109,126"
        
        # Call to action
        elif "PAY" in text_upper and "ONLINE" in text_upper:
            back_color = "255,51,145,82"
            fore_color = "255,255,255,255"
            alignment = "MiddleCenter"
        
        # Skip white-on-white
        if fore_color == "255,255,255,255" and not back_color:
            fore_color = ""
        
        return back_color, fore_color, borders, alignment, is_bold


def convert_with_pdf_layout_v2(frt_path: str, pdf_path: str,
                               output_folder: str = "output") -> Dict[str, str]:
    """Enhanced conversion with table detection"""
    converter = PDFBasedConverterV2(output_folder)
    return converter.convert(frt_path, pdf_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python converter_pdf_layout_v2.py <file.frt> <example.pdf> [output_folder]")
        sys.exit(1)
    
    frt_path = sys.argv[1]
    pdf_path = sys.argv[2]
    output_folder = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    result = convert_with_pdf_layout_v2(frt_path, pdf_path, output_folder)
    
    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE")
    print("="*60)
    print(f"📁 Output folder: {result['folder']}")
    print(f"📄 REPX file: {result['repx']}")
