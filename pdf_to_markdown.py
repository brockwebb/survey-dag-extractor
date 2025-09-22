#!/usr/bin/env python3
"""
PDF to Markdown Converter for Survey Documents

Converts survey PDFs to clean markdown using IBM's docling for better structure preservation.
Run this before the main extraction pipeline.

Usage:
    python pdf_to_markdown.py --input data/HTOPS_2502_Questionnaire_ENGLISH.pdf
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

def convert_pdf_to_markdown(pdf_path: Path, output_path: Path = None) -> Path:
    """Convert PDF to markdown using docling."""
    
    print(f"📄 Converting PDF to Markdown")
    print(f"   Input: {pdf_path}")
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Default output path
    if not output_path:
        output_path = pdf_path.with_suffix('.md')
    
    try:
        # Try importing docling
        try:
            from docling.document_converter import DocumentConverter
            print("   🔧 Using IBM docling for conversion")
            
            # Initialize converter
            converter = DocumentConverter()
            
            # Convert PDF
            result = converter.convert(pdf_path)
            
            # Extract markdown content
            markdown_content = result.document.export_to_markdown()
            
        except ImportError:
            print("   ⚠️  docling not installed, falling back to PyPDF2")
            markdown_content = convert_with_pypdf2(pdf_path)
        
        # Save markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"   ✅ Converted to: {output_path}")
        print(f"   📏 Size: {len(markdown_content):,} characters")
        
        # Analyze content
        analyze_markdown_content(markdown_content)
        
        return output_path
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        raise

def convert_with_pypdf2(pdf_path: Path) -> str:
    """Fallback conversion using PyPDF2."""
    
    try:
        import PyPDF2
    except ImportError:
        raise ImportError("Neither docling nor PyPDF2 is available. Install with: pip install docling PyPDF2")
    
    markdown_content = "# Survey Document\n\n"
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                markdown_content += f"## Page {page_num}\n\n{text}\n\n"
    
    return markdown_content

def analyze_markdown_content(content: str) -> None:
    """Analyze converted markdown content."""
    
    lines = content.split('\n')
    
    # Count structural elements
    headers = len([line for line in lines if line.startswith('#')])
    questions = len([line for line in lines if any(marker in line.lower() for marker in ['?', 'select', 'enter', 'mark'])])
    
    print(f"   📊 Analysis:")
    print(f"      Lines: {len(lines):,}")
    print(f"      Headers: {headers}")
    print(f"      Potential questions: {questions}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert survey PDF to markdown")
    parser.add_argument("--input", required=True, help="Input PDF file")
    parser.add_argument("--output", help="Output markdown file (default: same name with .md)")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    try:
        result_path = convert_pdf_to_markdown(pdf_path, output_path)
        print(f"\n🎉 Conversion completed: {result_path}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
