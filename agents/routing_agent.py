#!/usr/bin/env python3
"""
Routing Assignment Agent - Automated Survey Logic Generation

Processes survey questions in batches of 20 to automatically generate routing logic,
edges, and predicates for complete survey DAG construction.

Usage:
    python routing_agent.py --input htops_complete_nodes_minimal.json --batch-size 20
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

class RoutingAgent:
    """Automated routing assignment agent using LLM analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize routing agent."""
        # Load config from file if not provided
        if config is None:
            full_config = load_agent_config()
            config = full_config['agent_config']
        
        self.config = config
        self.batch_size = config.get('batch_settings', {}).get('default_batch_size', 10)  # Reduced for full extraction
        
        # Model settings from config
        model_settings = config.get('model_settings', {})
        self.model = model_settings.get('model', 'gpt-5')
        
        # Setup OpenAI client
        self.client = openai.OpenAI()  # Uses OPENAI_API_KEY from environment
        
        # Load full survey context (markdown if available, otherwise PDF)
        self.full_survey_context = self._load_full_survey_context()
        
        print(f"🤖 Routing Agent initialized with {self.model}")
        
        # Track processing state
        self.processed_batches = []
        self.routing_assignments = []
        
    def _load_full_survey_context(self) -> str:
        """Load complete survey context from PDF."""
        
        pdf_path = Path(__file__).parent.parent / "data" / "HTOPS_2502_Questionnaire_ENGLISH.pdf"
        if pdf_path.exists():
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pdf_text = ""
                    
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_text += page.extract_text() + "\n\n"
                    
                    print(f"   📄 Loaded survey context from PDF: {len(pdf_text):,} characters")
                    return pdf_text
                    
            except ImportError:
                print(f"   ⚠️  PyPDF2 not installed - install with: pip install PyPDF2")
            except Exception as e:
                print(f"   ⚠️  Could not load PDF: {e}")
        else:
            print(f"   ⚠️  PDF not found at: {pdf_path}")
        
        return ""
        
    def process_survey(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """Process entire survey in batches."""
        print(f"🤖 Starting Routing Assignment Agent")
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
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n📦 Processing Batch {batch_num}/{len(batches)} ({len(batch)} questions)")
            
            try:
                extractions = self._process_batch(batch, batch_num)
                all_extractions.extend(extractions)
                
                # Save batch results
                batch_output = {
                    "batch_number": batch_num,
                    "batch_size": len(batch),
                    "questions_processed": [q["id"] for q in batch if q.get("type") == "question"],
                    "extractions": extractions,  # Complete extractions instead of just routing
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_file = output_dir / f"routing_batch_{batch_num:02d}.json"
                with open(batch_file, 'w') as f:
                    json.dump(batch_output, f, indent=2)
                
                print(f"   ✅ Generated {len(extractions)} complete extractions")
                
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                continue
        
        # Generate final routing report
        result = self._generate_final_result(all_extractions, nodes, output_dir)
        
        print(f"\n🎯 Complete Extraction Finished!")
        print(f"   Total Extractions: {len(all_extractions)}")
        
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
    
    def _process_batch(self, batch: List[Dict], batch_num: int) -> List[RouteAssignment]:
        """Process a batch of questions to generate routing assignments."""
        
        # Process ALL nodes - instructions need routing too
        processable_nodes = [node for node in batch if node.get("type") in ["question", "instruction", "terminal"]]
        if not processable_nodes:
            return []
        
        node_ids = [n['id'] for n in processable_nodes]
        print(f"   Nodes in batch: {node_ids}")
        print(f"   Node types: {[n.get('type') for n in processable_nodes]}")
        
        # Build context for LLM
        batch_context = self._build_batch_context(processable_nodes, batch)
        
        # Generate routing assignments using LLM
        prompt = self._build_routing_prompt(batch_context, processable_nodes)
        
        try:
            # Build API call parameters based on model - USE CONFIG ONLY
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            }
            
            # NO hardcoded parameters - config file controls everything
            print(f"   Making API call with model: {self.model}")
            print(f"   Prompt length: {len(prompt):,} characters")
            print(f"   System prompt length: {len(self._get_system_prompt()):,} characters")
            print(f"   API params: {list(api_params.keys())}")
            
            response = self.client.chat.completions.create(**api_params)
            
            print(f"   API call completed")
            print(f"   Response object type: {type(response)}")
            print(f"   Response choices length: {len(response.choices) if hasattr(response, 'choices') else 'NO_CHOICES'}")
            
            if not hasattr(response, 'choices') or len(response.choices) == 0:
                print(f"   ERROR: No choices in API response")
                return []
            
            choice = response.choices[0]
            print(f"   Choice type: {type(choice)}")
            print(f"   Choice has message: {hasattr(choice, 'message')}")
            
            if not hasattr(choice, 'message'):
                print(f"   ERROR: No message in API response choice")
                return []
            
            message = choice.message
            print(f"   Message type: {type(message)}")
            print(f"   Message has content: {hasattr(message, 'content')}")
            
            response_content = message.content
            print(f"   Response content type: {type(response_content)}")
            print(f"   Response content is None: {response_content is None}")
            print(f"   Response content length: {len(response_content) if response_content else 0}")
            
            # Check for finish reason
            if hasattr(choice, 'finish_reason'):
                print(f"   Finish reason: {choice.finish_reason}")
            
            # Check for refusal or other issues
            if hasattr(message, 'refusal') and message.refusal:
                print(f"   Model refused: {message.refusal}")
                return []
            
            if not response_content or len(response_content.strip()) == 0:
                print(f"   Empty or whitespace-only response from API")
                print(f"   Raw content: {repr(response_content)}")
                # Try a simpler prompt to test if it's a prompt length issue
                print(f"   This may be due to prompt length ({len(prompt):,} chars) or content filtering")
                return []
            
            # Parse complete extraction results
            extractions = self._parse_complete_extraction(response_content, processable_nodes)
            
            print(f"   Raw response length: {len(response_content)}")
            print(f"   Parsed extractions: {len(extractions)}")
            print(f"   Expected nodes: {len(processable_nodes)}")
            
            # Show which nodes were successfully extracted
            extracted_node_ids = [e.get('question_id', 'UNKNOWN') for e in extractions]
            print(f"   Successfully extracted: {extracted_node_ids}")
            
            # Show failed nodes
            failed_nodes = [n['id'] for n in processable_nodes if n['id'] not in extracted_node_ids]
            if failed_nodes:
                print(f"   FAILED nodes: {failed_nodes}")
            
            if len(extractions) != len(processable_nodes):
                print(f"   MISMATCH: Got {len(extractions)} extractions for {len(processable_nodes)} nodes")
            
            if len(extractions) == 0 and len(processable_nodes) > 0:
                print(f"   WARNING: No extractions parsed from {len(processable_nodes)} nodes")
                print(f"   Response length: {len(response_content)} chars")
                print(f"   Response start: {response_content[:200]}...")
            
            return extractions
            
        except Exception as e:
            print(f"   LLM processing error: {e}")
            return []
    
    def _build_batch_context(self, nodes: List[Dict], full_batch: List[Dict]) -> Dict[str, Any]:
        """Build context for the current batch."""
        
        # Get blocks represented in this batch
        blocks = list(set(n.get("block") for n in nodes if n.get("block")))
        
        # Find order progression
        order_indices = sorted([n.get("order_index", 0) for n in nodes])
        
        return {
            "batch_blocks": blocks,
            "order_range": f"{order_indices[0]}-{order_indices[-1]}" if order_indices else "unknown",
            "node_count": len(nodes),
            "question_count": len([n for n in nodes if n.get("type") == "question"]),
            "instruction_count": len([n for n in nodes if n.get("type") == "instruction"]),
            "terminal_count": len([n for n in nodes if n.get("type") == "terminal"])
        }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for routing analysis."""
        return """You are a survey logic expert analyzing question routing patterns for complex conditional routing.

Your task: Analyze survey questions and extract CONDITIONAL ROUTING LOGIC in v1.2 schema format.

IMPORTANT: Look for CROSS-QUESTION DEPENDENCIES where routing depends on multiple previous answers.

EXAMPLE CONDITIONAL PATTERNS:
- "If Q1=1 AND Q2=1 then go to Q5" (two conditions required)
- "If Q3=2 then go to Q8" (single condition)
- "If SCREENING_Q=3 AND ELIGIBILITY=1 then go to MAIN_SURVEY"
- "If AGE_GROUP=1 AND INCOME_LEVEL=2 then go to SPECIAL_QUESTIONS"
- "If Q2=2 then go to TERMINATION (regardless of other answers)"
- "Always go to NEXT_Q" (no conditions)

EXTRACT FOR EACH QUESTION:
1. **Complete question text** (if missing or incomplete in input)
2. **Response options** (values, labels, types) 
3. **Universe conditions** (who should see this question)
4. **CONDITIONAL ROUTING** with multiple conditions per edge
5. **Skip patterns** (what gets skipped)
6. **Question metadata** (type, block, validation rules)

CONDITIONAL ROUTING FORMAT:
"routing_assignments": [
  {
    "conditions": [
      {"variable": "Q1", "operator": "equals", "value": "1"},
      {"variable": "Q2", "operator": "equals", "value": "1"}
    ],
    "target_question": "Q5",
    "edge_type": "branch",
    "priority": 1,
    "confidence": 0.9
  }
]

RULES:
- **Simple routing**: Single condition per edge
- **Complex routing**: Multiple conditions (AND logic)
- **Always routing**: Empty conditions array []
- **Priority**: Lower numbers evaluated first

USE THE FULL SURVEY CONTEXT to understand complete routing patterns and dependencies.

OUTPUT: JSON with complete question data and CONDITIONAL routing assignments."""
    
    def _build_routing_prompt(self, context: Dict[str, Any], nodes: List[Dict]) -> str:
        """Build LLM prompt for routing assignment."""
        
        prompt = f"""Analyze these {len(nodes)} survey nodes and generate routing assignments:

COMPLETE SURVEY CONTEXT:
{self.full_survey_context}

NODES TO ANALYZE ({len(nodes)} nodes):
"""
        
        for n in nodes:
            prompt += f"""
Node ID: {n['id']}
Text: {n.get('text', 'N/A')[:100]}...
Block: {n.get('block', 'unknown')}
Order: {n.get('order_index', 0)}
Type: {n.get('type', 'unknown')}
"""
        
        prompt += """
Return JSON array with COMPLETE extraction in v1.2 CONDITIONAL format:
[
  {{
    "question_id": "Q{n}",
    "complete_question_text": "Full question text from survey",
    "response_options": [
      {{"value": 1, "label": "Yes", "type": "categorical"}},
      {{"value": 2, "label": "No", "type": "categorical"}}
    ],
    "question_type": "single_select|multiple_select|numeric|text|instruction",
    "universe_condition": "Who should see this question",
    "routing_assignments": [
      {{
        "conditions": [
          {{"variable": "Q1", "operator": "equals", "value": "1"}},
          {{"variable": "Q2", "operator": "equals", "value": "2"}}
        ],
        "target_question": "Q5",
        "edge_type": "branch",
        "priority": 1,
        "confidence": 0.9
      }}
    ],
    "skip_patterns": ["Questions skipped based on responses"],
    "block": "survey_section",
    "order_index": 15,
    "validation_rules": ["Any validation requirements"],
    "confidence": 0.85,
    "reasoning": "Explanation of routing decisions"
  }}
]

CRITICAL: Look for CONDITIONAL PATTERNS like:
- Multi-step routing where later questions depend on multiple earlier answers
- Skip logic that references combinations of previous questions
- Eligibility or screening logic with multiple criteria
- Branching that depends on response combinations

Extract ALL conditional dependencies using the complete survey context."""
        
        return prompt
    
    def _parse_complete_extraction(self, response_text: str, questions: List[Dict]) -> List[Dict]:
        """Parse complete extraction response including routing and question data."""
        
        try:
            # Extract JSON from response with better pattern matching
            import re
            
            # Try multiple JSON extraction patterns
            json_patterns = [
                r'```json\s*(\[.*?\])\s*```',  # JSON in code block
                r'```\s*(\[.*?\])\s*```',      # JSON in generic code block  
                r'(\[\s*{.*}\s*\])',           # Simple array pattern
                r'\[.*\]'                      # Fallback greedy pattern
            ]
            
            json_text = None
            for pattern in json_patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    json_text = match.group(1) if match.groups() else match.group(0)
                    break
            
            if not json_text:
                print(f"   No JSON found in extraction response")
                print(f"   Response preview: {response_text[:300]}...")
                return []
            
            extractions_data = json.loads(json_text)
            
            extractions = []
            for item in extractions_data:
                # Create complete extraction object
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
            
            return extractions
            
        except Exception as e:
            print(f"   Failed to parse extraction response: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            return []
    
    def _assignment_to_dict(self, assignment: RouteAssignment) -> Dict[str, Any]:
        """Convert assignment to dictionary."""
        return assignment
    
    def _generate_final_result(self, extractions: List[Dict], nodes: List[Dict], output_dir: Path) -> Dict[str, Any]:
        """Generate final extraction result."""
        
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
        
        # Generate final report
        result = {
            "metadata": {
                "agent": "RoutingAgent",
                "version": "2.0",
                "processed_at": datetime.now().isoformat(),
                "total_nodes": len(nodes),
                "total_extractions": len(extractions),
                "total_routing_assignments": total_routing_assignments
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
        output_file = output_dir / "complete_extractions.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def _summarize_assignments_by_type(self, assignments: List[RouteAssignment]) -> Dict[str, int]:
        """Summarize routing assignments by type."""
        summary = {}
        for assignment in assignments:
            edge_type = assignment.edge_type
            summary[edge_type] = summary.get(edge_type, 0) + 1
        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Automated Survey Routing Assignment")
    parser.add_argument("--input", required=True, help="Input JSON file (minimal nodes)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--model", default=None, help="OpenAI model to use (overrides config)")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Configure agent
    config = None
    if args.model or args.batch_size != 20:
        # Override config if command line options provided
        base_config = load_agent_config()['agent_config']
        if args.model:
            base_config['model_settings']['model'] = args.model
        if args.batch_size != 20:
            base_config['batch_settings']['default_batch_size'] = args.batch_size
        config = base_config
    
    # Run routing agent
    agent = RoutingAgent(config)
    result = agent.process_survey(input_file, output_dir)
    
    print(f"\n✅ Results saved to {output_dir}")
    print(f"📊 Enhanced nodes: {len(result.get('enhanced_nodes', []))}")
    print(f"🔗 Total routing assignments: {result['metadata']['total_routing_assignments']}")


if __name__ == "__main__":
    main()
