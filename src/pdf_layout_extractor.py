"""
PDF Layout Extractor for REPX Conversion

Extracts text positions, fonts, colors, and layout from PDF files
to enable accurate REPX report generation.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
import json
import re


@dataclass
class TextBlock:
    """Represents a text block from the PDF"""
    text: str
    x: float  # Left position
    y: float  # Top position
    width: float
    height: float
    font_name: str
    font_size: float
    color: Tuple[float, float, float]  # RGB 0-1
    is_bold: bool = False
    is_italic: bool = False
    page: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "font": self.font_name,
            "font_size": round(self.font_size, 1),
            "color_rgb": [round(c, 3) for c in self.color],
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "page": self.page
        }


@dataclass
class PDFSection:
    """Represents a logical section in the PDF"""
    section_type: str  # header, billing_info, summary, message, footer, etc.
    bounds: Tuple[float, float, float, float]  # x, y, width, height
    blocks: List[TextBlock] = field(default_factory=list)
    background_color: Optional[Tuple[float, float, float]] = None


class PDFLayoutExtractor:
    """
    Extracts layout information from PDF files for REPX conversion.
    
    PDF coordinates: 72 DPI, origin at bottom-left
    DevExpress: typically 100 units/inch, origin at top-left
    """
    
    # Page dimensions (standard US Letter)
    PDF_PAGE_WIDTH = 612  # 8.5" * 72
    PDF_PAGE_HEIGHT = 792  # 11" * 72
    
    # DevExpress page dimensions 
    DX_PAGE_WIDTH = 850  # as seen in example REPX
    DX_PAGE_HEIGHT = 1100
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(str(pdf_path))
        self.blocks: List[TextBlock] = []
        self.sections: List[PDFSection] = []
        self.page_info: Dict = {}
        
    def extract_all(self) -> Dict[str, Any]:
        """Extract all layout information from the PDF"""
        result = {
            "source": str(self.pdf_path),
            "page_count": len(self.doc),
            "pages": []
        }
        
        for page_num in range(len(self.doc)):
            page_data = self._extract_page(page_num)
            result["pages"].append(page_data)
        
        # Analyze sections
        result["sections"] = self._identify_sections()
        
        # Get color palette
        result["color_palette"] = self._extract_color_palette()
        
        return result
    
    def _extract_page(self, page_num: int) -> Dict:
        """Extract layout from a single page"""
        page = self.doc[page_num]
        
        page_data = {
            "page_number": page_num + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "text_blocks": [],
            "lines": [],
            "rectangles": []
        }
        
        # Extract text with detailed information
        dict_blocks = page.get_text("dict")
        
        for block in dict_blocks.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        
                        # Convert PDF coordinates to top-left origin
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        x = bbox[0]
                        y = bbox[1]  # Already from top in PyMuPDF
                        width = bbox[2] - bbox[0]
                        height = bbox[3] - bbox[1]
                        
                        # Extract font info
                        font = span.get("font", "Arial")
                        size = span.get("size", 10)
                        color = span.get("color", 0)  # Integer color
                        
                        # Convert integer color to RGB
                        if isinstance(color, int):
                            r = ((color >> 16) & 0xFF) / 255
                            g = ((color >> 8) & 0xFF) / 255
                            b = (color & 0xFF) / 255
                        else:
                            r, g, b = 0, 0, 0
                        
                        # Check for bold/italic in font name
                        is_bold = "Bold" in font or "bold" in font
                        is_italic = "Italic" in font or "italic" in font or "Oblique" in font
                        
                        block = TextBlock(
                            text=text,
                            x=x,
                            y=y,
                            width=width,
                            height=height,
                            font_name=font,
                            font_size=size,
                            color=(r, g, b),
                            is_bold=is_bold,
                            is_italic=is_italic,
                            page=page_num
                        )
                        
                        self.blocks.append(block)
                        page_data["text_blocks"].append(block.to_dict())
        
        # Extract drawings (lines, rectangles for colored boxes)
        drawings = page.get_drawings()
        for item in drawings:
            if item.get("type") == "l":  # Line
                page_data["lines"].append({
                    "from": item.get("pts", [[0, 0], [0, 0]])[0],
                    "to": item.get("pts", [[0, 0], [0, 0]])[-1],
                    "color": item.get("color", [0, 0, 0])
                })
            elif item.get("type") == "re":  # Rectangle
                rect = item.get("rect", [0, 0, 0, 0])
                page_data["rectangles"].append({
                    "x": rect[0],
                    "y": rect[1],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1],
                    "fill": item.get("fill"),
                    "stroke": item.get("color")
                })
        
        return page_data
    
    def _identify_sections(self) -> List[Dict]:
        """Identify logical sections based on layout patterns"""
        sections = []
        
        if not self.blocks:
            return sections
        
        # Sort blocks by Y position (top to bottom)
        sorted_blocks = sorted(self.blocks, key=lambda b: (b.page, b.y))
        
        # Group blocks into horizontal bands
        current_band = []
        current_y = 0
        bands = []
        
        for block in sorted_blocks:
            if not current_band or abs(block.y - current_y) < 15:  # Same band
                current_band.append(block)
                current_y = block.y if not current_band else current_y
            else:
                if current_band:
                    bands.append(current_band)
                current_band = [block]
                current_y = block.y
        
        if current_band:
            bands.append(current_band)
        
        # Identify section types based on content
        for band in bands:
            text_content = " ".join(b.text for b in band).upper()
            
            section_type = "content"
            if any(x in text_content for x in ["GATEWAY", "SERVICES", "CDD"]):
                section_type = "company_header"
            elif any(x in text_content for x in ["BILLING INFORMATION", "ACCOUNT"]):
                section_type = "billing_info"
            elif any(x in text_content for x in ["BILL SUMMARY", "SUMMARY"]):
                section_type = "summary"
            elif any(x in text_content for x in ["MESSAGE", "KEEP IN MIND"]):
                section_type = "message"
            elif any(x in text_content for x in ["USAGE HISTORY", "GRAPH"]):
                section_type = "usage_chart"
            elif any(x in text_content for x in ["PAY BY", "DETACH", "RETURN"]):
                section_type = "payment_slip"
            elif any(x in text_content for x in ["SERVICE DATE", "METER"]):
                section_type = "meter_readings"
            
            # Calculate bounds
            min_x = min(b.x for b in band)
            min_y = min(b.y for b in band)
            max_x = max(b.x + b.width for b in band)
            max_y = max(b.y + b.height for b in band)
            
            sections.append({
                "type": section_type,
                "bounds": {
                    "x": round(min_x, 2),
                    "y": round(min_y, 2),
                    "width": round(max_x - min_x, 2),
                    "height": round(max_y - min_y, 2)
                },
                "block_count": len(band),
                "text_preview": text_content[:100]
            })
        
        return sections
    
    def _extract_color_palette(self) -> List[Dict]:
        """Extract unique colors used in the document"""
        colors = {}
        
        for block in self.blocks:
            r, g, b = block.color
            # Convert to 8-bit and create hex
            r8, g8, b8 = int(r * 255), int(g * 255), int(b * 255)
            hex_color = f"#{r8:02x}{g8:02x}{b8:02x}"
            
            if hex_color not in colors:
                colors[hex_color] = {
                    "hex": hex_color,
                    "rgb": (r8, g8, b8),
                    "argb_dx": f"255,{r8},{g8},{b8}",  # DevExpress ARGB format
                    "count": 0
                }
            colors[hex_color]["count"] += 1
        
        # Sort by usage
        return sorted(colors.values(), key=lambda c: c["count"], reverse=True)
    
    def pdf_to_dx_coords(self, x: float, y: float, 
                          width: float, height: float) -> Tuple[float, float, float, float]:
        """
        Convert PDF coordinates to DevExpress coordinates.
        
        PDF: 72 DPI, origin at top-left (in PyMuPDF)
        DevExpress: ~100 DPI equivalent, origin at top-left
        """
        # Scale factor from PDF to DevExpress page size
        scale_x = self.DX_PAGE_WIDTH / self.PDF_PAGE_WIDTH
        scale_y = self.DX_PAGE_HEIGHT / self.PDF_PAGE_HEIGHT
        
        dx_x = x * scale_x
        dx_y = y * scale_y
        dx_width = width * scale_x
        dx_height = height * scale_y
        
        return (round(dx_x, 2), round(dx_y, 2), 
                round(dx_width, 2), round(dx_height, 2))
    
    def get_blocks_in_region(self, x: float, y: float, 
                             width: float, height: float) -> List[TextBlock]:
        """Get all text blocks within a specified region"""
        result = []
        for block in self.blocks:
            # Check if block center is within region
            cx = block.x + block.width / 2
            cy = block.y + block.height / 2
            if x <= cx <= x + width and y <= cy <= y + height:
                result.append(block)
        return result
    
    def get_layout_for_repx(self) -> Dict[str, Any]:
        """
        Get layout information structured for REPX generation.
        Returns controls with DevExpress-compatible coordinates.
        """
        layout = {
            "page_width": self.DX_PAGE_WIDTH,
            "page_height": self.DX_PAGE_HEIGHT,
            "controls": [],
            "table_regions": [],
            "header_region": None,
            "footer_region": None
        }
        
        for block in self.blocks:
            # Convert coordinates
            dx_x, dx_y, dx_w, dx_h = self.pdf_to_dx_coords(
                block.x, block.y, block.width, block.height
            )
            
            # Map font to DevExpress format
            base_font = self._map_font(block.font_name)
            font_size = max(6, min(24, block.font_size))  # Clamp size
            
            font_str = f"{base_font}, {font_size:.0f}pt"
            if block.is_bold:
                font_str += ", style=Bold"
            if block.is_italic:
                font_str += ", style=Italic" if not block.is_bold else "|Italic"
            
            # Convert color to DevExpress format
            r8, g8, b8 = (int(c * 255) for c in block.color)
            fore_color = f"255,{r8},{g8},{b8}"
            
            control = {
                "text": block.text,
                "x": dx_x,
                "y": dx_y,
                "width": max(dx_w, len(block.text) * 6),  # Ensure minimum width
                "height": max(dx_h, font_size * 1.5),
                "font": font_str,
                "fore_color": fore_color if (r8, g8, b8) != (0, 0, 0) else "",
                "is_bold": block.is_bold,
                "page": block.page
            }
            
            layout["controls"].append(control)
        
        # Identify table regions (areas with aligned columns)
        layout["table_regions"] = self._identify_tables()
        
        return layout
    
    def _map_font(self, pdf_font: str) -> str:
        """Map PDF font name to standard font"""
        font_lower = pdf_font.lower()
        
        if "arial" in font_lower:
            return "Arial"
        elif "times" in font_lower:
            return "Times New Roman"
        elif "courier" in font_lower:
            return "Courier New"
        elif "calibri" in font_lower:
            return "Calibri"
        elif "ocr" in font_lower:
            return "OCR A Extended"
        else:
            return "Arial"  # Default
    
    def _identify_tables(self) -> List[Dict]:
        """Identify table-like regions based on column alignment"""
        tables = []
        
        # Group blocks by Y position (rows)
        rows = {}
        for block in self.blocks:
            y_key = round(block.y / 10) * 10  # Group by ~10 pixel bands
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append(block)
        
        # Find rows with multiple aligned columns
        for y_key, row_blocks in rows.items():
            if len(row_blocks) >= 3:  # At least 3 columns
                # Sort by X
                sorted_blocks = sorted(row_blocks, key=lambda b: b.x)
                
                # Check for regular column spacing
                x_positions = [b.x for b in sorted_blocks]
                if len(x_positions) >= 3:
                    # This row might be part of a table
                    tables.append({
                        "y": y_key,
                        "columns": len(row_blocks),
                        "x_positions": x_positions
                    })
        
        return tables


def extract_pdf_layout(pdf_path: str, output_json: str = None) -> Dict:
    """
    Main function to extract PDF layout.
    
    Args:
        pdf_path: Path to the PDF file
        output_json: Optional path to save the extracted layout
        
    Returns:
        Dict with layout information
    """
    extractor = PDFLayoutExtractor(pdf_path)
    layout = extractor.extract_all()
    
    # Also get REPX-ready layout
    repx_layout = extractor.get_layout_for_repx()
    layout["repx_layout"] = repx_layout
    
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(layout, f, indent=2)
        print(f"Layout saved to: {output_json}")
    
    return layout


if __name__ == "__main__":
    import sys
    
    # Default to FoxPro_Ebill PDF
    pdf_path = Path(__file__).parent.parent / "output" / "FoxPro_Ebill" / "FoxPro_Ebill_PDF_Example.pdf"
    
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    output_path = pdf_path.with_suffix(".layout.json")
    
    print(f"Extracting layout from: {pdf_path}")
    layout = extract_pdf_layout(str(pdf_path), str(output_path))
    
    print(f"\n📄 PDF Analysis:")
    print(f"   Pages: {layout['page_count']}")
    print(f"   Sections: {len(layout.get('sections', []))}")
    print(f"   Text blocks: {sum(len(p['text_blocks']) for p in layout['pages'])}")
    
    print(f"\n🎨 Color palette:")
    for color in layout.get("color_palette", [])[:5]:
        print(f"   {color['hex']} - used {color['count']} times (DX: {color['argb_dx']})")
    
    print(f"\n📍 Sections found:")
    for section in layout.get("sections", [])[:10]:
        print(f"   {section['type']}: {section['text_preview'][:50]}...")
    
    print(f"\n✅ Full layout saved to: {output_path}")
