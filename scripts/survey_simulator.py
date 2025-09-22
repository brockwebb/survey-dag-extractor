#!/usr/bin/env python3
"""
Survey Simulator - Actually take the survey to test the logic
"""

import sys
import os
import networkx as nx

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.database_manager import DatabaseManager

class SurveySimulator:
    def __init__(self):
        self.graph = DatabaseManager().load_graph()
        self.current_node = 'INTRO_INCENTIVE'
        self.responses = {}
        self.path_taken = []
    
    def start_survey(self):
        """Start taking the survey."""
        print("SURVEY SIMULATOR - HTOPS")
        print("=" * 40)
        print("Take the actual survey to test the logic")
        print("Type 'quit' to exit, 'back' to go back, 'debug' for details")
        print("=" * 40)
        
        self._take_next_step()
    
    def _take_next_step(self):
        """Process the current node and get user input."""
        if not self.graph.has_node(self.current_node):
            print(f"ERROR: Node '{self.current_node}' not found!")
            return
        
        self.path_taken.append(self.current_node)
        node_data = self.graph.nodes[self.current_node]
        node_type = node_data.get('type', 'unknown')
        
        print(f"\n" + "-" * 50)
        print(f"Current: {self.current_node} ({node_type})")
        print(f"Path length: {len(self.path_taken)}")
        
        if node_type == 'instruction':
            self._handle_instruction()
        elif node_type == 'question':
            self._handle_question()
        elif node_type in ['terminal', 'ultimate_terminal']:
            self._handle_terminal()
        else:
            print(f"Unknown node type: {node_type}")
            self._auto_advance()
    
    def _handle_instruction(self):
        """Handle instruction nodes."""
        node_data = self.graph.nodes[self.current_node]
        text = node_data.get('text', 'No instruction text')
        
        print(f"INSTRUCTION: {text}")
        
        # Auto-advance through instructions
        successors = list(self.graph.successors(self.current_node))
        if len(successors) == 1:
            print(f"[Press Enter to continue]")
            user_input = input().strip()
            if user_input.lower() == 'quit':
                self._quit_survey()
                return
            elif user_input.lower() == 'debug':
                self._debug_current_node()
                return
            
            self.current_node = successors[0]
            self._take_next_step()
        else:
            print(f"ERROR: Instruction node has {len(successors)} successors")
            self._debug_current_node()
    
    def _handle_question(self):
        """Handle question nodes."""
        node_data = self.graph.nodes[self.current_node]
        text = node_data.get('text', 'No question text')
        domain = node_data.get('domain', {})
        
        print(f"QUESTION: {text}")
        
        # Show response options
        choices = []
        if 'values' in domain:
            values = domain['values']
            if isinstance(values, list):
                print(f"\nChoices:")
                for i, value in enumerate(values, 1):
                    if isinstance(value, dict) and 'text' in value:
                        choice_text = value['text']
                        choice_value = value.get('value', i)
                    else:
                        choice_text = str(value)
                        choice_value = value
                    
                    choices.append({'text': choice_text, 'value': choice_value})
                    print(f"  {i}. {choice_text}")
        elif 'kind' in domain:
            kind = domain['kind']
            if kind == 'numeric':
                print(f"Enter a number")
                if 'range' in domain:
                    print(f"Range: {domain['range']}")
            elif kind == 'text':
                print(f"Enter text")
            else:
                print(f"Response type: {kind}")
        else:
            print(f"No response options found")
        
        # Get user response
        while True:
            user_input = input(f"\nYour answer: ").strip()
            
            if user_input.lower() == 'quit':
                self._quit_survey()
                return
            elif user_input.lower() == 'back':
                self._go_back()
                return
            elif user_input.lower() == 'debug':
                self._debug_current_node()
                continue
            
            # Process the response
            if choices:
                try:
                    choice_num = int(user_input)
                    if 1 <= choice_num <= len(choices):
                        selected_choice = choices[choice_num - 1]
                        self.responses[self.current_node] = selected_choice['value']
                        print(f"You selected: {selected_choice['text']}")
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(choices)}")
                except ValueError:
                    print(f"Please enter a valid number")
            else:
                # Free form response
                self.responses[self.current_node] = user_input
                break
        
        # Find next node based on response
        self._advance_based_on_response()
    
    def _advance_based_on_response(self):
        """Advance to next node based on current response."""
        successors = list(self.graph.successors(self.current_node))
        
        if not successors:
            print(f"ERROR: No successors from {self.current_node}")
            return
        
        if len(successors) == 1:
            # No branching
            self.current_node = successors[0]
            self._take_next_step()
            return
        
        # Multiple successors - need to evaluate conditions
        print(f"\nEvaluating {len(successors)} possible paths...")
        
        user_response = self.responses.get(self.current_node)
        
        for successor in successors:
            if self.graph.has_edge(self.current_node, successor):
                edge_data = self.graph.edges[self.current_node, successor]
                condition = edge_data.get('condition', 'always')
                
                print(f"  Path to {successor}: condition '{condition}'")
                
                # Evaluate condition
                if self._evaluate_condition(condition, user_response):
                    print(f"  → Taking path to {successor}")
                    self.current_node = successor
                    self._take_next_step()
                    return
        
        # No condition matched
        print(f"ERROR: No condition matched for response '{user_response}'")
        print(f"Available paths:")
        for successor in successors:
            if self.graph.has_edge(self.current_node, successor):
                condition = self.graph.edges[self.current_node, successor].get('condition', 'always')
                print(f"  → {successor}: {condition}")
        
        # Let user choose manually
        print(f"\nManually select next node:")
        for i, successor in enumerate(successors, 1):
            print(f"  {i}. {successor}")
        
        try:
            choice = int(input("Choice: ")) - 1
            if 0 <= choice < len(successors):
                self.current_node = successors[choice]
                self._take_next_step()
        except ValueError:
            print("Invalid choice")
            self._take_next_step()
    
    def _evaluate_condition(self, condition, response):
        """Evaluate if condition matches response."""
        if condition == 'always':
            return True
        
        # Handle common condition patterns
        if '==' in condition:
            # Extract the value after ==
            parts = condition.split('==')
            if len(parts) == 2:
                try:
                    expected = parts[1].strip()
                    # Try numeric comparison
                    if expected.isdigit():
                        expected_val = int(expected)
                        response_val = int(response) if isinstance(response, (str, int)) else response
                        return response_val == expected_val
                    else:
                        return str(response) == expected
                except:
                    return False
        
        if '>' in condition:
            parts = condition.split('>')
            if len(parts) == 2:
                try:
                    threshold = int(parts[1].strip())
                    response_val = int(response) if isinstance(response, (str, int)) else 0
                    return response_val > threshold
                except:
                    return False
        
        # Default: condition not recognized
        print(f"    Unknown condition format: '{condition}'")
        return False
    
    def _handle_terminal(self):
        """Handle terminal nodes."""
        node_data = self.graph.nodes[self.current_node]
        text = node_data.get('text', 'Survey complete')
        
        print(f"TERMINAL: {text}")
        print(f"\nSurvey completed!")
        print(f"Path taken: {len(self.path_taken)} nodes")
        print(f"Responses given: {len(self.responses)}")
        
        # Show path summary
        questions_answered = [node for node in self.path_taken 
                            if self.graph.nodes[node].get('type') == 'question']
        
        print(f"Questions answered: {len(questions_answered)}")
        print(f"\nPath: {' → '.join(self.path_taken[:5])} ... → {self.current_node}")
        
        print(f"\nOptions:")
        print(f"  r: Restart survey")
        print(f"  q: Quit")
        
        choice = input("Choice: ").strip().lower()
        if choice == 'r':
            self._restart_survey()
        else:
            print("Thanks for testing the survey!")
    
    def _debug_current_node(self):
        """Show debug info for current node."""
        print(f"\nDEBUG INFO FOR: {self.current_node}")
        print("-" * 30)
        
        node_data = self.graph.nodes[self.current_node]
        print(f"Type: {node_data.get('type', 'unknown')}")
        print(f"Block: {node_data.get('block', 'unknown')}")
        print(f"Text: {node_data.get('text', 'No text')}")
        print(f"Domain: {node_data.get('domain', {})}")
        
        successors = list(self.graph.successors(self.current_node))
        print(f"Successors: {successors}")
        
        for succ in successors:
            if self.graph.has_edge(self.current_node, succ):
                condition = self.graph.edges[self.current_node, succ].get('condition', 'always')
                print(f"  → {succ}: {condition}")
        
        print(f"Current responses: {self.responses}")
        print(f"Path so far: {self.path_taken[-5:]}")
        
        input("Press Enter to continue...")
        self._take_next_step()
    
    def _auto_advance(self):
        """Auto-advance through non-interactive nodes."""
        successors = list(self.graph.successors(self.current_node))
        if len(successors) == 1:
            self.current_node = successors[0]
            self._take_next_step()
        else:
            print(f"Multiple successors, need manual choice: {successors}")
            self._debug_current_node()
    
    def _go_back(self):
        """Go back to previous node."""
        if len(self.path_taken) > 1:
            self.path_taken.pop()  # Remove current
            previous = self.path_taken.pop()  # Remove and get previous
            self.current_node = previous
            print(f"Going back to: {self.current_node}")
            self._take_next_step()
        else:
            print("Cannot go back - at start of survey")
            self._take_next_step()
    
    def _restart_survey(self):
        """Restart the survey."""
        self.current_node = 'INTRO_INCENTIVE'
        self.responses = {}
        self.path_taken = []
        print("Survey restarted!")
        self._take_next_step()
    
    def _quit_survey(self):
        """Quit the survey."""
        print(f"\nSurvey quit at: {self.current_node}")
        print(f"Path taken: {len(self.path_taken)} nodes")
        print(f"Responses: {len(self.responses)}")

def main():
    simulator = SurveySimulator()
    simulator.start_survey()

if __name__ == "__main__":
    main()
