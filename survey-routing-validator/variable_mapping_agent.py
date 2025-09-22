#!/usr/bin/env python3
"""
Survey Variable Mapping Agent
Maps survey questions to data dictionary variables using LLM
"""

import json
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# Support both OpenAI and Anthropic
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

class VariableMappingAgent:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str = None):
        """Initialize variable mapping agent with LLM API"""
        self.model = model
        
        if model.startswith("gpt-") or model.startswith("o1"):
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
            self.client = openai.OpenAI(
                api_key=api_key or os.getenv('OPENAI_API_KEY')
            )
            self.provider = "openai"
        else:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
            self.client = anthropic.Anthropic(
                api_key=api_key or os.getenv('ANTHROPIC_API_KEY')
            )
            self.provider = "anthropic"
        
    def load_data_dictionary(self, excel_file: str) -> pd.DataFrame:
        """Load data dictionary from Excel file"""
        try:
            # Try "PUF Data Dictionary" sheet first
            df = pd.read_excel(excel_file, sheet_name="PUF Data Dictionary")
        except:
            # Fall back to first sheet
            df = pd.read_excel(excel_file, sheet_name=0)
        
        return df
    
    def process_variable_batch(self, batch_questions: List[Dict], data_dict_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Process a batch of questions to map to data dictionary variables
        
        Args:
            batch_questions: Batch of 20 questions to process
            data_dict_df: Data dictionary DataFrame
            
        Returns:
            Dict with variable mappings for this batch
        """
        
        # Create data dictionary context
        dict_context = self._create_dict_context(data_dict_df)
        
        # Create batch prompt
        prompt = self._create_mapping_prompt(dict_context, batch_questions)
        
        # Get LLM response
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            content = response.choices[0].message.content
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.1,
                system=self._get_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.content[0].text
        
        # Parse response
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {content}")
            return {"mappings": []}
    
    def _get_system_prompt(self) -> str:
        return """You are a survey data dictionary mapping expert. Your task is to map survey questions to their corresponding variables in the data dictionary.

KEY PRINCIPLES:
1. EXACT MATCHES: Look for exact or very close question text matches
2. VARIABLE NAMES: Match survey question IDs to data dictionary variable names when possible
3. CONTENT MATCHING: When text differs, match based on conceptual content
4. MISSING VARIABLES: Some survey questions may not have data dictionary entries

MAPPING APPROACH:
- Compare question text to data dictionary question text
- Compare survey question ID to data dictionary variable name
- Consider question content and purpose
- Note confidence level of each mapping

OUTPUT FORMAT: Valid JSON with "mappings" array.
MAPPING FORMAT: 
{
  "survey_question_id": "Q1",
  "data_dict_variable": "LANG", 
  "variable_label": "Language spoken at home",
  "confidence": "high|medium|low",
  "match_reason": "exact_text|question_id|content_match",
  "values_mapping": {"1": "English", "2": "Spanish"}
}

Be thorough but conservative - mark low confidence when uncertain."""

    def _create_dict_context(self, df: pd.DataFrame) -> str:
        """Create context from data dictionary"""
        context = f"DATA DICTIONARY VARIABLES ({len(df)} total):\n\n"
        
        # Sample first 50 variables for context
        for idx, row in df.head(50).iterrows():
            var_name = row.get('PUF Variable Name', row.iloc[0] if len(row) > 0 else '')
            var_label = row.get('Variable Label', row.iloc[1] if len(row) > 1 else '')
            question_text = row.get('Question text', row.iloc[2] if len(row) > 2 else '')
            values = row.get('Values', row.iloc[5] if len(row) > 5 else '')
            
            context += f"VARIABLE: {var_name}\n"
            context += f"LABEL: {var_label}\n"
            if question_text:
                context += f"QUESTION: {question_text[:200]}...\n"
            if values:
                context += f"VALUES: {str(values)[:200]}...\n"
            context += "\n"
            
        if len(df) > 50:
            context += f"... and {len(df) - 50} more variables in dictionary\n"
            
        return context
    
    def _create_mapping_prompt(self, dict_context: str, batch_questions: List[Dict]) -> str:
        """Create prompt for variable mapping"""
        
        prompt = f"""TASK: Map survey questions to data dictionary variables.

{dict_context}

SURVEY QUESTIONS TO MAP ({len(batch_questions)} questions):

"""
        
        for i, q in enumerate(batch_questions, 1):
            prompt += f"""
{i}. SURVEY QUESTION ID: {q['id']}
   BLOCK: {q['block']}
   TEXT: {q['text']}
   
"""

        prompt += """
MAPPING ANALYSIS NEEDED:
1. For each survey question, find the best matching data dictionary variable
2. Compare question text, variable names, and conceptual content
3. Extract value mappings where possible
4. Assign confidence levels

EXAMPLE OUTPUT:
{
  "mappings": [
    {
      "survey_question_id": "Language",
      "data_dict_variable": "LANG", 
      "variable_label": "Language spoken at home",
      "confidence": "high",
      "match_reason": "question_id_match",
      "values_mapping": {"1": "Yes", "2": "No"},
      "notes": "Direct match between question ID and variable name"
    }
  ]
}

Analyze and provide mappings:"""

        return prompt

def main():
    """Test the variable mapping agent"""
    
    # Load survey data
    data_file = Path('../data/htops_complete_nodes_minimal.json')
    with open(data_file, 'r') as f:
        nodes = json.load(f)
    
    # Get first batch of questions  
    questions = [n for n in nodes if n['type'] == 'question']
    batch_questions = questions[:3]  # Small test batch
    
    print(f"Processing {len(batch_questions)} questions...")
    
    # Initialize agent
    agent = VariableMappingAgent(model="claude-3-5-sonnet-20241022")
    
    # Load data dictionary
    dict_file = Path('../data/HTOPS_HPS_2502_DATA_DICTIONARY_PUF.xlsx')  # Update path as needed
    if dict_file.exists():
        data_dict_df = agent.load_data_dictionary(dict_file)
        print(f"Loaded data dictionary with {len(data_dict_df)} variables")
        
        # Process batch
        result = agent.process_variable_batch(batch_questions, data_dict_df)
        
        print("Variable mapping result:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Data dictionary file not found: {dict_file}")

if __name__ == "__main__":
    main()
