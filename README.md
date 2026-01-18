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
│   ├── expression_translator.py  # FoxPro → DevExpress expression translation
│   ├── frt_parser.py             # FRT file parser
│   ├── pdf_layout_extractor.py   # PDF text/position extractor
│   ├── pdf_validator.py          # OpenAI Vision validation
│   └── repx_generator.py         # REPX XML generator
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

## 🔮 Future Improvements

### Recommended: Hybrid Approach with FoxPro Runtime

For best results, consider using FoxPro runtime to extract report structure:

1. **FoxPro script** exports FRT structure to JSON with exact:
   - Control positions and sizes
   - Band definitions
   - Expressions in native format
   - All properties and settings

2. **Python** consumes the JSON and:
   - Translates expressions
   - Generates REPX XML
   - Handles conversion logic

This would eliminate PDF dependency and significantly improve accuracy.

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
