# PPTX Skill

## Overview
Use this skill when the user asks to **create or edit a PowerPoint presentation (.pptx)**.

Primary library: **`python-pptx`**

---

## Installation
```bash
pip install python-pptx
```

---

## 1. Create a new presentation

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
# Default slide size: 10 x 7.5 inches (widescreen 16:9 is 13.33 x 7.5)
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
```

---

## 2. Slide layouts (built-in)

```python
# Available layout indices (standard template):
# 0  = Title Slide
# 1  = Title and Content
# 2  = Title and Two Content
# 5  = Title Only
# 6  = Blank

layout = prs.slide_layouts[1]   # Title and Content
slide  = prs.slides.add_slide(layout)

# Access placeholders by index
title   = slide.shapes.title           # placeholder 0
content = slide.placeholders[1]        # placeholder 1 (body)

title.text   = "My Slide Title"
content.text = "Bullet point one\nBullet point two\nBullet point three"
```

---

## 3. Text boxes (free-form)

```python
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

txBox = slide.shapes.add_textbox(
    Inches(1), Inches(1.5), Inches(8), Inches(1)
)
tf   = txBox.text_frame
tf.word_wrap = True

para = tf.paragraphs[0]
run  = para.add_run()
run.text = "Custom text in a free textbox"
run.font.size  = Pt(24)
run.font.bold  = True
run.font.color.rgb = RGBColor(0x4F, 0x46, 0xE5)
```

### Multi-paragraph text frames
```python
from pptx.util import Pt
from pptx.oxml.ns import qn

tf = content.text_frame
tf.clear()

for i, bullet in enumerate(["First point", "Second point", "Third point"]):
    if i == 0:
        para = tf.paragraphs[0]
    else:
        para = tf.add_paragraph()
    para.text  = bullet
    para.level = 0          # indent level 0–4
    para.font.size = Pt(20)
```

---

## 4. Shapes and styling

```python
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.dml.color import RGBColor

# Rectangle
shape = slide.shapes.add_shape(
    MSO_SHAPE_TYPE.RECTANGLE,
    Inches(1), Inches(1), Inches(4), Inches(2)
)
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0x4F, 0x46, 0xE5)
shape.line.color.rgb      = RGBColor(0x37, 0x32, 0xAE)
shape.line.width          = Pt(1.5)
```

---

## 5. Images

```python
slide.shapes.add_picture(
    "path/to/image.png",
    left=Inches(1),
    top=Inches(2),
    width=Inches(5),
    height=Inches(3),
)
```

---

## 6. Speaker notes

```python
notes_slide = slide.notes_slide
notes_tf    = notes_slide.notes_text_frame
notes_tf.text = "Speaker note: remember to highlight the key metrics here."
```

---

## 7. Slide background colour

```python
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from lxml import etree

background = slide.background
fill = background.fill
fill.solid()
fill.fore_color.rgb = RGBColor(0x0D, 0x0D, 0x0D)  # dark background
```

---

## 8. Charts (bar, line, pie)

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

chart_data = ChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("Revenue",  (1.2, 1.5, 1.8, 2.1))
chart_data.add_series("Expenses", (0.9, 1.0, 1.1, 1.2))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.BAR_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(4.5),
    chart_data,
).chart

chart.has_legend     = True
chart.has_title      = True
chart.chart_title.text_frame.text = "Quarterly Performance"
```

---

## 9. Save the presentation

```python
prs.save("output.pptx")
print("Presentation saved: output.pptx")
```

---

## 10. Complete end-to-end example

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def create_presentation(filename: str, title: str, slides_data: list) -> str:
    """
    slides_data: list of dicts with keys 'heading' and 'bullets' (list of str)
    """
    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Title slide
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = title
    title_slide.placeholders[1].text = "Generated Report"

    # Content slides
    for slide_info in slides_data:
        slide  = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_info["heading"]
        tf = slide.placeholders[1].text_frame
        tf.clear()
        for i, bullet in enumerate(slide_info["bullets"]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.text = bullet
            para.font.size = Pt(20)

    prs.save(filename)
    print(f"Saved: {filename}")
    return filename
```

---

## Rules & Best Practices

1. **Always use `Inches()` or `Pt()`** for all size/position values.
2. **Use slide layouts** (index 0–6) for standard slide types — avoids formatting inconsistencies.
3. **`slide.shapes.title`** is the fastest way to access the title placeholder.
4. **Clear text frames** with `tf.clear()` before writing multi-paragraph content to avoid leftover text.
5. **Save to a clearly named `.pptx` file** and print the path.
6. **Speaker notes** significantly improve the quality of generated decks — always add them.
