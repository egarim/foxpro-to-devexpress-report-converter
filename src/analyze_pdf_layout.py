"""Analyze PDF layout to understand the original FoxPro report structure."""

import fitz
import json
import sys

def analyze_pdf(pdf_path: str):
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    print(f"Page size: {page.rect.width} x {page.rect.height} pts")
    print(f"  (1 inch = 72 pts, so this is {page.rect.width/72:.1f}\" x {page.rect.height/72:.1f}\")")
    print()
    
    # Get all text with positions
    items = []
    blocks = page.get_text('dict')['blocks']
    for block in blocks:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    text = span['text'].strip()
                    if text and len(text) > 0:
                        bbox = span['bbox']
                        items.append({
                            'x': bbox[0],
                            'y': bbox[1],
                            'w': bbox[2] - bbox[0],
                            'h': bbox[3] - bbox[1],
                            'text': text,
                            'size': span['size'],
                            'font': span.get('font', 'unknown')
                        })
    
    # Sort by Y then X
    items.sort(key=lambda i: (round(i['y']/15)*15, i['x']))
    
    print("PDF Layout Analysis (sorted by position):")
    print("=" * 80)
    current_row = -1
    for item in items:
        row = round(item['y']/15)*15
        if row != current_row:
            current_row = row
            print(f"\n--- Row ~{row}pt (y={item['y']:.0f}) ---")
        text_preview = item['text'][:35].ljust(35)
        print(f"  x={item['x']:5.0f} w={item['w']:5.0f} sz={item['size']:4.1f} | {text_preview}")
    
    # Save as JSON for further analysis
    output = {
        'page_width': page.rect.width,
        'page_height': page.rect.height,
        'items': items
    }
    
    with open('temp/pdf_layout.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n\nSaved layout to temp/pdf_layout.json")

if __name__ == '__main__':
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else 'FoxPro_Ebill_PDF_Example.pdf'
    analyze_pdf(pdf_path)
