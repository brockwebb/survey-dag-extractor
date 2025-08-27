import sys
sys.path.append('.')

from io_utils.pdf_utils import read_pdf_all_text_with_spans
from pathlib import Path

# Extract text from the HTOPS PDF
pdf_path = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/data/HTOPS_2502_Questionnaire_ENGLISH.pdf')
full_text, page_spans = read_pdf_all_text_with_spans(pdf_path)

print(f"Extracted {len(full_text)} characters from {len(page_spans)} pages")
print("\n=== FIRST 2000 CHARACTERS ===")
print(full_text[:2000])
print("\n=== PAGE SPANS ===")
for i, (start, end, page_num) in enumerate(page_spans[:5]):
    print(f"Page {page_num}: chars {start}-{end}")

# Write full text to a file for analysis
with open('/Users/brock/Documents/GitHub/survey-dag-extractor/extracted_text.txt', 'w', encoding='utf-8') as f:
    f.write(full_text)
    
print("\nFull text written to extracted_text.txt")
