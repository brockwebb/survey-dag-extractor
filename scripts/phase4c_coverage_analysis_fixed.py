#!/usr/bin/env python3
"""
Phase 4C: Coverage Analysis - Survey-Aware Path Analysis
"""

import sys
import os
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

class SurveyCoverageAnalyzer:
    """Analyzes survey DAG with proper survey methodology understanding."""
    
    def __init__(self):
        self.graph = None
        self.start_node = None
        self.terminal_nodes = []
        self.paths = []
        self.coverage_result = {}
    
    def analyze_coverage(self, graph: nx.DiGraph, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete coverage analysis on survey DAG."""
        
        print("🔍 Running Survey-Aware Coverage Analysis...")
        
        self.graph = graph
        
        # Extract key information
        graph_data = schema_data['survey_dag']['graph']
        self.start_node = graph_data['start']
        self.terminal_nodes = graph_data['terminals']
        
        print(f"   🏁 Start: {self.start_node}")
        print(f"   🎯 Terminals: {len(self.terminal_nodes)} ({', '.join(self.terminal_nodes)})")
        
        # Step 1: Generate all possible paths
        print("   📈 Generating survey paths...")
        self.paths = self._generate_all_paths()
        
        # Step 2: Analyze path coverage
        print("   📊 Analyzing path coverage...")
        coverage_metrics = self._analyze_path_coverage()
        
        # Step 3: Find paths with survey methodology awareness
        print("   🎯 Analyzing paths with survey methodology...")
        optimal_paths = self._find_survey_paths()
        
        # Step 4: Generate coverage elements
        print("   🧩 Generating coverage elements...")
        coverage_elements = self._generate_coverage_elements()
        
        # Step 5: Build final result
        self.coverage_result = {
            "universe": {
                "objective": "edge",
                "elements": coverage_elements,
                "total_count": len(coverage_elements)
            },
            "optimal_paths": optimal_paths,
            "metrics": coverage_metrics
        }
        
        # Update schema data
        schema_data['survey_dag']['coverage'] = self.coverage_result
        
        print(f"   ✅ Coverage analysis complete")
        print(f"   📊 {len(self.paths)} total paths")
        print(f"   🎯 {len(optimal_paths)} analyzed paths") 
        print(f"   🧩 {len(coverage_elements)} coverage elements")
        
        return self.coverage_result
    
    def _generate_all_paths(self) -> List[Dict[str, Any]]:
        """Generate all possible paths through the survey."""
        paths = []
        
        def dfs_paths(current: str, path: List[str], visited: Set[str], depth: int = 0):
            """DFS to find all paths to terminals."""
            if depth > 50:  # Prevent infinite loops
                return
            
            path = path + [current]
            
            # If we reached a terminal, record the path
            if current in self.terminal_nodes:
                paths.append({
                    "id": f"path_{len(paths):04d}",
                    "node_sequence": path.copy(),
                    "length": len(path),
                    "terminal": current,
                    "edges": self._path_to_edges(path)
                })
                return
            
            # Continue to successors
            for successor in self.graph.successors(current):
                if successor not in visited or successor in self.terminal_nodes:
                    new_visited = visited.copy()
                    new_visited.add(current)
                    dfs_paths(successor, path, new_visited, depth + 1)
        
        if self.graph.has_node(self.start_node):
            dfs_paths(self.start_node, [], set(), 0)
        
        return paths[:100]  # Limit to first 100 paths
    
    def _path_to_edges(self, node_path: List[str]) -> List[str]:
        """Convert node sequence to edge sequence."""
        edges = []
        for i in range(len(node_path) - 1):
            source, target = node_path[i], node_path[i + 1]
            if self.graph.has_edge(source, target):
                edge_data = self.graph.edges[source, target]
                edge_id = edge_data.get('id', f'{source}_to_{target}')
                edges.append(edge_id)
        return edges
    
    def _analyze_path_coverage(self) -> Dict[str, Any]:
        """Analyze coverage metrics across all paths."""
        
        # Count node visits
        node_visits = defaultdict(int)
        edge_visits = defaultdict(int)
        
        for path in self.paths:
            for node in path['node_sequence']:
                node_visits[node] += 1
            for edge in path['edges']:
                edge_visits[edge] += 1
        
        # Calculate coverage percentages
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()
        covered_nodes = len(node_visits)
        covered_edges = len(edge_visits)
        
        node_coverage = (covered_nodes / total_nodes) * 100 if total_nodes > 0 else 0
        edge_coverage = (covered_edges / total_edges) * 100 if total_edges > 0 else 0
        
        # Terminal distribution
        terminal_distribution = defaultdict(int)
        for path in self.paths:
            terminal_distribution[path['terminal']] += 1
        
        return {
            "coverage_percentage": round(edge_coverage, 2),
            "path_count": len(self.paths),
            "algorithm": "survey_aware_depth_first_search",
            "node_coverage": {
                "covered": covered_nodes,
                "total": total_nodes,
                "percentage": round(node_coverage, 2)
            },
            "edge_coverage": {
                "covered": covered_edges, 
                "total": total_edges,
                "percentage": round(edge_coverage, 2)
            },
            "terminal_distribution": dict(terminal_distribution),
            "average_path_length": round(sum(p['length'] for p in self.paths) / len(self.paths), 2) if self.paths else 0
        }
    
    def _find_survey_paths(self) -> List[Dict[str, Any]]:
        """Analyze paths with survey methodology awareness."""
        analyzed_paths = []
        
        # Survey methodology: Complete paths are desirable, early exits should be minimized
        for terminal in self.terminal_nodes:
            if not self.graph.has_node(terminal):
                continue
            
            try:
                if nx.has_path(self.graph, self.start_node, terminal):
                    shortest_path = nx.shortest_path(self.graph, self.start_node, terminal)
                    
                    # Classify path type based on survey methodology
                    if terminal == 'SURVEY_COMPLETE':
                        path_type = "optimal_completion"
                        priority = 1
                        survey_value = "HIGH"
                        methodology_note = "Desired outcome - full survey completion"
                    elif terminal in ['END', 'END_INELIGIBLE', 'R2a']:
                        path_type = "early_termination"
                        priority = 3  # Lower priority = avoid
                        survey_value = "LOW"
                        methodology_note = "Early termination - minimize in real deployment"
                    else:
                        path_type = "other_termination"
                        priority = 2
                        survey_value = "MEDIUM"
                        methodology_note = "Other termination path"
                    
                    analyzed_paths.append({
                        "id": f"path_to_{terminal}",
                        "terminal": terminal,
                        "node_sequence": shortest_path,
                        "length": len(shortest_path),
                        "edges": self._path_to_edges(shortest_path),
                        "type": path_type,
                        "priority": priority,
                        "survey_value": survey_value,
                        "methodology_note": methodology_note
                    })
            except nx.NetworkXNoPath:
                continue
        
        # Sort by priority (completion first, early termination last)
        analyzed_paths.sort(key=lambda x: x['priority'])
        
        return analyzed_paths
    
    def _generate_coverage_elements(self) -> List[Dict[str, Any]]:
        """Generate coverage elements for testing/validation."""
        elements = []
        
        # Create elements for each edge (since objective is "edge")
        for source, target, edge_data in self.graph.edges(data=True):
            elements.append({
                "id": edge_data.get('id', f'edge_{len(elements):04d}'),
                "type": "edge",
                "source": source,
                "target": target,
                "condition": edge_data.get('condition', 'always'),
                "predicate": edge_data.get('predicate', 'P_TRUE'),
                "covered_by_paths": len([p for p in self.paths 
                                       if edge_data.get('id', f'{source}_to_{target}') in p['edges']])
            })
        
        return elements
    
    def print_coverage_summary(self, coverage_result: Dict[str, Any]):
        """Print formatted survey-aware coverage analysis summary."""
        print("\\n" + "="*70)
        print("📊 SURVEY-AWARE COVERAGE ANALYSIS SUMMARY")
        print("="*70)
        
        metrics = coverage_result['metrics']
        universe = coverage_result['universe']
        optimal_paths = coverage_result['optimal_paths']
        
        print(f"\\n🎯 COVERAGE METRICS:")
        print(f"   📈 Overall Coverage: {metrics['coverage_percentage']}%")
        print(f"   📊 Total Paths: {metrics['path_count']}")
        print(f"   📏 Average Path Length: {metrics['average_path_length']} nodes")
        
        print(f"\\n🧩 ELEMENT COVERAGE:")
        print(f"   🔗 Edge Coverage: {metrics['edge_coverage']['covered']}/{metrics['edge_coverage']['total']} ({metrics['edge_coverage']['percentage']}%)")
        print(f"   📍 Node Coverage: {metrics['node_coverage']['covered']}/{metrics['node_coverage']['total']} ({metrics['node_coverage']['percentage']}%)")
        
        print(f"\\n🎯 TERMINAL DISTRIBUTION:")
        for terminal, count in metrics['terminal_distribution'].items():
            percentage = (count / metrics['path_count']) * 100 if metrics['path_count'] > 0 else 0
            print(f"   {terminal}: {count} paths ({percentage:.1f}%)")
        
        print(f"\\n📋 SURVEY METHODOLOGY ANALYSIS:")
        for path in optimal_paths:
            if path['type'] == 'optimal_completion':
                icon = "🎯 OPTIMAL"
            elif path['type'] == 'early_termination':
                icon = "⚠️  MINIMIZE"
            else:
                icon = "📍 OTHER"
            print(f"   {icon}: {path['terminal']} ({path['length']} nodes, {path['survey_value']} value)")
            print(f"      → {path['methodology_note']}")
        
        print(f"\\n📋 UNIVERSE:")
        print(f"   🎯 Objective: {universe['objective']}")
        print(f"   🧩 Elements: {universe['total_count']}")
        
        print("="*70)


def main():
    """Execute Phase 4C: Survey-Aware Coverage Analysis"""
    print("PHASE 4C: SURVEY-AWARE COVERAGE ANALYSIS")
    print("=" * 50)
    
    db = DatabaseManager()
    analyzer = SurveyCoverageAnalyzer()
    
    try:
        # Load the validated DAG
        print("📊 Loading validated DAG...")
        graph = db.load_graph()
        print(f"   ✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Load the schema export
        schema_path = Path('../exports/htops_survey_dag_v1.1.json')
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema export not found: {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema_data = json.load(f)
        
        print(f"   ✅ Loaded schema export")
        
        # Run coverage analysis
        print("\\n🔍 PHASE 4C: Running Survey-Aware Coverage Analysis...")
        coverage_result = analyzer.analyze_coverage(graph, schema_data)
        
        # Print summary
        analyzer.print_coverage_summary(coverage_result)
        
        # Save updated schema with coverage
        with open(schema_path, 'w') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
        print(f"\\n💾 Updated schema with coverage analysis: {schema_path}")
        
        # Create final snapshot
        db.create_snapshot("phase4c_survey_aware_coverage_complete")
        
        print("\\n🎉 PHASE 4C COMPLETE!")
        print("=" * 50)
        print("✅ Survey-aware coverage analysis complete")
        print("✅ Paths analyzed with survey methodology")
        print("✅ Early termination paths flagged for minimization")
        print("✅ Universe elements generated")
        print("✅ Schema updated with coverage data")
        print("\\n🏆 PHASE 4 COMPLETE: EXPORT + VALIDATION + SURVEY-AWARE COVERAGE")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 4C failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
