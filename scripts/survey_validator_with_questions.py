#!/usr/bin/env python3
"""
Interactive Survey Validator with Question Text and Response Choices
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.database_manager import DatabaseManager

class InteractiveSurveyValidator:
    def __init__(self):
        self.graph = DatabaseManager().load_graph()
        self.validated_nodes = set()
        self.decision_points = []
        self.current_decision_index = 0
    
    def start_validation(self):
        """Start the interactive validation process."""
        print("INTERACTIVE SURVEY VALIDATION - WITH QUESTIONS & CHOICES")
        print("=" * 60)
        
        # Step 1: Find all decision points in order
        self._find_decision_points()
        
        if not self.decision_points:
            print("No decision points found!")
            return
        
        print(f"Found {len(self.decision_points)} decision points to validate:")
        for i, dp in enumerate(self.decision_points):
            print(f"  {i+1}. {dp['node']} ({dp['out_degree']} branches)")
        
        # Step 2: Start interactive validation
        print(f"\nStarting validation at decision point 1/{len(self.decision_points)}")
        self._validate_current_decision()
    
    def _find_decision_points(self):
        """Find all decision points in survey order."""
        decision_nodes = []
        for node in self.graph.nodes():
            if self.graph.out_degree(node) > 1:
                decision_nodes.append(node)
        
        # Order by distance from start
        start_node = 'INTRO_INCENTIVE'
        if self.graph.has_node(start_node):
            distances = nx.single_source_shortest_path_length(self.graph, start_node)
            
            decision_nodes_with_distance = []
            for node in decision_nodes:
                if node in distances:
                    decision_nodes_with_distance.append((node, distances[node]))
            
            decision_nodes_with_distance.sort(key=lambda x: x[1])
            
            # Create decision point objects
            for node, distance in decision_nodes_with_distance:
                successors = list(self.graph.successors(node))
                
                self.decision_points.append({
                    'node': node,
                    'distance_from_start': distance,
                    'successors': successors,
                    'out_degree': len(successors),
                    'validated': False,
                    'type': self.graph.nodes[node].get('type', 'unknown'),
                    'block': self.graph.nodes[node].get('block', 'unknown')
                })
    
    def _show_question_details(self, node_id):
        """Show question text and response choices for a node."""
        node_data = self.graph.nodes[node_id]
        question_text = node_data.get('text', 'No question text found')
        metadata = node_data.get('metadata', {})
        domain = node_data.get('domain', {})
        
        print(f"\nQUESTION: {question_text}")
        
        # Show additional metadata if available
        if metadata and 'text' in metadata:
            additional_text = metadata['text']
            if additional_text != question_text:
                print(f"Additional text: {additional_text}")
        
        # Show response choices
        if domain:
            if 'values' in domain:
                choices = domain['values']
                print(f"\nRESPONSE CHOICES:")
                if isinstance(choices, list):
                    for i, choice in enumerate(choices, 1):
                        if isinstance(choice, dict) and 'text' in choice:
                            print(f"  {i}. {choice['text']}")
                        else:
                            print(f"  {i}. {choice}")
                else:
                    print(f"  {choices}")
            
            if 'kind' in domain:
                print(f"\nRESPONSE TYPE: {domain['kind']}")
                if 'range' in domain:
                    print(f"Range: {domain['range']}")
    
    def _validate_current_decision(self):
        """Validate the current decision point."""
        if self.current_decision_index >= len(self.decision_points):
            print("\nALL DECISION POINTS VALIDATED!")
            self._show_validation_summary()
            return
        
        dp = self.decision_points[self.current_decision_index]
        
        print(f"\n" + "="*70)
        print(f"DECISION POINT {self.current_decision_index + 1}/{len(self.decision_points)}")
        print(f"Node: {dp['node']} ({dp['type']}) in block '{dp['block']}'")
        print(f"Distance from start: {dp['distance_from_start']} nodes")
        print(f"Branches: {dp['out_degree']}")
        print("="*70)
        
        # Show question text and choices
        self._show_question_details(dp['node'])
        
        # Show each branch with its condition
        print(f"\nBRANCHES:")
        for i, successor in enumerate(dp['successors']):
            if self.graph.has_edge(dp['node'], successor):
                edge_data = self.graph.edges[dp['node'], successor]
                condition = edge_data.get('condition', 'always')
                edge_type = edge_data.get('edge_type', 'unknown')
                
                succ_type = self.graph.nodes[successor].get('type', 'unknown')
                succ_block = self.graph.nodes[successor].get('block', 'unknown')
                
                print(f"\n  Branch {i+1}: → {successor}")
                print(f"    Condition: {condition}")
                print(f"    Edge type: {edge_type}")
                print(f"    Target: {successor} ({succ_type}) in '{succ_block}'")
                
                if successor in self.validated_nodes:
                    print(f"    Status: ALREADY VALIDATED ✓")
                else:
                    print(f"    Status: NEEDS VALIDATION")
        
        # Interactive choice
        print(f"\n" + "-"*50)
        print(f"OPTIONS:")
        print(f"  1-{dp['out_degree']}: Explore branch 1-{dp['out_degree']}")
        print(f"  v: Mark this decision point as VALIDATED")
        print(f"  s: Skip to next decision point")
        print(f"  q: Quit validation")
        print("-"*50)
        
        choice = input(f"\nChoice: ").strip().lower()
        
        if choice == 'q':
            print("Validation stopped.")
            return
        elif choice == 's':
            print("Skipping to next decision point...")
            self.current_decision_index += 1
            self._validate_current_decision()
        elif choice == 'v':
            dp['validated'] = True
            self.validated_nodes.add(dp['node'])
            print(f"Decision point {dp['node']} marked as VALIDATED ✓")
            self.current_decision_index += 1
            self._validate_current_decision()
        elif choice.isdigit() and 1 <= int(choice) <= dp['out_degree']:
            branch_index = int(choice) - 1
            self._explore_branch(dp, branch_index)
        else:
            print("Invalid choice. Try again.")
            self._validate_current_decision()
    
    def _explore_branch(self, decision_point, branch_index):
        """Explore a specific branch from a decision point."""
        successor = decision_point['successors'][branch_index]
        
        print(f"\n" + "-"*60)
        print(f"EXPLORING BRANCH: {decision_point['node']} → {successor}")
        edge_condition = "Unknown"
        if self.graph.has_edge(decision_point['node'], successor):
            edge_condition = self.graph.edges[decision_point['node'], successor].get('condition', 'always')
        print(f"Branch condition: {edge_condition}")
        print("-"*60)
        
        # Follow this path until we hit a validated node or terminal
        current = successor
        path = [decision_point['node'], successor]
        step = 1
        
        while step < 20:  # Prevent infinite loops
            if current in self.validated_nodes:
                print(f"  {step}. {current} - REACHED VALIDATED NODE ✓")
                break
            
            node_data = self.graph.nodes[current]
            node_type = node_data.get('type', 'unknown')
            node_block = node_data.get('block', 'unknown')
            question_text = node_data.get('text', '')
            
            print(f"  {step}. {current} ({node_type}) [{node_block}]")
            if question_text and node_type == 'question':
                # Truncate long text for readability
                display_text = question_text[:80] + "..." if len(question_text) > 80 else question_text
                print(f"       Q: {display_text}")
            
            successors = list(self.graph.successors(current))
            
            if not successors:
                print(f"    → TERMINAL NODE")
                break
            elif len(successors) == 1:
                next_node = successors[0]
                print(f"    → {next_node}")
                current = next_node
                path.append(current)
            else:
                print(f"    → BRANCHES TO: {successors}")
                print(f"    → This is another decision point!")
                break
            
            step += 1
        
        if step >= 20:
            print(f"  → PATH TOO LONG (stopped at step {step})")
        
        print(f"\nPath explored: {' → '.join(path[:5])}{'...' if len(path) > 5 else ''}")
        print(f"Path length: {len(path)} nodes")
        
        # Count questions in path
        questions_in_path = [n for n in path if self.graph.nodes[n].get('type') == 'question']
        print(f"Questions in path: {len(questions_in_path)}")
        
        # Ask what to do next
        print(f"\nOPTIONS:")
        print(f"  b: Go back to decision point {decision_point['node']}")
        print(f"  v: Mark path as VALIDATED and continue")
        print(f"  d: Show details of a specific node in this path")
        
        choice = input(f"Choice: ").strip().lower()
        
        if choice == 'v':
            # Mark all nodes in path as validated
            for node in path:
                self.validated_nodes.add(node)
            print(f"Path validated. {len(path)} nodes marked as validated.")
            self._validate_current_decision()
        elif choice == 'd':
            # Show details of specific node
            print("Nodes in path:")
            for i, node in enumerate(path):
                print(f"  {i}: {node}")
            
            try:
                node_index = int(input("Enter node index to see details: "))
                if 0 <= node_index < len(path):
                    self._show_question_details(path[node_index])
                else:
                    print("Invalid index")
            except ValueError:
                print("Invalid input")
            
            # Return to branch exploration
            self._explore_branch(decision_point, branch_index)
        else:
            # Go back to decision point
            self._validate_current_decision()
    
    def _show_validation_summary(self):
        """Show final validation summary."""
        print(f"\n" + "="*60)
        print(f"VALIDATION SUMMARY")
        print("="*60)
        
        validated_decisions = sum(1 for dp in self.decision_points if dp['validated'])
        print(f"Decision points validated: {validated_decisions}/{len(self.decision_points)}")
        print(f"Total nodes validated: {len(self.validated_nodes)}")
        print(f"Graph coverage: {(len(self.validated_nodes)/self.graph.number_of_nodes())*100:.1f}%")
        
        if validated_decisions == len(self.decision_points):
            print(f"\n✓ ALL DECISION POINTS VALIDATED")
            print(f"✓ Survey logic validation COMPLETE")
        else:
            print(f"\n⚠ {len(self.decision_points) - validated_decisions} decision points still need validation")

def main():
    validator = InteractiveSurveyValidator()
    validator.start_validation()

if __name__ == "__main__":
    main()
