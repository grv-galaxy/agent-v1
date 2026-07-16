import os
import re

path = 'src/search_agent/static/styles.css'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make modal background dark solid
content = content.replace('background-color: var(--bg-card);', 'background-color: #1e293b;')
content = content.replace('background: var(--bg-hover);', 'background: #334155;')

# Ensure pre has better contrast
content = content.replace('background: #111;', 'background: #0f172a; border: 1px solid #334155;')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
