# DOCX Skill

## Overview
Use this skill when the user asks to **create, edit, read, or format a Word document (.docx)**.

Primary library: **`python-docx`**

---

## Installation
```bash
pip install python-docx
```

---

## 1. Create a new document

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()
```

---

## 2. Document structure

### Title and headings
```python
doc.add_heading("My Document Title", level=0)   # Title style
doc.add_heading("Section One", level=1)          # Heading 1
doc.add_heading("Subsection 1.1", level=2)       # Heading 2
```

### Paragraphs with formatting
```python
# Plain paragraph
para = doc.add_paragraph("This is a body paragraph.")

# Bold + italic inline formatting using runs
para = doc.add_paragraph()
run = para.add_run("Bold text ")
run.bold = True
run2 = para.add_run("and italic text.")
run2.italic = True

# Paragraph alignment
from docx.enum.text import WD_ALIGN_PARAGRAPH
para.alignment = WD_ALIGN_PARAGRAPH.CENTER   # LEFT | CENTER | RIGHT | JUSTIFY

# Font size and colour
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x4F, 0x46, 0xE5)  # indigo
```

### Bullet and numbered lists
```python
doc.add_paragraph("First bullet",  style="List Bullet")
doc.add_paragraph("Second bullet", style="List Bullet")
doc.add_paragraph("First item",    style="List Number")
doc.add_paragraph("Second item",   style="List Number")
```

### Page breaks and spacing
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc.add_page_break()

# Paragraph spacing
para.paragraph_format.space_before = Pt(6)
para.paragraph_format.space_after  = Pt(12)
para.paragraph_format.line_spacing = Pt(18)
```

---

## 3. Tables

```python
table = doc.add_table(rows=1, cols=3)
table.style = "Table Grid"   # or "Light Shading", "Medium Grid 1 Accent 1"

# Header row
hdr = table.rows[0].cells
hdr[0].text = "Name"
hdr[1].text = "Score"
hdr[2].text = "Grade"

# Make header bold
for cell in hdr:
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True

# Add data rows
data = [("Alice", "92", "A"), ("Bob", "78", "B"), ("Carol", "85", "B+")]
for name, score, grade in data:
    row = table.add_row().cells
    row[0].text = name
    row[1].text = score
    row[2].text = grade
```

### Set column widths
```python
from docx.shared import Cm
for i, width in enumerate([5, 3, 3]):
    for cell in table.columns[i].cells:
        cell.width = Cm(width)
```

---

## 4. Images

```python
from docx.shared import Cm

doc.add_picture("path/to/image.png", width=Cm(10))
# Image is centered by adjusting the last paragraph alignment:
last_para = doc.paragraphs[-1]
last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

---

## 5. Headers and footers

```python
section = doc.sections[0]

# Header
header = section.header
header.paragraphs[0].text = "My Company — Confidential"
header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

# Footer with page number
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

footer = section.footer
footer_para = footer.paragraphs[0]
footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer_para.add_run()
fldChar1 = OxmlElement("w:fldChar")
fldChar1.set(qn("w:fldCharType"), "begin")
instrText = OxmlElement("w:instrText")
instrText.text = "PAGE"
fldChar2 = OxmlElement("w:fldChar")
fldChar2.set(qn("w:fldCharType"), "end")
run._r.append(fldChar1)
run._r.append(instrText)
run._r.append(fldChar2)
```

---

## 6. Page setup (margins, orientation)

```python
from docx.shared import Cm
from docx.enum.section import WD_ORIENT

section = doc.sections[0]
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin   = Cm(3.17)
section.right_margin  = Cm(3.17)

# Landscape
section.orientation = WD_ORIENT.LANDSCAPE
section.page_width, section.page_height = section.page_height, section.page_width
```

---

## 7. Save the document

```python
doc.save("output.docx")
print("Document saved: output.docx")
```

---

## 8. Complete end-to-end example

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_report(filename: str, title: str, sections: dict) -> str:
    """
    sections: {heading_str: body_str}
    Returns the saved filename.
    """
    doc = Document()

    # Title
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()  # blank spacer

    for heading, body in sections.items():
        doc.add_heading(heading, level=1)
        doc.add_paragraph(body)
        doc.add_paragraph()

    doc.save(filename)
    print(f"Saved: {filename}")
    return filename
```

---

## Rules & Best Practices

1. **Use built-in styles** (`"Normal"`, `"Heading 1"`, `"List Bullet"`, `"Table Grid"`) where possible — they ensure correct rendering in Word.
2. **Add runs for inline formatting** (bold, italic, color) rather than setting it on the paragraph.
3. **Always save to a descriptive filename** ending in `.docx`.
4. **Use `Pt()`, `Cm()`, `Inches()`** for all measurements — never raw ints.
5. **Print the saved file path** so the user knows where to find it.
