import os
import re

path = 'src/search_agent/static/app.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add onclick to funnel row
pattern = r'(html \+= <div class="funnel-status">\$\{statusText\}</div>;\s*row\.innerHTML = html;\s*)(funnelContainer\.appendChild\(row\);)'

replacement = r'''\g<1>row.onclick = function() {
                if (typeof window.openToolTraceModal === "function") {
                    window.openToolTraceModal(tool, statusText);
                }
            };
            \g<2>'''

content, count = re.subn(pattern, replacement, content)

if count > 0:
    print("Replaced old_row")
else:
    print("Failed to replace old_row")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
