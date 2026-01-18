"""
PDF Validation using OpenAI Vision API

Compares converted DevExpress report structure against original PDF to validate accuracy.
"""

import os
import base64
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import field matching from expression translator
from expression_translator import normalize_field_name, match_field_names

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI package not installed. Run: pip install openai")


def get_openai_client() -> Optional["OpenAI"]:
    """Get OpenAI client using environment variable"""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY environment variable not set")
        return None
    
    return OpenAI(api_key=api_key)


def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def encode_pdf_page_to_base64(pdf_path: str, page_num: int = 0) -> Optional[str]:
    """Convert a PDF page to base64 encoded image"""
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            page_num = 0
        
        page = doc[page_num]
        # Render at 2x resolution for better quality
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        doc.close()
        
        return base64.standard_b64encode(png_bytes).decode("utf-8")
    except ImportError:
        print("⚠️ PyMuPDF not installed. Run: pip install pymupdf")
        return None
    except Exception as e:
        print(f"❌ Error converting PDF: {e}")
        return None


def analyze_pdf_layout(pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI Vision to analyze the layout of a PDF report.
    
    Returns a structured analysis of:
    - Header elements (company name, logo position, etc.)
    - Column layout
    - Field positions
    - Data types visible
    - Formatting patterns
    """
    client = get_openai_client()
    if not client:
        return None
    
    # Convert PDF to image
    image_base64 = encode_pdf_page_to_base64(pdf_path)
    if not image_base64:
        return None
    
    print(f"🔍 Analyzing PDF layout with OpenAI Vision...")
    
    prompt = """Analyze this report/invoice PDF and extract its structure. Provide a JSON response with:

1. "header": Description of header area (company name, logo, address positions)
2. "sections": List of distinct sections in the report
3. "fields": List of visible data fields with:
   - "name": Field name/label
   - "position": Approximate position (top-left, center, etc.)
   - "data_type": text, currency, date, number
   - "format": Any visible formatting (currency symbol, date format, etc.)
4. "tables": Any tabular data with column headers
5. "layout_notes": Important layout observations (margins, spacing, alignment)

Return ONLY valid JSON, no markdown or explanation."""

    # Try multiple models in order of preference
    models_to_try = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview"]
    
    last_error = None
    for model in models_to_try:
        try:
            print(f"   Trying model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            break  # Success, exit loop
        except Exception as e:
            last_error = e
            print(f"   ⚠️ {model} not available: {str(e)[:50]}...")
            continue
    else:
        # All models failed
        print(f"❌ No vision models available: {last_error}")
        return None
    
    try:
        
        result_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {"raw_analysis": result_text}
            
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return None


def compare_conversion(
    pdf_path: str,
    analysis_json_path: str,
    repx_path: str
) -> Dict[str, Any]:
    """
    Compare PDF analysis with converted REPX to identify gaps.
    
    Returns a report of:
    - Matched fields
    - Missing fields
    - Extra fields
    - Format mismatches
    """
    # Load the conversion analysis
    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        conversion_analysis = json.load(f)
    
    # Extract data from nested structure if needed
    labels = conversion_analysis.get('labels', [])
    field_expressions = conversion_analysis.get('field_expressions', [])
    fonts = conversion_analysis.get('fonts', [])
    
    # Check for nested 'basic' structure
    if not labels and 'basic' in conversion_analysis:
        basic = conversion_analysis['basic']
        # Extract labels from strings (those in quotes that look like labels)
        strings = basic.get('strings', [])
        labels = [s.strip('"') for s in strings if s.startswith('"') and s.endswith('"') and not '(' in s]
        # Extract field expressions (those with function calls)
        field_expressions = [s for s in strings if '(' in s and not s.startswith('"')]
        fonts = basic.get('fonts', [])
    
    # Get PDF analysis
    pdf_analysis = analyze_pdf_layout(pdf_path)
    if not pdf_analysis:
        return {"error": "Could not analyze PDF"}
    
    print(f"🔄 Comparing conversion results...")
    
    # Extract PDF field names
    pdf_fields = []
    if 'fields' in pdf_analysis:
        pdf_fields = [f.get('name', '') for f in pdf_analysis['fields'] if f.get('name')]
    
    # Perform local field matching first
    print(f"   📊 Local matching: {len(pdf_fields)} PDF fields vs {len(labels)} FRT labels")
    local_matches = match_field_names(pdf_fields, labels)
    
    matched = list(local_matches.keys())
    missing = [f for f in pdf_fields if f not in local_matches]
    
    print(f"   ✅ Locally matched: {len(matched)} fields")
    print(f"   ⚠️ Potentially missing: {len(missing)} fields")
    
    # Use GPT to refine the comparison
    client = get_openai_client()
    if not client:
        # Return local analysis only
        return {
            "matched": matched,
            "matched_details": local_matches,
            "missing_in_conversion": missing,
            "extra_in_conversion": [l for l in labels if l not in local_matches.values()],
            "format_issues": [],
            "recommendations": ["OpenAI not available - using local matching only"]
        }
    
    # Create comparison prompt
    prompt = f"""Compare these two analyses of the same report:

ORIGINAL PDF ANALYSIS:
{json.dumps(pdf_analysis, indent=2)}

CONVERTED FOXPRO REPORT ANALYSIS:
Labels found: {labels[:30]}... (total: {len(labels)})
Field expressions found: {field_expressions[:20]}... (total: {len(field_expressions)})
Fonts: {fonts}

LOCAL MATCHING RESULTS (already performed):
Matched fields: {matched}
Potentially missing: {missing}

Refine this comparison. Some fields may match with different naming conventions.
For example: "PREVIOUS BALANCE" in FRT matches "Previous Balance" in PDF.

Return JSON with:
1. "matched": Fields that appear in both (confirmed matches)
2. "missing_in_conversion": Fields truly missing from conversion
3. "extra_in_conversion": Fields in conversion not in PDF  
4. "format_issues": Any formatting differences
5. "recommendations": Suggestions to improve

Return ONLY valid JSON."""

    # Try multiple models in order of preference
    models_to_try = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    
    last_error = None
    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096
            )
            break  # Success
        except Exception as e:
            last_error = e
            continue
    else:
        print(f"❌ No models available: {last_error}")
        return {"error": str(last_error)}
    
    try:
        result_text = response.choices[0].message.content
        
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text)
    except json.JSONDecodeError:
        return {"raw_comparison": result_text}
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return {"error": str(e)}


def validate_conversion(
    pdf_path: str,
    frt_analysis_path: str,
    output_report_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main validation function - analyzes PDF and compares with FRT conversion.
    
    Args:
        pdf_path: Path to original PDF report
        frt_analysis_path: Path to JSON analysis from FRT conversion
        output_report_path: Optional path to save validation report
    
    Returns:
        Validation report dictionary
    """
    print("=" * 60)
    print("📊 PDF Validation Report")
    print("=" * 60)
    
    pdf_path = Path(pdf_path)
    frt_analysis_path = Path(frt_analysis_path)
    
    if not pdf_path.exists():
        return {"error": f"PDF not found: {pdf_path}"}
    
    if not frt_analysis_path.exists():
        return {"error": f"Analysis file not found: {frt_analysis_path}"}
    
    # Analyze PDF
    print(f"\n📄 Analyzing PDF: {pdf_path.name}")
    pdf_analysis = analyze_pdf_layout(str(pdf_path))
    
    if not pdf_analysis:
        return {"error": "Failed to analyze PDF"}
    
    print("✅ PDF analysis complete")
    
    # Load FRT analysis
    with open(frt_analysis_path, 'r', encoding='utf-8') as f:
        frt_analysis = json.load(f)
    
    # Compare
    print(f"\n🔄 Comparing with FRT conversion...")
    
    # Extract FRT data from nested structure if needed
    labels = frt_analysis.get('labels', [])
    field_expressions = frt_analysis.get('field_expressions', [])
    fonts = frt_analysis.get('fonts', [])
    
    if not labels and 'basic' in frt_analysis:
        basic = frt_analysis['basic']
        strings = basic.get('strings', [])
        labels = [s.strip('"') for s in strings if s.startswith('"') and s.endswith('"') and not '(' in s]
        field_expressions = [s for s in strings if '(' in s and not s.startswith('"')]
        fonts = basic.get('fonts', [])
    
    report = {
        "pdf_file": str(pdf_path),
        "frt_analysis_file": str(frt_analysis_path),
        "pdf_analysis": pdf_analysis,
        "frt_summary": {
            "labels_count": len(labels),
            "fields_count": len(field_expressions),
            "fonts": fonts,
            "sample_labels": labels[:10],
            "sample_fields": field_expressions[:10]
        },
        "comparison": compare_conversion(
            str(pdf_path),
            str(frt_analysis_path),
            ""  # REPX path not needed for comparison
        )
    }
    
    # Save report if path provided
    if output_report_path:
        with open(output_report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"\n📊 Validation report saved to: {output_report_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    comparison = report.get("comparison", {})
    if "matched" in comparison:
        print(f"✅ Matched fields: {len(comparison.get('matched', []))}")
    if "missing_in_conversion" in comparison:
        missing = comparison.get('missing_in_conversion', [])
        print(f"⚠️ Missing in conversion: {len(missing)}")
        for item in missing[:5]:  # Show first 5
            print(f"   - {item}")
    if "recommendations" in comparison:
        print(f"\n💡 Recommendations:")
        for rec in comparison.get('recommendations', [])[:3]:
            print(f"   • {rec}")
    
    return report


if __name__ == "__main__":
    import sys
    
    # Check for OpenAI key
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print(f"✅ OpenAI API key found (length: {len(api_key)})")
    else:
        print("❌ OPENAI_API_KEY not set in environment")
        sys.exit(1)
    
    # Look for PDF files in current directory
    pdf_files = list(Path(".").glob("*.pdf")) + list(Path(".").glob("*.PDF"))
    
    if pdf_files:
        print(f"\n📂 Found PDF files: {[p.name for p in pdf_files]}")
        
        # Look for corresponding analysis files
        for pdf_file in pdf_files:
            # Try to find matching analysis
            base_name = pdf_file.stem
            analysis_patterns = [
                f"{base_name}.analysis.json",
                f"FoxPro_{base_name}.analysis.json",
                "FoxPro_Ebill.analysis.json"  # Default
            ]
            
            for pattern in analysis_patterns:
                analysis_path = Path(pattern)
                if analysis_path.exists():
                    print(f"\n🔍 Validating {pdf_file.name} against {analysis_path.name}")
                    result = validate_conversion(
                        str(pdf_file),
                        str(analysis_path),
                        f"{base_name}_validation.json"
                    )
                    break
            else:
                print(f"\n⚠️ No analysis file found for {pdf_file.name}")
                # Just analyze the PDF
                print("📄 Analyzing PDF layout only...")
                pdf_analysis = analyze_pdf_layout(str(pdf_file))
                if pdf_analysis:
                    output_path = f"{base_name}_pdf_analysis.json"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(pdf_analysis, f, indent=2)
                    print(f"✅ PDF analysis saved to: {output_path}")
    else:
        print("\n⚠️ No PDF files found in current directory")
        print("Usage: python pdf_validator.py")
        print("       (Place PDF files in the same directory)")
