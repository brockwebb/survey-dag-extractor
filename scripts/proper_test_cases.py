#!/usr/bin/env python3
"""
Proper Test Case Generation - Focus on Real Survey Logic
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def generate_proper_test_cases():
    """Generate proper test cases focusing on real survey logic."""
    print("🧪 PROPER TEST CASE GENERATION")
    print("=" * 50)
    
    db = DatabaseManager()
    config = DAGConfig()
    graph = db.load_graph()
    
    # Identify key survey sections (excluding instructions)
    print("📋 IDENTIFYING KEY SURVEY SECTIONS...")
    
    # Filter out instruction nodes
    question_nodes = []
    instruction_nodes = []
    
    for node in graph.nodes():
        node_data = graph.nodes[node]
        node_type = node_data.get('type', 'unknown')
        
        if node_type == 'question':
            question_nodes.append(node)
        elif node_type in ['instruction', 'display']:
            instruction_nodes.append(node)
    
    print(f"   Questions: {len(question_nodes)}")
    print(f"   Instructions: {len(instruction_nodes)} (ignoring for test logic)")
    
    # Find the actual survey entry point (first question after instructions)
    print("\\n🚪 FINDING REAL SURVEY ENTRY POINT...")
    
    start_node = config.get_start_node()
    
    # Find first question node reachable from start
    first_question = None
    if graph.has_node(start_node):
        for node in nx.dfs_preorder_nodes(graph, start_node):
            if node in question_nodes:
                first_question = node
                break
    
    print(f"   First question after instructions: {first_question}")
    
    # Generate test cases for the specific flows you mentioned
    print("\\n🧪 GENERATING FOCUSED TEST CASES...")
    
    test_cases = []
    
    # TEST CASE 1: Address Confirm → Get Name → Early Exit
    print("\\n📍 TEST CASE 1: Address/Name Confirmation → Early Exit")
    if graph.has_node('ADDRESS_CONFIRM') and graph.has_node('GET_NAME'):
        # Find path: ADDRESS_CONFIRM → GET_NAME → END
        early_exit_path = find_specific_path(graph, 'ADDRESS_CONFIRM', ['END', 'R2a', 'END_INELIGIBLE'])
        if early_exit_path:
            test_cases.append({
                'id': 'TC001_AddressName_EarlyExit',
                'description': 'Address confirmation → Name → Early termination',
                'path': early_exit_path,
                'focus': 'Early screening and eligibility',
                'questions_only': [n for n in early_exit_path if n in question_nodes]
            })
            print(f"   ✅ Found path: {len(early_exit_path)} nodes")
            print(f"   Questions: {[n for n in early_exit_path if n in question_nodes]}")
    
    # TEST CASE 2: Address → Name → Continue to Language (English=Yes) → Mood  
    print("\\n🗣️  TEST CASE 2: English Primary Language → Direct to Mood")
    english_yes_path = find_language_path_english_primary(graph, question_nodes)
    if english_yes_path:
        test_cases.append({
            'id': 'TC002_English_Primary',  
            'description': 'English primary language → direct to mood question',
            'path': english_yes_path,
            'focus': 'English-primary respondents (shortest language path)',
            'questions_only': [n for n in english_yes_path if n in question_nodes]
        })
        print(f"   ✅ English primary path: {len(english_yes_path)} nodes")
        print(f"   Questions: {[n for n in english_yes_path[:10] if n in question_nodes]} ...")
    
    # TEST CASE 3: Address → Name → Language (English=No) → Primary Lang → Proficiency → Mood
    print("\\n🌍 TEST CASE 3: Non-English Primary → Language Questions → Mood")  
    non_english_path = find_language_path_non_english_primary(graph, question_nodes)
    if non_english_path:
        test_cases.append({
            'id': 'TC003_Non_English_Primary',
            'description': 'Non-English primary → language questions → mood question',
            'path': non_english_path,
            'focus': 'Non-English speakers (full language assessment)',
            'questions_only': [n for n in non_english_path if n in question_nodes]
        })
        print(f"   ✅ Non-English path: {len(non_english_path)} nodes")
        print(f"   Questions: {[n for n in non_english_path[:15] if n in question_nodes]} ...")
    
    # TEST CASE 4: From mood question, take shortest path to completion
    print("\\n🎯 TEST CASE 4: From Mood Question → Shortest to Completion")
    mood_to_completion_path = find_mood_to_completion_shortest_path(graph)
    if mood_to_completion_path:
        test_cases.append({
            'id': 'TC004_Mood_To_Completion',
            'description': 'From mood question → shortest path to survey completion',
            'path': mood_to_completion_path,
            'focus': 'Core survey completion (minimal branching)',
            'questions_only': [n for n in mood_to_completion_path if n in question_nodes]
        })
        print(f"   ✅ Mood→Completion: {len(mood_to_completion_path)} nodes")
        print(f"   Questions: {len([n for n in mood_to_completion_path if n in question_nodes])} total")
    
    # Summary of test cases
    print("\\n📊 TEST CASE SUMMARY:")
    total_unique_nodes = set()
    total_unique_questions = set()
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\\n   Test Case {i}: {tc['id']}")
        print(f"      Description: {tc['description']}")
        print(f"      Total nodes: {len(tc['path'])}")
        print(f"      Questions: {len(tc['questions_only'])}")
        print(f"      Focus: {tc['focus']}")
        
        # Track coverage
        total_unique_nodes.update(tc['path'])
        total_unique_questions.update(tc['questions_only'])
    
    print(f"\\n🎯 COVERAGE ANALYSIS:")
    print(f"   Total unique nodes covered: {len(total_unique_nodes)}")
    print(f"   Total unique questions covered: {len(total_unique_questions)}")
    print(f"   Node coverage: {(len(total_unique_nodes)/graph.number_of_nodes())*100:.1f}%")
    print(f"   Question coverage: {(len(total_unique_questions)/len(question_nodes))*100:.1f}%")
    
    # Export test cases
    export_test_cases(test_cases)
    
    return test_cases

def find_specific_path(graph, start_node, target_nodes):
    """Find path from start to any of the target nodes."""
    for target in target_nodes:
        if graph.has_node(start_node) and graph.has_node(target):
            try:
                if nx.has_path(graph, start_node, target):
                    return nx.shortest_path(graph, start_node, target)
            except:
                continue
    return None

def find_language_path_english_primary(graph, question_nodes):
    """Find path for English primary speakers."""
    # Look for: ADDRESS_CONFIRM → GET_NAME → LANG → (English=Yes branch) → Q1 (mood)
    
    try:
        # Start from ADDRESS_CONFIRM, go through language routing to Q1
        if graph.has_node('ADDRESS_CONFIRM') and graph.has_node('Q1'):
            # Find path that goes through LANG but NOT LANG1_R (English primary)
            all_paths = list(nx.all_simple_paths(graph, 'ADDRESS_CONFIRM', 'Q1', cutoff=20))
            
            for path in all_paths:
                # Look for path with LANG but without LANG1_R (English primary path)
                if 'LANG' in path and 'LANG1_R' not in path:
                    return path
            
            # Fallback: any path from ADDRESS_CONFIRM to Q1
            if all_paths:
                return all_paths[0]
                
    except Exception as e:
        print(f"   ⚠️ Error finding English primary path: {e}")
    
    return None

def find_language_path_non_english_primary(graph, question_nodes):
    """Find path for non-English primary speakers."""
    # Look for: ADDRESS_CONFIRM → GET_NAME → LANG → LANG1_R → LANG_WELL → Q1
    
    try:
        if graph.has_node('ADDRESS_CONFIRM') and graph.has_node('Q1'):
            all_paths = list(nx.all_simple_paths(graph, 'ADDRESS_CONFIRM', 'Q1', cutoff=25))
            
            for path in all_paths:
                # Look for path with both LANG and LANG1_R (non-English primary)
                if 'LANG' in path and 'LANG1_R' in path:
                    return path
    
    except Exception as e:
        print(f"   ⚠️ Error finding non-English primary path: {e}")
    
    return None

def find_mood_to_completion_shortest_path(graph):
    """Find shortest path from mood question to completion."""
    try:
        if graph.has_node('Q1') and graph.has_node('SURVEY_COMPLETE'):
            return nx.shortest_path(graph, 'Q1', 'SURVEY_COMPLETE')
    except Exception as e:
        print(f"   ⚠️ Error finding mood to completion path: {e}")
    
    return None

def export_test_cases(test_cases):
    """Export test cases to JSON file."""
    import json
    
    export_data = {
        'test_suite': 'HTOPS_Focused_Test_Cases',
        'generated_at': '2025-09-16',
        'description': 'Focused test cases for key survey logic paths',
        'test_cases': []
    }
    
    for tc in test_cases:
        export_data['test_cases'].append({
            'id': tc['id'],
            'description': tc['description'],
            'focus_area': tc['focus'],
            'path_length': len(tc['path']),
            'question_count': len(tc['questions_only']),
            'node_sequence': tc['path'],
            'questions_sequence': tc['questions_only']
        })
    
    export_path = Path('../exports/focused_test_cases.json')
    with open(export_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\\n💾 Exported test cases to: {export_path}")

if __name__ == "__main__":
    test_cases = generate_proper_test_cases()
