"""
Compare generated REPX positions with original PDF positions.
"""
import json
import re
import fitz

def analyze_repx(repx_path: str):
    """Extract control positions from REPX."""
    with open(repx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    controls = []
    # Split by <Item tags
    items = content.split('<Item')
    
    for item in items[1:]:
        loc_match = re.search(r'LocationFloat="([^"]+)"', item)
        size_match = re.search(r'SizeF="([^"]+)"', item)
        text_match = re.search(r'Text="([^"]+)"', item)
        name_match = re.search(r'Name="([^"]+)"', item)
        
        if loc_match and size_match:
            loc = loc_match.group(1).split(', ')
            x, y = float(loc[0]), float(loc[1])
            text = text_match.group(1)[:30] if text_match else '(expr)'
            name = name_match.group(1) if name_match else ''
            
            # Convert to points (DevExpress: 100 units = 1 inch, 72 pts = 1 inch)
            x_pts = x * 0.72
            y_pts = y * 0.72
            
            controls.append({
                'name': name,
                'x': x,
                'y': y,
                'x_pts': x_pts,
                'y_pts': y_pts,
                'text': text
            })
    
    return controls

def analyze_pdf(pdf_path: str):
    """Extract text positions from PDF."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    items = []
    blocks = page.get_text('dict')['blocks']
    for block in blocks:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    text = span['text'].strip()
                    if text:
                        bbox = span['bbox']
                        items.append({
                            'text': text[:30],
                            'x_pts': bbox[0],
                            'y_pts': bbox[1]
                        })
    return items

def compare_positions():
    repx_controls = analyze_repx('output/ebill_hybrid/ebill.repx')
    pdf_items = analyze_pdf('FoxPro_Ebill_PDF_Example.pdf')
    
    print("REPX Controls with static text (sorted by y):")
    print("=" * 70)
    repx_controls.sort(key=lambda c: (c['y_pts'], c['x_pts']))
    
    for ctrl in repx_controls[:40]:
        print(f"y={ctrl['y_pts']:5.0f} x={ctrl['x_pts']:5.0f} | {ctrl['text']}")
    
    print("\n\nPDF items (sorted by y):")
    print("=" * 70)
    pdf_items.sort(key=lambda i: (i['y_pts'], i['x_pts']))
    
    for item in pdf_items[:40]:
        print(f"y={item['y_pts']:5.0f} x={item['x_pts']:5.0f} | {item['text']}")

if __name__ == '__main__':
    compare_positions()
