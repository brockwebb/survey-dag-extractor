#!/usr/bin/env python3
"""
Survey Routing Validator - Human Validation of Automated Extractions
Flask web app for human review and validation of automated routing extractions
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from collections import defaultdict, Counter
import re

app = Flask(__name__)
app.secret_key = 'survey-routing-validator-2025-human'

# Configuration
OUTPUT_DIR = Path('./validated_output')
OUTPUT_DIR.mkdir(exist_ok=True)

class HumanValidationInterface:
    def __init__(self):
        self.survey_data = None
        self.enhanced_nodes = []
        self.metadata = {}
        self.current_question_idx = 0
        self.validation_notes = {}
        self.manual_corrections = {}
        
    def load_automated_survey(self, filepath):
        """Load complete automated survey output for human validation"""
        with open(filepath, 'r') as f:
            self.survey_data = json.load(f)
        
        self.metadata = self.survey_data.get('metadata', {})
        self.enhanced_nodes = self.survey_data.get('enhanced_nodes', [])
        self.current_question_idx = 0
        self.validation_notes = {}
        self.manual_corrections = {}
        
        return True
    
    def get_questions(self):
        """Get all nodes that need routing validation (questions and instructions)"""
        return [n for n in self.enhanced_nodes if n.get('type') in ['question', 'instruction']]
    
    def get_question_by_index(self, idx):
        """Get question by index in question list"""
        questions = self.get_questions()
        if 0 <= idx < len(questions):
            return questions[idx]
        return None
    
    def get_validation_summary(self):
        """Get summary of validation status"""
        questions = self.get_questions()
        total_questions = len(questions)
        
        not_reviewed = 0
        flagged_for_review = 0
        validated = 0
        missing_routing = 0
        
        for q in questions:
            question_id = q.get('id')
            routing_assignments = q.get('routing_assignments', [])
            validation_entry = self.validation_notes.get(question_id, {})
            validation_status = validation_entry.get('status', 'not_reviewed')
            
            # Check routing status
            has_no_routing = len(routing_assignments) == 0
            
            if has_no_routing:
                missing_routing += 1
            elif validation_status == 'validated':
                validated += 1
            elif validation_status == 'flagged_for_review':
                flagged_for_review += 1
            else:
                not_reviewed += 1
        
        return {
            'total_questions': total_questions,
            'not_reviewed': not_reviewed,
            'flagged_for_review': flagged_for_review,
            'validated': validated,
            'missing_routing': missing_routing,
            'completion_percentage': (validated / total_questions) * 100 if total_questions > 0 else 0
        }
    
    def get_available_targets(self):
        """Get all possible routing targets (questions + terminals)"""
        targets = []
        for node in self.enhanced_nodes:
            if node.get('type') in ['question', 'terminal']:
                targets.append({
                    'id': node.get('id'),
                    'type': node.get('type'),
                    'text': node.get('text', '')[:100] + '...' if len(node.get('text', '')) > 100 else node.get('text', '')
                })
        return sorted(targets, key=lambda x: x['id'])
    
    def add_terminal(self, terminal_id, terminal_text):
        """Add new terminal node"""
        new_terminal = {
            'id': terminal_id,
            'type': 'terminal',
            'block': 'validation_added',
            'order_index': len(self.enhanced_nodes) + 1,
            'text': terminal_text,
            'routing_assignments': [],  # Terminals don't route anywhere
            'metadata': {
                'created_by': 'human_validator',
                'created_at': datetime.now().isoformat()
            }
        }
        self.enhanced_nodes.append(new_terminal)
        return new_terminal
    
    def update_routing_assignment(self, question_id, routing_assignments):
        """Update routing assignments for a question (human validation)"""
        # Find the question node
        question = next((n for n in self.enhanced_nodes if n.get('id') == question_id), None)
        if not question:
            return False
        
        # Update routing assignments
        question['routing_assignments'] = routing_assignments
        
        # Mark as manually corrected
        self.manual_corrections[question_id] = {
            'corrected_at': datetime.now().isoformat(),
            'routing_count': len(routing_assignments)
        }
        
        return True
    
    def add_validation_status(self, question_id, status):
        """Set validation status for a question (not_reviewed, flagged_for_review, validated)"""
        if status in ['not_reviewed', 'flagged_for_review', 'validated']:
            self.validation_notes[question_id] = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            return True
        return False
    
    def add_validation_note(self, question_id, note):
        """Add validation note for a question"""
        existing = self.validation_notes.get(question_id, {})
        self.validation_notes[question_id] = {
            'note': note,
            'status': existing.get('status', 'not_reviewed'),
            'validated_at': datetime.now().isoformat()
        }
    
    def get_question_validation_status(self, question_id):
        """Get validation status for a specific question"""
        question = next((n for n in self.enhanced_nodes if n.get('id') == question_id), None)
        if not question:
            return None
        
        routing_assignments = question.get('routing_assignments', [])
        has_routing = len(routing_assignments) > 0
        has_low_confidence = any(r.get('confidence', 0) < 0.7 for r in routing_assignments)
        has_manual_corrections = question_id in self.manual_corrections
        has_validation_notes = question_id in self.validation_notes
        
        if not has_routing:
            status = 'missing_routing'
        elif has_low_confidence and not (has_manual_corrections or has_validation_notes):
            status = 'needs_attention'
        elif has_manual_corrections:
            status = 'manually_corrected'
        elif has_validation_notes:
            status = 'validated'
        else:
            status = 'auto_validated'  # High confidence, no issues
        
        return {
            'status': status,
            'has_routing': has_routing,
            'routing_count': len(routing_assignments),
            'min_confidence': min((r.get('confidence', 0) for r in routing_assignments), default=0),
            'avg_confidence': sum(r.get('confidence', 0) for r in routing_assignments) / len(routing_assignments) if routing_assignments else 0,
            'manual_corrections': self.manual_corrections.get(question_id),
            'validation_notes': self.validation_notes.get(question_id)
        }
    
    def export_validated_dag(self):
        """Export human-validated survey to DAG format"""
        
        # Convert routing assignments to edges and predicates
        edges = []
        predicates = {}
        edge_counter = 0
        
        for node in self.enhanced_nodes:
            source_id = node.get('id')
            routing_assignments = node.get('routing_assignments', [])
            
            for assignment in routing_assignments:
                edge_id = f"E_{edge_counter:08d}"
                edge_counter += 1
                
                target_id = assignment.get('target_question')
                response_value = assignment.get('response_value', '*')
                predicate_text = assignment.get('predicate', 'ALWAYS')
                edge_type = assignment.get('edge_type', 'fallthrough')
                confidence = assignment.get('confidence', 1.0)  # Human validated = high confidence
                
                # Create predicate
                predicate_id = f"P_{source_id}_{response_value}".replace(' ', '_').replace('|', '_OR_').upper()
                predicates[predicate_id] = {
                    'ast': self._parse_predicate_to_ast(predicate_text, source_id, response_value),
                    'complexity': 'simple' if predicate_text == 'ALWAYS' else 'moderate',
                    'text': predicate_text,
                    'depends_on': [source_id] if predicate_text != 'ALWAYS' else [],
                    'human_validated': source_id in self.manual_corrections or source_id in self.validation_notes
                }
                
                # Determine edge kind/subkind
                target_node = next((n for n in self.enhanced_nodes if n.get('id') == target_id), None)
                if target_node and target_node.get('type') == 'terminal':
                    kind = 'terminate'
                    subkind = 'terminal_branch'
                elif edge_type == 'branch':
                    kind = 'branch'
                    subkind = 'skip'
                else:
                    kind = 'sequence'
                    subkind = 'fallthrough'
                
                edges.append({
                    'id': edge_id,
                    'source': source_id,
                    'target': target_id,
                    'predicate': predicate_id,
                    'kind': kind,
                    'subkind': subkind,
                    'priority': 0,
                    'metadata': {
                        'condition_text': f"If {source_id} = '{response_value}'",
                        'original_confidence': confidence,
                        'human_validated': source_id in self.manual_corrections or source_id in self.validation_notes,
                        'extraction_method': 'human_validated'
                    }
                })
        
        # Convert enhanced nodes back to simple format
        simple_nodes = []
        for node in self.enhanced_nodes:
            simple_node = {
                'id': node.get('id'),
                'type': node.get('type'),
                'text': node.get('text'),
                'block': node.get('block'),
                'order_index': node.get('order_index')
            }
            
            # Add variable info if it's a question
            if node.get('type') == 'question':
                variable = node.get('variable', '')
                if variable:
                    simple_node['variable'] = variable
                
                # Add domain info if available
                var_metadata = node.get('variable_metadata', {})
                if var_metadata.get('data_type'):
                    simple_node['domain'] = {
                        'kind': var_metadata.get('data_type'),
                        'confidence': var_metadata.get('confidence', 0)
                    }
            
            simple_nodes.append(simple_node)
        
        # Find start node and terminals
        start_node = self.enhanced_nodes[0].get('id') if self.enhanced_nodes else None
        terminals = [n.get('id') for n in self.enhanced_nodes if n.get('type') == 'terminal']
        
        # Validation summary
        validation_summary = self.get_validation_summary()
        
        dag = {
            "survey_dag": {
                "metadata": {
                    "id": f"htops_human_validated_{self.metadata.get('run_id', 'unknown')}",
                    "title": "HTOPS Survey - Human Validated",
                    "version": "1.1",
                    "objective": "edge",
                    "build": {
                        "extractor_version": "human_validated_automated_base",
                        "extracted_at": datetime.now().isoformat(),
                        "method": "human_validation",
                        "source_format": "automated_extraction_base",
                        "validation_passed": True,
                        "post_edit": True,
                        "original_run_id": self.metadata.get('run_id'),
                        "validation_stats": {
                            "total_questions": validation_summary['total_questions'],
                            "manually_corrected": len(self.manual_corrections),
                            "validation_notes": len(self.validation_notes),
                            "completion_percentage": validation_summary['completion_percentage']
                        }
                    }
                },
                "graph": {
                    "start": start_node,
                    "terminals": terminals,
                    "nodes": simple_nodes,
                    "edges": edges
                },
                "predicates": predicates,
                "validation": {
                    "status": "HUMAN_VALIDATED",
                    "validation_summary": validation_summary,
                    "manual_corrections": self.manual_corrections,
                    "validation_notes": self.validation_notes
                }
            }
        }
        
        return dag
    
    def _parse_predicate_to_ast(self, predicate_text, source_id, response_value):
        """Convert predicate text to AST format"""
        if predicate_text == 'ALWAYS':
            return True
        
        # Simple parsing - can be enhanced
        if 'RESPONSE ==' in predicate_text:
            match = re.search(r'RESPONSE == (\w+)', predicate_text)
            if match:
                return ["==", source_id, match.group(1)]
        
        if 'RESPONSE IN' in predicate_text:
            match = re.search(r'RESPONSE IN \{([^}]+)\}', predicate_text)
            if match:
                values = [v.strip() for v in match.group(1).split(',')]
                return ["in", source_id, values]
        
        # Default fallback
        return ["==", source_id, response_value] if response_value != '*' else True

# Global validator instance
validator = HumanValidationInterface()

@app.route('/')
def index():
    """Main page - load automated survey for human validation"""
    available_surveys = []
    
    # Look in pipeline output directories
    for pipeline_dir in Path('..').glob('pipeline_run_*'):
        complete_survey = pipeline_dir / 'complete_automated_survey.json'
        if complete_survey.exists():
            available_surveys.append({
                'name': complete_survey.name,
                'path': str(complete_survey),
                'run_id': pipeline_dir.name,
                'modified': complete_survey.stat().st_mtime
            })
    
    # Sort by modification time (newest first)
    available_surveys.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('index_human_validation.html', surveys=available_surveys)

@app.route('/load_survey', methods=['POST'])
def load_survey():
    """Load selected automated survey for human validation"""
    survey_path = request.form.get('survey_path')
    if not survey_path:
        return redirect(url_for('index'))
    
    try:
        validator.load_automated_survey(survey_path)
        session['survey_path'] = survey_path
        session['current_question'] = 0
        return redirect(url_for('validate'))
    except Exception as e:
        return f"Error loading survey: {e}", 400

@app.route('/game')
def survey_quest_game():
    """Survey Quest game interface"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    return render_template('survey_quest.html')

@app.route('/api/game_data')
def get_game_data():
    """Get survey data formatted for the game"""
    print(f"DEBUG: game_data called, session keys: {list(session.keys())}")
    print(f"DEBUG: validator.enhanced_nodes length: {len(validator.enhanced_nodes)}")
    
    if not validator.enhanced_nodes:
        print("DEBUG: No enhanced nodes found")
        return jsonify({'error': 'No survey loaded - please load a survey first'}), 400
    
    # Convert survey nodes to game format
    game_nodes = []
    game_edges = []
    
    # Layout nodes in a more interesting pattern
    blocks = {}
    for node in validator.enhanced_nodes:
        block = node.get('block', 'unknown')
        if block not in blocks:
            blocks[block] = []
        blocks[block].append(node)
    
    # Position nodes by block
    x_offset = 100
    y_offset = 100
    block_spacing_x = 200
    node_spacing_y = 80
    
    for i, (block_name, block_nodes) in enumerate(blocks.items()):
        block_x = x_offset + (i * block_spacing_x)
        
        for j, node in enumerate(block_nodes):
            # Get current validation status
            validation_entry = validator.validation_notes.get(node.get('id'), {})
            status = validation_entry.get('status', 'not_reviewed')
            
            # Check for routing issues
            routing_assignments = node.get('routing_assignments', [])
            has_routing = len(routing_assignments) > 0
            has_low_confidence = any(r.get('confidence', 0) < 0.7 for r in routing_assignments)
            
            # Auto-detect issues for game display
            if not has_routing and node.get('type') != 'terminal':
                display_status = 'missing_routing'
            elif has_low_confidence and status == 'not_reviewed':
                display_status = 'needs_attention'
            else:
                display_status = status
            
            game_node = {
                'id': node.get('id'),
                'x': block_x + (j % 2) * 50,  # Slight offset for variety
                'y': y_offset + (j * node_spacing_y),
                'type': node.get('type'),
                'block': block_name,
                'status': display_status,
                'text': node.get('text', '')[:100] + '...' if len(node.get('text', '')) > 100 else node.get('text', ''),
                'routing_count': len(routing_assignments),
                'confidence': sum(r.get('confidence', 0) for r in routing_assignments) / len(routing_assignments) if routing_assignments else 0
            }
            game_nodes.append(game_node)
    
    # Create edges from routing assignments
    for node in validator.enhanced_nodes:
        source_id = node.get('id')
        routing_assignments = node.get('routing_assignments', [])
        
        for assignment in routing_assignments:
            target_id = assignment.get('target_question')
            if target_id:
                game_edges.append({
                    'from': source_id,
                    'to': target_id,
                    'condition': assignment.get('response_value', '*'),
                    'confidence': assignment.get('confidence', 0),
                    'edge_type': assignment.get('edge_type', 'fallthrough')
                })
    
    # Calculate game stats
    validation_summary = validator.get_validation_summary()
    
    return jsonify({
        'nodes': game_nodes,
        'edges': game_edges,
        'stats': validation_summary,
        'survey_info': {
            'run_id': validator.metadata.get('run_id', 'unknown'),
            'total_nodes': len(game_nodes),
            'processed_at': validator.metadata.get('processed_at')
        }
    })

@app.route('/api/game_validate_node', methods=['POST'])
def game_validate_node():
    """Validate a node from the game interface"""
    data = request.json
    node_id = data.get('node_id')
    action = data.get('action')  # 'validate', 'flag', 'report_issue'
    
    if not node_id or not action:
        return jsonify({'error': 'Node ID and action required'}), 400
    
    # Map game actions to validation statuses
    status_map = {
        'validate': 'validated',
        'flag': 'flagged_for_review',
        'report_issue': 'issues'
    }
    
    status = status_map.get(action)
    if not status:
        return jsonify({'error': 'Invalid action'}), 400
    
    success = validator.add_validation_status(node_id, status)
    if success:
        # Calculate XP reward
        xp_rewards = {
            'validate': 10,
            'flag': 5,
            'report_issue': 2
        }
        xp = xp_rewards.get(action, 0)
        
        return jsonify({
            'success': True,
            'message': f'Node {node_id} {action}d successfully',
            'xp_reward': xp,
            'new_status': status
        })
    else:
        return jsonify({'error': 'Failed to update status'}), 400

@app.route('/validate')
def validate():
    """Main validation interface - question by question"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    questions = validator.get_questions()
    current_idx = session.get('current_question', 0)
    current_question = validator.get_question_by_index(current_idx)
    
    if not current_question:
        return redirect(url_for('complete'))
    
    # Get validation status for current question
    question_id = current_question.get('id')
    validation_status = validator.get_question_validation_status(question_id)
    
    # Get available routing targets
    available_targets = validator.get_available_targets()
    
    # Get existing routing assignments (from automated extraction or manual corrections)
    existing_routing = current_question.get('routing_assignments', [])
    
    # Get validation summary
    validation_summary = validator.get_validation_summary()
    
    context = {
        'survey_path': session['survey_path'],
        'current_question': current_question,
        'question_index': current_idx + 1,
        'total_questions': len(questions),
        'validation_status': validation_status,
        'available_targets': available_targets,
        'existing_routing': existing_routing,
        'validation_summary': validation_summary,
        'progress_percent': int((current_idx / len(questions)) * 100),
        'variable_info': current_question.get('variable_metadata', {}),
        'variable_name': current_question.get('variable', '')
    }
    
    return render_template('validate_human.html', **context)

@app.route('/api/node_details/<node_id>')
def node_details(node_id):
    """Get detailed information about a specific node"""
    node = next((n for n in validator.enhanced_nodes if n.get('id') == node_id), None)
    
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    return jsonify({
        'id': node.get('id'),
        'type': node.get('type'),
        'text': node.get('text'),
        'variable': node.get('variable', ''),
        'variable_metadata': node.get('variable_metadata', {}),
        'routing_assignments': node.get('routing_assignments', []),
        'block': node.get('block'),
        'order_index': node.get('order_index')
    })

@app.route('/api/add_terminal', methods=['POST'])
def add_terminal():
    """Add new terminal node"""
    data = request.json
    terminal_id = data.get('id')
    terminal_text = data.get('text', f"Terminal: {terminal_id}")
    
    if not terminal_id:
        return jsonify({'error': 'Terminal ID required'}), 400
    
    # Check if ID already exists
    if any(n.get('id') == terminal_id for n in validator.enhanced_nodes):
        return jsonify({'error': 'Terminal ID already exists'}), 400
    
    new_terminal = validator.add_terminal(terminal_id, terminal_text)
    return jsonify({
        'success': True,
        'terminal': {
            'id': new_terminal.get('id'),
            'type': new_terminal.get('type'),
            'text': new_terminal.get('text')
        }
    })

@app.route('/api/update_routing', methods=['POST'])
def update_routing():
    """Update routing assignments for current question"""
    data = request.json
    question_id = data.get('question_id')
    routing_assignments = data.get('routing_assignments', [])
    
    if not question_id:
        return jsonify({'error': 'Question ID required'}), 400
    
    success = validator.update_routing_assignment(question_id, routing_assignments)
    if success:
        return jsonify({'success': True, 'message': 'Routing updated successfully'})
    else:
        return jsonify({'error': 'Failed to update routing'}), 400

@app.route('/api/set_validation_status', methods=['POST'])
def set_validation_status():
    """Set validation status for current question"""
    data = request.json
    question_id = data.get('question_id')
    status = data.get('status')
    
    if not question_id or not status:
        return jsonify({'error': 'Question ID and status required'}), 400
    
    success = validator.add_validation_status(question_id, status)
    if success:
        return jsonify({'success': True, 'message': f'Status updated to {status}'})
    else:
        return jsonify({'error': 'Invalid status'}), 400

@app.route('/api/add_validation_note', methods=['POST'])
def add_validation_note():
    """Add validation note for current question"""
    data = request.json
    question_id = data.get('question_id')
    note = data.get('note', '')
    
    if not question_id:
        return jsonify({'error': 'Question ID required'}), 400
    
    validator.add_validation_note(question_id, note)
    return jsonify({'success': True, 'message': 'Validation note added'})

@app.route('/next_question', methods=['POST'])
def next_question():
    """Move to next question"""
    questions = validator.get_questions()
    current_idx = session.get('current_question', 0)
    
    if current_idx < len(questions) - 1:
        session['current_question'] = current_idx + 1
    
    return redirect(url_for('validate'))

@app.route('/prev_question', methods=['POST'])
def prev_question():
    """Move to previous question"""
    current_idx = session.get('current_question', 0)
    
    if current_idx > 0:
        session['current_question'] = current_idx - 1
    
    return redirect(url_for('validate'))

@app.route('/jump_to/<int:question_idx>')
def jump_to(question_idx):
    """Jump to specific question index"""
    questions = validator.get_questions()
    if 0 <= question_idx < len(questions):
        session['current_question'] = question_idx
    
    return redirect(url_for('validate'))

@app.route('/complete')
def complete():
    """Validation complete - export options"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    validation_summary = validator.get_validation_summary()
    
    context = {
        'survey_path': session['survey_path'],
        'validation_summary': validation_summary,
        'manual_corrections': len(validator.manual_corrections),
        'validation_notes': len(validator.validation_notes)
    }
    
    return render_template('complete_human.html', **context)

@app.route('/export_dag')
def export_dag():
    """Export human-validated DAG"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    dag = validator.export_validated_dag()
    
    # Generate filename
    run_id = validator.metadata.get('run_id', 'unknown')
    output_file = OUTPUT_DIR / f"htops_human_validated_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Save file
    with open(output_file, 'w') as f:
        json.dump(dag, f, indent=2)
    
    return jsonify({
        'success': True,
        'filename': output_file.name,
        'path': str(output_file),
        'validation_summary': validator.get_validation_summary()
    })

if __name__ == '__main__':
    app.run(debug=True, port=5003)  # Different port to avoid conflicts
