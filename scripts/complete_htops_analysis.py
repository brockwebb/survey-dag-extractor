#!/usr/bin/env python3
"""
Complete HTOPS Survey Analysis - Final Report
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict, Counter
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.database_manager import DatabaseManager

def complete_htops_analysis():
    """Generate complete analysis of HTOPS survey."""
    print("HTOPS SURVEY ANALYSIS - COMPLETE REPORT")
    print("=" * 50)
    
    db = DatabaseManager()
    graph = db.load_graph()
    
    analysis = {}
    
    # 1. Survey Structure
    print("1. SURVEY STRUCTURE")
    print("-" * 20)
    
    structure = {
        'total_nodes': graph.number_of_nodes(),
        'total_edges': graph.number_of_edges(),
        'node_types': dict(Counter(graph.nodes[n].get('type', 'unknown') for n in graph.nodes())),
        'total_questions': sum(1 for n in graph.nodes() if graph.nodes[n].get('type') == 'question')
    }
    
    print(f"Total nodes: {structure['total_nodes']}")
    print(f"Total edges: {structure['total_edges']}")
    print(f"Questions: {structure['total_questions']}")
    print(f"Instructions: {structure['node_types'].get('instruction', 0)}")
    print(f"Terminals: {structure['node_types'].get('terminal', 0) + structure['node_types'].get('ultimate_terminal', 0)}")
    
    analysis['structure'] = structure
    
    # 2. Survey Sections
    print("\n2. SURVEY SECTIONS")
    print("-" * 20)
    
    sections = defaultdict(list)
    for node in graph.nodes():
        if graph.nodes[node].get('type') == 'question':
            block = graph.nodes[node].get('block', 'unknown')
            sections[block].append(node)
    
    section_summary = {}
    for block, questions in sorted(sections.items()):
        section_summary[block] = {
            'question_count': len(questions),
            'first_question': questions[0],
            'last_question': questions[-1] if len(questions) > 1 else questions[0]
        }
        print(f"{block}: {len(questions)} questions")
    
    analysis['sections'] = section_summary
    
    # 3. Decision Points
    print("\n3. DECISION POINTS")
    print("-" * 20)
    
    decision_points = []
    for node in graph.nodes():
        if graph.out_degree(node) > 1:
            successors = list(graph.successors(node))
            conditions = []
            for succ in successors:
                edge_data = graph.edges[node, succ]
                conditions.append(edge_data.get('condition', 'always'))
            
            # Only real decision points (different conditions)
            if len(set(conditions)) > 1:
                dp = {
                    'node': node,
                    'type': graph.nodes[node].get('type', 'unknown'),
                    'block': graph.nodes[node].get('block', 'unknown'),
                    'branches': []
                }
                
                for succ, cond in zip(successors, conditions):
                    dp['branches'].append({'target': succ, 'condition': cond})
                
                decision_points.append(dp)
                
                print(f"{node} ({dp['type']}) in {dp['block']}")
                for branch in dp['branches']:
                    print(f"  -> {branch['target']}: {branch['condition']}")
    
    analysis['decision_points'] = decision_points
    
    # 4. Survey Pathways
    print("\n4. SURVEY PATHWAYS")
    print("-" * 20)
    
    pathways = {}
    
    # Main completion path
    try:
        main_path = nx.shortest_path(graph, 'INTRO_INCENTIVE', 'SURVEY_COMPLETE')
        main_questions = [n for n in main_path if graph.nodes[n].get('type') == 'question']
        
        pathways['completion'] = {
            'total_nodes': len(main_path),
            'questions': len(main_questions),
            'estimated_time_minutes': len(main_questions) * 0.5  # 30 seconds per question
        }
        
        print(f"Main completion path: {len(main_path)} nodes, {len(main_questions)} questions")
        print(f"Estimated time: {pathways['completion']['estimated_time_minutes']:.1f} minutes")
        
    except Exception as e:
        print(f"Could not find main path: {e}")
        pathways['completion'] = None
    
    # Early exit paths
    early_exits = ['END', 'R2a', 'END_INELIGIBLE']
    pathways['early_exits'] = {}
    
    for exit_node in early_exits:
        if graph.has_node(exit_node):
            try:
                exit_path = nx.shortest_path(graph, 'INTRO_INCENTIVE', exit_node)
                exit_questions = [n for n in exit_path if graph.nodes[n].get('type') == 'question']
                
                pathways['early_exits'][exit_node] = {
                    'total_nodes': len(exit_path),
                    'questions': len(exit_questions),
                    'estimated_time_minutes': len(exit_questions) * 0.5
                }
                
                print(f"Early exit to {exit_node}: {len(exit_questions)} questions, {pathways['early_exits'][exit_node]['estimated_time_minutes']:.1f} minutes")
                
            except Exception as e:
                pathways['early_exits'][exit_node] = None
    
    analysis['pathways'] = pathways
    
    # 5. Coverage Analysis
    print("\n5. COVERAGE ANALYSIS")
    print("-" * 20)
    
    # Find all completion paths (sample)
    completion_paths = list(nx.all_simple_paths(graph, 'INTRO_INCENTIVE', 'SURVEY_COMPLETE', cutoff=200))
    
    if completion_paths:
        # Limit for analysis
        sample_paths = completion_paths[:min(1000, len(completion_paths))]
        
        path_lengths = [len(path) for path in sample_paths]
        question_counts = []
        
        for path in sample_paths:
            questions = [n for n in path if graph.nodes[n].get('type') == 'question']
            question_counts.append(len(questions))
        
        coverage = {
            'total_possible_paths': len(completion_paths),
            'analyzed_paths': len(sample_paths),
            'avg_questions': sum(question_counts) / len(question_counts),
            'min_questions': min(question_counts),
            'max_questions': max(question_counts),
            'avg_completion_time': (sum(question_counts) / len(question_counts)) * 0.5
        }
        
        print(f"Total possible completion paths: {coverage['total_possible_paths']}")
        print(f"Average questions per completion: {coverage['avg_questions']:.1f}")
        print(f"Question range: {coverage['min_questions']} - {coverage['max_questions']}")
        print(f"Average completion time: {coverage['avg_completion_time']:.1f} minutes")
        
        analysis['coverage'] = coverage
    
    # 6. Generate Final Report
    report_path = Path('../exports/htops_complete_analysis.json')
    with open(report_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n6. REPORT GENERATED")
    print("-" * 20)
    print(f"Complete analysis saved to: {report_path}")
    
    # Summary
    print(f"\nHTOPS SURVEY SUMMARY:")
    print(f"- {structure['total_questions']} questions across {len(section_summary)} sections")
    print(f"- {len(decision_points)} real decision points")
    print(f"- {coverage.get('total_possible_paths', 'Unknown')} possible completion paths")
    print(f"- Average completion: {coverage.get('avg_completion_time', 'Unknown'):.1f} minutes")
    
    return analysis

if __name__ == "__main__":
    complete_htops_analysis()
