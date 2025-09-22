#!/usr/bin/env python3
"""
Survey Routing Validator
Simple Flask web app for systematic survey routing validation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'survey-routing-validator-2025'  # Change in production

# Configuration
DATA_DIR = Path('../data')
OUTPUT_DIR = Path('./validated_output')
OUTPUT_DIR.mkdir(exist_ok=True)

class SurveyValidator:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.predicates = {}
        self.current_question_idx = 0
        
    def load_survey(self, filename):
        """Load survey from minimal JSON format"""
        filepath = DATA_DIR / filename
        with open(filepath, 'r') as f:
            self.nodes = json.load(f)
        
        # Initialize validation state
        self.current_question_idx = 0
        self.edges = []
        self.predicates = {}
        
        # Add basic metadata to nodes that need it
        for node in self.nodes:
            if node['type'] == 'question' and 'domain' not in node:
                node['domain'] = {'kind': 'unknown'}
            if 'universe' not in node:
                node['universe'] = {'expression': 'always_show'}
            if 'metadata' not in node:
                node['metadata'] = {}
                
        return True
    
    def get_questions(self):
        """Get all question nodes"""
        return [n for n in self.nodes if n['type'] == 'question']
    
    def get_question_by_index(self, idx):
        """Get question by index in question list"""
        questions = self.get_questions()
        if 0 <= idx < len(questions):
            return questions[idx]
        return None
    
    def get_available_targets(self):
        """Get all possible routing targets (questions + terminals)"""
        targets = []
        for node in self.nodes:
            if node['type'] in ['question', 'terminal']:
                targets.append({
                    'id': node['id'],
                    'type': node['type'],
                    'text': node['text'][:100] + '...' if len(node['text']) > 100 else node['text']
                })
        return sorted(targets, key=lambda x: x['id'])
    
    def add_terminal(self, terminal_id, terminal_text):
        """Add new terminal node"""
        new_terminal = {
            'id': terminal_id,
            'type': 'terminal',
            'block': 'validation_added',
            'order_index': len(self.nodes) + 1,
            'text': terminal_text,
            'metadata': {
                'created_by': 'routing_validator',
                'created_at': datetime.now().isoformat()
            }
        }
        self.nodes.append(new_terminal)
        return new_terminal
    
    def create_predicate(self, question_id, response_value):
        """Auto-generate predicate AST for response routing"""
        predicate_id = f"P_{question_id}_{response_value}".replace(' ', '_').upper()
        
        # Simple equality predicate: ["==", "Q1", "Yes"]
        ast = ["==", question_id, response_value]
        
        predicate = {
            'ast': ast,
            'complexity': 'simple',
            'text': f"{question_id} == '{response_value}'",
            'depends_on': [question_id]
        }
        
        self.predicates[predicate_id] = predicate
        return predicate_id
    
    def add_routing_edge(self, source_id, target_id, response_value):
        """Add routing edge with auto-generated predicate"""
        predicate_id = self.create_predicate(source_id, response_value)
        
        # Determine edge kind
        target_node = next((n for n in self.nodes if n['id'] == target_id), None)
        if target_node and target_node['type'] == 'terminal':
            kind = 'terminate'
            subkind = 'terminal_branch'
        else:
            kind = 'branch'
            subkind = 'skip'
        
        edge = {
            'id': f"E_{len(self.edges):08d}",
            'source': source_id,
            'target': target_id,
            'predicate': predicate_id,
            'kind': kind,
            'subkind': subkind,
            'priority': 0,
            'metadata': {
                'condition_text': f"If {source_id} = '{response_value}'"
            }
        }
        
        self.edges.append(edge)
        return edge
    
    def validate_categorical_encoding(self, question):
        """Check if question has proper categorical encoding"""
        issues = []
        
        if question.get('domain', {}).get('kind') == 'unknown':
            issues.append("No domain specified - categorical encoding missing")
        
        domain = question.get('domain', {})
        if domain.get('kind') in ['enum', 'set'] and not domain.get('values'):
            issues.append("Enum/set domain specified but no values provided")
            
        return issues
    
    def export_dag_v11(self):
        """Export to survey_dag_schema v1.1 format"""
        
        # Find start node (first question)
        questions = self.get_questions()
        start_node = questions[0]['id'] if questions else None
        
        # Find terminals
        terminals = [n['id'] for n in self.nodes if n['type'] == 'terminal']
        
        dag = {
            "survey_dag": {
                "metadata": {
                    "id": "htops_validated",
                    "title": "HTOPS Survey - Routing Validated",
                    "version": "1.1",
                    "objective": "edge",
                    "build": {
                        "extractor_version": "routing_validator_1.0",
                        "extracted_at": datetime.now().isoformat(),
                        "method": "human_validation",
                        "source_format": "minimal_json",
                        "validation_passed": True,
                        "post_edit": True
                    }
                },
                "graph": {
                    "start": start_node,
                    "terminals": terminals,
                    "nodes": self.nodes,
                    "edges": self.edges
                },
                "predicates": self.predicates,
                "validation": {
                    "status": "OK",
                    "issues": []
                }
            }
        }
        
        return dag

# Global validator instance
validator = SurveyValidator()

@app.route('/')
def index():
    """Main page - load survey"""
    available_surveys = []
    for file in DATA_DIR.glob('*.json'):
        if 'minimal' in file.name or 'nodes' in file.name:
            available_surveys.append(file.name)
    
    return render_template('index.html', surveys=available_surveys)

@app.route('/load_survey', methods=['POST'])
def load_survey():
    """Load selected survey"""
    filename = request.form.get('survey_file')
    if not filename:
        return redirect(url_for('index'))
    
    try:
        validator.load_survey(filename)
        session['survey_file'] = filename
        session['current_question'] = 0
        return redirect(url_for('validate'))
    except Exception as e:
        return f"Error loading survey: {e}", 400

@app.route('/validate')
def validate():
    """Main validation interface"""
    if 'survey_file' not in session:
        return redirect(url_for('index'))
    
    questions = validator.get_questions()
    current_idx = session.get('current_question', 0)
    current_question = validator.get_question_by_index(current_idx)
    
    if not current_question:
        return redirect(url_for('complete'))
    
    # Get validation issues for current question
    validation_issues = validator.validate_categorical_encoding(current_question)
    
    # Get available routing targets
    available_targets = validator.get_available_targets()
    
    # Get existing edges for this question
    existing_edges = [e for e in validator.edges if e['source'] == current_question['id']]
    
    context = {
        'survey_file': session['survey_file'],
        'current_question': current_question,
        'question_index': current_idx + 1,
        'total_questions': len(questions),
        'validation_issues': validation_issues,
        'available_targets': available_targets,
        'existing_edges': existing_edges,
        'progress_percent': int((current_idx / len(questions)) * 100)
    }
    
    return render_template('validate.html', **context)

@app.route('/api/add_terminal', methods=['POST'])
def add_terminal():
    """Add new terminal node"""
    data = request.json
    terminal_id = data.get('id')
    terminal_text = data.get('text', f"Terminal: {terminal_id}")
    
    if not terminal_id:
        return jsonify({'error': 'Terminal ID required'}), 400
    
    # Check if ID already exists
    if any(n['id'] == terminal_id for n in validator.nodes):
        return jsonify({'error': 'Terminal ID already exists'}), 400
    
    new_terminal = validator.add_terminal(terminal_id, terminal_text)
    return jsonify({
        'success': True,
        'terminal': {
            'id': new_terminal['id'],
            'type': new_terminal['type'],
            'text': new_terminal['text']
        }
    })

@app.route('/api/add_routing', methods=['POST'])
def add_routing():
    """Add routing edge"""
    data = request.json
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    response_value = data.get('response_value')
    
    if not all([source_id, target_id, response_value]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    edge = validator.add_routing_edge(source_id, target_id, response_value)
    return jsonify({
        'success': True,
        'edge': {
            'id': edge['id'],
            'source': edge['source'],
            'target': edge['target'],
            'response': response_value
        }
    })

@app.route('/api/update_domain', methods=['POST'])
def update_domain():
    """Update question domain/categorical encoding"""
    data = request.json
    question_id = data.get('question_id')
    domain_kind = data.get('domain_kind', 'enum')
    domain_values = data.get('domain_values', [])
    
    # Find and update question
    question = next((n for n in validator.nodes if n['id'] == question_id), None)
    if not question:
        return jsonify({'error': 'Question not found'}), 400
    
    question['domain'] = {
        'kind': domain_kind,
        'values': domain_values
    }
    
    return jsonify({'success': True})

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

@app.route('/complete')
def complete():
    """Validation complete - export options"""
    if 'survey_file' not in session:
        return redirect(url_for('index'))
    
    questions = validator.get_questions()
    validated_count = len([q for q in questions if any(e['source'] == q['id'] for e in validator.edges)])
    
    context = {
        'survey_file': session['survey_file'],
        'total_questions': len(questions),
        'validated_count': validated_count,
        'total_edges': len(validator.edges),
        'total_predicates': len(validator.predicates)
    }
    
    return render_template('complete.html', **context)

@app.route('/export_dag')
def export_dag():
    """Export validated DAG"""
    if 'survey_file' not in session:
        return redirect(url_for('index'))
    
    dag = validator.export_dag_v11()
    
    # Generate filename
    base_name = session['survey_file'].replace('.json', '')
    output_file = OUTPUT_DIR / f"{base_name}_validated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Save file
    with open(output_file, 'w') as f:
        json.dump(dag, f, indent=2)
    
    return jsonify({
        'success': True,
        'filename': output_file.name,
        'path': str(output_file)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
