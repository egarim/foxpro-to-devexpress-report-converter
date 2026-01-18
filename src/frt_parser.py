"""
Custom FRT File Parser for Visual FoxPro Reports
FRT files have a specific binary structure that differs from standard DBF
"""

import struct
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class FRTRecord:
    """Represents a record in the FRT file"""
    platform: int  # Platform code
    obj_type: int  # Object type
    obj_code: int  # Object code/subtype
    name: str  # Object name
    expr: str  # Expression
    vpos: int  # Vertical position
    hpos: int  # Horizontal position
    height: int  # Height
    width: int  # Width
    style: int  # Style flags
    picture: str  # Picture/format string
    tag: str  # Tag
    tag2: str  # Tag2
    penred: int  # Pen color red
    pengreen: int  # Pen color green
    penblue: int  # Pen color blue
    fillred: int  # Fill color red
    fillgreen: int  # Fill color green
    fillblue: int  # Fill color blue
    fontface: str  # Font face name
    fontsize: int  # Font size
    fontstyle: int  # Font style (bold, italic, etc.)
    raw_data: bytes = None  # Raw record data for debugging


class FRTParser:
    """
    Parser for Visual FoxPro FRT (Form Report) files
    
    Based on the FoxPro Report File structure:
    - FRT files contain records of varying types
    - Each record has a fixed header and variable data
    """
    
    # Object types in FRT files
    OBJ_TYPES = {
        0: "Band",
        1: "ReportHeader",
        2: "PageHeader", 
        3: "ColumnHeader",
        4: "GroupHeader",
        5: "Detail",
        6: "GroupFooter",
        7: "ColumnFooter",
        8: "PageFooter",
        9: "Summary",
        17: "DataEnvironment",
        18: "Cursor",
        19: "Relation",
        23: "Field",
        25: "Label",
        26: "Line",
        27: "Rectangle",
        28: "RoundedRectangle",
        29: "Picture",
        30: "OLEBound",
        31: "OLEUnbound"
    }
    
    # Band types (OBJCODE when OBJTYPE=0)
    BAND_TYPES = {
        0: "Title",
        1: "PageHeader",
        2: "ColumnHeader", 
        3: "GroupHeader",
        4: "Detail",
        5: "GroupFooter",
        6: "ColumnFooter",
        7: "PageFooter",
        8: "Summary",
        9: "DetailHeader"
    }

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.records: List[Dict] = []
        self.header_info: Dict = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse the FRT file and return structured data"""
        
        with open(self.filepath, 'rb') as f:
            data = f.read()
        
        print(f"File size: {len(data)} bytes")
        print(f"First 64 bytes (hex): {data[:64].hex()}")
        
        # Analyze the file structure
        result = {
            "source_file": str(self.filepath),
            "file_size": len(data),
            "analysis": self._analyze_structure(data),
            "strings": self._extract_strings(data),
            "fonts": self._extract_fonts(data),
            "procedures": self._extract_procedures(data),
            "positions": self._extract_positions(data)
        }
        
        return result
    
    def _analyze_structure(self, data: bytes) -> Dict:
        """Analyze the overall structure of the file"""
        
        # Look for common patterns
        analysis = {
            "header_marker": data[:4].hex(),
            "possible_record_count": struct.unpack('<I', data[4:8])[0] if len(data) >= 8 else 0,
        }
        
        # Find record boundaries by looking for repeating patterns
        # FRT files often have fixed-size records or length-prefixed records
        
        return analysis
    
    def _extract_strings(self, data: bytes) -> List[str]:
        """Extract readable strings from the binary data"""
        strings = []
        current_string = b""
        
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                current_string += bytes([byte])
            else:
                if len(current_string) >= 4:  # Only keep strings of length >= 4
                    try:
                        decoded = current_string.decode('ascii')
                        strings.append(decoded)
                    except:
                        pass
                current_string = b""
        
        # Deduplicate and sort
        unique_strings = sorted(set(strings))
        return unique_strings
    
    def _extract_fonts(self, data: bytes) -> List[str]:
        """Extract font names from the file"""
        known_fonts = ['Arial', 'Calibri', 'Courier', 'Times', 'OCR', 'Narrow']
        found_fonts = []
        
        strings = self._extract_strings(data)
        for s in strings:
            for font in known_fonts:
                if font.lower() in s.lower() and s not in found_fonts:
                    found_fonts.append(s)
        
        return found_fonts
    
    def _extract_procedures(self, data: bytes) -> List[Dict]:
        """Extract FoxPro procedure code from the file"""
        procedures = []
        
        # Look for PROCEDURE keyword
        text = data.decode('latin-1', errors='ignore')
        
        import re
        proc_pattern = r'PROCEDURE\s+(\w+)(.*?)(?=PROCEDURE|ENDPROC|\x00\x00\x00)'
        matches = re.findall(proc_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            proc_name = match[0]
            proc_body = match[1].strip()
            procedures.append({
                "name": proc_name,
                "body": proc_body[:500]  # Limit length
            })
        
        return procedures
    
    def _extract_positions(self, data: bytes) -> List[Dict]:
        """Extract position information (Top, Left, Width, Height patterns)"""
        positions = []
        
        text = data.decode('latin-1', errors='ignore')
        
        import re
        # Look for Top = X, Left = Y patterns
        pos_pattern = r'Top\s*=\s*(\d+).*?Left\s*=\s*(\d+).*?Width\s*=\s*(\d+).*?Height\s*=\s*(\d+)'
        matches = re.findall(pos_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            positions.append({
                "top": int(match[0]),
                "left": int(match[1]),
                "width": int(match[2]),
                "height": int(match[3])
            })
        
        return positions


def analyze_frt_deep(filepath: str) -> Dict:
    """
    Deep analysis of FRT file by examining byte patterns
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    result = {
        "total_size": len(data),
        "sections": []
    }
    
    # The FRT file appears to have 592-byte records based on hex analysis
    # Let's verify this by looking for repeating patterns
    
    # Check if it's a compound document or simple record structure
    # Look for record length indicators
    
    # Scan for null-separated sections
    sections = data.split(b'\x00' * 32)  # Split on 32+ null bytes
    
    for i, section in enumerate(sections):
        if len(section) > 10:  # Skip tiny sections
            # Try to decode as text
            try:
                text = section.decode('cp1252', errors='replace')
                # Filter to printable characters
                printable = ''.join(c if c.isprintable() or c in '\r\n\t' else ' ' for c in text)
                printable = ' '.join(printable.split())  # Normalize whitespace
                if len(printable.strip()) > 5:
                    result["sections"].append({
                        "index": i,
                        "offset": data.find(section),
                        "size": len(section),
                        "text_preview": printable[:200]
                    })
            except:
                pass
    
    return result


if __name__ == "__main__":
    frt_path = Path(__file__).parent.parent / "FoxPro_Ebill.frt"
    
    print("=" * 80)
    print("FRT File Analysis")
    print("=" * 80)
    
    # Basic parsing
    parser = FRTParser(str(frt_path))
    result = parser.parse()
    
    print(f"\n📝 Extracted Strings ({len(result['strings'])} total):")
    print("-" * 40)
    # Show interesting strings (not just single words)
    for s in result['strings']:
        if len(s) > 8:
            print(f"  {s}")
    
    print(f"\n🎨 Fonts Found ({len(result['fonts'])} total):")
    print("-" * 40)
    for font in result['fonts']:
        print(f"  - {font}")
    
    print(f"\n📦 Procedures Found ({len(result['procedures'])} total):")
    print("-" * 40)
    for proc in result['procedures']:
        print(f"  - {proc['name']}")
        if proc['body']:
            for line in proc['body'].split('\n')[:5]:
                print(f"      {line.strip()}")
    
    print(f"\n📐 Position Data ({len(result['positions'])} total):")
    print("-" * 40)
    for pos in result['positions'][:10]:
        print(f"  Top={pos['top']}, Left={pos['left']}, Width={pos['width']}, Height={pos['height']}")
    
    # Deep analysis
    print("\n" + "=" * 80)
    print("Deep Structure Analysis")
    print("=" * 80)
    
    deep_result = analyze_frt_deep(str(frt_path))
    print(f"\nFile has {len(deep_result['sections'])} distinct sections")
    
    for section in deep_result['sections'][:15]:
        print(f"\n  Section {section['index']} at offset {section['offset']} ({section['size']} bytes):")
        print(f"    Preview: {section['text_preview'][:100]}...")
    
    # Save full analysis to JSON
    output_path = Path(__file__).parent.parent / "frt_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "basic_analysis": result,
            "deep_analysis": deep_result
        }, f, indent=2, default=str)
    
    print(f"\n✅ Full analysis saved to: {output_path}")
