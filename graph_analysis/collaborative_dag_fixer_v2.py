#!/usr/bin/env python3
"""
Collaborative DAG Fixing Tool - SINGLE SOURCE OF TRUTH VERSION

Uses DatabaseManager for clean single-file database operations.
No more confusion about which database file to use.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database_manager import DatabaseManager

class CollaborativeDAGFixer:
    """Interactive DAG fixing with single source of truth."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.extractor = None
        self.analysis_results = None
        
    def load_database(self) -> bool:
        """Load current database using DatabaseManager."""
        try:
            self.extractor = self.db.load_graph()
            print(f"✓ Loaded current database")
            print(f"  📊 {self.extractor.number_of_nodes()} nodes, {self.extractor.number_of_edges()} edges")
            return True
        except Exception as e:
            print(f"✗ Error loading database: {e}")
            return False
    
    def save_database(self, message: str = "Database updated"):
        """Save current state using DatabaseManager."""
        self.db.save_graph(self.extractor)
        print(f"  💾 {message}")
    
    def create_checkpoint(self, checkpoint_name: str):
        """Create a named snapshot before major changes."""
        self.db.create_snapshot(checkpoint_name)
    
    def analyze_connectivity_issues(self) -> Dict[str, Any]:
        """Analyze specific connectivity problems."""
        import networkx as nx
        
        isolated_nodes = list(nx.isolates(self.extractor))
        
        # Get node data from NetworkX graph
        instruction_nodes = [n for n in isolated_nodes if self.extractor.nodes[n].get('type') == 'instruction']
        terminal_nodes = [n for n in isolated_nodes if self.extractor.nodes[n].get('type') in ['terminal', 'ultimate_terminal']]
        question_nodes = [n for n in isolated_nodes if self.extractor.nodes[n].get('type') == 'question']
        
        # Find start node and reachability
        all_nodes = list(self.extractor.nodes())
        question_nodes_with_order = [(n, self.extractor.nodes[n].get('order_index', 999)) 
                                     for n in all_nodes 
                                     if self.extractor.nodes[n].get('type') == 'question']
        
        start_node = min(question_nodes_with_order, key=lambda x: x[1])[0] if question_nodes_with_order else None
        
        reachable_nodes = set()
        if start_node:
            reachable_nodes = set(nx.descendants(self.extractor, start_node))
            reachable_nodes.add(start_node)
        
        unreachable_nodes = [n for n in all_nodes if n not in reachable_nodes]
        
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
                'components': nx.number_weakly_connected_components(self.extractor),
                'total_edges': self.extractor.number_of_edges()
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
        """Apply Claude's suggested fixes and update database."""
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
                    
                    if not self.extractor.has_node(source):
                        errors.append(f"Source node '{source}' not found")
                        continue
                    if not self.extractor.has_node(target):
                        errors.append(f"Target node '{target}' not found")
                        continue
                    
                    # Add edge to NetworkX graph
                    edge_count = self.extractor.number_of_edges()
                    edge_id = f"E_{edge_count:08d}"
                    
                    self.extractor.add_edge(source, target, 
                                          id=edge_id,
                                          condition=condition,
                                          edge_type=edge_type)
                    
                    edges_added += 1
                    print(f"    ✓ {source} → {target} ({condition})")
                        
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
            if self.extractor.has_node('RECONTACT') and self.extractor.has_node('SURVEY_COMPLETE'):
                try:
                    return not nx.has_path(self.extractor, 'RECONTACT', 'SURVEY_COMPLETE')
                except:
                    return True
            return True
        elif category_id == "unreachable":
            return len(issues['reachability']['unreachable_nodes']) > 5
        
        return False
    
    def run_fixing_session(self):
        """Run fixing session with single source of truth."""
        print("COLLABORATIVE DAG FIXING - SINGLE SOURCE OF TRUTH")
        print("=" * 55)
        
        if not self.load_database():
            return False
        
        # Create checkpoint before starting
        self.create_checkpoint("before_collaborative_fixing")
        
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
                        
                        # 🔥 SAVE TO SINGLE SOURCE OF TRUTH 🔥
                        self.save_database(f"Updated after {category_name.lower()} fixes")
                        
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
            self.create_checkpoint("fully_connected")
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
        
        return True

def main():
    """Main entry point."""
    fixer = CollaborativeDAGFixer()
    fixer.run_fixing_session()

if __name__ == "__main__":
    main()
