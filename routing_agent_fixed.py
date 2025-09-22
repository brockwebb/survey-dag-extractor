#!/usr/bin/env python3
"""
Fixed Routing Assignment Agent - Debug version

Key fixes applied:
1. Fixed gpt-5 API parameters (removed unsupported temperature/max_tokens)
2. Added detailed error logging and debug prints 
3. Reduced PDF context length to prevent timeouts
4. Added robust error handling for API calls
5. Fixed prompt length issues
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
import os
from dataclasses import dataclass

# Load environment from .env file
from dotenv import load_dotenv
load_dotenv()

def load_agent_config() -> Dict[str, Any]:
    """Load agent configuration from config file."""
    config_path = Path(__file__).parent / "agent_config.json"
    with open(config_path, 'r') as f:
        return json.load(f)

@dataclass
class RouteAssignment:
    """Represents a routing assignment for a question."""
    source_question: str
    response_value: str
    target_question: str
    predicate: str
    edge_type: str
    priority: int

class RoutingAgentFixed:
    """Fixed routing assignment agent with improved error handling."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize routing agent."""
        # Load config from file if not provided
        if config is None:
            full_config = load_agent_config()
            config = full_config['agent_config']
        
        self.config = config
        self.batch_size = config.get('batch_settings', {}).get('default_batch_size', 10)
        
        # Model settings from config
        model_settings = config.get('model_settings', {})
        self.model = model_settings.get('model', 'gpt-5')
        
        # Setup OpenAI client
        self.client = openai.OpenAI()
        
        # Load truncated survey context for efficiency
        self.full_survey_context = self._load_truncated_survey_context()
        
        print(f"🤖 Fixed Routing Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Batch size: {self.batch_size}")
        print(f"   PDF context: {len(self.full_survey_context):,} characters")
        
        # Track processing state
        self.processed_batches = []
        self.routing_assignments = []
        self.debug_mode = True  # Enable debugging
        
    def _load_truncated_survey_context(self) -> str:
        """Load TRUNCATED survey context to prevent timeouts."""
        
        pdf_path = Path(__file__).parent.parent / "data" / "HTOPS_2502_Questionnaire_ENGLISH.pdf"
        if pdf_path.exists():
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pdf_text = ""
                    
                    # CRITICAL FIX: Only load first 10 pages to prevent timeouts
                    max_pages = min(10, len(pdf_reader.pages))
                    
                    for page_num in range(max_pages):
                        page = pdf_reader.pages[page_num]
                        pdf_text += page.extract_text() + "\n\n"
                    
                    # CRITICAL FIX: Truncate to 10,000 characters max
                    if len(pdf_text) > 10000:
                        pdf_text = pdf_text[:10000] + "\n[... truncated for efficiency ...]"
                    
                    print(f"   📄 Loaded truncated PDF context: {len(pdf_text):,} characters from {max_pages} pages")
                    return pdf_text
                    
            except ImportError:
                print(f"   ⚠️  PyPDF2 not installed")
            except Exception as e:
                print(f"   ⚠️  Could not load PDF: {e}")
        else:
            print(f"   ⚠️  PDF not found at: {pdf_path}")
        
        return "Survey context not available"
        
    def process_survey(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """Process entire survey in batches with improved error handling."""
        print(f"🤖 Starting Fixed Routing Assignment Agent")
        print(f"   Input: {input_file}")
        print(f"   Batch Size: {self.batch_size}")
        
        # Load survey data
        with open(input_file) as f:
            nodes = json.load(f)
        
        print(f"   Total Nodes: {len(nodes)}")
        
        # Process in batches
        batches = self._create_batches(nodes)
        print(f"   Processing {len(batches)} batches...")
        
        all_extractions = []
        successful_batches = 0
        failed_batches = 0
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n📦 Processing Batch {batch_num}/{len(batches)} ({len(batch)} questions)")
            
            try:
                extractions = self._process_batch_with_retry(batch, batch_num)
                
                if extractions:
                    all_extractions.extend(extractions)
                    successful_batches += 1
                    print(f"   ✅ Generated {len(extractions)} complete extractions")
                else:
                    failed_batches += 1
                    print(f"   ❌ No extractions generated")
                
                # Save batch results with debugging info
                batch_output = {
                    "batch_number": batch_num,
                    "batch_size": len(batch),
                    "questions_processed": [q["id"] for q in batch if q.get("type") == "question"],
                    "extractions": extractions,
                    "success": len(extractions) > 0,
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_file = output_dir / f"routing_batch_{batch_num:02d}.json"
                with open(batch_file, 'w') as f:
                    json.dump(batch_output, f, indent=2)
                
            except Exception as e:
                failed_batches += 1
                print(f"   ❌ Batch {batch_num} failed with exception: {e}")
                
                # Save error batch
                error_output = {
                    "batch_number": batch_num,
                    "batch_size": len(batch),
                    "questions_processed": [q["id"] for q in batch if q.get("type") == "question"],
                    "extractions": [],
                    "error": str(e),
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_file = output_dir / f"routing_batch_{batch_num:02d}_ERROR.json"
                with open(batch_file, 'w') as f:
                    json.dump(error_output, f, indent=2)
                
                continue
        
        # Generate final routing report
        result = self._generate_final_result(all_extractions, nodes, output_dir)
        
        print(f"\n🎯 Fixed Routing Agent Results!")
        print(f"   ✅ Successful Batches: {successful_batches}/{len(batches)}")
        print(f"   ❌ Failed Batches: {failed_batches}/{len(batches)}")
        print(f"   Total Extractions: {len(all_extractions)}")
        print(f"   Success Rate: {len(all_extractions)/max(1,len([n for n in nodes if n.get('type')=='question'])):.1%}")
        
        return result
    
    def _create_batches(self, nodes: List[Dict]) -> List[List[Dict]]:
        """Split nodes into processing batches."""
        batches = []
        current_batch = []
        
        for node in nodes:
            current_batch.append(node)
            
            if len(current_batch) >= self.batch_size:
                batches.append(current_batch.copy())
                current_batch = []
        
        # Add remaining nodes
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _process_batch_with_retry(self, batch: List[Dict], batch_num: int, max_retries: int = 2) -> List[Dict]:
        """Process batch with retry logic."""
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f"   🔄 Retry attempt {attempt}")
                
                extractions = self._process_batch(batch, batch_num)
                
                if extractions:  # Success
                    return extractions
                else:
                    print(f"   ⚠️ Attempt {attempt + 1} returned no extractions")
                    
            except Exception as e:
                print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:  # Last attempt
                    raise e
        
        return []  # All attempts failed
    
    def _process_batch(self, batch: List[Dict], batch_num: int) -> List[Dict]:
        """Process a batch of questions to generate routing assignments."""
        
        # Filter to questions only
        questions = [node for node in batch if node.get("type") == "question"]
        if not questions:
            print(f"   No questions in batch {batch_num}")
            return []
        
        print(f"   Questions: {[q['id'] for q in questions]}")
        
        # Build shortened prompt
        prompt = self._build_shortened_routing_prompt(questions)
        
        if self.debug_mode:
            print(f"   Prompt length: {len(prompt):,} characters")
        
        # Make API call with proper error handling
        try:
            response_text = self._make_api_call(prompt)
            
            if not response_text:
                print(f"   No response from API")
                return []
            
            # Parse extractions
            extractions = self._parse_complete_extraction(response_text, questions)
            
            if self.debug_mode:
                print(f"   Parsed {len(extractions)} extractions")
            
            return extractions
            
        except Exception as e:
            print(f"   API processing error: {e}")
            return []
    
    def _build_shortened_routing_prompt(self, questions: List[Dict]) -> str:
        """Build shortened prompt to prevent timeouts."""
        
        # CRITICAL FIX: Much shorter prompt
        prompt = f"""Extract routing logic for these {len(questions)} survey questions.

SURVEY CONTEXT (key info):
{self.full_survey_context}

QUESTIONS TO ANALYZE:
"""
        
        for q in questions:
            # CRITICAL FIX: Truncate question text
            text = q.get('text', 'N/A')
            if len(text) > 100:
                text = text[:100] + '...'
            
            prompt += f"""
ID: {q['id']} | Block: {q.get('block', 'unknown')} | Order: {q.get('order_index', 0)}
Text: {text}
"""
        
        prompt += """
Return JSON array with routing data:
[
  {
    "question_id": "{question_id}",
    "complete_question_text": "Full question text",
    "response_options": [{"value": 1, "label": "Yes", "type": "categorical"}],
    "question_type": "single_select|multiple_select|numeric|text",
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
    "skip_patterns": ["Questions skipped"],
    "block": "survey_section",
    "order_index": 15,
    "validation_rules": ["Validation requirements"],
    "confidence": 0.85,
    "reasoning": "Logic explanation"
  }
]

IMPORTANT: Return valid JSON only."""
        
        return prompt
    
    def _make_api_call(self, prompt: str) -> Optional[str]:
        """Make API call with proper gpt-5 parameters."""
        
        try:
            # CRITICAL FIX: Correct gpt-5 API parameters
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a survey logic expert. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "max_completion_tokens": 3000  # gpt-5 parameter name
                # Note: temperature not supported in gpt-5, uses default of 1
            }
            
            if self.debug_mode:
                print(f"   API params: {list(api_params.keys())}")
                print(f"   Messages length: {len(api_params['messages'])}")
            
            response = self.client.chat.completions.create(**api_params)
            
            response_text = response.choices[0].message.content
            
            if self.debug_mode:
                print(f"   Response length: {len(response_text):,} characters")
                print(f"   First 200 chars: {response_text[:200]}")
            
            return response_text
            
        except Exception as e:
            print(f"   API call failed: {e}")
            return None
    
    def _parse_complete_extraction(self, response_text: str, questions: List[Dict]) -> List[Dict]:
        """Parse complete extraction response with better error handling."""
        
        try:
            # CRITICAL FIX: Better JSON extraction
            import re
            
            # Try to find JSON array
            json_patterns = [
                r'\\[.*?\\](?=\\s*(?:```|$))',  # JSON array until end or code block
                r'```json\\s*(\\[.*?\\])\\s*```',  # JSON in code block
                r'```\\s*(\\[.*?\\])\\s*```',  # JSON in generic code block
                r'(\\[\\s*{.*}\\s*\\])',  # Simple array pattern
            ]
            
            json_text = None
            for pattern in json_patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    json_text = match.group(1) if match.groups() else match.group(0)
                    if self.debug_mode:
                        print(f"   Found JSON with pattern: {pattern[:20]}...")
                    break
            
            if not json_text:
                print(f"   No JSON found in response")
                return []
            
            # Parse JSON
            extractions_data = json.loads(json_text)
            
            if not isinstance(extractions_data, list):
                print(f"   Response is not a JSON array")
                return []
            
            # Convert to extraction objects
            extractions = []
            for item in extractions_data:
                if not isinstance(item, dict):
                    continue
                    
                extraction = {
                    "question_id": item.get('question_id', ''),
                    "complete_question_text": item.get('complete_question_text', ''),
                    "response_options": item.get('response_options', []),
                    "question_type": item.get('question_type', 'unknown'),
                    "universe_condition": item.get('universe_condition', ''),
                    "routing_assignments": item.get('routing_assignments', []),
                    "skip_patterns": item.get('skip_patterns', []),
                    "block": item.get('block', ''),
                    "order_index": item.get('order_index', 0),
                    "validation_rules": item.get('validation_rules', []),
                    "confidence": float(item.get('confidence', 0.5)),
                    "reasoning": item.get('reasoning', '')
                }
                extractions.append(extraction)
            
            if self.debug_mode:
                print(f"   Successfully parsed {len(extractions)} extractions")
            
            return extractions
            
        except json.JSONDecodeError as e:
            print(f"   JSON parsing failed: {e}")
            return []
        except Exception as e:
            print(f"   Extraction parsing failed: {e}")
            return []
    
    def _generate_final_result(self, extractions: List[Dict], nodes: List[Dict], output_dir: Path) -> Dict[str, Any]:
        """Generate final extraction result with fixed field names."""
        
        # Create enhanced nodes with complete extraction data
        enhanced_nodes = []
        extraction_lookup = {e['question_id']: e for e in extractions}
        
        for node in nodes:
            enhanced_node = node.copy()
            
            # Add complete extraction data for this node
            if node['id'] in extraction_lookup:
                extraction = extraction_lookup[node['id']]
                
                # Update question text if extracted
                if extraction.get('complete_question_text'):
                    enhanced_node['text'] = extraction['complete_question_text']
                
                # Add response options
                if extraction.get('response_options'):
                    enhanced_node['response_options'] = extraction['response_options']
                
                # Add universe condition
                if extraction.get('universe_condition'):
                    enhanced_node['universe_condition'] = extraction['universe_condition']
                
                # Add routing assignments
                if extraction.get('routing_assignments'):
                    enhanced_node['routing_assignments'] = extraction['routing_assignments']
                
                # Add other metadata
                enhanced_node['extraction_metadata'] = {
                    'question_type': extraction.get('question_type'),
                    'skip_patterns': extraction.get('skip_patterns', []),
                    'validation_rules': extraction.get('validation_rules', []),
                    'confidence': extraction.get('confidence', 0),
                    'reasoning': extraction.get('reasoning', '')
                }
            
            enhanced_nodes.append(enhanced_node)
        
        # Count routing assignments from extractions
        total_routing_assignments = sum(len(e.get('routing_assignments', [])) for e in extractions)
        
        # Generate final report with FIXED field name
        result = {
            "metadata": {
                "agent": "RoutingAgentFixed",
                "version": "2.1",  # Updated version
                "processed_at": datetime.now().isoformat(),
                "total_nodes": len(nodes),
                "total_extractions": len(extractions),
                "total_routing_assignments": total_routing_assignments  # FIXED: correct field name
            },
            "enhanced_nodes": enhanced_nodes,
            "extraction_summary": {
                "questions_extracted": len(extractions),
                "questions_with_routing": len([e for e in extractions if e.get('routing_assignments')]),
                "questions_with_response_options": len([e for e in extractions if e.get('response_options')]),
                "avg_confidence": sum(e.get('confidence', 0) for e in extractions) / len(extractions) if extractions else 0,
                "blocks_processed": list(set(n.get("block") for n in nodes if n.get("block"))),
                "extraction_coverage": len(extractions) / max(1, len([n for n in nodes if n.get("type") == "question"]))
            }
        }
        
        # Save final result
        output_file = output_dir / "complete_extractions_fixed.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fixed Survey Routing Assignment")
    parser.add_argument("--input", required=True, help="Input JSON file (minimal nodes)")
    parser.add_argument("--output", default="output_fixed", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size (reduced for stability)")
    parser.add_argument("--model", default=None, help="OpenAI model to use (overrides config)")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Configure agent
    config = None
    if args.model or args.batch_size != 10:
        # Override config if command line options provided
        base_config = load_agent_config()['agent_config']
        if args.model:
            base_config['model_settings']['model'] = args.model
        if args.batch_size != 10:
            base_config['batch_settings']['default_batch_size'] = args.batch_size
        config = base_config
    
    # Run fixed routing agent
    agent = RoutingAgentFixed(config)
    result = agent.process_survey(input_file, output_dir)
    
    print(f"\n✅ Fixed Results saved to {output_dir}")
    print(f"📊 Enhanced nodes: {len(result.get('enhanced_nodes', []))}")
    print(f"🔗 Total routing assignments: {result['metadata']['total_routing_assignments']}")


if __name__ == "__main__":
    main()
