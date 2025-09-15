#!/usr/bin/env python3
"""
Collaborative DAG Fixing Tool - PROPER DATABASE UPDATES

Interactive tool that UPDATES the database in place instead of creating copies.
Maintains a single working database that gets updated after each fix round.
"""

import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

class CollaborativeDAGFixer:
    """Interactive DAG fixing with proper database updates."""
    
    def __init__(self, database_path: Path):
        self.original_database_path = database_path
        self.working_database_path = database_path.parent / "phase3_working_database.pkl"
        self.extractor = None
        self.analysis_results = None
        
    def load_database(self) -> bool:
        """Load database, prioritizing working version."""
        # Priority: working database > original database
        if self.working_database_path.exists():
            load_path = self.working_database_path
            print(f"✓ Loading working database: {load_path.name}")
        elif self.original_database_path.exists():
            load_path = self.original_database_path
            print(f"✓ Loading original database: {load_path.name}")
            print("  (Will create working copy)")
        else:
            print(f"✗ No database found at {self.original_database_path}")
            return False
            
        try:
            with open(load_path, 'rb') as f:
                self.extractor = pickle.load(f)
            
            # If loaded from original, immediately create working copy
            if load_path == self.original_database_path:
                self.save_working_database("Initial working copy created")
                
            print(f"  📊 {len(self.extractor.nodes)} nodes, {self.extractor.graph.number_of_edges()} edges")
            return True
        except Exception as e:
            print(f"✗ Error loading database: {e}")
            return False
    
    def save_working_database(self, message: str = "Database updated"):
        """Save current state to working database - UPDATES IN PLACE."""
        with open(self.working_database_path, 'wb') as f:
            pickle.dump(self.extractor, f)
        print(f"  💾 {message}")
    
    def analyze_connectivity_issues(self) -> Dict[str, Any]:
        """Analyze specific connectivity problems."""
        import networkx as nx
        
        isolated_nodes = list(nx.isolates(self.extractor.graph))
        
        # Categorize isolated nodes
        instruction_nodes = []
        terminal_nodes = []
        question_nodes = []
        
        for node_id in isolated_nodes:
            node = next((n for n in self.extractor.nodes if n['id'] == node_id), None)
            if node:
                if node['type'] == 'instruction':
                    instruction_nodes.append(node_id)
                elif node['type'] in ['terminal', 'ultimate_terminal']:
                    terminal_nodes.append(node_id)
                elif node['type'] == 'question':
                    question_nodes.append(node_id)
        
        # Find start node and reachability
        questions = [n for n in self.extractor.nodes if n['type'] == 'question']
        start_node = min(questions, key=lambda x: x.get('order_index', 0))['id'] if questions else None
        
        reachable_nodes = set()
        if start_node:
            reachable_nodes = set(nx.descendants(self.extractor.graph, start_node))
            reachable_nodes.add(start_node)
        
        unreachable_nodes = [n['id'] for n in self.extractor.nodes if n['id'] not in reachable_nodes]
        
        self.analysis_results = {
            'isolated_nodes': {
                'total': len(isolated_nodes),
                'instructions': instruction_nodes,
                'terminals': terminal_nodes,
                'questions': question_nodes
            },
            'reachability': {
                'start_node': start_node,
                'reachable_count': len(reachable_nodes),
                'unreachable_nodes': unreachable_nodes
            },
            'connectivity': {
                'components': nx.number_weakly_connected_components(self.extractor.graph),
                'total_edges': self.extractor.graph.number_of_edges()
            }
        }
        
        return self.analysis_results
    
    def generate_prompt(self, issue_type: str) -> str:
        """Generate Claude prompt for specific issue."""
        base = '''Fix DAG connectivity issues. Return ONLY JSON in this format:

```json
{
  "edges_to_add": [
    {"source": "node_id", "target": "node_id", "condition": "always", "type": "fallthrough", "reason": "explanation"}
  ]
}
```

**Edge Types:** fallthrough, branch, terminate
**Conditions:** always, == 1, == 2, > 0, etc.

'''
        
        if issue_type == "terminals":
            terminals = self.analysis_results['isolated_nodes']['terminals']
            return base + f'''**ISSUE: Isolated Terminals**
These terminal nodes need connections: {terminals}

**Required connections:**
- Survey questions should route to SURVEY_COMPLETE at end
- R2a (ineligible) should be reachable from END 
- SURVEY_COMPLETE should connect to FINAL_TERMINATION (may exist)

**Task:** Add edges to connect these terminals to survey flow.'''
        
        elif issue_type == "instructions":
            instructions = self.analysis_results['isolated_nodes']['instructions']
            return base + f'''**ISSUE: Isolated Instructions**
These instruction nodes need connections: {instructions}

**Expected flow:**
- INTRO_INCENTIVE should be first (before Language)
- Continue, PRA should follow in sequence  
- Section headers (EMP_Intro, display_HLTH, etc.) should precede their question blocks

**Task:** Connect instructions to appropriate survey positions.'''
        
        elif issue_type == "completion":
            return base + '''**ISSUE: Missing Completion Path**
Survey has no completion path. Last question (RECONTACT) needs to route to SURVEY_COMPLETE.

**Task:** Add edges so survey can be completed normally.'''
        
        elif issue_type == "unreachable":
            unreachable = self.analysis_results['reachability']['unreachable_nodes'][:10]
            return base + f'''**ISSUE: Unreachable Nodes**
These nodes cannot be reached from survey start: {unreachable}

**Task:** Add edges to make important nodes reachable. Some may be intentionally unreachable.'''
        
        else:
            return base + f"**ISSUE:** {issue_type}"
    
    def apply_fixes(self, claude_json: str) -> Tuple[int, List[str]]:
        """Apply Claude's suggested fixes and UPDATE database."""
        try:
            # Clean the JSON string
            claude_json = claude_json.strip()
            claude_json = claude_json.replace('\\\\n', '\\n').replace('\\n', ' ').replace('\\r', ' ')
            
            import re
            claude_json = re.sub(r'\\s+', ' ', claude_json)
            
            if '```json' in claude_json:
                start = claude_json.find('{') 
                end = claude_json.rfind('}') + 1
                if start >= 0 and end > start:
                    claude_json = claude_json[start:end]
            
            fixes = json.loads(claude_json)
            
            edges_added = 0
            errors = []
            
            for edge in fixes.get('edges_to_add', []):
                try:
                    source = edge['source']
                    target = edge['target']
                    condition = edge.get('condition', 'always')
                    edge_type = edge.get('type', 'fallthrough')
                    reason = edge.get('reason', 'Claude suggestion')
                    
                    if not self.extractor.graph.has_node(source):
                        errors.append(f"Source node '{source}' not found")
                        continue
                    if not self.extractor.graph.has_node(target):
                        errors.append(f"Target node '{target}' not found")
                        continue
                    
                    edge_id = self.extractor.add_conditional_edge(source, target, condition, edge_type)
                    if edge_id:
                        edges_added += 1
                        print(f"    ✓ {source} → {target} ({condition})")
                    else:
                        errors.append(f"Failed to add: {source} → {target}")
                        
                except KeyError as e:
                    errors.append(f"Missing field: {e}")
                except Exception as e:
                    errors.append(f"Error: {e}")
            
            return edges_added, errors
            
        except json.JSONDecodeError as e:
            return 0, [f"JSON error: {e}"]
    
    def category_needs_fixing(self, category_id: str) -> bool:
        """Check if a category still has issues."""
        issues = self.analysis_results
        
        if category_id == "terminals":
            return len(issues['isolated_nodes']['terminals']) > 0
        elif category_id == "instructions": 
            return len(issues['isolated_nodes']['instructions']) > 0
        elif category_id == "completion":
            import networkx as nx
            if self.extractor.graph.has_node('RECONTACT') and self.extractor.graph.has_node('SURVEY_COMPLETE'):
                try:
                    return not nx.has_path(self.extractor.graph, 'RECONTACT', 'SURVEY_COMPLETE')
                except:
                    return True
            return True
        elif category_id == "unreachable":
            return len(issues['reachability']['unreachable_nodes']) > 5
        
        return False
    
    def run_fixing_session(self):
        """Run fixing session with proper database updates."""
        print("COLLABORATIVE DAG FIXING - DATABASE UPDATE MODE")
        print("=" * 55)
        
        if not self.load_database():
            return False
        
        print("\\nInitial Analysis...")
        self.analyze_connectivity_issues()
        
        initial_issues = self.analysis_results
        print(f"📊 Initial state:")
        print(f"   Isolated: {initial_issues['isolated_nodes']['total']}")
        print(f"   Components: {initial_issues['connectivity']['components']}")
        print(f"   Unreachable: {len(initial_issues['reachability']['unreachable_nodes'])}")
        
        # Fixing categories
        categories = [
            ("terminals", "Isolated Terminals"),
            ("instructions", "Isolated Instructions"), 
            ("completion", "Missing Completion Path"),
            ("unreachable", "Unreachable Nodes")
        ]
        
        session_edges_added = 0
        
        for category_id, category_name in categories:
            print(f"\\n{'='*55}")
            print(f"CATEGORY: {category_name.upper()}")
            print(f"{'='*55}")
            
            # Re-analyze current state
            self.analyze_connectivity_issues()
            
            if self.category_needs_fixing(category_id):
                print(f"\\n🔍 Issues found in {category_name.lower()}")
                
                prompt = self.generate_prompt(category_id)
                
                print("\\n" + "-"*50)
                print("COPY TO CLAUDE:")
                print("-"*50)
                print(prompt)
                print("-"*50)
                
                print(f"\\nPaste Claude's JSON (or 'skip'):")
                response = ""
                while True:
                    line = input()
                    if line.strip().lower() == "skip":
                        break
                    response += line + "\\n"
                    if line.strip() == "":
                        break
                
                if response.strip() and response.strip().lower() != "skip":
                    print(f"\\n⚙️  Applying fixes...")
                    edges_added, errors = self.apply_fixes(response.strip())
                    
                    if edges_added > 0:
                        session_edges_added += edges_added
                        print(f"\\n  ✅ Added {edges_added} edges")
                        
                        # 🔥 UPDATE DATABASE IN PLACE 🔥
                        self.save_working_database(f"Updated after {category_name.lower()} fixes")
                        
                        # Show new state
                        self.analyze_connectivity_issues()
                        current = self.analysis_results
                        print(f"     📊 Now: {current['isolated_nodes']['total']} isolated, {current['connectivity']['components']} components")
                    
                    if errors:
                        print("\\n  ⚠️  Errors:")
                        for error in errors:
                            print(f"      {error}")
                else:
                    print(f"⏭️  Skipped {category_name.lower()}")
            else:
                print(f"✅ {category_name} - No issues found")
        
        # Final summary
        print(f"\\n{'='*55}")
        print("SESSION COMPLETE")
        print(f"{'='*55}")
        
        final_issues = self.analysis_results
        
        print(f"\\n📈 PROGRESS THIS SESSION:")
        print(f"   Edges added: {session_edges_added}")
        print(f"   Isolated: {initial_issues['isolated_nodes']['total']} → {final_issues['isolated_nodes']['total']}")
        print(f"   Components: {initial_issues['connectivity']['components']} → {final_issues['connectivity']['components']}")
        print(f"   Unreachable: {len(initial_issues['reachability']['unreachable_nodes'])} → {len(final_issues['reachability']['unreachable_nodes'])}")
        
        # Check if fully fixed
        is_fully_connected = (
            final_issues['isolated_nodes']['total'] == 0 and
            final_issues['connectivity']['components'] == 1 and
            len(final_issues['reachability']['unreachable_nodes']) <= 2  # Allow some terminals
        )
        
        if is_fully_connected:
            print(f"\\n🎉 DAG IS FULLY CONNECTED! Ready for Phase 4")
        else:
            remaining = []
            if final_issues['isolated_nodes']['total'] > 0:
                remaining.append(f"{final_issues['isolated_nodes']['total']} isolated")
            if final_issues['connectivity']['components'] > 1:
                remaining.append(f"{final_issues['connectivity']['components']} components")
            if len(final_issues['reachability']['unreachable_nodes']) > 2:
                remaining.append(f"{len(final_issues['reachability']['unreachable_nodes'])} unreachable")
            
            print(f"\\n🔄 Remaining: {', '.join(remaining)}")
            print(f"   Run tool again to continue fixing")
        
        print(f"\\n💾 Working database: {self.working_database_path}")
        return True

def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    database_path = project_root / "surveys_db" / "phase3_output" / "phase3_database.pkl"
    
    fixer = CollaborativeDAGFixer(database_path)
    fixer.run_fixing_session()

if __name__ == "__main__":
    main()
