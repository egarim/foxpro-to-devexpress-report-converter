"""
FoxPro FRT to DevExpress REPX CLI Tool

Command-line interface for converting FoxPro reports to DevExpress format.

Usage:
    python cli.py convert <input.frt> [--pdf <example.pdf>] [--output <folder>]
    python cli.py batch <input_folder> [--output <folder>]
    python cli.py analyze <input.frt>
    python cli.py preview <report.repx> [--output <image.png>]
"""

import argparse
import sys
from pathlib import Path
from typing import List

from converter_v2 import convert_frt_to_repx, FRTToREPXConverter


def cmd_convert(args):
    """Convert a single FRT file to REPX"""
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return 1
    
    # Get PDF path if provided
    pdf_path = getattr(args, 'pdf', None)
    
    # Get output folder
    output_folder = getattr(args, 'output', 'output')
    
    try:
        result = convert_frt_to_repx(str(input_path), pdf_path, output_folder)
        print(f"\n✅ Conversion complete!")
        print(f"   📁 Output: {result['folder']}")
        return 0
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_batch(args):
    """Convert multiple FRT files in a folder"""
    
    input_folder = Path(args.input_folder)
    
    if not input_folder.exists():
        print(f"❌ Error: Input folder not found: {input_folder}")
        return 1
    
    output_folder = getattr(args, 'output', 'output')
    
    # Find all FRT files
    frt_files = list(input_folder.glob("*.frt")) + list(input_folder.glob("*.FRT"))
    
    if not frt_files:
        print(f"⚠️ No FRT files found in: {input_folder}")
        return 1
    
    print(f"📂 Found {len(frt_files)} FRT files to convert")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for frt_file in frt_files:
        try:
            print(f"\n🔄 Converting: {frt_file.name}")
            # Look for matching PDF
            pdf_candidates = list(frt_file.parent.glob(f"{frt_file.stem}*.pdf"))
            pdf_path = str(pdf_candidates[0]) if pdf_candidates else None
            
            convert_frt_to_repx(str(frt_file), pdf_path, output_folder)
            success_count += 1
        except Exception as e:
            print(f"❌ Error converting {frt_file.name}: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Batch Conversion Complete:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    
    return 0 if error_count == 0 else 1


def cmd_analyze(args):
    """Analyze an FRT file without converting"""
    from frt_parser import analyze_frt_deep
    import json
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return 1
    
    print(f"🔍 Analyzing: {input_path}")
    print("=" * 60)
    
    analysis = analyze_frt_deep(str(input_path))
    
    # Print summary
    basic = analysis.get("basic", {})
    strings = basic.get("strings", [])
    fonts = basic.get("fonts", [])
    
    labels = [s.strip('"') for s in strings if s.startswith('"') and s.endswith('"')]
    expressions = [s for s in strings if '(' in s]
    
    print(f"\n📊 Summary:")
    print(f"   Labels: {len(labels)}")
    print(f"   Expressions: {len(expressions)}")
    print(f"   Fonts: {len(fonts)}")
    
    print(f"\n🎨 Fonts: {', '.join(fonts)}")
    
    print(f"\n📝 Sample Labels:")
    for label in labels[:10]:
        print(f"   - {label}")
    
    # Save analysis to JSON
    output_folder = Path("output") / input_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)
    
    analysis_path = output_folder / f"{input_path.stem}_analysis.json"
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({
            "source": str(input_path),
            "labels": labels,
            "expressions": expressions,
            "fonts": fonts,
            "raw": analysis
        }, f, indent=2, default=str)
    
    print(f"\n📊 Full analysis saved to: {analysis_path}")
    
    return 0


def cmd_preview(args):
    """Generate preview image from REPX using C# tool"""
    import subprocess
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return 1
    
    # Check if preview tool exists
    preview_tool = Path("tools/RepxPreview/bin/Release/net8.0/win-x64/publish/RepxPreview.exe")
    
    if not preview_tool.exists():
        print("⚠️ Preview tool not built. Building now...")
        result = subprocess.run(
            ["dotnet", "publish", "-c", "Release", "-r", "win-x64"],
            cwd="tools/RepxPreview",
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Build failed: {result.stderr}")
            return 1
    
    output_path = getattr(args, 'output', None) or input_path.with_suffix('.png')
    
    result = subprocess.run(
        [str(preview_tool), str(input_path), str(output_path)],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="FoxPro FRT to DevExpress REPX Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s convert report.frt
  %(prog)s convert report.frt --pdf example.pdf --output ./output
  %(prog)s batch ./foxpro_reports --output ./output
  %(prog)s analyze report.frt
  %(prog)s preview report.repx --output preview.png
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert a single FRT file')
    convert_parser.add_argument('input', help='Input FRT file path')
    convert_parser.add_argument('--pdf', help='PDF example for reference')
    convert_parser.add_argument('--output', '-o', default='output', help='Output folder (default: output)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Convert multiple FRT files')
    batch_parser.add_argument('input_folder', help='Folder containing FRT files')
    batch_parser.add_argument('--output', '-o', default='output', help='Output folder (default: output)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze an FRT file')
    analyze_parser.add_argument('input', help='Input FRT file path')
    
    # Preview command
    preview_parser = subparsers.add_parser('preview', help='Generate preview image from REPX')
    preview_parser.add_argument('input', help='Input REPX file path')
    preview_parser.add_argument('--output', '-o', help='Output PNG file path')
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        return cmd_convert(args)
    elif args.command == 'batch':
        return cmd_batch(args)
    elif args.command == 'analyze':
        return cmd_analyze(args)
    elif args.command == 'preview':
        return cmd_preview(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
