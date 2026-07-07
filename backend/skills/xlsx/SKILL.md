# XLSX Skill

## Overview
Use this skill when the user asks to **create, edit, or analyze spreadsheets (.xlsx, .csv)**.

Primary library: **`openpyxl`** (Excel) + **`pandas`** (data analysis / CSV).

---

## Installation
```bash
pip install openpyxl pandas
```

---

## 1. Create a workbook with openpyxl

```python
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Sheet1"
```

---

## 2. Write data

```python
# Write single cell
ws["A1"] = "Name"
ws["B1"] = "Score"
ws["C1"] = "Grade"

# Write rows
data = [
    ("Alice", 92, "A"),
    ("Bob",   78, "B"),
    ("Carol", 85, "B+"),
]
for row in data:
    ws.append(row)

# Write using row/column numbers (1-indexed)
ws.cell(row=1, column=1, value="Header")
```

---

## 3. Formatting

### Fonts and alignment
```python
from openpyxl.styles import Font, Alignment

header_font = Font(name="Calibri", bold=True, size=12, color="FFFFFFFF")
center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

ws["A1"].font = header_font
ws["A1"].alignment = center_align
```

### Cell fill (background colour)
```python
from openpyxl.styles import PatternFill

blue_fill = PatternFill(fill_type="solid", fgColor="4F46E5")
ws["A1"].fill = blue_fill
```

### Borders
```python
from openpyxl.styles import Border, Side

thin = Side(style="thin", color="DDDDDD")
ws["A1"].border = Border(left=thin, right=thin, top=thin, bottom=thin)
```

### Apply styles across a header row
```python
header_row = ["Name", "Q1", "Q2", "Q3", "Q4", "Total"]
for col_idx, header in enumerate(header_row, start=1):
    cell = ws.cell(row=1, column=col_idx, value=header)
    cell.font      = Font(bold=True, color="FFFFFF")
    cell.fill      = PatternFill(fill_type="solid", fgColor="4F46E5")
    cell.alignment = Alignment(horizontal="center")
```

### Column width
```python
ws.column_dimensions["A"].width = 20
ws.column_dimensions["B"].width = 12

# Auto-fit all columns by content length (approximate)
for col in ws.columns:
    max_len = max(len(str(cell.value or "")) for cell in col)
    ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 4
```

### Row height
```python
ws.row_dimensions[1].height = 25
```

---

## 4. Formulas

```python
# SUM of a range
ws["F2"] = "=SUM(B2:E2)"

# AVERAGE
ws["G2"] = "=AVERAGE(B2:E2)"

# IF statement
ws["H2"] = '=IF(F2>300,"Pass","Fail")'

# AutoSum for a full column
ws[f"B{ws.max_row + 1}"] = f"=SUM(B2:B{ws.max_row})"
```

---

## 5. Multiple sheets

```python
ws2 = wb.create_sheet(title="Summary")
ws2["A1"] = "Summary Sheet"

# Copy data between sheets
for row in ws.iter_rows(min_row=2, values_only=True):
    ws2.append(row)
```

---

## 6. Charts (bar, line, pie)

```python
from openpyxl.chart import BarChart, LineChart, PieChart, Reference

# Bar chart
chart = BarChart()
chart.type  = "col"
chart.title = "Quarterly Sales"
chart.y_axis.title = "Revenue"
chart.x_axis.title = "Quarter"

data_ref = Reference(ws, min_col=2, max_col=5, min_row=1, max_row=ws.max_row)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.width  = 20
chart.height = 12

ws.add_chart(chart, "A10")  # anchor cell
```

---

## 7. Freeze panes and filters

```python
# Freeze the top header row
ws.freeze_panes = "A2"

# Auto-filter on the header row
ws.auto_filter.ref = ws.dimensions
```

---

## 8. Save

```python
wb.save("output.xlsx")
print("Saved: output.xlsx")
```

---

## 9. Read existing Excel / CSV with pandas

```python
import pandas as pd

# Read Excel
df = pd.read_excel("input.xlsx", sheet_name="Sheet1")

# Read CSV
df = pd.read_csv("input.csv")

print(df.head())
print(df.describe())
```

### Write DataFrame back to Excel
```python
with pd.ExcelWriter("output.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Data", index=False)
    df.describe().to_excel(writer, sheet_name="Stats", index=True)
```

---

## 10. Complete end-to-end example

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

def create_spreadsheet(filename: str, headers: list, rows: list) -> str:
    """
    headers: list of column header strings
    rows:    list of tuples/lists with row data
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"

    # Write headers
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font      = Font(bold=True, color="FFFFFF")
        cell.fill      = PatternFill(fill_type="solid", fgColor="4F46E5")
        cell.alignment = Alignment(horizontal="center")

    # Write data
    for row in rows:
        ws.append(list(row))

    # Auto-fit columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 4

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    wb.save(filename)
    print(f"Saved: {filename}")
    return filename
```

---

## Rules & Best Practices

1. **Use `openpyxl` for Excel creation/editing** and **`pandas`** for reading/analysis.
2. **Always write a header row first** with bold formatting so the file is immediately usable.
3. **Apply `freeze_panes = "A2"`** to keep headers visible when scrolling.
4. **Apply `auto_filter`** to enable sorting and filtering in Excel.
5. **Use `get_column_letter()`** when computing column letters dynamically.
6. **Don't open the file while saving** — Excel locks files; ensure it's closed before overwriting.
7. **Print the saved path** so the user knows where to find it.
