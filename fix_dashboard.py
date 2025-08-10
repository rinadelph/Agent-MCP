#\!/usr/bin/env python3
import re

# Read the file
with open('beverly_comprehensive_erp.py', 'r') as f:
    content = f.read()

# Fix all template literals ${...} to ${{...}}
content = re.sub(r'\$\{([^}]+)\}', r'${{\1}}', content)

# Fix arrow functions  => { to => {{
content = re.sub(r'=>\s*\{', r'=> {{', content)

# Fix closing braces
content = content.replace('});', '}});')
content = content.replace('}}}});', '}});')  # Fix triple braces

# Write back
with open('beverly_comprehensive_erp.py', 'w') as f:
    f.write(content)
    
print("Fixed template literals and arrow functions")
