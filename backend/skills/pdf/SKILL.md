# PDF Skill

## Overview
Use this skill when the user asks to **create, read, merge, split, watermark, or fill a PDF**.

Primary library: **`reportlab`** (creation) + **`pypdf`** (reading/merging/splitting).

---

## Installation
```bash
pip install reportlab pypdf
```

---

## 1. Create a PDF with reportlab

### Basic document setup
```python
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)

def create_pdf(filename: str, title: str, content_blocks: list):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 0.5*cm))

    for block in content_blocks:
        elements.append(Paragraph(block, styles["BodyText"]))
        elements.append(Spacer(1, 0.3*cm))

    doc.build(elements)
    print(f"PDF saved: {filename}")
```

### All commonly used styles
```python
styles = getSampleStyleSheet()
# Available: "Title", "Heading1"–"Heading4", "BodyText", "Italic",
#            "Code", "Normal", "Bullet"

# Custom style example
custom = ParagraphStyle(
    "Custom",
    parent=styles["BodyText"],
    fontSize=11,
    textColor=colors.HexColor("#333333"),
    leading=16,          # line spacing
    spaceAfter=8,
    leftIndent=20,
)
```

### Tables
```python
data = [
    ["Name", "Score", "Grade"],   # header row
    ["Alice", "92", "A"],
    ["Bob",   "78", "B"],
]
table = Table(data, colWidths=[6*cm, 3*cm, 3*cm])
table.setStyle(TableStyle([
    ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#4F46E5")),
    ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
    ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
    ("FONTSIZE",    (0, 0), (-1, -1), 10),
    ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
    ("TOPPADDING",  (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING",(0, 0),(-1, -1), 6),
]))
elements.append(table)
```

### Images
```python
from reportlab.platypus import Image

img = Image("path/to/image.png", width=10*cm, height=6*cm)
elements.append(img)
```

### Headers and footers (canvas-based)
```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.grey)
    # Header
    canvas.drawString(2*cm, A4[1] - 1.5*cm, "My Document")
    # Footer with page number
    canvas.drawString(2*cm, 1.2*cm, f"Page {doc.page}")
    canvas.restoreState()

doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
```

---

## 2. Read & Merge PDFs with pypdf

### Read text from a PDF
```python
from pypdf import PdfReader

reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    print(f"--- Page {i+1} ---")
    print(text)
```

### Merge multiple PDFs
```python
from pypdf import PdfMerger

merger = PdfMerger()
for pdf_path in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    merger.append(pdf_path)

merger.write("merged_output.pdf")
merger.close()
print("Merged PDF saved.")
```

### Split: extract specific pages
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Extract pages 2-4 (0-indexed: 1-3)
for page_num in range(1, 4):
    writer.add_page(reader.pages[page_num])

with open("extracted_pages.pdf", "wb") as f:
    writer.write(f)
```

### Watermark a PDF
```python
from pypdf import PdfReader, PdfWriter

base   = PdfReader("input.pdf")
wm     = PdfReader("watermark.pdf")
writer = PdfWriter()

for page in base.pages:
    page.merge_page(wm.pages[0])
    writer.add_page(page)

with open("watermarked.pdf", "wb") as f:
    writer.write(f)
```

---

## 3. Complete end-to-end example

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def create_report(filename: str, subject: str, sections: dict):
    """
    subject:  str — document title
    sections: dict — {heading: body_text}
    """
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            topMargin=2.5*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(subject, styles["Title"]))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#4F46E5"), thickness=1.5))
    elements.append(Spacer(1, 0.5*cm))

    for heading, body in sections.items():
        elements.append(Paragraph(heading, styles["Heading2"]))
        elements.append(Paragraph(body, styles["BodyText"]))
        elements.append(Spacer(1, 0.4*cm))

    doc.build(elements)
    return filename
```

---

## Rules & Best Practices

1. **Always use `cm` or `inch` units** from `reportlab.lib.units` — never raw pixel values.
2. **Use `SimpleDocTemplate`** for multi-page documents with automatic flow.
3. **Use `canvas`-based approach** only when you need absolute pixel-level control (e.g., certificates, invoices).
4. **Don't mix `platypus` and `canvas`** modes without the `header_footer` callback pattern.
5. **Always close `PdfMerger`** after writing.
6. **Save to a specific path** the user can easily find, e.g. their Desktop or current working directory.
7. **Print the saved path** so the user knows where the file is.
