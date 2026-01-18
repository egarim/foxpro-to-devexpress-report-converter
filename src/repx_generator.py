"""
DevExpress REPX Report Generator

Generates DevExpress Reports (.repx) from parsed FoxPro report data
"""

from lxml import etree
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime


@dataclass
class ReportObject:
    """Represents a report object (label, field, line, etc.)"""
    obj_type: str  # "Label", "Field", "Line", "Rectangle", "Picture"
    text: str = ""
    expression: str = ""
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 20
    font_name: str = "Arial"
    font_size: float = 10
    font_style: str = ""  # "Bold", "Italic", etc.
    visible_expr: str = ""
    band: str = "Detail"


@dataclass  
class ReportBand:
    """Represents a report band"""
    band_type: str  # "TopMargin", "PageHeader", "GroupHeader", "Detail", etc.
    height: float = 100
    objects: List[ReportObject] = None
    
    def __post_init__(self):
        if self.objects is None:
            self.objects = []


class REPXGenerator:
    """
    Generates DevExpress REPX format reports
    """
    
    # Band type mapping
    BAND_TYPES = {
        "TopMargin": "TopMarginBand",
        "ReportHeader": "ReportHeaderBand",
        "PageHeader": "PageHeaderBand",
        "GroupHeader": "GroupHeaderBand",
        "Detail": "DetailBand",
        "GroupFooter": "GroupFooterBand",
        "PageFooter": "PageFooterBand",
        "ReportFooter": "ReportFooterBand",
        "BottomMargin": "BottomMarginBand"
    }
    
    # Control type mapping
    CONTROL_TYPES = {
        "Label": "XRLabel",
        "Field": "XRLabel",
        "Line": "XRLine",
        "Rectangle": "XRPanel",
        "Picture": "XRPictureBox",
        "Table": "XRTable",
        "Subreport": "XRSubreport"
    }
    
    def __init__(self, report_name: str = "Report"):
        self.report_name = report_name
        self.bands: List[ReportBand] = []
        self.parameters: List[Dict] = []
        self.calculated_fields: List[Dict] = []
        self.data_source: Optional[Dict] = None
        
        # Report settings
        self.page_width = 850  # 8.5 inches in 1/100ths
        self.page_height = 1100  # 11 inches
        self.margins = {"left": 0, "right": 0, "top": 0, "bottom": 0}
        self.font_default = "Arial"
        self.font_size_default = 10
        
    def add_band(self, band: ReportBand):
        """Add a band to the report"""
        self.bands.append(band)
        
    def add_parameter(self, name: str, param_type: str = "String", 
                      description: str = "", visible: bool = True):
        """Add a report parameter"""
        self.parameters.append({
            "name": name,
            "type": param_type,
            "description": description,
            "visible": visible
        })
        
    def add_calculated_field(self, name: str, expression: str, 
                            field_type: str = "String", data_member: str = ""):
        """Add a calculated field"""
        self.calculated_fields.append({
            "name": name,
            "expression": expression,
            "type": field_type,
            "data_member": data_member
        })
        
    def set_data_source(self, source_type: str, connection_info: Dict):
        """Set the report data source"""
        self.data_source = {
            "type": source_type,
            **connection_info
        }
        
    def generate(self) -> str:
        """Generate the REPX XML content"""
        
        # Create root element
        root = etree.Element("XtraReportsLayoutSerializer")
        root.set("SerializerVersion", "24.2.10.0")
        root.set("Ref", "1")
        root.set("ControlType", f"DevExpress.XtraReports.UI.XtraReport, DevExpress.XtraReports.v24.2")
        root.set("Name", self.report_name)
        root.set("SnappingMode", "None")
        root.set("Margins", f"{self.margins['left']}, {self.margins['right']}, {self.margins['top']}, {self.margins['bottom']}")
        root.set("PageWidth", str(self.page_width))
        root.set("PageHeight", str(self.page_height))
        root.set("Version", "24.2")
        root.set("RequestParameters", "false")
        root.set("Font", f"{self.font_default}, {self.font_size_default}pt")
        
        # Add parameters
        if self.parameters:
            params_elem = etree.SubElement(root, "Parameters")
            for i, param in enumerate(self.parameters):
                item = etree.SubElement(params_elem, f"Item{i+1}")
                item.set("Ref", str(i + 3))
                item.set("Visible", str(param['visible']).lower())
                item.set("Description", param['description'])
                item.set("Name", param['name'])
        
        # Add calculated fields
        if self.calculated_fields:
            calc_elem = etree.SubElement(root, "CalculatedFields")
            for i, field in enumerate(self.calculated_fields):
                item = etree.SubElement(calc_elem, f"Item{i+1}")
                item.set("Ref", str(100 + i))
                item.set("Name", field['name'])
                item.set("FieldType", field['type'])
                item.set("Expression", field['expression'])
                if field.get('data_member'):
                    item.set("DataMember", field['data_member'])
        
        # Add bands
        bands_elem = etree.SubElement(root, "Bands")
        ref_counter = 200
        
        for i, band in enumerate(self.bands):
            band_elem = etree.SubElement(bands_elem, f"Item{i+1}")
            band_elem.set("Ref", str(ref_counter))
            ref_counter += 1
            
            control_type = self.BAND_TYPES.get(band.band_type, "DetailBand")
            band_elem.set("ControlType", control_type)
            band_elem.set("Name", f"{band.band_type.lower()}Band1")
            band_elem.set("HeightF", str(band.height))
            
            # Add controls to band
            if band.objects:
                controls_elem = etree.SubElement(band_elem, "Controls")
                for j, obj in enumerate(band.objects):
                    control = etree.SubElement(controls_elem, f"Item{j+1}")
                    control.set("Ref", str(ref_counter))
                    ref_counter += 1
                    
                    ctrl_type = self.CONTROL_TYPES.get(obj.obj_type, "XRLabel")
                    control.set("ControlType", ctrl_type)
                    control.set("Name", f"{ctrl_type.lower()}{ref_counter}")
                    
                    if obj.text:
                        control.set("Text", obj.text)
                    if obj.expression:
                        # Create expression binding
                        bindings = etree.SubElement(control, "ExpressionBindings")
                        binding = etree.SubElement(bindings, "Item1")
                        binding.set("Ref", str(ref_counter))
                        ref_counter += 1
                        binding.set("EventName", "BeforePrint")
                        binding.set("PropertyName", "Text")
                        binding.set("Expression", obj.expression)
                    
                    control.set("SizeF", f"{obj.width},{obj.height}")
                    control.set("LocationFloat", f"{obj.x},{obj.y}")
                    
                    if obj.font_name or obj.font_size:
                        font_str = obj.font_name or "Arial"
                        font_str += f", {obj.font_size}pt" if obj.font_size else ""
                        if obj.font_style:
                            font_str += f", style={obj.font_style}"
                        control.set("Font", font_str)
        
        # Generate XML string
        xml_declaration = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml_content = etree.tostring(root, pretty_print=True, encoding='unicode')
        
        return xml_declaration + xml_content
    
    def save(self, filepath: str):
        """Save the report to a file"""
        content = self.generate()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Report saved to: {filepath}")


def create_sample_report() -> REPXGenerator:
    """Create a sample report to demonstrate the generator"""
    
    generator = REPXGenerator("SampleBillReport")
    
    # Set page settings
    generator.page_width = 850
    generator.page_height = 1100
    generator.margins = {"left": 50, "right": 50, "top": 50, "bottom": 50}
    
    # Add parameters
    generator.add_parameter("prmBillDate", "DateTime", "Bill Date", visible=False)
    
    # Add calculated fields
    generator.add_calculated_field(
        name="CustomerFullAddress",
        expression="Trim([CustomerAdrs1]) + NewLine() + Trim([CustomerCity]) + ', ' + [CustomerStateAbv] + ' ' + [CustomerZipCode]",
        field_type="String"
    )
    
    generator.add_calculated_field(
        name="TotalDue",
        expression="[CurrentCharges] + [PreviousBalance] - [Payments]",
        field_type="Decimal"
    )
    
    # Create bands
    # Top Margin
    top_margin = ReportBand(band_type="TopMargin", height=50)
    generator.add_band(top_margin)
    
    # Page Header
    page_header = ReportBand(band_type="PageHeader", height=100)
    page_header.objects.append(ReportObject(
        obj_type="Label",
        text="GATEWAY SERVICES DISTRICT",
        x=300, y=10, width=200, height=25,
        font_name="Arial", font_size=14, font_style="Bold"
    ))
    page_header.objects.append(ReportObject(
        obj_type="Label",
        text="ACCOUNT NO.",
        x=50, y=50, width=100, height=20,
        font_name="Arial", font_size=10, font_style="Bold"
    ))
    page_header.objects.append(ReportObject(
        obj_type="Field",
        expression="[AcctNo]",
        x=150, y=50, width=150, height=20,
        font_name="Arial", font_size=10
    ))
    generator.add_band(page_header)
    
    # Detail Band
    detail = ReportBand(band_type="Detail", height=200)
    detail.objects.append(ReportObject(
        obj_type="Label",
        text="PREVIOUS BALANCE",
        x=50, y=10, width=120, height=20
    ))
    detail.objects.append(ReportObject(
        obj_type="Field",
        expression="FormatString('{0:C}', [PreviousBalance])",
        x=200, y=10, width=100, height=20
    ))
    detail.objects.append(ReportObject(
        obj_type="Label",
        text="CURRENT CHARGES",
        x=50, y=35, width=120, height=20
    ))
    detail.objects.append(ReportObject(
        obj_type="Field",
        expression="FormatString('{0:C}', [CurrentCharges])",
        x=200, y=35, width=100, height=20
    ))
    detail.objects.append(ReportObject(
        obj_type="Label",
        text="AMOUNT DUE",
        x=50, y=60, width=120, height=20,
        font_style="Bold"
    ))
    detail.objects.append(ReportObject(
        obj_type="Field",
        expression="FormatString('{0:C}', [TotalDue])",
        x=200, y=60, width=100, height=20,
        font_style="Bold"
    ))
    generator.add_band(detail)
    
    # Page Footer
    page_footer = ReportBand(band_type="PageFooter", height=50)
    page_footer.objects.append(ReportObject(
        obj_type="Label",
        text="Page",
        x=700, y=10, width=50, height=20
    ))
    generator.add_band(page_footer)
    
    # Bottom Margin
    bottom_margin = ReportBand(band_type="BottomMargin", height=50)
    generator.add_band(bottom_margin)
    
    return generator


if __name__ == "__main__":
    # Test the generator
    print("=" * 60)
    print("REPX Generator Test")
    print("=" * 60)
    
    generator = create_sample_report()
    
    # Save to file
    output_path = Path(__file__).parent.parent / "Sample_Generated.repx"
    generator.save(str(output_path))
    
    # Also print a preview
    print("\n📄 Generated XML Preview (first 2000 chars):")
    print("-" * 60)
    content = generator.generate()
    print(content[:2000])
    print("..." if len(content) > 2000 else "")
