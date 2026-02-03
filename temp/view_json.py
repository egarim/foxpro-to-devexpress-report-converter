import json

with open('temp/ebill.json') as f:
    data = json.load(f)

print(f"Report: {data['report']['name']}")
print(f"Bands: {len(data['bands'])}")
print(f"Controls: {len(data['controls'])}")
print()

# Show controls with expressions
controls_with_expr = [c for c in data['controls'] if c.get('expression')]
print(f"Controls with expressions: {len(controls_with_expr)}")
print()

print("=== Sample Controls ===")
for ctrl in controls_with_expr[:15]:
    print(f"ID: {ctrl['id']}, Type: {ctrl['objtype_name']}")
    print(f"  Position: ({ctrl['position']['left_fru']}, {ctrl['position']['top_fru']})")
    print(f"  Size: {ctrl['position']['width_fru']} x {ctrl['position']['height_fru']}")
    print(f"  Font: {ctrl['font']['name']} {ctrl['font']['size']}pt")
    expr = ctrl['expression'][:80] + "..." if len(ctrl['expression']) > 80 else ctrl['expression']
    print(f"  Expression: {expr}")
    print()
