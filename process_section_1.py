#!/usr/bin/env python3
"""
Process Section 1: Introduction and First Questions (Pages 1-5)
"""

import sys
sys.path.append('.')

from agents.structure_agent import StructureAgent  
from agents.content_agent import ContentAgent
from io_utils.pdf_utils import read_pdf_all_text_with_spans
from pathlib import Path
import json

def process_section_1():
    """Process first section of survey"""
    
    # Extract full PDF first
    pdf_path = Path('data/HTOPS_2502_Questionnaire_ENGLISH.pdf')
    full_text, page_spans = read_pdf_all_text_with_spans(pdf_path)
    
    # Get first 5 pages
    if len(page_spans) >= 5:
        section_start = page_spans[0][0]
        section_end = page_spans[4][1]  # End of page 5
        section_text = full_text[section_start:section_end]
    else:
        section_text = full_text
    
    print(f"Section 1 text length: {len(section_text)} chars")
    print("\n=== FIRST 500 CHARS ===")
    print(section_text[:500])
    
    # Process with Structure Agent
    print("\n=== Processing Structure ===")
    structure_agent = StructureAgent(model="gpt-4", passes=2, workers=1, char_buf=1200, quiet=False)
    structure_result = structure_agent.run(section_text)
    
    # Process with Content Agent  
    print("\n=== Processing Content ===")
    content_agent = ContentAgent(model="gpt-4", passes=2, workers=1, char_buf=1200, quiet=False)
    content_result = content_agent.run(section_text)
    
    # Save results
    output_dir = Path('output/sections')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'section_1_structure.json', 'w') as f:
        json.dump(structure_result, f, indent=2)
    
    with open(output_dir / 'section_1_content.json', 'w') as f:
        json.dump(content_result, f, indent=2)
    
    print(f"\nResults saved to {output_dir}")
    return structure_result, content_result

if __name__ == "__main__":
    structure, content = process_section_1()
    print("Section 1 processing complete!")
