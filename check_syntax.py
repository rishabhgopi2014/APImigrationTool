import sys
import re

# Quick JS syntax checker
file_path = "src/web/static/index.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract JavaScript section
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    
    # Check for common syntax errors
    issues = []
    
    # Double commas
    if ',,' in js_code:
        issues.append("Found double comma (,,)")
    
    # Unopened/unclosed braces
    open_braces = js_code.count('{')
    close_braces = js_code.count('}')
    if open_braces != close_braces:
        issues.append(f"Brace mismatch: {open_braces} open, {close_braces} close")
    
    # Unopened/unclosed parentheses
    open_paren = js_code.count('(')
    close_paren = js_code.count(')')
    if open_paren != close_paren:
        issues.append(f"Parenthesis mismatch: {open_paren} open, {close_paren} close")
    
    if issues:
        print("❌ JavaScript syntax issues found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ Basic syntax checks passed")
        sys.exit(0)
else:
    print("❌ No script tag found")
    sys.exit(1)
