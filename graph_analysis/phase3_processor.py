#!/usr/bin/env python3
"""
Generic Phase 3: Universe Validation & Edge Creation

Reusable processor that works with ANY survey extraction:
1. Makes all universe conditions explicit
2. Extracts routing logic from progress files
3. Creates conditional edges based on extracted routing
4. Validates mathematical DAG properties

Works with any survey - no hard-coded routing rules.
"""

import sys
import json
import pickle
from pathlib import Path
import re
from typing import Dict, List, Any, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

class GenericPhase3Processor:
    """Generic Phase 3 processor for any survey extraction."""
    
    def __init__(self, database_path: Path, progress_files_dir: Path):
        """Initialize with database and progress files directory."""
        self.database_path = database_path
        self.progress_files_dir = progress_files_dir
        self.extractor = None
        self.routing_rules = []
        
    def load_database(self) -> bool:
        """Load the consolidated database."""
        if not self.database_path.exists():
            print(f"✗ Database not found: {self.database_path}")
            return False
            
        try:
            with open(self.database_path, 'rb') as f:
                self.extractor = pickle.load(f)
            print(f"✓ Loaded database: {len(self.extractor.nodes)} nodes, {self.extractor.graph.number_of_edges()} edges")
            return True
        except Exception as e:
            print(f"✗ Error loading database: {e}")
            return False
    
    def make_universe_explicit(self) -> int:
        """Make all universe conditions explicit - generic for any survey."""
        explicit_count = 0
        
        for node in self.extractor.nodes:
            # Only process questions and instructions
            if node['type'] in ['question', 'instruction']:
                if 'universe' not in node or not node.get('universe'):
                    # Add explicit "always" condition
                    node['universe'] = {
                        'expression': 'always',
                        'dependencies': []
                    }
                    # Update graph node
                    if self.extractor.graph.has_node(node['id']):
                        self.extractor.graph.nodes[node['id']]['universe'] = node['universe']
                    explicit_count += 1
                    print(f"  Added 'always' universe to {node['id']}")
        
        return explicit_count
    
    def extract_routing_from_progress_files(self) -> List[Dict[str, Any]]:
        """Extract routing logic from progress files - generic parser."""
        routing_rules = []
        
        # Find all progress files
        progress_files = sorted(self.progress_files_dir.glob("*progress_chunk_*.json"))
        
        if not progress_files:
            print("  No progress files found - looking for routing in database nodes")
            return self._extract_routing_from_nodes()
        
        print(f"  Found {len(progress_files)} progress files")
        
        for progress_file in progress_files:
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                
                # Extract routing from nodes_updated
                if 'nodes_updated' in progress_data:
                    for node_data in progress_data['nodes_updated']:
                        if 'routing' in node_data:
                            # This would be if routing was saved in progress files
                            # Currently our progress files don't have routing data
                            pass
                
                print(f"    Processed {progress_file.name}")
                
            except Exception as e:
                print(f"    Warning: Error reading {progress_file.name}: {e}")
        
        # If no routing found in progress files, extract from current nodes
        if not routing_rules:
            print("  No routing in progress files, extracting from current node structure")
            routing_rules = self._extract_routing_from_nodes()
        
        return routing_rules
    
    def _extract_routing_from_nodes(self) -> List[Dict[str, Any]]:
        """Extract routing logic from current node structure."""
        routing_rules = []
        
        # Look for universe conditions that imply routing
        for node in self.extractor.nodes:
            if 'universe' in node and node['universe'].get('expression') != 'always':
                universe_expr = node['universe']['expression']
                
                # Parse universe expressions to infer routing
                # e.g., "ASK IF Q1 == 2 OR Q1 == 3" implies Q1 routes to this node
                routing_rule = self._parse_universe_to_routing(node['id'], universe_expr)
                if routing_rule:
                    routing_rules.extend(routing_rule)
        
        # Add basic sequential routing for nodes without explicit routing
        routing_rules.extend(self._infer_sequential_routing())
        
        return routing_rules
    
    def _parse_universe_to_routing(self, target_node: str, universe_expr: str) -> List[Dict[str, Any]]:
        """Parse universe expression to infer routing rules."""
        routing_rules = []
        
        # Basic parsing of common patterns
        # "ASK IF Q1 == 2" -> Q1 routes to target_node when condition == 2
        # "ASK IF D11 > 0" -> D11 routes to target_node when > 0
        
        # Simple regex patterns for common universe conditions
        patterns = [
            r'ASK IF ([A-Za-z0-9_]+) == ([0-9]+)',  # Q1 == 2
            r'ASK IF ([A-Za-z0-9_]+) > ([0-9]+)',   # D11 > 0
            r'ASK IF ([A-Za-z0-9_]+) != ([0-9]+)', # Q1 != 1
            r'ASK IF ([A-Za-z0-9_]+) includes option ([0-9]+)', # D12 includes option 1
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, universe_expr)
            for match in matches:
                source_node = match[0]
                condition_value = match[1]
                
                # Create routing rule
                routing_rules.append({
                    'source': source_node,
                    'target': target_node,
                    'condition': f"== {condition_value}" if "==" in pattern else f"> {condition_value}",
                    'type': 'branch',
                    'derived_from': f"universe condition: {universe_expr}"
                })
        
        return routing_rules
    
    def _infer_sequential_routing(self) -> List[Dict[str, Any]]:
        """Infer basic sequential routing for questions without explicit routing."""
        routing_rules = []
        
        # Get questions in order
        questions = [n for n in self.extractor.nodes if n['type'] == 'question']
        questions.sort(key=lambda x: x.get('order_index', 0))
        
        # Create basic sequential flow
        for i, question in enumerate(questions[:-1]):
            current_id = question['id']
            next_question = questions[i + 1]
            next_id = next_question['id']
            
            # Only add if no other routing exists for this node
            existing_rules = [r for r in self.routing_rules if r['source'] == current_id]
            if not existing_rules:
                routing_rules.append({
                    'source': current_id,
                    'target': next_id,
                    'condition': 'always',
                    'type': 'fallthrough',
                    'derived_from': 'sequential order inference'
                })
        
        return routing_rules
    
    def create_conditional_edges(self, routing_rules: List[Dict[str, Any]]) -> int:
        """Create conditional edges from routing rules - generic implementation."""
        edges_created = 0
        
        for rule in routing_rules:
            source = rule['source']
            target = rule['target']
            condition = rule['condition']
            edge_type = rule.get('type', 'branch')
            
            # Validate nodes exist
            if not self.extractor.graph.has_node(source):
                print(f"    Warning: Source node {source} not found")
                continue
            if not self.extractor.graph.has_node(target):
                print(f"    Warning: Target node {target} not found") 
                continue
            
            # Create edge
            try:
                edge_id = self.extractor.add_conditional_edge(source, target, condition, edge_type)
                if edge_id:
                    edges_created += 1
                    print(f"    {source} → {target} ({condition}) [{rule.get('derived_from', 'explicit')}]")
            except Exception as e:
                print(f"    Error: {source} → {target}: {e}")
        
        return edges_created
    
    def validate_dag_properties(self) -> Dict[str, Any]:
        """Validate mathematical properties - generic validation."""
        import networkx as nx
        
        # Basic validation
        validation = self.extractor.validate_current_state()
        
        # Enhanced DAG validation
        results = {
            'basic_properties': validation['graph_properties'],
            'dag_validation': {
                'is_acyclic': nx.is_directed_acyclic_graph(self.extractor.graph),
                'node_count': self.extractor.graph.number_of_nodes(),
                'edge_count': self.extractor.graph.number_of_edges(),
                'isolated_nodes': list(nx.isolates(self.extractor.graph)),
                'weakly_connected_components': len(list(nx.weakly_connected_components(self.extractor.graph))),
                'strongly_connected_components': len(list(nx.strongly_connected_components(self.extractor.graph)))
            }
        }
        
        # Reachability analysis
        questions = [n for n in self.extractor.nodes if n['type'] == 'question']
        if questions:
            start_node = min(questions, key=lambda x: x.get('order_index', 0))['id']
            try:
                reachable = set(nx.descendants(self.extractor.graph, start_node))
                reachable.add(start_node)
                
                results['reachability'] = {
                    'start_node': start_node,
                    'reachable_count': len(reachable),
                    'total_nodes': len(self.extractor.nodes),
                    'unreachable_nodes': [n['id'] for n in self.extractor.nodes if n['id'] not in reachable]
                }
            except Exception as e:
                results['reachability'] = {'error': str(e)}
        
        return results
    
    def save_results(self, output_dir: Path, routing_rules: List[Dict[str, Any]], 
                    validation_results: Dict[str, Any]) -> Tuple[Path, Path]:
        """Save Phase 3 results - generic output."""
        output_dir.mkdir(exist_ok=True)
        
        # Save updated database
        db_path = output_dir / "phase3_database.pkl"
        with open(db_path, 'wb') as f:
            pickle.dump(self.extractor, f)
        
        # Save analysis results
        results_path = output_dir / "phase3_analysis.json"
        results = {
            'phase3_summary': {
                'total_nodes': len(self.extractor.nodes),
                'total_edges': self.extractor.graph.number_of_edges(),
                'routing_rules_applied': len(routing_rules),
                'explicit_universe_conditions': len([n for n in self.extractor.nodes if 'universe' in n])
            },
            'routing_rules': routing_rules,
            'validation_results': validation_results
        }
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return db_path, results_path
    
    def process_phase3(self, output_dir: Path) -> bool:
        """Run complete Phase 3 processing - main entry point."""
        print("PHASE 3: UNIVERSE VALIDATION & EDGE CREATION")
        print("=" * 60)
        
        # Step 1: Load database
        if not self.load_database():
            return False
        
        # Step 2: Make universe conditions explicit
        print(f"\nSTEP 1: UNIVERSE CONDITION ENHANCEMENT")
        print("-" * 40)
        explicit_count = self.make_universe_explicit()
        print(f"✓ Made {explicit_count} universe conditions explicit")
        
        # Step 3: Extract routing logic
        print(f"\nSTEP 2: ROUTING LOGIC EXTRACTION")
        print("-" * 40)
        self.routing_rules = self.extract_routing_from_progress_files()
        print(f"✓ Extracted {len(self.routing_rules)} routing rules")
        
        # Step 4: Create conditional edges
        print(f"\nSTEP 3: CONDITIONAL EDGE CREATION")
        print("-" * 40)
        edges_created = self.create_conditional_edges(self.routing_rules)
        print(f"✓ Created {edges_created} conditional edges")
        
        # Step 5: Validate DAG properties
        print(f"\nSTEP 4: MATHEMATICAL VALIDATION")
        print("-" * 40)
        validation_results = self.validate_dag_properties()
        self._print_validation_summary(validation_results)
        
        # Step 6: Save results
        print(f"\nSTEP 5: SAVE RESULTS")
        print("-" * 40)
        db_path, results_path = self.save_results(output_dir, self.routing_rules, validation_results)
        print(f"✓ Database saved: {db_path}")
        print(f"✓ Analysis saved: {results_path}")
        
        print(f"\n" + "=" * 60)
        print("PHASE 3 COMPLETE! 🎉")
        print("=" * 60)
        
        return True
    
    def _print_validation_summary(self, results: Dict[str, Any]):
        """Print validation results summary."""
        if 'dag_validation' in results:
            dag = results['dag_validation']
            print(f"  Is Acyclic: {dag['is_acyclic']}")
            print(f"  Nodes: {dag['node_count']}")
            print(f"  Edges: {dag['edge_count']}")
            print(f"  Isolated nodes: {len(dag['isolated_nodes'])}")
            print(f"  Connected components: {dag['weakly_connected_components']}")
        
        if 'reachability' in results and 'error' not in results['reachability']:
            reach = results['reachability']
            print(f"  Reachable from start: {reach['reachable_count']}/{reach['total_nodes']}")

def main():
    """Main entry point for command-line usage."""
    project_root = Path(__file__).parent.parent
    
    # Default paths
    database_path = project_root / "surveys_db" / "htops_graph_database.pkl"
    progress_files_dir = project_root / "surveys_db"
    output_dir = project_root / "surveys_db" / "phase3_output"
    
    # Create processor
    processor = GenericPhase3Processor(database_path, progress_files_dir)
    
    # Run Phase 3
    success = processor.process_phase3(output_dir)
    
    if success:
        print("\nPhase 3 processing completed successfully!")
    else:
        print("\nPhase 3 processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
