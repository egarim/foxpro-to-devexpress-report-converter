import json

data = json.load(open('temp/ebill.json'))
controls = data.get('controls', [])

# Find labels in the main report area
labels = []
for c in controls:
    if c.get('objtype') in [5, 8]:  # Labels and fields
        pos = c.get('position', {})
        top = (pos.get('top_fru', 0) or 0) / 100
        left = (pos.get('left_fru', 0) or 0) / 100
        width = (pos.get('width_fru', 0) or 0) / 100
        height = (pos.get('height_fru', 0) or 0) / 100
        expr = (c.get('expression', '') or '')[:50]
        
        if 100 < top < 250:  # Header/table area
            labels.append({
                'top': top,
                'left': left,
                'width': width,
                'height': height,
                'expr': expr
            })

# Sort by position and print
print("Labels in header/table area:")
print("-" * 100)
for l in sorted(labels, key=lambda x: (x['top'], x['left'])):
    print(f"Y:{l['top']:5.0f} X:{l['left']:5.0f} W:{l['width']:4.0f} H:{l['height']:3.0f} | {l['expr']}")
