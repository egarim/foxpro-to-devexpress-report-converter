# FoxPro FRT to DevExpress REPX Converter

A Python-based tool for converting Visual FoxPro Report files (`.frt`) to DevExpress XtraReports format (`.repx`).

## 📋 Overview

This tool automates the migration of FoxPro reports to DevExpress XtraReports by:

1. **Parsing FRT files** - Extracts expressions, strings, and metadata from FoxPro report files
2. **Extracting PDF layout** - Uses a reference PDF to capture exact text positions, fonts, and colors
3. **Translating expressions** - Converts FoxPro expressions to DevExpress expression syntax
4. **Generating REPX** - Creates valid DevExpress report files with proper controls and bindings
5. **Validating output** - Generates preview images and compares them using AI vision

## 🏗️ Project Structure

```
fwdcusifoxprocrystalreportstodevexpress/
├── src/                          # Python source code
│   ├── cli.py                    # Command-line interface
│   ├── converter.py              # Basic converter (v1)
│   ├── converter_v2.py           # Improved converter
│   ├── converter_pdf_layout.py   # PDF-based layout converter
│   ├── converter_pdf_layout_v2.py # Enhanced PDF converter with table detection
│   ├── converter_foxpro_json.py  # Hybrid: converts FoxPro JSON to REPX
│   ├── expression_translator.py  # FoxPro → DevExpress expression translation
│   ├── frt_parser.py             # FRT file parser
│   ├── pdf_layout_extractor.py   # PDF text/position extractor
│   ├── pdf_validator.py          # OpenAI Vision validation
│   └── repx_generator.py         # REPX XML generator
│
├── foxpro/                       # FoxPro scripts (hybrid approach)
│   └── export_frt_to_json.prg    # Exports FRX/FRT to JSON
│
├── docs/                         # Documentation
│   └── HYBRID_APPROACH_PLAN.md   # Detailed hybrid implementation plan
│
├── tools/
│   └── RepxPreview/              # C# tool to render REPX previews
│       ├── Program.cs
│       └── RepxPreview.csproj
│
├── output/                       # Generated reports
│   └── [ReportName]/
│       ├── [ReportName].repx     # Generated DevExpress report
│       ├── *_preview.png         # Preview images
│       └── *_analysis.json       # Conversion analysis
│
└── .venv/                        # Python virtual environment
```

## 📦 Requirements

### Python Requirements

- **Python 3.11+** (tested with Python 3.13.9)

Install dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.\.venv\Scripts\activate.bat

# Activate (Linux/macOS)
source .venv/bin/activate

# Install packages
pip install dbfread lxml openai pymupdf
```

#### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `dbfread` | Latest | Reading DBF/FRT file structures |
| `lxml` | Latest | XML generation for REPX files |
| `openai` | Latest | AI vision validation (optional) |
| `pymupdf` (fitz) | Latest | PDF parsing and image extraction |

### .NET Requirements (for Preview Generation)

- **.NET 8.0 SDK** - Required to build the RepxPreview tool
- **DevExpress Reporting v24.2** - DevExpress NuGet packages (requires license)

Build the preview tool:

```bash
cd tools/RepxPreview
dotnet publish -c Release -r win-x64 --self-contained
```

### Optional Requirements

- **OpenAI API Key** - For AI-powered layout validation
  - Set environment variable: `OPENAI_API_KEY=your-key-here`

## 🚀 Usage

### Basic Conversion (PDF-Based Layout)

The recommended approach uses a reference PDF for accurate layout:

```bash
cd src

# Convert with PDF reference (recommended)
python converter_pdf_layout_v2.py <file.frt> <example.pdf> [output_folder]

# Example
python converter_pdf_layout_v2.py ../FoxPro_Ebill.frt ../FoxPro_Ebill_PDF_Example.pdf ../output/FoxPro_Ebill
```

### CLI Commands

```bash
cd src

# Convert single file
python cli.py convert <input.frt> --pdf <example.pdf> --output <folder>

# Batch convert folder
python cli.py batch <input_folder> --output <folder>

# Analyze FRT file (no conversion)
python cli.py analyze <input.frt>
```

### Generate Preview Image

```bash
# Using the C# preview tool
.\tools\RepxPreview\bin\Release\net8.0\win-x64\RepxPreview.exe "output\Report.repx" "output\preview.png"
```

### Validate with AI Vision

```python
# Requires OPENAI_API_KEY environment variable
python src/pdf_validator.py output/Report/Report.repx output/Report/original.pdf
```

## 🔧 How It Works

### 1. FRT Parsing (`frt_parser.py`)

The FRT parser reads FoxPro report files and extracts:
- **Expressions** - Field bindings and calculated expressions
- **Strings** - Static text content
- **Metadata** - Report properties and settings

```python
from frt_parser import FRTParser

parser = FRTParser("report.frt")
data = parser.parse()
print(data["expressions"])  # List of FoxPro expressions
print(data["strings"])      # List of static text
```

### 2. PDF Layout Extraction (`pdf_layout_extractor.py`)

Extracts exact positions from a reference PDF:
- Text positions (X, Y coordinates)
- Font information (family, size, style)
- Colors (foreground and background)
- Page dimensions

```python
from pdf_layout_extractor import PDFLayoutExtractor

extractor = PDFLayoutExtractor("example.pdf")
layout = extractor.get_layout_for_repx()
print(layout["controls"])  # List of controls with positions
```

### 3. Expression Translation (`expression_translator.py`)

Converts FoxPro expressions to DevExpress syntax:

| FoxPro | DevExpress |
|--------|------------|
| `ALLTRIM(field)` | `Trim([field])` |
| `IIF(cond, a, b)` | `Iif(cond, a, b)` |
| `TRANSFORM(val, "$999.99")` | `FormatString('{0:C}', [val])` |
| `SHORTDATE(date)` | `FormatString('{0:d}', [date])` |
| `STR(num)` | `ToStr([num])` |
| `DTOC(date)` | `FormatString('{0:d}', [date])` |
| `EMPTY(field)` | `IsNullOrEmpty([field])` |

```python
from expression_translator import ExpressionTranslator

translator = ExpressionTranslator()
result = translator.translate("ALLTRIM(customer.name)")
print(result)  # "Trim([customer.name])"
```

### 4. REPX Generation (`converter_pdf_layout_v2.py`)

Generates DevExpress REPX XML with:
- **XRLabel** controls for text
- **XRTable** controls for grid layouts (auto-detected)
- **Calculated fields** for expressions
- **Styling** (fonts, colors, borders)

### 5. Preview Generation (`tools/RepxPreview`)

C# tool using DevExpress Reporting to render REPX to PNG:
- Loads the REPX file
- Renders all pages
- Exports as PNG image

## 📊 Conversion Results

Current accuracy (measured by OpenAI Vision comparison):

| Metric | Score |
|--------|-------|
| Text Positioning | 6/10 |
| Layout Structure | 7/10 |
| Color Scheme | 8/10 |
| Font Usage | 7/10 |
| Data Completeness | 8/10 |
| **Overall** | **7/10** |

## ⚠️ Limitations

### Current Limitations

1. **FRT Parsing** - The FRT binary format has undocumented fields; we extract what we can but some metadata may be lost

2. **Layout Accuracy** - Without FoxPro runtime, we rely on PDF extraction which may have minor positioning differences

3. **Expression Translation** - Not all FoxPro functions are mapped; complex expressions may need manual review

4. **Dynamic Content** - Data-bound content shows placeholder values in previews

### Not Supported (Yet)

- Subreports
- Charts/Graphs
- Complex grouping logic
- Print-when visibility conditions
- Multi-column layouts

## 🔮 Hybrid Approach (FoxPro Runtime + Python)

For **best results**, use the hybrid approach on the `hybrid` branch. This leverages FoxPro runtime for 100% accurate report extraction.

### Why Hybrid?

| Approach | Accuracy | Requirement |
|----------|----------|-------------|
| Pure Python (PDF-based) | ~70% | No FoxPro needed |
| **Hybrid (FoxPro+Python)** | **~95%+** | VFP9 runtime |

### Hybrid Workflow

**Step 1:** Run FoxPro script to export report structure to JSON:

```foxpro
* In FoxPro IDE or with VFP9 runtime
DO foxpro\export_frt_to_json WITH "FoxPro_Ebill.frx", "FoxPro_Ebill.json"
```

**Step 2:** Run Python converter on the JSON:

```bash
cd src
python converter_foxpro_json.py ../FoxPro_Ebill.json ../output/FoxPro_Ebill
```

### Automated Batch Script

```batch
@echo off
REM convert_hybrid.bat - Full hybrid conversion
SET FRX=%1
SET OUT=%2

REM Step 1: FoxPro exports to JSON
vfp9.exe foxpro\export_frt_to_json.prg %FRX% temp\report.json

REM Step 2: Python generates REPX
python src\converter_foxpro_json.py temp\report.json %OUT%
```

### What the Hybrid Approach Captures

- ✅ **100% accurate** control positions (FRU coordinates)
- ✅ **Complete band structure** with all properties
- ✅ **Native expressions** exactly as stored
- ✅ **Font properties** (name, size, style)
- ✅ **Colors** (RGB values for foreground/background)
- ✅ **Print-when conditions**
- ✅ **Stretch modes**

See [docs/HYBRID_APPROACH_PLAN.md](docs/HYBRID_APPROACH_PLAN.md) for full technical details.

## 🐛 Troubleshooting

### "Module not found" errors

```bash
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Reinstall packages
pip install --upgrade dbfread lxml openai pymupdf
```

### Preview tool errors

```bash
# Rebuild the preview tool
cd tools/RepxPreview
dotnet clean
dotnet publish -c Release -r win-x64 --self-contained
```

### "Expression error" in generated report

Some FoxPro expressions may not translate correctly. Check:
1. The `*_analysis.json` file for calculated fields
2. Manually review complex expressions
3. Edit the REPX file to fix invalid expressions

## 📝 License

[Your license here]

## 🤝 Contributing

Contributions welcome! Areas that need work:
- Additional FoxPro function mappings
- Better table detection algorithm
- Subreport support
- Chart/graph conversion
