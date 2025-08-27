#!/usr/bin/env python3
"""
Break HTOPS Survey into Manageable Chunks
"""

import sys
sys.path.append('/Users/brock/Documents/GitHub/survey-dag-extractor')

from io_utils.pdf_utils import read_pdf_all_text_with_spans
from pathlib import Path
import json

def create_section_files():
    """Break the survey into page-based sections for easier processing"""
    
    # Extract the PDF
    pdf_path = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/data/HTOPS_2502_Questionnaire_ENGLISH.pdf')
    full_text, page_spans = read_pdf_all_text_with_spans(pdf_path)
    
    print(f"Extracted {len(full_text)} characters from {len(page_spans)} pages")
    
    # Create sections directory
    sections_dir = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/sections')
    sections_dir.mkdir(exist_ok=True)
    
    # Break into 5-page chunks with 1 page overlap
    chunk_size = 5
    overlap = 1
    
    sections = []
    
    for i in range(0, len(page_spans), chunk_size - overlap):
        start_page = i
        end_page = min(i + chunk_size, len(page_spans))
        
        # Get the text for this chunk
        if start_page < len(page_spans):
            chunk_start = page_spans[start_page][0]  # Start char of first page
            
            if end_page < len(page_spans):
                chunk_end = page_spans[end_page - 1][1]  # End char of last page
            else:
                chunk_end = page_spans[-1][1]  # End of document
            
            chunk_text = full_text[chunk_start:chunk_end]
            
            section_info = {
                'section_id': f'section_{start_page+1}_{end_page}',
                'pages': list(range(start_page + 1, end_page + 1)),
                'char_start': chunk_start,
                'char_end': chunk_end,
                'text_length': len(chunk_text)
            }
            
            # Write section text file
            section_file = sections_dir / f'section_{start_page+1}_{end_page}.txt'
            with open(section_file, 'w', encoding='utf-8') as f:
                f.write(f"SECTION: Pages {start_page+1} to {end_page}\n")
                f.write("=" * 50 + "\n\n")
                f.write(chunk_text)
            
            sections.append(section_info)
            print(f"Created {section_file} - Pages {start_page+1}-{end_page} ({len(chunk_text)} chars)")
    
    # Write sections index
    index_file = sections_dir / 'sections_index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_pages': len(page_spans),
            'total_chars': len(full_text),
            'sections': sections
        }, f, indent=2)
    
    print(f"\nCreated {len(sections)} sections")
    print(f"Index written to {index_file}")
    
    # Also create a sample of the first few pages to understand structure
    sample_pages = 3
    sample_text = full_text[page_spans[0][0]:page_spans[min(sample_pages-1, len(page_spans)-1)][1]]
    
    sample_file = sections_dir / 'sample_first_3_pages.txt'
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write("SAMPLE: First 3 pages for manual review\n")
        f.write("=" * 50 + "\n\n")
        f.write(sample_text)
    
    print(f"Sample file created: {sample_file}")
    return sections

if __name__ == "__main__":
    sections = create_section_files()
