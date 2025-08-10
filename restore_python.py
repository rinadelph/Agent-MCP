#\!/usr/bin/env python3
"""Fix Python code that was broken by JavaScript fixes"""

with open('beverly_comprehensive_erp.py', 'r') as f:
    lines = f.readlines()

in_dashboard = False
fixed_lines = []

for i, line in enumerate(lines):
    # Track dashboard function (that's where JS is)
    if 'def comprehensive_dashboard' in line:
        in_dashboard = True
    elif not in_dashboard and line.strip().startswith('def '):
        in_dashboard = False
    
    # Outside dashboard, fix Python dict/list closings
    if not in_dashboard:
        # Fix double closing braces back to single
        if '}}' in line and 'f"' not in lines[max(0,i-5):i+1]:
            line = line.replace('}}', '}')
    
    fixed_lines.append(line)

with open('beverly_comprehensive_erp.py', 'w') as f:
    f.writelines(fixed_lines)

print("Python code restored outside dashboard function")
