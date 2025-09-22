#!/usr/bin/env python3
"""
Semantic Variable Mapping Agent - Intelligent Survey Variable Assignment

Maps survey questions to data dictionary variables using semantic analysis.
Performs intelligent matching between question content and variable descriptions.

Usage:
    python variable_agent_semantic.py --input htops_complete_nodes_minimal.json --data-dict htops_data_dictionary.json
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
class SemanticVariableMapping:
    """Represents a semantic variable mapping for a question."""
    question_id: str
    variable_names: List[str]  # Support multiple variables per question
    confidence: float
    reasoning: str
    data_type: str
    semantic_match_score: float
    dictionary_descriptions: List[str]  # Descriptions for each variable
    question_text: str
    alternative_matches: List[Tuple[str, float]] = None
    
    @property
    def primary_variable(self) -> str:
        """Return the primary (first) variable name."""
        return self.variable_names[0] if self.variable_names else ''
    
    @property
    def is_multi_variable(self) -> bool:
        """Check if this mapping has multiple variables."""
        return len(self.variable_names) > 1

class SemanticVariableAgent:
    """Semantic variable mapping agent using intelligent content analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize semantic variable mapping agent."""
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
        
        print(f"🧠 Semantic Variable Agent initialized with {self.model}")
        
        # Load full survey context from PDF
        self.full_survey_context = self._load_full_survey_context()
        
        # Data dictionary
        self.data_dictionary = {}
        self.variable_mappings = []
        
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
    
    def load_data_dictionary(self, data_dict_file: Path) -> None:
        if data_dict_file and data_dict_file.exists():
            with open(data_dict_file) as f:
                data = json.load(f)
                if 'variables' in data:
                    self.data_dictionary = data['variables']
                else:
                    self.data_dictionary = data
            print(f"📚 Loaded data dictionary: {len(self.data_dictionary)} variables")
        else:
            print(f"❌ Data dictionary not found: {data_dict_file}")
            raise FileNotFoundError("Data dictionary is required for semantic matching")
    
    def process_survey(self, input_file: Path, output_dir: Path, data_dict_file: Path) -> Dict[str, Any]:
        """Process entire survey for semantic variable mapping."""
        print(f"🤖 Starting Semantic Variable Mapping Agent")
        print(f"   Input: {input_file}")
        print(f"   Data Dictionary: {data_dict_file}")
        print(f"   Batch Size: {self.batch_size}")
        
        # Load data dictionary (required)
        self.load_data_dictionary(data_dict_file)
        
        # Load survey data
        with open(input_file) as f:
            nodes = json.load(f)
        
        # Filter to questions only
        questions = [node for node in nodes if node.get("type") == "question"]
        print(f"   Total Questions: {len(questions)}")
        
        # Process in batches
        batches = self._create_batches(questions)
        print(f"   Processing {len(batches)} batches...")
        
        all_mappings = []
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n📦 Processing Batch {batch_num}/{len(batches)} ({len(batch)} questions)")
            
            try:
                mappings = self._process_batch_semantic(batch, batch_num)
                all_mappings.extend(mappings)
                
                # Save batch results
                batch_output = {
                    "batch_number": batch_num,
                    "batch_size": len(batch),
                    "questions_processed": [q["id"] for q in batch],
                    "variable_mappings": [self._mapping_to_dict(m) for m in mappings],
                    "semantic_analysis": self._analyze_batch_semantics(mappings),
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_file = output_dir / f"semantic_batch_{batch_num:02d}.json"
                with open(batch_file, 'w') as f:
                    json.dump(batch_output, f, indent=2)
                
                print(f"   ✅ Generated {len(mappings)} semantic mappings")
                print(f"   🎯 Avg semantic score: {self._avg_semantic_score(mappings):.2f}")
                
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                continue
        
        # Generate final result with enhanced nodes
        result = self._generate_enhanced_survey(all_mappings, nodes, output_dir)
        
        print(f"\n🎯 Semantic Variable Mapping Complete!")
        print(f"   Total Mappings: {len(all_mappings)}")
        print(f"   Coverage: {len(all_mappings) / len(questions):.1%}")
        print(f"   Avg Confidence: {sum(m.confidence for m in all_mappings) / len(all_mappings):.2f}")
        
        return result
    
    def _create_batches(self, questions: List[Dict]) -> List[List[Dict]]:
        """Split questions into processing batches."""
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
    
    def _process_batch_semantic(self, batch: List[Dict], batch_num: int) -> List[SemanticVariableMapping]:
        """Process a batch using semantic analysis."""
        
        if not batch:
            return []
        
        # Build semantic mapping prompt
        prompt = self._build_semantic_prompt(batch)
        
        try:
            # Build API call parameters based on model
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._get_semantic_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Only add model-specific parameters for supported models
            if not self.model.startswith('gpt-5') and not self.model.startswith('o1'):
                # gpt-4 and earlier models support these parameters
                api_params["temperature"] = 0.1
                api_params["max_tokens"] = 4000
            else:
                # gpt-5/o1 models use different parameters
                api_params["max_completion_tokens"] = 4000
                # temperature not supported - uses default of 1
            
            response = self.client.chat.completions.create(**api_params)
            
            # Parse semantic mappings
            mappings = self._parse_semantic_response(response.choices[0].message.content, batch)
            return mappings
            
        except Exception as e:
            print(f"   LLM semantic processing error: {e}")
            return []
    
    def _get_semantic_system_prompt(self) -> str:
        """Get system prompt for semantic variable mapping."""
        return """You are an expert survey data analyst specializing in semantic variable mapping.

Your task: Match survey questions to data dictionary variables using semantic analysis.

SEMANTIC MATCHING RULES:
1. Analyze question MEANING, not just text similarity
2. Match conceptual intent between questions and variables
3. Consider context: demographics, employment, health, housing, etc.
4. Handle paraphrasing (e.g., "How many children" = "Number of people under 18")
5. Identify multi-part questions that map to multiple variables
6. Account for survey flow and logical groupings

CONFIDENCE SCORING:
- 1.0: Perfect semantic match (same concept, same domain)
- 0.9: Very strong match (same concept, slightly different wording)
- 0.8: Strong match (related concepts, clear connection)  
- 0.7: Good match (related concepts, some ambiguity)
- 0.6: Moderate match (possibly related, requires judgment)
- 0.5: Weak match (low confidence, fallback option)
- <0.5: Poor match (should not map)

SEMANTIC ANALYSIS FACTORS:
- Question domain (demographics, employment, health, housing)
- Response type (yes/no, numeric, categorical, multiple choice)
- Population scope (household, individual, children)
- Time frame (current, last 4 weeks, last 7 days)
- Measurement unit (count, rating, frequency)

OUTPUT: JSON with semantic mappings including confidence, reasoning, and alternative matches."""
    
    def _build_semantic_prompt(self, questions: List[Dict]) -> str:
        """Build semantic matching prompt."""
        
        # Organize data dictionary by domain for better context
        dict_by_domain = self._organize_dict_by_domain()
        
        prompt = f"""SEMANTIC VARIABLE MAPPING TASK

COMPLETE SURVEY CONTEXT (PDF):
{self.full_survey_context}

DATA DICTIONARY ({len(self.data_dictionary)} variables):
{self._format_dict_for_semantic_analysis(dict_by_domain)}

QUESTIONS TO MAP ({len(questions)} questions):
"""
        
        for q in questions:
            question_text = q.get('text', 'No text available')
            block = q.get('block', 'unknown')
            order = q.get('order_index', 0)
            response_options = q.get('response_options', [])
            question_type = q.get('type', 'unknown')
            extraction_metadata = q.get('extraction_metadata', {})
            universe_condition = q.get('universe_condition', '')
            
            prompt += f"""
---
QUESTION ID: {q['id']}
BLOCK: {block}  
ORDER: {order}
TYPE: {question_type}
TEXT: {question_text}
UNIVERSE: {universe_condition}
RESPONSE OPTIONS: {response_options if response_options else 'Not specified'}
EXTRACTION METADATA: {extraction_metadata if extraction_metadata else 'None'}
"""
        
        prompt += """
---

SEMANTIC ANALYSIS INSTRUCTIONS:
1. For each question, analyze its semantic meaning and intent
2. **USE ALL AVAILABLE INFORMATION**: question text, response options, universe conditions, block context
3. **RESPONSE VALUE MAPPING**: For multi-part questions, map each response option to appropriate variables
4. Find the best matching variable(s) from the data dictionary
5. Consider question context (block, order, surrounding questions)
6. Match based on conceptual meaning, not just text similarity
7. **SPECIAL ATTENTION**: Age ranges, categories, multi-select options each may need separate variables
8. Provide confidence scores and detailed reasoning
9. Include alternative matches when relevant

EXAMPLES OF RESPONSE VALUE MAPPING:
- Question: "In your household, are there..." with options ["Children under 1", "Children 1-4", "Children 5-11"] 
  → Map to ["KIDS_LT1Y", "KIDS_1_4Y", "KIDS_5_11Y"]
- Question: "Are you covered by..." with options ["Employer insurance", "Direct purchase", "Medicare"]
  → Map to ["HLTHINS1", "HLTHINS2", "HLTHINS3"]
- Question: "Transportation options" with options ["Walk", "Bike", "Car", "Bus"]
  → Map to ["TRANSPORT1", "TRANSPORT2", "TRANSPORT3", "TRANSPORT4"]

Return JSON array with format:
[
  {
    "question_id": "Q1",
    "variable_names": ["PRIMARY_VAR", "SECONDARY_VAR"], 
    "confidence": 0.95,
    "semantic_match_score": 0.90,
    "reasoning": "Detailed explanation of semantic match",
    "dictionary_descriptions": ["Description of primary var", "Description of secondary var"],
    "question_domain": "demographics|employment|health|housing|other",
    "data_type": "numeric|categorical|text|multiple_choice",
    "alternative_matches": [
      {"variable": "ALT_VAR", "score": 0.75},
      {"variable": "ALT_VAR2", "score": 0.65}
    ]
  }
]

IMPORTANT: For questions that collect multiple related data points, map to ALL relevant variables:
- Children questions → KIDS_LT1Y, KIDS_1_4Y, KIDS_5_11Y, KIDS_12_17Y
- School enrollment → ENRPUBCHK, ENRPRVCHK, ENRHMSCHK
- Health insurance → HLTHINS1, HLTHINS2, HLTHINS3, etc.
- Transportation → TRANSPORT1, TRANSPORT2, TRANSPORT3, etc.

Focus on semantic meaning over surface text similarity."""
        
        return prompt
    
    def _organize_dict_by_domain(self) -> Dict[str, List[Dict]]:
        """Organize data dictionary by semantic domain."""
        domains = {
            "demographics": [],
            "employment": [],
            "health": [],
            "housing": [], 
            "food_security": [],
            "education": [],
            "transportation": [],
            "financial": [],
            "social": [],
            "other": []
        }
        
        for var in self.data_dictionary:
            var_name = var.get('variable_name', '').upper()
            description = var.get('description', '').lower()
            
            # Classify by domain
            if any(keyword in description for keyword in ['age', 'household', 'children', 'people', 'adult', 'birth']):
                domains["demographics"].append(var)
            elif any(keyword in description for keyword in ['work', 'job', 'employ', 'income', 'telework']):
                domains["employment"].append(var)
            elif any(keyword in description for keyword in ['health', 'medical', 'mental', 'disability', 'anxious', 'depressed']):
                domains["health"].append(var)
            elif any(keyword in description for keyword in ['house', 'rent', 'mortgage', 'home', 'apartment']):
                domains["housing"].append(var)
            elif any(keyword in description for keyword in ['food', 'eat', 'meal', 'nutrition', 'hungry']):
                domains["food_security"].append(var)
            elif any(keyword in description for keyword in ['school', 'education', 'enroll', 'childcare']):
                domains["education"].append(var)
            elif any(keyword in description for keyword in ['transport', 'travel', 'vehicle', 'car', 'bus', 'walk']):
                domains["transportation"].append(var)
            elif any(keyword in description for keyword in ['money', 'cost', 'expense', 'price', 'afford', 'pay']):
                domains["financial"].append(var)
            elif any(keyword in description for keyword in ['social', 'support', 'lonely', 'friends', 'family']):
                domains["social"].append(var)
            else:
                domains["other"].append(var)
        
        return domains
    
    def _format_dict_for_semantic_analysis(self, dict_by_domain: Dict[str, List[Dict]]) -> str:
        """Format dictionary for semantic analysis prompt."""
        formatted = ""
        
        for domain, variables in dict_by_domain.items():
            if not variables:
                continue
                
            formatted += f"\n{domain.upper()} VARIABLES:\n"
            for var in variables:
                var_name = var.get('variable_name', 'Unknown')
                description = var.get('description', 'No description')
                data_type = var.get('data_type', 'Unknown')
                
                # Truncate long descriptions
                if len(description) > 120:
                    description = description[:120] + "..."
                
                formatted += f"  {var_name}: {description} [{data_type}]\n"
        
        return formatted
    
    def _parse_semantic_response(self, response_text: str, questions: List[Dict]) -> List[SemanticVariableMapping]:
        """Parse semantic mapping response."""
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                print(f"   No JSON found in semantic response")
                return []
            
            mappings_data = json.loads(json_match.group())
            
            mappings = []
            for item in mappings_data:
                # Find original question for context
                question = next((q for q in questions if q['id'] == item.get('question_id')), {})
                
                # Parse alternative matches
                alt_matches = []
                if 'alternative_matches' in item:
                    for alt in item['alternative_matches']:
                        if isinstance(alt, dict):
                            alt_matches.append((alt.get('variable', ''), alt.get('score', 0.0)))
                
                # Handle both single and multiple variable mappings
                variable_names = item.get('variable_names', [])
                if not variable_names and 'variable_name' in item:
                    variable_names = [item['variable_name']]  # Backward compatibility
                
                dictionary_descriptions = item.get('dictionary_descriptions', [])
                if not dictionary_descriptions and 'dictionary_description' in item:
                    dictionary_descriptions = [item['dictionary_description']]  # Backward compatibility
                
                mapping = SemanticVariableMapping(
                    question_id=item.get('question_id', ''),
                    variable_names=variable_names,
                    confidence=float(item.get('confidence', 0.5)),
                    reasoning=item.get('reasoning', ''),
                    data_type=item.get('data_type', 'text'),
                    semantic_match_score=float(item.get('semantic_match_score', 0.5)),
                    dictionary_descriptions=dictionary_descriptions,
                    question_text=question.get('text', ''),
                    alternative_matches=alt_matches
                )
                mappings.append(mapping)
            
            return mappings
            
        except Exception as e:
            print(f"   Failed to parse semantic response: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            return []
    
    def _mapping_to_dict(self, mapping: SemanticVariableMapping) -> Dict[str, Any]:
        """Convert semantic mapping to dictionary."""
        return {
            "question_id": mapping.question_id,
            "variable_names": mapping.variable_names,
            "primary_variable": mapping.primary_variable,
            "is_multi_variable": mapping.is_multi_variable,
            "confidence": mapping.confidence,
            "semantic_match_score": mapping.semantic_match_score,
            "reasoning": mapping.reasoning,
            "data_type": mapping.data_type,
            "dictionary_descriptions": mapping.dictionary_descriptions,
            "question_text": mapping.question_text[:100] + "..." if len(mapping.question_text) > 100 else mapping.question_text,
            "alternative_matches": mapping.alternative_matches or []
        }
    
    def _analyze_batch_semantics(self, mappings: List[SemanticVariableMapping]) -> Dict[str, Any]:
        """Analyze semantic matching quality for batch."""
        if not mappings:
            return {}
        
        return {
            "avg_confidence": sum(m.confidence for m in mappings) / len(mappings),
            "avg_semantic_score": sum(m.semantic_match_score for m in mappings) / len(mappings),
            "high_confidence_count": len([m for m in mappings if m.confidence >= 0.8]),
            "low_confidence_count": len([m for m in mappings if m.confidence < 0.6]),
            "data_type_distribution": self._count_data_types(mappings)
        }
    
    def _count_data_types(self, mappings: List[SemanticVariableMapping]) -> Dict[str, int]:
        """Count data types in mappings."""
        counts = {}
        for mapping in mappings:
            data_type = mapping.data_type
            counts[data_type] = counts.get(data_type, 0) + 1
        return counts
    
    def _avg_semantic_score(self, mappings: List[SemanticVariableMapping]) -> float:
        """Calculate average semantic match score."""
        if not mappings:
            return 0.0
        return sum(m.semantic_match_score for m in mappings) / len(mappings)
    
    def _generate_enhanced_survey(self, mappings: List[SemanticVariableMapping], nodes: List[Dict], output_dir: Path) -> Dict[str, Any]:
        """Generate enhanced survey with semantic variable mappings."""
        
        # Create mapping lookup
        mapping_dict = {m.question_id: m for m in mappings}
        
        # Enhance nodes with semantic mappings
        enhanced_nodes = []
        for node in nodes:
            enhanced_node = node.copy()
            
            # Add semantic variable mapping for questions
            if node.get("type") == "question" and node["id"] in mapping_dict:
                mapping = mapping_dict[node["id"]]
                
                # Handle multiple variables
                if mapping.is_multi_variable:
                    enhanced_node["variables"] = mapping.variable_names  # Use plural for multiple
                    enhanced_node["primary_variable"] = mapping.primary_variable
                else:
                    enhanced_node["variable"] = mapping.primary_variable  # Single variable (backward compatibility)
                
                enhanced_node["variable_metadata"] = {
                    "data_type": mapping.data_type,
                    "confidence": mapping.confidence,
                    "semantic_match_score": mapping.semantic_match_score,
                    "reasoning": mapping.reasoning,
                    "dictionary_descriptions": mapping.dictionary_descriptions,
                    "is_multi_variable": mapping.is_multi_variable,
                    "variable_count": len(mapping.variable_names),
                    "alternative_matches": mapping.alternative_matches or [],
                    "mapping_method": "semantic_analysis"
                }
            
            enhanced_nodes.append(enhanced_node)
        
        # Generate comprehensive result
        result = {
            "metadata": {
                "agent": "SemanticVariableAgent",
                "version": "1.0",
                "processed_at": datetime.now().isoformat(),
                "total_nodes": len(nodes),
                "total_questions": len([n for n in nodes if n.get("type") == "question"]),
                "total_mappings": len(mappings),
                "data_dict_size": len(self.data_dictionary),
                "mapping_method": "semantic_analysis"
            },
            "enhanced_nodes": enhanced_nodes,
            "semantic_summary": {
                "avg_confidence": sum(m.confidence for m in mappings) / len(mappings) if mappings else 0,
                "avg_semantic_score": sum(m.semantic_match_score for m in mappings) / len(mappings) if mappings else 0,
                "confidence_distribution": self._confidence_distribution(mappings),
                "data_type_distribution": self._count_data_types(mappings),
                "domain_coverage": self._analyze_domain_coverage(mappings),
                "quality_metrics": self._calculate_quality_metrics(mappings)
            }
        }
        
        # Save enhanced survey
        output_file = output_dir / "semantic_enhanced_survey.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"📄 Enhanced survey saved: {output_file}")
        
        return result
    
    def _confidence_distribution(self, mappings: List[SemanticVariableMapping]) -> Dict[str, int]:
        """Calculate confidence score distribution."""
        distribution = {
            "excellent (0.9+)": 0,
            "good (0.8-0.89)": 0, 
            "fair (0.7-0.79)": 0,
            "poor (0.6-0.69)": 0,
            "very_poor (<0.6)": 0
        }
        
        for mapping in mappings:
            confidence = mapping.confidence
            if confidence >= 0.9:
                distribution["excellent (0.9+)"] += 1
            elif confidence >= 0.8:
                distribution["good (0.8-0.89)"] += 1
            elif confidence >= 0.7:
                distribution["fair (0.7-0.79)"] += 1
            elif confidence >= 0.6:
                distribution["poor (0.6-0.69)"] += 1
            else:
                distribution["very_poor (<0.6)"] += 1
        
        return distribution
    
    def _analyze_domain_coverage(self, mappings: List[SemanticVariableMapping]) -> Dict[str, int]:
        """Analyze which domains are covered by mappings."""
        domain_coverage = {}
        
        for mapping in mappings:
            var_name = mapping.primary_variable.upper()
            description = " ".join(mapping.dictionary_descriptions).lower() if mapping.dictionary_descriptions else ""
            
            # Simple domain classification
            if 'demographic' in description or any(x in var_name for x in ['AGE', 'SEX', 'RACE', 'EDUC']):
                domain = "demographics"
            elif 'employ' in description or 'EMP' in var_name:
                domain = "employment"  
            elif 'health' in description or any(x in var_name for x in ['HLTH', 'MENTAL', 'MED']):
                domain = "health"
            elif 'hous' in description or any(x in var_name for x in ['HSE', 'RENT', 'MORT']):
                domain = "housing"
            else:
                domain = "other"
            
            domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
        
        return domain_coverage
    
    def _calculate_quality_metrics(self, mappings: List[SemanticVariableMapping]) -> Dict[str, Any]:
        """Calculate quality metrics for semantic mappings."""
        if not mappings:
            return {}
        
        return {
            "total_mappings": len(mappings),
            "high_quality_mappings": len([m for m in mappings if m.confidence >= 0.8 and m.semantic_match_score >= 0.8]),
            "questionable_mappings": len([m for m in mappings if m.confidence < 0.6]),
            "semantic_score_range": {
                "min": min(m.semantic_match_score for m in mappings),
                "max": max(m.semantic_match_score for m in mappings),
                "avg": sum(m.semantic_match_score for m in mappings) / len(mappings)
            },
            "alternative_matches_provided": len([m for m in mappings if m.alternative_matches])
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Semantic Survey Variable Mapping")
    parser.add_argument("--input", required=True, help="Input JSON file (minimal nodes)")
    parser.add_argument("--data-dict", required=True, help="Data dictionary JSON file")
    parser.add_argument("--output", default="semantic_output", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    data_dict_file = Path(args.data_dict)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Configure agent
    config = {
        'batch_settings': {'default_batch_size': args.batch_size},
        'model_settings': {'model': args.model}
    }
    
    # Run semantic variable mapping agent
    agent = SemanticVariableAgent(config)
    result = agent.process_survey(input_file, output_dir, data_dict_file)
    
    print(f"\n✅ Semantic mapping results saved to {output_dir}")
    print(f"📊 Enhanced nodes: {len(result.get('enhanced_nodes', []))}")
    print(f"🏷️  Total variable mappings: {result['metadata']['total_mappings']}")
    print(f"🎯 Average confidence: {result['semantic_summary']['avg_confidence']:.2f}")
    print(f"🧠 Average semantic score: {result['semantic_summary']['avg_semantic_score']:.2f}")


if __name__ == "__main__":
    main()
