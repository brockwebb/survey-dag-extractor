#!/usr/bin/env python3
"""
Essential Rich Survey Extraction

Extracts the most valuable survey data:
- Response options with codes
- Universe conditions  
- Basic routing logic
- Exact question text
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.append(str(project_root))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

def main():
    print("Phase 2: Manual Response Options Extraction")
    print("=" * 50)
    
    # Initialize extractor
    schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
    nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
    
    print(f"Looking for schema at: {schema_path}")
    print(f"Looking for nodes at: {nodes_path}")
    
    try:
        extractor = SchemaCompliantExtractor(schema_path, nodes_path)
        print(f"✓ Database loaded: {len(extractor.nodes)} nodes")
    except Exception as e:
        print(f"✗ Failed to load database: {e}")
        return
    
    # Get question chunks
    question_chunks = extractor.get_question_chunks(chunk_size=5)
    print(f"✓ Generated {len(question_chunks)} chunks of ~5 questions each\n")
    
    # Show new thread setup
    print("STEP 1: NEW CLAUDE THREAD SETUP")
    print("=" * 40)
    print("📎 IMPORTANT: Attach the PDF file to your new Claude thread first!")
    print()
    print("Copy this prompt to start a new Claude thread:")
    print()
    print("-" * 60)
    print("""**Extract complete survey question data from the PDF.** For each question listed below, extract and return ALL information in this exact JSON format:

```json
{
  "question_id": {
    "text": "Full question text exactly as shown in PDF",
    "response_options": [
      {"code": 1, "text": "Response option 1"},
      {"code": 2, "text": "Response option 2"}
    ],
    "universe": "ASK IF condition (if any)",
    "routing": [
      {"condition": "== 1", "target": "next_question"},
      {"condition": "== 2", "target": "different_question"}
    ]
  }
}
```

**REQUIRED for EVERY question:**
* `text`: Extract the complete question text
* `response_options`: Extract all response options with their codes
* `universe`: ALWAYS include - use "always" if no conditions, otherwise "ASK IF condition"
* `routing`: Include if question has skip logic, otherwise omit

**CRITICAL ROUTING RULES:**
* Every response option MUST have a routing path
* For numeric inputs, include: `== 0`, `> 0`, or appropriate ranges
* For text inputs, use: `"any"` or `"not_empty"`
* For multi-select, consider: `"any_selected"` and `"none_selected"`
* Check the PDF for where each path leads (may skip several questions)
* If no explicit routing shown, infer from document flow

**For these question types:**
* Text input: `[{"code": "text", "text": "TEXT_INPUT"}]`
* Numeric input: `[{"code": "number", "text": "NUMERIC_INPUT"}]`
* Check all that apply: Include all options with their codes
* Instructions/displays: `"response_options": []` (empty array)

**Universe conditions (REQUIRED):**
* If question shown to everyone: `"universe": "always"`
* If conditional: `"universe": "ASK IF D11 > 0"`
* If after instruction: `"universe": "ASK IF [instruction] displayed"`

**VALIDATION CHECK:** Before returning JSON, verify:
✓ ALL questions have explicit universe conditions ("always" or "ASK IF...")
✓ All response options have routing paths
✓ Numeric questions include paths for 0 and >0
✓ Check-all questions have paths for selected/none

Return ONLY the JSON with ALL fields populated where applicable.""")
    print("-" * 60)
    print()
    input("Press Enter after you've set up the new Claude thread with this prompt...")
    
    # Process chunks
    for chunk_num, chunk in enumerate(question_chunks, 1):
        print(f"\n" + "=" * 60)
        print(f"CHUNK {chunk_num}/{len(question_chunks)}")
        print("=" * 60)
        
        # Generate extraction prompt
        chunk_prompt = generate_chunk_prompt(chunk)
        
        print("STEP 2: COPY THIS TO CLAUDE")
        print("-" * 40)
        print(chunk_prompt)
        print("-" * 40)
        
        # Get response from user
        print("\nSTEP 3: PASTE CLAUDE'S JSON RESPONSE")
        print("-" * 40)
        print("Paste Claude's JSON response here (or 'skip' to skip this chunk):")
        
        response = ""
        while True:
            line = input()
            if line.strip() == "skip":
                print("Skipping this chunk...")
                break
            response += line + "\n"
            if line.strip() == "":
                break
        
        if response.strip() == "":
            continue
            
        # Process response
        try:
            response_data = json.loads(response.strip())
            updated_count = update_database(extractor, response_data)
            print(f"✓ Updated {updated_count} questions in database")
            
            # Save progress
            save_progress(extractor, chunk_num)
            print(f"✓ Progress saved")
            
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
            print("Skipping this chunk. Try again with valid JSON.")
        except Exception as e:
            print(f"✗ Error updating database: {e}")
    
    print(f"\n" + "=" * 60)
    print("EXTRACTION COMPLETE!")
    print("=" * 60)
    extractor.print_status()

def generate_chunk_prompt(chunk):
    """Generate extraction prompt for a chunk of questions."""
    prompt = "**Extract these questions:**\n\n"
    
    for i, node in enumerate(chunk, 1):
        prompt += f"{i}. Question ID: {node['id']}\n"
        prompt += f"   Text: {node['text']}\n\n"
    
    return prompt

def update_database(extractor, response_data):
    """Update database with essential rich data."""
    updated_count = 0
    routing_rules = []  # Collect for edge creation
    
    for question_id, data in response_data.items():
        node_updated = False
        
        # Update response options from rich format
        if 'response_options' in data and data['response_options']:
            # Convert rich format to simple values for DAG compatibility
            if len(data['response_options']) > 0 and isinstance(data['response_options'][0], dict):
                # Rich format: [{"code": 1, "text": "No difficulty"}, ...]
                values = [opt['text'] for opt in data['response_options']]
            elif len(data['response_options']) > 0:
                # Simple format: ["Yes", "No"]
                values = data['response_options']
            else:
                # Empty response options (terminals)
                values = []
            
            if values:  # Only update if there are actual values
                if extractor.update_node_response_options(question_id, values):
                    node_updated = True
        
        # Update universe conditions
        if 'universe' in data and data['universe']:
            # Simple universe format - extract dependencies from text
            universe_expr = data['universe']
            dependencies = []  # Could parse from universe_expr if needed
            if extractor.update_node_universe_condition(question_id, universe_expr, dependencies):
                node_updated = True
        
        # Collect routing rules for edge creation
        if 'routing' in data:
            for rule in data['routing']:
                routing_rules.append({
                    'source': question_id,
                    'condition': rule.get('condition', 'always'),
                    'target': rule.get('target', ''),
                    'action': 'continue'
                })
        
        if node_updated:
            updated_count += 1
    
    # Create edges from routing rules  
    edges_created = 0
    for rule in routing_rules:
        try:
            edge_id = extractor.add_conditional_edge(
                source=rule['source'],
                target=rule['target'], 
                condition=rule['condition'],
                edge_type='branch' if rule['condition'] != 'always' else 'fallthrough'
            )
            edges_created += 1
        except Exception as e:
            print(f"Warning: Could not create edge for {rule}: {e}")
    
    print(f"Rich data updated: {updated_count} nodes, {edges_created} routing edges")
    return updated_count

def save_progress(extractor, chunk_num):
    """Save progress with rich schema data."""
    progress_file = project_root / "surveys_db" / f"rich_extraction_progress_chunk_{chunk_num:02d}.json"
    progress_file.parent.mkdir(exist_ok=True)
    
    # Extract current state with rich data
    rich_nodes = []
    for node in extractor.nodes:
        rich_node = {
            'id': node['id'],
            'basic': {
                'text': node.get('text', ''),
                'type': node.get('type', ''),
                'block': node.get('block', ''),
                'order_index': node.get('order_index', 0)
            }
        }
        
        # Add rich domain data if present
        if 'domain' in node and 'values' in node.get('domain', {}):
            rich_node['domain'] = node['domain']
            
        # Add universe data if present
        if 'universe' in node:
            rich_node['universe'] = node['universe']
            
        rich_nodes.append(rich_node)
    
    with open(progress_file, 'w') as f:
        json.dump({
            'chunk_number': chunk_num,
            'extraction_type': 'rich_comprehensive',
            'nodes_updated': rich_nodes,
            'timestamp': str(Path(__file__).stat().st_mtime)
        }, f, indent=2)
    
    print(f"Rich extraction progress saved: {progress_file}")

if __name__ == "__main__":
    main()
