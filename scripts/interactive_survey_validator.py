#!/usr/bin/env python3
"""
Interactive Survey Validation - Step through every decision point systematically
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
        print("INTERACTIVE SURVEY VALIDATION")
        print("=" * 40)
        
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
        # Find decision points (nodes with multiple successors)
        decision_nodes = []
        for node in self.graph.nodes():
            if self.graph.out_degree(node) > 1:
                decision_nodes.append(node)
        
        # Order them by their position in a typical path
        start_node = 'INTRO_INCENTIVE'
        if self.graph.has_node(start_node):
            # Use BFS to order decision points by distance from start
            distances = nx.single_source_shortest_path_length(self.graph, start_node)
            
            decision_nodes_with_distance = []
            for node in decision_nodes:
                if node in distances:
                    decision_nodes_with_distance.append((node, distances[node]))
            
            # Sort by distance from start
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
    
    def _validate_current_decision(self):
        """Validate the current decision point."""
        if self.current_decision_index >= len(self.decision_points):
            print("\nALL DECISION POINTS VALIDATED!")
            self._show_validation_summary()
            return
        
        dp = self.decision_points[self.current_decision_index]
        
        print(f"\n" + "="*60)
        print(f"DECISION POINT {self.current_decision_index + 1}/{len(self.decision_points)}")
        print(f"Node: {dp['node']} ({dp['type']}) in block '{dp['block']}'")
        print(f"Distance from start: {dp['distance_from_start']} nodes")
        print(f"Branches: {dp['out_degree']}")
        
        # Show question text if available
        node_data = self.graph.nodes[dp['node']]
        question_text = node_data.get('text', 'No question text found')
        domain = node_data.get('domain', {})
        
        print(f"\nQUESTION TEXT: {question_text}")
        
        # Show response choices if available
        if domain and 'values' in domain:
            choices = domain['values']
            print(f"\nRESPONSE CHOICES:")
            if isinstance(choices, list):
                for i, choice in enumerate(choices, 1):
                    print(f"  {i}. {choice}")
            else:
                print(f"  {choices}")
        elif domain and 'kind' in domain:
            print(f"\nRESPONSE TYPE: {domain['kind']}")
            if 'range' in domain:
                print(f"Range: {domain['range']}")
        
        print("="*60)
        
        # Show each branch with its condition
        for i, successor in enumerate(dp['successors']):
            if self.graph.has_edge(dp['node'], successor):
                edge_data = self.graph.edges[dp['node'], successor]
                condition = edge_data.get('condition', 'always')
                edge_type = edge_data.get('edge_type', 'unknown')
                
                succ_type = self.graph.nodes[successor].get('type', 'unknown')
                succ_block = self.graph.nodes[successor].get('block', 'unknown')
                
                print(f"\nBranch {i+1}: {dp['node']} → {successor}")
                print(f"  Condition: {condition}")
                print(f"  Edge type: {edge_type}")
                print(f"  Target: {successor} ({succ_type}) in '{succ_block}'")
                
                # Show if target connects to validated nodes
                if successor in self.validated_nodes:
                    print(f"  Status: ALREADY VALIDATED ✓")
                else:
                    print(f"  Status: NEEDS VALIDATION")
        
        # Interactive choice
        print(f"\nOptions:")
        print(f"  1-{dp['out_degree']}: Explore branch 1-{dp['out_degree']}")
        print(f"  v: Mark this decision point as VALIDATED")
        print(f"  s: Skip to next decision point")
        print(f"  q: Quit validation")
        
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
        
        print(f"\n" + "-"*50)
        print(f"EXPLORING BRANCH: {decision_point['node']} → {successor}")
        print("-"*50)
        
        # Follow this path until we hit a validated node or terminal
        current = successor
        path = [decision_point['node'], successor]
        step = 1
        
        while step < 20:  # Prevent infinite loops
            if current in self.validated_nodes:
                print(f"  {step}. {current} - REACHED VALIDATED NODE ✓")
                break
            
            node_type = self.graph.nodes[current].get('type', 'unknown')
            node_block = self.graph.nodes[current].get('block', 'unknown')
            
            print(f"  {step}. {current} ({node_type}) [{node_block}]")
            
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
        
        print(f"\nPath explored: {' → '.join(path)}")
        print(f"Path length: {len(path)} nodes")
        
        # Ask what to do next
        print(f"\nOptions:")
        print(f"  b: Go back to decision point {decision_point['node']}")
        print(f"  v: Mark path as VALIDATED and continue")
        print(f"  n: Mark nodes in path as validated")
        
        choice = input(f"Choice: ").strip().lower()
        
        if choice == 'v':
            # Mark all nodes in path as validated
            for node in path:
                self.validated_nodes.add(node)
            print(f"Path validated. {len(path)} nodes marked as validated.")
            self._validate_current_decision()
        elif choice == 'n':
            # Mark individual nodes
            for node in path:
                self.validated_nodes.add(node)
            print(f"{len(path)} nodes marked as validated.")
            self._validate_current_decision()
        else:
            # Go back to decision point
            self._validate_current_decision()
    
    def _show_validation_summary(self):
        """Show final validation summary."""
        print(f"\n" + "="*50)
        print(f"VALIDATION SUMMARY")
        print("="*50)
        
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
