#!/usr/bin/env python3
"""
Debug Routing Agent - Diagnose the routing extraction failure

This script debugs the routing agent to identify why it's returning 1/118 instead of 118/119.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
import openai

load_dotenv()

def load_test_data():
    """Load a small batch of test questions."""
    data_file = Path("data/htops_complete_nodes_minimal.json")
    with open(data_file) as f:
        nodes = json.load(f)
    
    # Get first 3 questions for testing
    questions = [node for node in nodes if node.get("type") == "question"][:3]
    return questions

def test_pdf_loading():
    """Test if PDF context is loading correctly."""
    pdf_path = Path("data/HTOPS_2502_Questionnaire_ENGLISH.pdf")
    print(f"🔍 Testing PDF loading from: {pdf_path}")
    print(f"   PDF exists: {pdf_path.exists()}")
    
    if pdf_path.exists():
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_text = ""
                
                for page_num in range(min(3, len(pdf_reader.pages))):  # First 3 pages
                    page = pdf_reader.pages[page_num]
                    pdf_text += page.extract_text() + "\n\n"
                
                print(f"   PDF loaded: {len(pdf_text):,} characters from first 3 pages")
                print(f"   First 500 chars: {pdf_text[:500]}")
                return pdf_text
                
        except ImportError:
            print("   ⚠️  PyPDF2 not installed")
        except Exception as e:
            print(f"   ❌ PDF load error: {e}")
    
    return ""

def test_api_call(questions, pdf_context):
    """Test the API call directly."""
    print(f"\n🤖 Testing OpenAI API call")
    
    client = openai.OpenAI()
    
    # Build prompt like the agent does
    prompt = f"""Analyze these {len(questions)} survey questions and generate routing assignments:

COMPLETE SURVEY CONTEXT:
{pdf_context[:2000]}...

QUESTIONS TO ANALYZE ({len(questions)} questions):
"""
    
    for q in questions:
        prompt += f"""
Question ID: {q['id']}
Text: {q.get('text', 'N/A')[:100]}...
Block: {q.get('block', 'unknown')}
Order: {q.get('order_index', 0)}
Type: {q.get('type', 'unknown')}
"""
    
    prompt += """
Return JSON array with COMPLETE extraction:
[
  {
    "question_id": "{q['id']}",
    "complete_question_text": "Full question text from survey",
    "response_options": [
      {"value": 1, "label": "Yes", "type": "categorical"},
      {"value": 2, "label": "No", "type": "categorical"}
    ],
    "question_type": "single_select|multiple_select|numeric|text|instruction",
    "universe_condition": "Who should see this question",
    "routing_assignments": [
      {
        "response_value": "1",
        "target_question": "NEXT_Q",
        "predicate": "RESPONSE == 1",
        "edge_type": "branch",
        "confidence": 0.9
      }
    ],
    "skip_patterns": ["Questions skipped based on responses"],
    "block": "survey_section",
    "order_index": 15,
    "validation_rules": ["Any validation requirements"],
    "confidence": 0.85,
    "reasoning": "Explanation of routing decisions"
  }
]

Extract ALL available data using the complete survey context."""
    
    print(f"   Prompt length: {len(prompt):,} characters")
    print(f"   First 300 chars of prompt: {prompt[:300]}...")
    
    try:
        # Test API parameters for gpt-5
        api_params = {
            "model": "gpt-5",
            "messages": [
                {"role": "system", "content": "You are a survey logic expert analyzing question routing patterns."},
                {"role": "user", "content": prompt}
            ],
            "max_completion_tokens": 4000  # gpt-5 parameter
        }
        
        print(f"   Using API parameters: {list(api_params.keys())}")
        
        response = client.chat.completions.create(**api_params)
        
        response_text = response.choices[0].message.content
        print(f"   ✅ API call successful!")
        print(f"   Response length: {len(response_text):,} characters")
        print(f"   First 500 chars: {response_text[:500]}")
        print(f"   Last 500 chars: {response_text[-500:]}")
        
        return response_text
        
    except Exception as e:
        print(f"   ❌ API call failed: {e}")
        return None

def test_json_parsing(response_text):
    """Test JSON extraction and parsing."""
    print(f"\n📝 Testing JSON parsing")
    
    if not response_text:
        print("   No response text to parse")
        return []
    
    import re
    
    # Look for JSON array
    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if not json_match:
        print("   ❌ No JSON array found in response")
        print("   Looking for other JSON patterns...")
        
        # Look for any JSON-like structure
        json_patterns = [
            r'\{.*\}',  # Single object
            r'```json\s*(\[.*\])\s*```',  # Markdown JSON block  
            r'```\s*(\[.*\])\s*```',  # Generic code block
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                print(f"   Found alternative JSON pattern: {pattern}")
                json_text = match.group(1) if match.groups() else match.group(0)
                print(f"   Extracted JSON (first 200 chars): {json_text[:200]}...")
                break
        else:
            print("   ❌ No JSON found at all")
            return []
    else:
        json_text = json_match.group()
        print(f"   ✅ Found JSON array")
        print(f"   JSON length: {len(json_text):,} characters")
        print(f"   JSON preview (first 300 chars): {json_text[:300]}...")
    
    try:
        extractions_data = json.loads(json_text)
        print(f"   ✅ JSON parsed successfully!")
        print(f"   Number of extractions: {len(extractions_data)}")
        
        for i, item in enumerate(extractions_data[:2]):  # Show first 2
            print(f"   Extraction {i+1}: {item.get('question_id', 'NO_ID')} - {len(item.get('routing_assignments', []))} routing assignments")
        
        return extractions_data
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON parsing failed: {e}")
        print(f"   Invalid JSON at position {e.pos}")
        if hasattr(e, 'pos') and e.pos < len(json_text):
            start = max(0, e.pos - 50)
            end = min(len(json_text), e.pos + 50)
            print(f"   Context around error: ...{json_text[start:end]}...")
        return []

def main():
    """Run complete debugging."""
    print("🚨 ROUTING AGENT DEBUGGING")
    print("="*50)
    
    # Step 1: Test PDF loading
    pdf_context = test_pdf_loading()
    
    # Step 2: Load test data
    print(f"\n📊 Loading test data")
    questions = load_test_data()
    print(f"   Loaded {len(questions)} test questions")
    for q in questions:
        print(f"   - {q['id']}: {q.get('text', 'NO_TEXT')[:50]}...")
    
    # Step 3: Test API call
    response_text = test_api_call(questions, pdf_context)
    
    # Step 4: Test JSON parsing
    extractions = test_json_parsing(response_text)
    
    # Final diagnosis
    print(f"\n🎯 DIAGNOSIS:")
    print(f"   PDF Context: {'✅ Loaded' if pdf_context else '❌ Failed'}")
    print(f"   API Call: {'✅ Success' if response_text else '❌ Failed'}")
    print(f"   JSON Parsing: {'✅ Success' if extractions else '❌ Failed'}")
    print(f"   Extractions Found: {len(extractions)}")
    
    if len(extractions) == 0:
        print(f"\n🔥 ROOT CAUSE: No valid extractions returned!")
        if not pdf_context:
            print("   - PDF context loading is broken")
        if not response_text:
            print("   - OpenAI API call is failing")
        elif extractions == []:
            print("   - JSON response parsing is broken")
    else:
        print(f"\n✅ DEBUGGING SUCCESS: Found {len(extractions)} valid extractions")

if __name__ == "__main__":
    main()
