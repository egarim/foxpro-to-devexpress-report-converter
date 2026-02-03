import json

data = json.load(open('temp/ebill.json'))
controls = data.get('controls', [])

# Find all controls
all_controls = []
for c in controls:
    objtype = c.get('objtype')
    if objtype in [5, 8]:  # Labels and fields
        pos = c.get('position', {})
        top = (pos.get('top_fru', 0) or 0) / 100
        left = (pos.get('left_fru', 0) or 0) / 100
        width = (pos.get('width_fru', 0) or 0) / 100
        height = (pos.get('height_fru', 0) or 0) / 100
        expr = (c.get('expression', '') or '')
        
        all_controls.append({
            'top': top,
            'left': left,
            'right': left + width,
            'bottom': top + height,
            'width': width,
            'height': height,
            'expr': expr[:40]
        })

# Find overlapping controls
print("Checking for overlapping labels...")
print("-" * 80)

overlaps = []
for i, c1 in enumerate(all_controls):
    for j, c2 in enumerate(all_controls):
        if i >= j:
            continue
        # Check if rectangles overlap
        if (c1['left'] < c2['right'] and c1['right'] > c2['left'] and
            c1['top'] < c2['bottom'] and c1['bottom'] > c2['top']):
            # Calculate overlap amount
            overlap_x = min(c1['right'], c2['right']) - max(c1['left'], c2['left'])
            overlap_y = min(c1['bottom'], c2['bottom']) - max(c1['top'], c2['top'])
            if overlap_x > 5 and overlap_y > 5:  # Significant overlap
                overlaps.append({
                    'c1': c1,
                    'c2': c2,
                    'overlap_x': overlap_x,
                    'overlap_y': overlap_y
                })

print(f"Found {len(overlaps)} significant overlaps")
for o in overlaps[:20]:
    print(f"\nOverlap: {o['overlap_x']:.0f}x{o['overlap_y']:.0f}")
    print(f"  1: Y:{o['c1']['top']:3.0f} X:{o['c1']['left']:3.0f} | {o['c1']['expr']}")
    print(f"  2: Y:{o['c2']['top']:3.0f} X:{o['c2']['left']:3.0f} | {o['c2']['expr']}")
