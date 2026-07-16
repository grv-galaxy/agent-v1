import os

with open("src/search_agent/static/styles.css", "r", encoding="utf-8") as f:
    css_content = f.read()

# We need to fix the missing closing brace around line 64.
# The text looks like:
#   box-sizing: border-box;
# 
# /* --- Diagnostic Trace UI --- */
# ...
#   word-wrap: break-word;
# }
#   backdrop-filter: var(--glass-blur);
#   transition: border-color 0.2s ease, box-shadow 0.2s ease;
# }

# Let's extract everything, and rebuild it properly.
search_input_start = css_content.find(".search-input {")
diagnostic_start = css_content.find("/* --- Diagnostic Trace UI --- */")
backdrop_start = css_content.find("  backdrop-filter: var(--glass-blur);")

if search_input_start != -1 and diagnostic_start != -1:
    # Build proper search-input block
    fixed_search_input = """
.search-input {
  width: 100%;
  padding: 16px 24px;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  color: white;
  font-size: 16px;
  font-family: var(--font-ui);
  outline: none;
  box-sizing: border-box;
  backdrop-filter: var(--glass-blur);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 15px var(--accent-glow);
}

/* --- Deep Search Toggle --- */
.search-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deep-search-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-muted);
  user-select: none;
  align-self: flex-end;
}

.deep-search-toggle input {
  display: none;
}

.deep-search-toggle .slider {
  position: relative;
  width: 36px;
  height: 20px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  transition: 0.3s;
}

.deep-search-toggle .slider::before {
  content: "";
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: white;
  top: 3px;
  left: 3px;
  transition: 0.3s;
}

.deep-search-toggle input:checked + .slider {
  background-color: var(--accent);
}

.deep-search-toggle input:checked + .slider::before {
  transform: translateX(16px);
}

/* --- Diagnostic Trace UI --- */
.diagnostic-tools-helper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  justify-content: center;
}
.tool-chip {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-muted);
}
.tool-chip:hover {
  background: rgba(96, 165, 250, 0.2);
  border-color: var(--accent);
  color: var(--accent);
}

.diagnostic-console {
  background: rgba(0,0,0,0.4);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  width: 100%;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}
.diagnostic-console h3 {
  margin-top: 0;
  margin-bottom: 12px;
  color: #fbbf24;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.diag-section {
  margin-bottom: 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  overflow: hidden;
}
.diag-section summary {
  padding: 10px 14px;
  font-weight: 500;
  cursor: pointer;
  background: rgba(255,255,255,0.02);
  user-select: none;
}
.diag-section summary:hover {
  background: rgba(255,255,255,0.05);
}
.diag-section pre {
  margin: 0;
  padding: 14px;
  max-height: 400px;
  overflow-y: auto;
  font-size: 12px;
  color: #a3a3a3;
  white-space: pre-wrap;
  word-wrap: break-word;
}
"""
    # Replace from ".search-input {" all the way down to the closing brace after backdrop-filter
    end_of_bad_block = css_content.find("}", backdrop_start) + 1
    new_css = css_content[:search_input_start] + fixed_search_input + css_content[end_of_bad_block:]
    
    # We must also clean up the duplicate `.search-input:focus` which was left below the bad block
    if ".search-input:focus" in new_css[new_css.find(fixed_search_input)+len(fixed_search_input):]:
        # we added it inside the new block, so remove the old one if it exists
        old_focus_start = new_css.find(".search-input:focus", new_css.find(fixed_search_input)+len(fixed_search_input))
        if old_focus_start != -1:
            old_focus_end = new_css.find("}", old_focus_start) + 1
            new_css = new_css[:old_focus_start] + new_css[old_focus_end:]

    with open("src/search_agent/static/styles.css", "w", encoding="utf-8") as f:
        f.write(new_css)
    print("Fixed CSS!")
else:
    print("Could not find blocks to fix")
