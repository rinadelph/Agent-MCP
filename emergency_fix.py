#\!/usr/bin/env python3
"""Emergency fix for dashboard JavaScript/CSS in f-strings"""

with open('beverly_comprehensive_erp.py', 'r') as f:
    lines = f.readlines()

in_dashboard = False
in_script = False
fixed_lines = []

for i, line in enumerate(lines):
    # Track if we're in the dashboard function
    if 'def comprehensive_dashboard' in line:
        in_dashboard = True
    elif in_dashboard and line.strip().startswith('def '):
        in_dashboard = False
    
    # Track if we're in script tags
    if in_dashboard:
        if '<script>' in line:
            in_script = True
        elif '</script>' in line:
            in_script = False
    
    # Fix JavaScript lines
    if in_dashboard and in_script:
        # Fix forEach, then, catch patterns
        if '.forEach(' in line or '.then(' in line or '.catch(' in line:
            # Make sure arrow functions have double braces
            if '=> {' in line and '=> {{' not in line:
                line = line.replace('=> {', '=> {{')
            # Ensure closing braces are doubled
            if '});' in line and not '}});' in line:
                line = line.replace('});', '}});')
    
    fixed_lines.append(line)

# Write back
with open('beverly_comprehensive_erp.py', 'w') as f:
    f.writelines(fixed_lines)

print("Emergency fix applied")
