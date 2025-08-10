#\!/usr/bin/env python3
"""Fix all f-string issues"""
import re

with open('beverly_comprehensive_erp.py', 'r') as f:
    content = f.read()

# Find and fix f-strings with double braces that should be single
# This pattern finds f-strings with {{variable}} that should be {variable}
pattern = r'(f["\'][^"\']*)\{\{([^}]+)\}\}([^"\']*["\'])'

def fix_fstring(match):
    return match.group(1) + '{' + match.group(2) + '}' + match.group(3)

# Only fix f-strings, not JavaScript template literals
lines = content.split('\n')
fixed_lines = []
in_dashboard = False

for line in lines:
    if 'def comprehensive_dashboard' in line:
        in_dashboard = True
    elif line.strip().startswith('def ') and not in_dashboard:
        in_dashboard = False
    
    # Fix f-strings outside dashboard
    if not in_dashboard and 'f"' in line or "f'" in line:
        line = re.sub(pattern, fix_fstring, line)
    
    fixed_lines.append(line)

with open('beverly_comprehensive_erp.py', 'w') as f:
    f.write('\n'.join(fixed_lines))

print("F-strings fixed")
