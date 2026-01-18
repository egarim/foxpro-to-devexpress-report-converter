"""
FoxPro FRT to DevExpress REPX Converter

Main conversion tool that combines:
1. FRT Parser - Extract data from FoxPro report files
2. Expression Translator - Convert FoxPro expressions to DevExpress
3. REPX Generator - Generate DevExpress report XML
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from frt_parser import FRTParser, analyze_frt_deep
from expression_translator import ExpressionTranslator
from repx_generator import REPXGenerator, ReportBand, ReportObject


@dataclass
class FRTElement:
    """Parsed element from FRT file"""
    element_type: str  # "label", "field", "line", "rectangle", "picture"
    text: str = ""
    expression: str = ""
    visibility_condition: str = ""
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 20
    font_name: str = "Arial"
    font_size: float = 10
    font_bold: bool = False
    font_italic: bool = False
    band_type: str = "Detail"


class FRTToREPXConverter:
    """
    Main converter class for FoxPro FRT to DevExpress REPX
    """
    
    def __init__(self):
        self.translator = ExpressionTranslator()
        self.elements: List[FRTElement] = []
        self.fonts: List[str] = []
        self.procedures: List[Dict] = []
        self.analysis: Dict = {}
        
    def parse_frt(self, frt_path: str) -> Dict:
        """Parse the FRT file and extract all components"""
        
        print(f"📂 Parsing FRT file: {frt_path}")
        
        # Use our custom parser
        parser = FRTParser(frt_path)
        result = parser.parse()
        
        # Also do deep analysis
        deep_result = analyze_frt_deep(frt_path)
        
        self.analysis = {
            "basic": result,
            "deep": deep_result
        }
        
        # Extract components
        self.fonts = result.get("fonts", [])
        self.procedures = result.get("procedures", [])
        
        # Parse elements from strings
        self._extract_elements_from_strings(result.get("strings", []))
        
        return self.analysis
    
    def _extract_elements_from_strings(self, strings: List[str]):
        """Extract report elements from parsed strings"""
        
        # Patterns to identify different element types
        for s in strings:
            # Skip short strings
            if len(s) < 5:
                continue
            
            # Check for label text (starts with quote)
            if s.startswith('"') and not 'TRANSFORM' in s.upper():
                text = s.strip('"')
                if len(text) > 2:
                    self.elements.append(FRTElement(
                        element_type="label",
                        text=text
                    ))
            
            # Check for field expressions
            elif 'TRANSFORM' in s.upper():
                # Extract the field/expression
                self.elements.append(FRTElement(
                    element_type="field",
                    expression=s
                ))
            
            elif 'SHORTDATE' in s.upper():
                self.elements.append(FRTElement(
                    element_type="field",
                    expression=s
                ))
            
            elif '.note' in s.lower() or 'alltrim(' in s.lower():
                self.elements.append(FRTElement(
                    element_type="field",
                    expression=s
                ))
    
    def convert(self, output_name: str = "ConvertedReport") -> REPXGenerator:
        """Convert parsed FRT data to REPX generator"""
        
        print(f"🔄 Converting to DevExpress format...")
        
        generator = REPXGenerator(output_name)
        
        # Set up page settings (standard letter size)
        generator.page_width = 850
        generator.page_height = 1100
        generator.margins = {"left": 20, "right": 0, "top": 0, "bottom": 16}
        
        # Add standard bands
        top_margin = ReportBand(band_type="TopMargin", height=0)
        generator.add_band(top_margin)
        
        page_header = ReportBand(band_type="PageHeader", height=100)
        generator.add_band(page_header)
        
        detail = ReportBand(band_type="Detail", height=500)
        
        # Add labels
        y_pos = 10
        for element in self.elements:
            if element.element_type == "label":
                obj = ReportObject(
                    obj_type="Label",
                    text=element.text,
                    x=50,
                    y=y_pos,
                    width=400,
                    height=20,
                    font_name=self.fonts[0] if self.fonts else "Arial",
                    font_size=10
                )
                detail.objects.append(obj)
                y_pos += 25
        
        # Add fields
        for element in self.elements:
            if element.element_type == "field":
                # Translate expression
                dx_expr = self.translator.translate(element.expression)
                
                obj = ReportObject(
                    obj_type="Field",
                    expression=dx_expr,
                    x=50,
                    y=y_pos,
                    width=200,
                    height=20,
                    font_name=self.fonts[0] if self.fonts else "Arial",
                    font_size=10
                )
                detail.objects.append(obj)
                y_pos += 25
        
        generator.add_band(detail)
        
        page_footer = ReportBand(band_type="PageFooter", height=50)
        generator.add_band(page_footer)
        
        bottom_margin = ReportBand(band_type="BottomMargin", height=16)
        generator.add_band(bottom_margin)
        
        return generator
    
    def extract_calculated_fields(self) -> List[Dict]:
        """Extract calculated fields from FRT analysis"""
        
        calc_fields = []
        
        # Look for TRANSFORM expressions which typically become calculated fields
        for element in self.elements:
            if element.element_type == "field" and element.expression:
                # Create a calculated field
                name = self._generate_field_name(element.expression)
                dx_expr = self.translator.translate(element.expression)
                
                calc_fields.append({
                    "name": name,
                    "expression": dx_expr,
                    "original": element.expression
                })
        
        return calc_fields
    
    def _generate_field_name(self, expression: str) -> str:
        """Generate a calculated field name from expression"""
        
        # Extract field names from expression
        # e.g., TRANSFORM(tot_cur, ...) -> fmlTotCur
        
        match = re.search(r'\(([a-zA-Z_][a-zA-Z0-9_]*)', expression)
        if match:
            field = match.group(1)
            # Convert to PascalCase with fml prefix
            pascal = ''.join(word.title() for word in field.split('_'))
            return f"fml{pascal}"
        
        return f"fmlCalculated{len(self.elements)}"
    
    def generate_mapping_report(self) -> str:
        """Generate a report showing FoxPro to DevExpress mappings"""
        
        report = []
        report.append("=" * 80)
        report.append("FoxPro to DevExpress Conversion Report")
        report.append("=" * 80)
        
        report.append(f"\n📊 Statistics:")
        report.append(f"   - Total elements found: {len(self.elements)}")
        report.append(f"   - Labels: {sum(1 for e in self.elements if e.element_type == 'label')}")
        report.append(f"   - Fields: {sum(1 for e in self.elements if e.element_type == 'field')}")
        report.append(f"   - Fonts: {len(self.fonts)}")
        
        report.append(f"\n🎨 Fonts:")
        for font in self.fonts:
            report.append(f"   - {font}")
        
        report.append(f"\n📝 Labels:")
        for element in self.elements:
            if element.element_type == "label":
                report.append(f"   - {element.text[:60]}...")
        
        report.append(f"\n🔢 Field Expressions (FoxPro → DevExpress):")
        for element in self.elements:
            if element.element_type == "field":
                original = element.expression[:50]
                translated = self.translator.translate(element.expression)[:50]
                report.append(f"   FoxPro:    {original}...")
                report.append(f"   DevExpress: {translated}...")
                report.append("")
        
        return "\n".join(report)


def convert_frt_to_repx(frt_path: str, output_path: str = None) -> str:
    """
    Main conversion function
    
    Args:
        frt_path: Path to the FoxPro FRT file
        output_path: Path for the output REPX file (optional)
        
    Returns:
        Path to the generated REPX file
    """
    
    frt_path = Path(frt_path)
    
    if output_path is None:
        output_path = frt_path.with_suffix('.repx')
    else:
        output_path = Path(output_path)
    
    print("=" * 80)
    print("FoxPro FRT to DevExpress REPX Converter")
    print("=" * 80)
    
    # Initialize converter
    converter = FRTToREPXConverter()
    
    # Parse FRT
    converter.parse_frt(str(frt_path))
    
    # Generate mapping report
    mapping_report = converter.generate_mapping_report()
    print(mapping_report)
    
    # Convert to REPX
    generator = converter.convert(frt_path.stem)
    
    # Add calculated fields
    calc_fields = converter.extract_calculated_fields()
    for field in calc_fields:
        generator.add_calculated_field(
            name=field['name'],
            expression=field['expression'],
            field_type="String"  # Default to string, could be smarter
        )
    
    # Save the report
    generator.save(str(output_path))
    
    # Also save analysis for debugging
    analysis_path = frt_path.with_suffix('.analysis.json')
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(converter.analysis, f, indent=2, default=str)
    print(f"📊 Analysis saved to: {analysis_path}")
    
    return str(output_path)


if __name__ == "__main__":
    import sys
    
    # Default to the Ebill FRT in the workspace
    if len(sys.argv) > 1:
        frt_file = sys.argv[1]
    else:
        frt_file = Path(__file__).parent.parent / "FoxPro_Ebill.frt"
    
    output_file = Path(__file__).parent.parent / "Converted_Ebill.repx"
    
    result = convert_frt_to_repx(str(frt_file), str(output_file))
    print(f"\n✅ Conversion complete: {result}")
