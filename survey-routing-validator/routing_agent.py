#!/usr/bin/env python3
"""
Survey Routing Agent
Automated routing assignment for survey questions using LLM
"""

import json
import os
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

class RoutingAgent:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str = None):
        """Initialize routing agent with LLM API"""
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
        
    def process_routing_batch(self, nodes: List[Dict], batch_questions: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of questions to assign routing logic
        
        Args:
            nodes: Full list of all survey nodes for context
            batch_questions: Batch of questions to process routing for
            
        Returns:
            Dict with edges and predicates for this batch
        """
        
        # Create context of all available nodes
        node_context = self._create_node_context(nodes)
        
        # Create batch prompt
        prompt = self._create_routing_prompt(node_context, batch_questions)
        
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
            return {"edges": [], "predicates": {}}
    
    def _get_system_prompt(self) -> str:
        return """You are a survey routing logic expert. Your task is to analyze survey questions and assign routing logic.

KEY PRINCIPLES:
1. SEQUENTIAL FLOW: Most questions flow to the next question in order_index sequence
2. CONDITIONAL ROUTING: Some responses skip to different questions or terminate early
3. UNIVERSE CONDITIONS: Questions with skip logic typically have universe conditions
4. TERMINALS: Route to terminal nodes for survey completion or early exit

ROUTING PATTERNS TO IDENTIFY:
- Ineligibility screening (route to END_INELIGIBLE or R2a)
- Skip logic based on responses (e.g., "No" → skip related questions)
- Branching paths for different respondent types
- Sequential continuation (most common)

OUTPUT FORMAT: Valid JSON with "edges" and "predicates" arrays.
EDGE FORMAT: {"id": "E_XXXXXXXX", "source": "Q1", "target": "Q2", "predicate": "P_Q1_YES", "kind": "branch|fallthrough|terminate", "subkind": "skip|sequence|terminal_branch", "priority": 0}
PREDICATE FORMAT: {"P_Q1_YES": {"ast": ["==", "Q1", "1"], "complexity": "simple", "text": "Q1 == '1'"}}

Be conservative - when unsure, use sequential fallthrough routing."""

    def _create_node_context(self, nodes: List[Dict]) -> str:
        """Create context of all available nodes"""
        context = "AVAILABLE SURVEY NODES:\n\n"
        
        # Group by type
        questions = [n for n in nodes if n['type'] == 'question']
        instructions = [n for n in nodes if n['type'] == 'instruction'] 
        terminals = [n for n in nodes if n['type'] == 'terminal']
        
        context += f"QUESTIONS ({len(questions)} total):\n"
        for q in questions[:20]:  # Show first 20 for context
            context += f"- {q['id']} (order: {q['order_index']}) - {q['text'][:100]}...\n"
        
        if len(questions) > 20:
            context += f"... and {len(questions) - 20} more questions\n"
        
        context += f"\nINSTRUCTIONS ({len(instructions)} total):\n"
        for i in instructions:
            context += f"- {i['id']} (order: {i['order_index']})\n"
        
        context += f"\nTERMINALS ({len(terminals)} total):\n"
        for t in terminals:
            context += f"- {t['id']}\n"
            
        return context
    
    def _create_routing_prompt(self, node_context: str, batch_questions: List[Dict]) -> str:
        """Create prompt for routing assignment"""
        
        prompt = f"""TASK: Assign routing logic for the following survey questions.

{node_context}

QUESTIONS TO ROUTE ({len(batch_questions)} questions):

"""
        
        for i, q in enumerate(batch_questions, 1):
            prompt += f"""
{i}. QUESTION ID: {q['id']}
   ORDER INDEX: {q['order_index']}
   BLOCK: {q['block']}
   TEXT: {q['text']}
   
"""

        prompt += """
ROUTING ANALYSIS NEEDED:
1. Identify the likely response options for each question based on question text
2. Determine routing logic:
   - Sequential flow (most common): Route to next question in order_index
   - Skip logic: Route based on specific responses 
   - Early termination: Route to terminal nodes for ineligibility
   - Branching: Route to different question paths

3. Create edges and predicates in JSON format

EXAMPLE OUTPUT:
{
  "edges": [
    {
      "id": "E_00000001", 
      "source": "Q1",
      "target": "Q2", 
      "predicate": "P_Q1_YES",
      "kind": "branch",
      "subkind": "sequence", 
      "priority": 0
    }
  ],
  "predicates": {
    "P_Q1_YES": {
      "ast": ["==", "Q1", "1"],
      "complexity": "simple", 
      "text": "Q1 == '1'"
    }
  }
}

Analyze the questions and provide routing logic:"""

        return prompt

def main():
    """Test the routing agent"""
    from pathlib import Path
    
    # Load survey data
    data_file = Path('../data/htops_complete_nodes_minimal.json')
    with open(data_file, 'r') as f:
        nodes = json.load(f)
    
    # Get first batch of questions
    questions = [n for n in nodes if n['type'] == 'question']
    batch_questions = questions[:5]  # Small test batch
    
    print(f"Processing {len(batch_questions)} questions...")
    
    # Initialize agent with Claude
    agent = RoutingAgent(model="claude-3-5-sonnet-20241022")
    
    # Process batch
    result = agent.process_routing_batch(nodes, batch_questions)
    
    print("Routing result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
