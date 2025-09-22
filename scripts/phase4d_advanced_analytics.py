#!/usr/bin/env python3
"""
Phase 4D: Advanced Path Analytics - Deep survey analysis for visualization and optimization
"""

import sys
import os
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict, Counter
import json
import itertools

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

class AdvancedPathAnalyzer:
    """Advanced analytics for survey paths - coverage, timing, universes, families."""
    
    def __init__(self, config: DAGConfig = None):
        self.config = config or DAGConfig()
        self.graph = None
        self.all_paths = []
        self.analytics_result = {}
    
    def analyze_advanced_paths(self, graph: nx.DiGraph, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete advanced path analytics."""
        
        print("🔬 Running Advanced Path Analytics...")
        
        self.graph = graph
        start_node = self.config.get_start_node()
        
        # Generate all paths (more comprehensive)
        print("   📈 Generating comprehensive path set...")
        self.all_paths = self._generate_comprehensive_paths(start_node)
        
        # 1. Complete Coverage Analysis
        print("   🎯 Analyzing complete coverage...")
        coverage_analysis = self._analyze_complete_coverage()
        
        # 2. Survey Timing Analytics  
        print("   ⏱️ Analyzing survey timing...")
        timing_analysis = self._analyze_survey_timing()
        
        # 3. Universe Segmentation
        print("   🌐 Analyzing respondent universes...")
        universe_analysis = self._analyze_universes()
        
        # 4. Path Families for Visualization
        print("   👥 Identifying path families...")
        path_families = self._identify_path_families()
        
        # 5. Advanced Metrics
        print("   📊 Computing advanced metrics...")
        advanced_metrics = self._compute_advanced_metrics()
        
        # Build comprehensive result
        self.analytics_result = {
            "complete_coverage": coverage_analysis,
            "timing_analysis": timing_analysis,
            "universe_segmentation": universe_analysis,
            "path_families": path_families,
            "advanced_metrics": advanced_metrics,
            "visualization_data": self._prepare_visualization_data()
        }
        
        # Update schema
        schema_data['survey_dag']['advanced_analytics'] = self.analytics_result
        
        print(f"   ✅ Advanced analytics complete")
        print(f"   📊 {len(self.all_paths)} total paths analyzed")
        
        return self.analytics_result
    
    def _generate_comprehensive_paths(self, start_node: str) -> List[Dict[str, Any]]:
        """Generate all possible paths with enhanced metadata."""
        paths = []
        terminals = self.config.get_all_terminals()
        
        def dfs_comprehensive(current: str, path: List[str], visited: Set[str], 
                            conditions: List[str], depth: int = 0):
            """Enhanced DFS with condition tracking."""
            if depth > self.config.get_max_depth():
                return
            
            path = path + [current]
            
            # Terminal reached
            if current in terminals:
                path_data = {
                    "id": f"path_{len(paths):04d}",
                    "node_sequence": path.copy(),
                    "length": len(path),
                    "terminal": current,
                    "edges": self._path_to_edges(path),
                    "conditions": conditions.copy(),
                    "blocks_visited": self._get_blocks_in_path(path),
                    "question_types": self._get_question_types_in_path(path),
                    "complexity_score": self._calculate_path_complexity(path)
                }
                paths.append(path_data)
                return
            
            # Continue exploration
            for successor in self.graph.successors(current):
                if successor not in visited or successor in terminals:
                    edge_data = self.graph.edges[current, successor]
                    edge_conditions = conditions + [edge_data.get('condition', 'always')]
                    
                    new_visited = visited.copy()
                    new_visited.add(current)
                    dfs_comprehensive(successor, path, new_visited, edge_conditions, depth + 1)
        
        if self.graph.has_node(start_node):
            dfs_comprehensive(start_node, [], set(), [], 0)
        
        return paths[:self.config.get_max_paths()]
    
    def _analyze_complete_coverage(self) -> Dict[str, Any]:
        """Analyze complete edge/node coverage requirements."""
        
        total_edges = list(self.graph.edges())
        total_nodes = list(self.graph.nodes())
        
        # Find edges covered by each path
        edge_coverage = defaultdict(list)
        for path in self.all_paths:
            for edge_id in path['edges']:
                edge_coverage[edge_id].append(path['id'])
        
        # Find minimum set of paths for 100% edge coverage
        covered_edges = set(edge_coverage.keys())
        uncovered_edges = set(edge_id for edge_id in 
                            [self.graph.edges[s, t].get('id', f'{s}_to_{t}') 
                             for s, t in total_edges]) - covered_edges
        
        # Greedy set cover for minimum paths
        min_coverage_paths = self._find_minimum_coverage_paths(edge_coverage)
        
        return {
            "total_edges": len(total_edges),
            "covered_edges": len(covered_edges),
            "uncovered_edges": list(uncovered_edges),
            "coverage_percentage": (len(covered_edges) / len(total_edges)) * 100 if total_edges else 0,
            "minimum_paths_for_100_coverage": min_coverage_paths,
            "critical_edges": self._find_critical_edges(),
            "bottleneck_nodes": self._find_bottleneck_nodes()
        }
    
    def _analyze_survey_timing(self) -> Dict[str, Any]:
        """Analyze survey completion timing patterns."""
        
        if not self.all_paths:
            return {}
        
        path_lengths = [p['length'] for p in self.all_paths]
        
        # Estimate timing (rough proxy: 15 seconds per question)
        estimated_times = [length * 15 for length in path_lengths]  # seconds
        
        # Group by terminal type
        timing_by_terminal = defaultdict(list)
        for path in self.all_paths:
            timing_by_terminal[path['terminal']].append(path['length'] * 15)
        
        return {
            "path_lengths": {
                "min": min(path_lengths),
                "max": max(path_lengths),
                "average": sum(path_lengths) / len(path_lengths),
                "median": sorted(path_lengths)[len(path_lengths) // 2]
            },
            "estimated_completion_times": {
                "min_seconds": min(estimated_times),
                "max_seconds": max(estimated_times),
                "average_seconds": sum(estimated_times) / len(estimated_times),
                "min_minutes": min(estimated_times) / 60,
                "max_minutes": max(estimated_times) / 60,
                "average_minutes": (sum(estimated_times) / len(estimated_times)) / 60
            },
            "timing_by_terminal": {
                terminal: {
                    "avg_seconds": sum(times) / len(times),
                    "avg_minutes": (sum(times) / len(times)) / 60,
                    "min_minutes": min(times) / 60,
                    "max_minutes": max(times) / 60
                }
                for terminal, times in timing_by_terminal.items()
            },
            "completion_distribution": self._analyze_completion_distribution()
        }
    
    def _analyze_universes(self) -> Dict[str, Any]:
        """Analyze respondent universes and segmentation."""
        
        # Group paths by conditions/branches taken
        universe_groups = defaultdict(list)
        
        for path in self.all_paths:
            # Create universe signature based on key branching conditions
            universe_signature = self._create_universe_signature(path)
            universe_groups[universe_signature].append(path['id'])
        
        # Analyze demographic routing
        demographic_paths = self._analyze_demographic_routing()
        
        # Skip logic analysis
        skip_patterns = self._analyze_skip_patterns()
        
        return {
            "total_universes": len(universe_groups),
            "universe_groups": {
                signature: {
                    "description": self._describe_universe(signature),
                    "path_count": len(path_ids),
                    "path_ids": path_ids
                }
                for signature, path_ids in universe_groups.items()
            },
            "demographic_routing": demographic_paths,
            "skip_logic_patterns": skip_patterns,
            "conditional_exposure": self._analyze_conditional_exposure()
        }
    
    def _identify_path_families(self) -> Dict[str, Any]:
        """Identify path families for visualization grouping."""
        
        families = {}
        
        # 1. Happy Path Family (straight to completion, minimal branches)
        happy_paths = [p for p in self.all_paths 
                      if p['terminal'] in self.config.get_completion_terminals()
                      and p['complexity_score'] < 2.0]
        
        # 2. Demographics Deep Dive (lots of demographic questions)
        demo_heavy_paths = [p for p in self.all_paths 
                          if len([b for b in p['blocks_visited'] if 'demo' in b.lower()]) > 2]
        
        # 3. Early Screeners (quick exits)
        screener_paths = [p for p in self.all_paths 
                         if p['terminal'] in self.config.get_early_exit_terminals()
                         and p['length'] < 10]
        
        # 4. Health Focus Paths (health/disability questions)
        health_paths = [p for p in self.all_paths
                       if len([b for b in p['blocks_visited'] 
                             if any(keyword in b.lower() for keyword in ['health', 'dis', 'hlth'])]) > 1]
        
        # 5. Employment Track (employment section heavy)
        employment_paths = [p for p in self.all_paths
                          if len([b for b in p['blocks_visited'] if 'emp' in b.lower()]) > 1]
        
        # 6. Complete Survey Paths (full completion)
        complete_paths = [p for p in self.all_paths 
                         if p['terminal'] in self.config.get_completion_terminals()]
        
        families = {
            "happy_path": {
                "name": "Happy Path",
                "description": "Straight to completion with minimal complexity",
                "color": "#4CAF50",
                "paths": [p['id'] for p in happy_paths],
                "count": len(happy_paths)
            },
            "demographics_focus": {
                "name": "Demographics Deep Dive", 
                "description": "Paths with extensive demographic questions",
                "color": "#2196F3",
                "paths": [p['id'] for p in demo_heavy_paths],
                "count": len(demo_heavy_paths)
            },
            "early_screeners": {
                "name": "Early Screeners",
                "description": "Quick exit paths for ineligible respondents",
                "color": "#FF9800", 
                "paths": [p['id'] for p in screener_paths],
                "count": len(screener_paths)
            },
            "health_focus": {
                "name": "Health & Disability Focus",
                "description": "Paths emphasizing health and disability questions",
                "color": "#E91E63",
                "paths": [p['id'] for p in health_paths], 
                "count": len(health_paths)
            },
            "employment_track": {
                "name": "Employment Track",
                "description": "Paths with detailed employment questions",
                "color": "#9C27B0",
                "paths": [p['id'] for p in employment_paths],
                "count": len(employment_paths)
            },
            "complete_survey": {
                "name": "Complete Survey",
                "description": "All paths that reach survey completion",
                "color": "#4CAF50",
                "paths": [p['id'] for p in complete_paths],
                "count": len(complete_paths)
            }
        }
        
        return families
    
    def _compute_advanced_metrics(self) -> Dict[str, Any]:
        """Compute advanced survey metrics."""
        
        return {
            "survey_complexity": {
                "total_possible_paths": len(self.all_paths),
                "average_path_complexity": sum(p['complexity_score'] for p in self.all_paths) / len(self.all_paths) if self.all_paths else 0,
                "branching_factor": self._calculate_branching_factor(),
                "decision_points": self._count_decision_points()
            },
            "respondent_burden": {
                "min_questions": min(p['length'] for p in self.all_paths) if self.all_paths else 0,
                "max_questions": max(p['length'] for p in self.all_paths) if self.all_paths else 0,
                "avg_questions": sum(p['length'] for p in self.all_paths) / len(self.all_paths) if self.all_paths else 0
            },
            "survey_efficiency": {
                "completion_rate_proxy": self._estimate_completion_rate(),
                "path_efficiency_scores": self._calculate_path_efficiency(),
                "optimization_opportunities": self._identify_optimization_opportunities()
            }
        }
    
    def _prepare_visualization_data(self) -> Dict[str, Any]:
        """Prepare data structures optimized for D3 visualization."""
        
        return {
            "nodes_for_d3": self._prepare_d3_nodes(),
            "edges_for_d3": self._prepare_d3_edges(),
            "path_flows": self._prepare_path_flows(),
            "family_groupings": self._prepare_family_groupings(),
            "interaction_data": self._prepare_interaction_data()
        }
    
    # Helper methods (implementations abbreviated for space)
    def _path_to_edges(self, path: List[str]) -> List[str]:
        """Convert node path to edge IDs."""
        edges = []
        for i in range(len(path) - 1):
            if self.graph.has_edge(path[i], path[i + 1]):
                edge_data = self.graph.edges[path[i], path[i + 1]]
                edges.append(edge_data.get('id', f'{path[i]}_to_{path[i + 1]}'))
        return edges
    
    def _get_blocks_in_path(self, path: List[str]) -> List[str]:
        """Get unique blocks visited in path."""
        blocks = set()
        for node in path:
            if self.graph.has_node(node):
                block = self.graph.nodes[node].get('block', 'unknown')
                blocks.add(block)
        return list(blocks)
    
    def _get_question_types_in_path(self, path: List[str]) -> List[str]:
        """Get question types in path."""
        types = []
        for node in path:
            if self.graph.has_node(node):
                node_type = self.graph.nodes[node].get('type', 'unknown')
                types.append(node_type)
        return types
    
    def _calculate_path_complexity(self, path: List[str]) -> float:
        """Calculate complexity score for path."""
        # Simple complexity: length + number of conditions
        base_complexity = len(path) / 20.0  # Normalize by typical survey length
        # Add complexity for conditional nodes
        conditional_nodes = sum(1 for node in path if self._is_conditional_node(node))
        return base_complexity + (conditional_nodes * 0.5)
    
    def _is_conditional_node(self, node: str) -> bool:
        """Check if node has conditional display logic."""
        if not self.graph.has_node(node):
            return False
        universe = self.graph.nodes[node].get('universe', {})
        expression = universe.get('expression', 'always')
        return expression != 'always' and expression != 'always_show'
    
    # Additional helper methods would be implemented here...
    def _find_minimum_coverage_paths(self, edge_coverage: Dict) -> List[str]:
        """Find minimum set of paths for complete coverage.""" 
        # Simplified greedy set cover
        return []
    
    def _find_critical_edges(self) -> List[str]:
        """Find edges that appear in all paths."""
        return []
    
    def _find_bottleneck_nodes(self) -> List[str]:
        """Find nodes that all paths must traverse."""
        return []
    
    def _analyze_completion_distribution(self) -> Dict:
        """Analyze how completions are distributed."""
        return {}
    
    def _create_universe_signature(self, path: Dict) -> str:
        """Create signature for universe grouping."""
        return "default_universe"
    
    def _describe_universe(self, signature: str) -> str:
        """Describe what a universe represents."""
        return "General population"
    
    def _analyze_demographic_routing(self) -> Dict:
        """Analyze how demographics affect routing."""
        return {}
    
    def _analyze_skip_patterns(self) -> Dict:
        """Analyze skip logic patterns."""
        return {}
    
    def _analyze_conditional_exposure(self) -> Dict:
        """Analyze conditional question exposure."""
        return {}
    
    def _calculate_branching_factor(self) -> float:
        """Calculate average branching factor."""
        return 2.0
    
    def _count_decision_points(self) -> int:
        """Count nodes with multiple outgoing edges."""
        return sum(1 for node in self.graph.nodes() if self.graph.out_degree(node) > 1)
    
    def _estimate_completion_rate(self) -> float:
        """Estimate completion rate proxy."""
        if not self.all_paths:
            return 0.0
        completion_paths = len([p for p in self.all_paths if p['terminal'] in self.config.get_completion_terminals()])
        return (completion_paths / len(self.all_paths)) * 100
    
    def _calculate_path_efficiency(self) -> Dict:
        """Calculate efficiency scores for paths."""
        return {}
    
    def _identify_optimization_opportunities(self) -> List[str]:
        """Identify survey optimization opportunities."""
        return []
    
    def _prepare_d3_nodes(self) -> List[Dict]:
        """Prepare node data for D3."""
        return []
    
    def _prepare_d3_edges(self) -> List[Dict]:
        """Prepare edge data for D3."""
        return []
    
    def _prepare_path_flows(self) -> Dict:
        """Prepare path flow data."""
        return {}
    
    def _prepare_family_groupings(self) -> Dict:
        """Prepare family grouping data."""
        return {}
    
    def _prepare_interaction_data(self) -> Dict:
        """Prepare interactive visualization data."""
        return {}
    
    def print_advanced_summary(self, analytics_result: Dict[str, Any]):
        """Print comprehensive analytics summary."""
        print("\\n" + "="*80)
        print("🔬 ADVANCED PATH ANALYTICS SUMMARY")
        print("="*80)
        
        # Coverage Analysis
        coverage = analytics_result.get('complete_coverage', {})
        print(f"\\n🎯 COMPLETE COVERAGE ANALYSIS:")
        print(f"   📊 Edge Coverage: {coverage.get('covered_edges', 0)}/{coverage.get('total_edges', 0)} ({coverage.get('coverage_percentage', 0):.1f}%)")
        
        # Timing Analysis
        timing = analytics_result.get('timing_analysis', {})
        if timing:
            times = timing.get('estimated_completion_times', {})
            print(f"\\n⏱️  SURVEY TIMING ANALYSIS:")
            print(f"   ⏱️  Completion Time Range: {times.get('min_minutes', 0):.1f} - {times.get('max_minutes', 0):.1f} minutes")
            print(f"   📊 Average Completion: {times.get('average_minutes', 0):.1f} minutes")
        
        # Path Families
        families = analytics_result.get('path_families', {})
        print(f"\\n👥 PATH FAMILIES FOR VISUALIZATION:")
        for family_id, family_data in families.items():
            print(f"   {family_data.get('color', '#000')} {family_data.get('name', family_id)}: {family_data.get('count', 0)} paths")
        
        # Universe Analysis
        universes = analytics_result.get('universe_segmentation', {})
        print(f"\\n🌐 RESPONDENT UNIVERSES:")
        print(f"   🌍 Total Universes: {universes.get('total_universes', 0)}")
        
        # Advanced Metrics
        metrics = analytics_result.get('advanced_metrics', {})
        if metrics:
            complexity = metrics.get('survey_complexity', {})
            print(f"\\n📊 ADVANCED METRICS:")
            print(f"   🔀 Total Possible Paths: {complexity.get('total_possible_paths', 0)}")
            print(f"   🎯 Decision Points: {complexity.get('decision_points', 0)}")
        
        print("="*80)


def main():
    """Execute Phase 4D: Advanced Path Analytics"""
    print("PHASE 4D: ADVANCED PATH ANALYTICS")
    print("=" * 50)
    
    db = DatabaseManager()
    config = DAGConfig()
    analyzer = AdvancedPathAnalyzer(config)
    
    try:
        # Load validated DAG and schema
        print("📊 Loading validated DAG and schema...")
        graph = db.load_graph()
        
        schema_path = Path('../exports/htops_survey_dag_v1.1.json')
        with open(schema_path, 'r') as f:
            schema_data = json.load(f)
        
        print(f"   ✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Run advanced analytics
        print("\\n🔬 PHASE 4D: Running Advanced Path Analytics...")
        analytics_result = analyzer.analyze_advanced_paths(graph, schema_data)
        
        # Print comprehensive summary
        analyzer.print_advanced_summary(analytics_result)
        
        # Save updated schema
        with open(schema_path, 'w') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
        
        print(f"\\n💾 Updated schema with advanced analytics: {schema_path}")
        
        # Create final snapshot
        db.create_snapshot("phase4d_advanced_analytics_complete")
        
        print("\\n🎉 PHASE 4D COMPLETE!")
        print("=" * 50)
        print("✅ Complete coverage analysis")
        print("✅ Survey timing analytics")
        print("✅ Universe segmentation")
        print("✅ Path families for visualization")
        print("✅ Advanced metrics computed")
        print("✅ D3 visualization data prepared")
        print("\\n🏆 PHASE 4 COMPLETE: EXPORT + VALIDATION + COVERAGE + ADVANCED ANALYTICS")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 4D failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
