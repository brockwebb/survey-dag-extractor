#!/usr/bin/env python3
"""
Variable Mapping Agent - Automated Survey Variable Assignment

Maps survey questions to data dictionary variables using LLM analysis.
Processes questions in batches to assign appropriate variable names.

Usage:
    python variable_agent.py --input htops_complete_nodes_minimal.json --data-dict data_dictionary.json
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
class VariableMapping:
    """Represents a variable mapping for a question."""
    question_id: str
    variable_name: str
    confidence: float
    reasoning: str
    data_type: str
    description: Optional[str] = None

class VariableAgent:
    """Automated variable mapping agent using LLM analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize variable mapping agent."""
        # Load config from file if not provided
        if config is None:
            full_config = load_agent_config()
            config = full_config['agent_config']
        
        self.config = config
        self.batch_size = config.get('batch_settings', {}).get('default_batch_size', 20)
        
        # Model settings from config
        model_settings = config.get('model_settings', {})
        self.model = model_settings.get('model', 'gpt-5')
        
        # Setup OpenAI client
        self.client = openai.OpenAI()  # Uses OPENAI_API_KEY from environment
        
        print(f"🏷️ Variable Agent initialized with {self.model}")
        
        # Data dictionary
        self.data_dictionary = {}
        self.variable_mappings = []
        
        # Load PDF context
        self.pdf_context = self._load_pdf_context()
        
    def _load_pdf_context(self) -> str:
        """Load survey PDF content for context."""
        pdf_path = Path(__file__).parent.parent / "data" / "HTOPS_2502_Questionnaire_ENGLISH.pdf"
        
        if pdf_path.exists():
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pdf_text = ""
                    
                    # Extract text from all pages
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_text += page.extract_text() + "\n\n"
                    
                    print(f"   📄 Loaded PDF content: {len(pdf_text)} characters")
                    return pdf_text
                    
            except ImportError:
                print(f"   ⚠️  PyPDF2 not installed - install with: pip install PyPDF2")
                return ""
            except Exception as e:
                print(f"   ⚠️  Could not load PDF: {e}")
                return ""
        
        print(f"   ⚠️  PDF not found at: {pdf_path}")
        return ""
        
    def load_data_dictionary(self, data_dict_file: Path) -> None:
        """Load data dictionary for variable mapping."""
        if data_dict_file and data_dict_file.exists():
            with open(data_dict_file) as f:
                self.data_dictionary = json.load(f)
            print(f"📚 Loaded data dictionary: {len(self.data_dictionary.get('variables', []))} variables")
        else:
            print(f"⚠️  Data dictionary not found: {data_dict_file}")
            print("    Using fallback variable inference...")
    
    def process_survey(self, input_file: Path, output_dir: Path, data_dict_file: Optional[Path] = None) -> Dict[str, Any]:
        """Process entire survey for variable mapping."""
        print(f"🤖 Starting Variable Mapping Agent")
        print(f"   Input: {input_file}")
        print(f"   Batch Size: {self.batch_size}")
        
        # Load data dictionary if provided
        if data_dict_file:
            self.load_data_dictionary(data_dict_file)
        
        # Load survey data
        with open(input_file) as f:
            nodes = json.load(f)
        
        print(f"   Total Nodes: {len(nodes)}")
        
        # Process in batches
        batches = self._create_batches(nodes)
        print(f"   Processing {len(batches)} batches...")
        
        all_mappings = []
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n📦 Processing Batch {batch_num}/{len(batches)} ({len(batch)} questions)")
            
            try:
                mappings = self._process_batch(batch, batch_num)
                all_mappings.extend(mappings)
                
                # Save batch results
                batch_output = {
                    "batch_number": batch_num,
                    "batch_size": len(batch),
                    "questions_processed": [q["id"] for q in batch if q.get("type") == "question"],
                    "variable_mappings": [self._mapping_to_dict(m) for m in mappings],
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_file = output_dir / f"variable_batch_{batch_num:02d}.json"
                with open(batch_file, 'w') as f:
                    json.dump(batch_output, f, indent=2)
                
                print(f"   ✅ Generated {len(mappings)} variable mappings")
                
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                continue
        
        # Generate final variable mapping result
        result = self._generate_final_result(all_mappings, nodes, output_dir)
        
        print(f"\n🎯 Variable Mapping Complete!")
        print(f"   Total Mappings: {len(all_mappings)}")
        print(f"   Coverage: {len(all_mappings) / max(1, len([n for n in nodes if n.get('type') == 'question'])):.1%}")
        
        return result
    
    def _create_batches(self, nodes: List[Dict]) -> List[List[Dict]]:
        """Split nodes into processing batches."""
        # Focus on questions only for variable mapping
        questions = [node for node in nodes if node.get("type") == "question"]
        
        batches = []
        current_batch = []
        
        for question in questions:
            current_batch.append(question)
            
            if len(current_batch) >= self.batch_size:
                batches.append(current_batch.copy())
                current_batch = []
        
        # Add remaining questions
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _process_batch(self, batch: List[Dict], batch_num: int) -> List[VariableMapping]:
        """Process a batch of questions for variable mapping."""
        
        if not batch:
            return []
        
        # Build context for LLM
        batch_context = self._build_batch_context(batch)
        
        # Generate variable mappings using LLM
        prompt = self._build_mapping_prompt(batch_context, batch)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse LLM response into variable mappings
            mappings = self._parse_llm_response(response.choices[0].message.content, batch)
            return mappings
            
        except Exception as e:
            print(f"   LLM processing error: {e}")
            return []
    
    def _build_batch_context(self, questions: List[Dict]) -> Dict[str, Any]:
        """Build context for variable mapping."""
        
        # Get question blocks
        blocks = list(set(q.get("block") for q in questions if q.get("block")))
        
        # Analyze question types
        question_types = {}
        for q in questions:
            text = q.get("text", "").lower()
            if any(word in text for word in ["how many", "number", "age", "months", "years"]):
                question_types[q["id"]] = "numeric"
            elif any(word in text for word in ["yes", "no", "select only one"]):
                question_types[q["id"]] = "categorical"
            elif "select all" in text:
                question_types[q["id"]] = "multiple_choice"
            else:
                question_types[q["id"]] = "text"
        
        return {
            "blocks": blocks,
            "question_count": len(questions),
            "question_types": question_types,
            "has_data_dict": len(self.data_dictionary) > 0
        }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for variable mapping."""
        return """You are a survey data expert specializing in variable naming and data dictionary mapping.

Your task: Assign appropriate variable names to survey questions following these conventions:

VARIABLE NAMING RULES:
1. Use existing question IDs when they follow standard patterns (Q1, D11, EMP1, etc.)
2. Create descriptive names for unclear IDs (Language -> LANG, Address_Confirm -> ADDR_CONFIRM)
3. Follow survey conventions: Demographics (D_), Employment (EMP_), Health (HLTH_), etc.
4. Keep names concise but meaningful (max 15 characters)
5. Use uppercase with underscores for multi-word names

DATA TYPES:
- numeric: Age, counts, ratings, scales
- categorical: Yes/No, single-select options
- multiple_choice: "Select all that apply" questions
- text: Open-ended responses, names, addresses

OUTPUT FORMAT: JSON array with:
- question_id: Survey question ID
- variable_name: Assigned variable name
- confidence: Confidence score (0.0-1.0)
- reasoning: Brief explanation of naming choice
- data_type: Expected data type
- description: Brief variable description

Focus on consistency, clarity, and standard survey naming conventions."""
    
    def _build_mapping_prompt(self, context: Dict[str, Any], questions: List[Dict]) -> str:
        """Build LLM prompt for variable mapping."""
        
        prompt = f"""Assign variable names to these {len(questions)} survey questions:

SURVEY PDF CONTENT:
{self._get_pdf_context_for_questions(questions)}

DATA DICTIONARY:
{self._format_data_dictionary()}

CONTEXT:
- Survey Blocks: {', '.join(context['blocks'])}
- Question Types: {context['question_count']} questions
- Data Dictionary Available: {len(self.data_dictionary) > 0}
"""
        
        prompt += "\nQUESTIONS TO MAP:\n"
        
        for q in questions:
            prompt += f"""
ID: {q['id']}
Block: {q.get('block', 'unknown')}
Text: {q.get('text', 'N/A')[:150]}...
Order: {q.get('order_index', 0)}
Suggested Type: {context['question_types'].get(q['id'], 'unknown')}
---
"""
        
        prompt += """
Generate variable mappings considering:
1. Existing question ID patterns
2. Survey block context (demographics, employment, health, etc.)  
3. Question content and response type
4. Standard survey variable conventions
5. Data dictionary compatibility (if available)

Return JSON array of variable mappings."""
        
        return prompt
    
    def _get_pdf_context_for_questions(self, questions: List[Dict]) -> str:
        """Get relevant PDF context for the questions being mapped."""
        # For now, return truncated PDF content - in production, could do smarter extraction
        if hasattr(self, 'pdf_context') and self.pdf_context:
            return self.pdf_context[:5000] + "\n[PDF content truncated for brevity...]"
        return "PDF content not available"
    
    def _format_data_dictionary(self) -> str:
        """Format data dictionary for prompt inclusion."""
        if not self.data_dictionary:
            return "No data dictionary available"
            
        variables = self.data_dictionary.get('variables', [])
        if not variables:
            return "No variables in data dictionary"
            
        # Format first 50 variables
        formatted = "Available Variables:\n"
        for var in variables[:50]:
            var_name = var.get('variable_name', 'Unknown')
            description = var.get('description', 'No description')[:100]
            data_type = var.get('data_type', 'Unknown')
            formatted += f"- {var_name}: {description} (Type: {data_type})\n"
        
        if len(variables) > 50:
            formatted += f"\n[... and {len(variables) - 50} more variables]"
            
        return formatted
    
    def _parse_llm_response(self, response_text: str, questions: List[Dict]) -> List[VariableMapping]:
        """Parse LLM response into variable mappings."""
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                print(f"   No JSON found in response")
                return []
            
            mappings_data = json.loads(json_match.group())
            
            mappings = []
            for item in mappings_data:
                mapping = VariableMapping(
                    question_id=item.get('question_id', ''),
                    variable_name=item.get('variable_name', ''),
                    confidence=float(item.get('confidence', 0.8)),
                    reasoning=item.get('reasoning', ''),
                    data_type=item.get('data_type', 'text'),
                    description=item.get('description')
                )
                mappings.append(mapping)
            
            return mappings
            
        except Exception as e:
            print(f"   Failed to parse LLM response: {e}")
            return []
    
    def _mapping_to_dict(self, mapping: VariableMapping) -> Dict[str, Any]:
        """Convert mapping to dictionary."""
        return {
            "question_id": mapping.question_id,
            "variable_name": mapping.variable_name,
            "confidence": mapping.confidence,
            "reasoning": mapping.reasoning,
            "data_type": mapping.data_type,
            "description": mapping.description
        }
    
    def _generate_final_result(self, mappings: List[VariableMapping], nodes: List[Dict], output_dir: Path) -> Dict[str, Any]:
        """Generate final variable mapping result."""
        
        # Create enhanced nodes with variable assignments
        enhanced_nodes = []
        mapping_dict = {m.question_id: m for m in mappings}
        
        for node in nodes:
            enhanced_node = node.copy()
            
            # Add variable mapping for questions
            if node.get("type") == "question" and node["id"] in mapping_dict:
                mapping = mapping_dict[node["id"]]
                enhanced_node["variable"] = mapping.variable_name
                enhanced_node["variable_metadata"] = {
                    "data_type": mapping.data_type,
                    "confidence": mapping.confidence,
                    "reasoning": mapping.reasoning,
                    "description": mapping.description
                }
            
            enhanced_nodes.append(enhanced_node)
        
        # Generate final report
        result = {
            "metadata": {
                "agent": "VariableAgent",
                "version": "1.0",
                "processed_at": datetime.now().isoformat(),
                "total_nodes": len(nodes),
                "total_mappings": len(mappings),
                "data_dict_size": len(self.data_dictionary)
            },
            "enhanced_nodes": enhanced_nodes,
            "variable_summary": {
                "mappings_by_type": self._summarize_mappings_by_type(mappings),
                "blocks_processed": list(set(n.get("block") for n in nodes if n.get("block"))),
                "confidence_stats": self._calculate_confidence_stats(mappings),
                "coverage_rate": len(mappings) / max(1, len([n for n in nodes if n.get("type") == "question"]))
            }
        }
        
        # Save final result
        output_file = output_dir / "variable_mappings_complete.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def _summarize_mappings_by_type(self, mappings: List[VariableMapping]) -> Dict[str, int]:
        """Summarize variable mappings by data type."""
        summary = {}
        for mapping in mappings:
            data_type = mapping.data_type
            summary[data_type] = summary.get(data_type, 0) + 1
        return summary
    
    def _calculate_confidence_stats(self, mappings: List[VariableMapping]) -> Dict[str, float]:
        """Calculate confidence statistics."""
        if not mappings:
            return {"mean": 0.0, "min": 0.0, "max": 0.0}
        
        confidences = [m.confidence for m in mappings]
        return {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "high_confidence": len([c for c in confidences if c >= 0.9]) / len(confidences)
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Automated Survey Variable Mapping")
    parser.add_argument("--input", required=True, help="Input JSON file (minimal nodes)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--data-dict", help="Data dictionary JSON file (optional)")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--model", default=None, help="OpenAI model to use (overrides config)")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    data_dict_file = Path(args.data_dict) if args.data_dict else None
    
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
    
    # Run variable mapping agent
    agent = VariableAgent(config)
    result = agent.process_survey(input_file, output_dir, data_dict_file)
    
    print(f"\n✅ Results saved to {output_dir}")
    print(f"📊 Enhanced nodes: {len(result.get('enhanced_nodes', []))}")
    print(f"🏷️  Total variable mappings: {result['metadata']['total_mappings']}")
    print(f"🎯 Coverage rate: {result['variable_summary']['coverage_rate']:.1%}")


if __name__ == "__main__":
    main()
