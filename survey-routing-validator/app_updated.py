#!/usr/bin/env python3
"""
Survey Routing Validator - Updated for Complete Automated Survey Format
Flask web app for analyzing and validating automated survey routing extractions
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from collections import defaultdict, Counter
import re

app = Flask(__name__)
app.secret_key = 'survey-routing-validator-2025-automated'

# Configuration - Updated paths to handle complete pipeline outputs
DATA_DIR = Path('../pipeline_run_20250918_103425')  # Point to your latest successful run
OUTPUT_DIR = Path('./validated_output')
OUTPUT_DIR.mkdir(exist_ok=True)

class AutomatedSurveyAnalyzer:
    def __init__(self):
        self.survey_data = None
        self.enhanced_nodes = []
        self.metadata = {}
        self.routing_stats = {}
        
    def load_automated_survey(self, filepath):
        """Load complete automated survey output"""
        with open(filepath, 'r') as f:
            self.survey_data = json.load(f)
        
        self.metadata = self.survey_data.get('metadata', {})
        self.enhanced_nodes = self.survey_data.get('enhanced_nodes', [])
        
        self._analyze_routing_quality()
        return True
    
    def _analyze_routing_quality(self):
        """Analyze routing extraction quality and statistics"""
        total_nodes = len(self.enhanced_nodes)
        nodes_with_routing = 0
        confidence_scores = []
        edge_types = Counter()
        
        for node in self.enhanced_nodes:
            routing_assignments = node.get('routing_assignments', [])
            if routing_assignments:
                nodes_with_routing += 1
                
                for assignment in routing_assignments:
                    confidence = assignment.get('confidence', 0)
                    confidence_scores.append(confidence)
                    edge_type = assignment.get('edge_type', 'unknown')
                    edge_types[edge_type] += 1
        
        self.routing_stats = {
            'total_nodes': total_nodes,
            'nodes_with_routing': nodes_with_routing,
            'routing_coverage': (nodes_with_routing / total_nodes) * 100 if total_nodes > 0 else 0,
            'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'min_confidence': min(confidence_scores) if confidence_scores else 0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0,
            'edge_type_distribution': dict(edge_types),
            'total_routing_assignments': len(confidence_scores)
        }
    
    def get_nodes_by_type(self, node_type=None):
        """Get nodes filtered by type"""
        if node_type:
            return [n for n in self.enhanced_nodes if n.get('type') == node_type]
        return self.enhanced_nodes
    
    def get_questions(self):
        """Get all question nodes"""
        return self.get_nodes_by_type('question')
    
    def get_routing_issues(self):
        """Identify potential routing issues"""
        issues = []
        
        for node in self.enhanced_nodes:
            node_id = node.get('id')
            routing_assignments = node.get('routing_assignments', [])
            
            # Check for low confidence routing
            for assignment in routing_assignments:
                confidence = assignment.get('confidence', 0)
                if confidence < 0.5:
                    issues.append({
                        'type': 'low_confidence',
                        'node_id': node_id,
                        'confidence': confidence,
                        'target': assignment.get('target_question'),
                        'severity': 'high' if confidence < 0.3 else 'medium'
                    })
            
            # Check for missing variable mappings in questions
            if node.get('type') == 'question':
                variable = node.get('variable', '')
                var_confidence = node.get('variable_metadata', {}).get('confidence', 0)
                
                if not variable or var_confidence < 0.5:
                    issues.append({
                        'type': 'variable_mapping',
                        'node_id': node_id,
                        'confidence': var_confidence,
                        'severity': 'medium'
                    })
            
            # Check for nodes without routing (except terminals)
            if not routing_assignments and node.get('type') != 'terminal':
                issues.append({
                    'type': 'missing_routing',
                    'node_id': node_id,
                    'severity': 'high'
                })
        
        return sorted(issues, key=lambda x: (x['severity'] == 'high', x['severity'] == 'medium'))
    
    def get_routing_flow(self):
        """Generate routing flow analysis"""
        flow_data = []
        
        for node in self.enhanced_nodes:
            node_id = node.get('id')
            node_type = node.get('type')
            routing_assignments = node.get('routing_assignments', [])
            
            targets = []
            for assignment in routing_assignments:
                targets.append({
                    'target': assignment.get('target_question'),
                    'condition': assignment.get('response_value'),
                    'confidence': assignment.get('confidence'),
                    'edge_type': assignment.get('edge_type')
                })
            
            flow_data.append({
                'source': node_id,
                'type': node_type,
                'text': node.get('text', '')[:100] + '...' if len(node.get('text', '')) > 100 else node.get('text', ''),
                'targets': targets,
                'target_count': len(targets)
            })
        
        return flow_data
    
    def get_variable_coverage(self):
        """Analyze variable mapping coverage"""
        questions = self.get_questions()
        total_questions = len(questions)
        
        mapped_questions = 0
        high_confidence_mapped = 0
        variable_stats = {
            'total_questions': total_questions,
            'mapped_count': 0,
            'high_confidence_count': 0,
            'coverage_percentage': 0,
            'high_confidence_percentage': 0,
            'variable_distribution': Counter()
        }
        
        for question in questions:
            variable = question.get('variable', '')
            var_metadata = question.get('variable_metadata', {})
            confidence = var_metadata.get('confidence', 0)
            
            if variable:
                mapped_questions += 1
                variable_stats['variable_distribution'][variable] += 1
                
                if confidence >= 0.8:
                    high_confidence_mapped += 1
        
        variable_stats.update({
            'mapped_count': mapped_questions,
            'high_confidence_count': high_confidence_mapped,
            'coverage_percentage': (mapped_questions / total_questions) * 100 if total_questions > 0 else 0,
            'high_confidence_percentage': (high_confidence_mapped / total_questions) * 100 if total_questions > 0 else 0
        })
        
        return variable_stats
    
    def export_dag_v11(self):
        """Export to survey_dag_schema v1.1 format from automated extraction"""
        
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
                confidence = assignment.get('confidence', 0)
                
                # Create predicate
                predicate_id = f"P_{source_id}_{response_value}".replace(' ', '_').replace('|', '_OR_').upper()
                predicates[predicate_id] = {
                    'ast': self._parse_predicate_to_ast(predicate_text, source_id, response_value),
                    'complexity': 'simple' if predicate_text == 'ALWAYS' else 'moderate',
                    'text': predicate_text,
                    'depends_on': [source_id] if predicate_text != 'ALWAYS' else [],
                    'confidence': confidence
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
                        'confidence': confidence,
                        'extraction_method': 'automated'
                    }
                })
        
        # Find start node and terminals
        questions = self.get_questions()
        start_node = self.enhanced_nodes[0].get('id') if self.enhanced_nodes else None
        terminals = [n.get('id') for n in self.enhanced_nodes if n.get('type') == 'terminal']
        
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
        
        dag = {
            "survey_dag": {
                "metadata": {
                    "id": f"htops_automated_{self.metadata.get('run_id', 'unknown')}",
                    "title": "HTOPS Survey - Automated Extraction",
                    "version": "1.1",
                    "objective": "edge",
                    "build": {
                        "extractor_version": "routing_agent_fixed",
                        "extracted_at": self.metadata.get('processed_at', datetime.now().isoformat()),
                        "method": "automated_extraction",
                        "source_format": "complete_pipeline",
                        "validation_passed": len(self.get_routing_issues()) == 0,
                        "post_edit": False,
                        "extraction_stats": self.routing_stats
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
                    "status": "AUTOMATED" if len(self.get_routing_issues()) < 5 else "NEEDS_REVIEW",
                    "issues": self.get_routing_issues()[:10],  # Limit to top 10 issues
                    "routing_stats": self.routing_stats
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

# Global analyzer instance
analyzer = AutomatedSurveyAnalyzer()

@app.route('/')
def index():
    """Main page - load automated survey"""
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
    
    return render_template('index_automated.html', surveys=available_surveys)

@app.route('/load_survey', methods=['POST'])
def load_survey():
    """Load selected automated survey"""
    survey_path = request.form.get('survey_path')
    if not survey_path:
        return redirect(url_for('index'))
    
    try:
        analyzer.load_automated_survey(survey_path)
        session['survey_path'] = survey_path
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Error loading survey: {e}", 400

@app.route('/dashboard')
def dashboard():
    """Main analysis dashboard"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    # Get analysis data
    routing_stats = analyzer.routing_stats
    variable_stats = analyzer.get_variable_coverage()
    issues = analyzer.get_routing_issues()
    metadata = analyzer.metadata
    
    context = {
        'survey_path': session['survey_path'],
        'metadata': metadata,
        'routing_stats': routing_stats,
        'variable_stats': variable_stats,
        'issues': issues[:10],  # Top 10 issues
        'total_issues': len(issues)
    }
    
    return render_template('dashboard.html', **context)

@app.route('/routing_flow')
def routing_flow():
    """Interactive routing flow visualization"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    flow_data = analyzer.get_routing_flow()
    
    context = {
        'survey_path': session['survey_path'],
        'flow_data': flow_data,
        'total_nodes': len(flow_data)
    }
    
    return render_template('routing_flow.html', **context)

@app.route('/question_analysis')
def question_analysis():
    """Detailed question and variable analysis"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    questions = analyzer.get_questions()
    
    # Enhanced question data
    question_data = []
    for q in questions:
        var_metadata = q.get('variable_metadata', {})
        routing_assignments = q.get('routing_assignments', [])
        
        question_data.append({
            'id': q.get('id'),
            'text': q.get('text', '')[:200] + '...' if len(q.get('text', '')) > 200 else q.get('text', ''),
            'variable': q.get('variable', ''),
            'confidence': var_metadata.get('confidence', 0),
            'data_type': var_metadata.get('data_type', ''),
            'routing_count': len(routing_assignments),
            'avg_routing_confidence': sum(r.get('confidence', 0) for r in routing_assignments) / len(routing_assignments) if routing_assignments else 0
        })
    
    context = {
        'survey_path': session['survey_path'],
        'questions': question_data,
        'total_questions': len(question_data)
    }
    
    return render_template('question_analysis.html', **context)

@app.route('/api/node_details/<node_id>')
def node_details(node_id):
    """Get detailed information about a specific node"""
    node = next((n for n in analyzer.enhanced_nodes if n.get('id') == node_id), None)
    
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

@app.route('/export_dag')
def export_dag():
    """Export analyzed survey to DAG format"""
    if 'survey_path' not in session:
        return redirect(url_for('index'))
    
    dag = analyzer.export_dag_v11()
    
    # Generate filename
    run_id = analyzer.metadata.get('run_id', 'unknown')
    output_file = OUTPUT_DIR / f"htops_automated_dag_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Save file
    with open(output_file, 'w') as f:
        json.dump(dag, f, indent=2)
    
    return jsonify({
        'success': True,
        'filename': output_file.name,
        'path': str(output_file),
        'dag_stats': {
            'nodes': len(dag['survey_dag']['graph']['nodes']),
            'edges': len(dag['survey_dag']['graph']['edges']),
            'predicates': len(dag['survey_dag']['predicates'])
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5002)  # Different port to avoid conflicts
