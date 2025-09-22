#!/usr/bin/env python3
"""
Mathematical DAG Validator - Comprehensive validation using graph theory
"""

import json
import networkx as nx
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import jsonschema

class MathematicalValidator:
    """Comprehensive mathematical validation of survey DAG."""
    
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path
        self.schema = None
        self.issues = []
        self.gates = {}
        
        if schema_path and Path(schema_path).exists():
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)
    
    def validate_survey_dag(self, survey_dag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete mathematical validation on survey DAG."""
        
        print("🔍 Running Mathematical Validation...")
        
        self.issues = []
        self.gates = {}
        
        # Extract graph data
        graph_data = survey_dag_data['survey_dag']['graph']
        nodes = graph_data['nodes']
        edges = graph_data['edges']
        start = graph_data['start']
        terminals = graph_data['terminals']
        predicates = survey_dag_data['survey_dag']['predicates']
        
        # Build NetworkX graph for analysis
        G = self._build_networkx_graph(nodes, edges)
        
        # Run validation gates
        print("   📊 Validating graph topology...")
        self._validate_topology(G, start, terminals)
        
        print("   🎯 Validating terminals...")
        self._validate_terminals(G, nodes, terminals)
        
        print("   🔗 Validating edges...")
        self._validate_edges(G, edges, nodes)
        
        print("   🧮 Validating predicates...")
        self._validate_predicates(predicates, edges)
        
        print("   📐 Validating schema compliance...")
        self._validate_schema_compliance(survey_dag_data)
        
        # Generate final status
        status = self._determine_final_status()
        
        # Build result
        validation_result = {
            "status": status,
            "issues": self.issues,
            "gates": self.gates
        }
        
        # Update the original data
        survey_dag_data['survey_dag']['validation'] = validation_result
        
        print(f"   ✅ Validation complete: {status}")
        print(f"   📋 Issues found: {len(self.issues)}")
        print(f"   🚪 Gates passed: {sum(1 for v in self.gates.values() if v)}/{len(self.gates)}")
        
        return validation_result
    
    def _build_networkx_graph(self, nodes: List[Dict], edges: List[Dict]) -> nx.DiGraph:
        """Build NetworkX graph from schema data."""
        G = nx.DiGraph()
        
        # Add nodes
        for node in nodes:
            G.add_node(node['id'], **node)
        
        # Add edges
        for edge in edges:
            G.add_edge(edge['source'], edge['target'], **edge)
        
        return G
    
    def _validate_topology(self, G: nx.DiGraph, start: str, terminals: List[str]):
        """Validate basic graph topology."""
        
        # Gate 1: Acyclic check
        try:
            cycles = list(nx.simple_cycles(G))
            if cycles:
                self.gates['acyclic'] = False
                for cycle in cycles:
                    self._add_issue("CYCLE_DETECTED", "error", 
                                  f"/graph/edges", 
                                  f"Cycle detected: {' -> '.join(cycle + [cycle[0]])}")
            else:
                self.gates['acyclic'] = True
        except Exception as e:
            self.gates['acyclic'] = False
            self._add_issue("TOPOLOGY_ERROR", "error", "/graph", f"Topology analysis failed: {e}")
        
        # Gate 2: Single start node
        self.gates['single_start'] = G.has_node(start)
        if not self.gates['single_start']:
            self._add_issue("MISSING_START_NODE", "error", "/graph/start", f"Start node '{start}' not found in graph")
        
        # Gate 3: All nodes reachable from start
        if self.gates['single_start']:
            try:
                reachable = set(nx.descendants(G, start))
                reachable.add(start)
                all_nodes = set(G.nodes())
                unreachable = all_nodes - reachable
                
                if unreachable:
                    self.gates['all_reachable'] = False
                    self._add_issue("UNREACHABLE_NODES", "error", "/graph/nodes", 
                                  f"Unreachable nodes: {sorted(list(unreachable))}")
                else:
                    self.gates['all_reachable'] = True
            except Exception as e:
                self.gates['all_reachable'] = False
                self._add_issue("REACHABILITY_ERROR", "error", "/graph", f"Reachability analysis failed: {e}")
        else:
            self.gates['all_reachable'] = False
    
    def _validate_terminals(self, G: nx.DiGraph, nodes: List[Dict], terminals: List[str]):
        """Validate terminal node architecture."""
        
        # Find ultimate terminal (SURVEY_COMPLETE)
        ultimate_terminals = [t for t in terminals if t == 'SURVEY_COMPLETE']
        
        # Gate 4: Single ultimate terminal
        if len(ultimate_terminals) == 1:
            self.gates['single_ultimate_terminal'] = True
        else:
            self.gates['single_ultimate_terminal'] = False
            if len(ultimate_terminals) == 0:
                self._add_issue("MISSING_ULTIMATE_TERMINAL", "error", "/graph/terminals", 
                              "No SURVEY_COMPLETE ultimate terminal found")
            else:
                self._add_issue("MULTIPLE_ULTIMATE_TERMINALS", "error", "/graph/terminals", 
                              f"Multiple ultimate terminals: {ultimate_terminals}")
        
        # Gate 5: All terminals reachable
        terminal_nodes = set(terminals)
        existing_terminals = set(n for n in G.nodes() if n in terminal_nodes)
        missing_terminals = terminal_nodes - existing_terminals
        
        if missing_terminals:
            self.gates['terminals_reachable'] = False
            self._add_issue("MISSING_TERMINALS", "error", "/graph/terminals", 
                          f"Terminal nodes not found in graph: {sorted(list(missing_terminals))}")
        else:
            self.gates['terminals_reachable'] = True
        
        # Gate 6: Terminals connected to ultimate
        if self.gates['single_ultimate_terminal'] and 'SURVEY_COMPLETE' in G.nodes():
            try:
                # Check if intermediate terminals have path to SURVEY_COMPLETE
                intermediate_terminals = [t for t in terminals if t != 'SURVEY_COMPLETE']
                disconnected = []
                
                for terminal in intermediate_terminals:
                    if terminal in G.nodes():
                        try:
                            path_exists = nx.has_path(G, terminal, 'SURVEY_COMPLETE')
                            if not path_exists:
                                disconnected.append(terminal)
                        except nx.NetworkXError:
                            disconnected.append(terminal)
                
                if disconnected:
                    self.gates['terminals_connected_to_ultimate'] = False
                    self._add_issue("TERMINALS_NOT_CONNECTED", "warning", "/graph/terminals",
                                  f"Terminals not connected to SURVEY_COMPLETE: {disconnected}")
                else:
                    self.gates['terminals_connected_to_ultimate'] = True
            except Exception as e:
                self.gates['terminals_connected_to_ultimate'] = False
                self._add_issue("TERMINAL_CONNECTION_ERROR", "error", "/graph/terminals",
                              f"Terminal connection analysis failed: {e}")
        else:
            self.gates['terminals_connected_to_ultimate'] = False
        
        # Validate terminal node types
        node_types = {n['id']: n['type'] for n in nodes}
        for terminal in terminals:
            if terminal in node_types:
                expected_type = 'ultimate_terminal' if terminal == 'SURVEY_COMPLETE' else 'terminal'
                actual_type = node_types[terminal]
                if actual_type != expected_type:
                    self._add_issue("INVALID_TERMINAL_TYPE", "warning", f"/graph/nodes",
                                  f"Terminal {terminal} has type '{actual_type}', expected '{expected_type}'")
    
    def _validate_edges(self, G: nx.DiGraph, edges: List[Dict], nodes: List[Dict]):
        """Validate edge structure and consistency."""
        
        # Build node type lookup
        node_types = {n['id']: n['type'] for n in nodes}
        
        edge_issues = []
        
        for edge in edges:
            edge_id = edge['id']
            source = edge['source']
            target = edge['target']
            
            # Check source exists
            if source not in G.nodes():
                edge_issues.append(f"Edge {edge_id}: source '{source}' not found")
                continue
            
            # Check target exists  
            if target not in G.nodes():
                edge_issues.append(f"Edge {edge_id}: target '{target}' not found")
                continue
            
            # Check source is not terminal UNLESS connecting to collector terminal
            source_type = node_types.get(source, 'unknown')
            target_type = node_types.get(target, 'unknown')
            
            # Allow terminal-to-terminal connections for collector architecture
            # But flag ultimate_terminal with outgoing edges (except to system collector)
            if source_type == 'ultimate_terminal' and target not in ['FINAL_TERMINATION']:
                edge_issues.append(f"Edge {edge_id}: ultimate terminal '{source}' should only connect to FINAL_TERMINATION")
            elif source_type == 'terminal' and target_type not in ['terminal', 'ultimate_terminal']:
                edge_issues.append(f"Edge {edge_id}: terminal '{source}' should only connect to other terminals")
            
            # Check required fields
            if 'predicate' not in edge:
                edge_issues.append(f"Edge {edge_id}: missing predicate")
            
            if 'kind' not in edge:
                edge_issues.append(f"Edge {edge_id}: missing kind")
        
        # Record edge validation results
        if edge_issues:
            for issue in edge_issues:
                self._add_issue("INVALID_EDGE", "error", "/graph/edges", issue)
        
        # Check for duplicate edges
        edge_pairs = [(e['source'], e['target']) for e in edges]
        duplicates = []
        seen = set()
        for pair in edge_pairs:
            if pair in seen:
                duplicates.append(pair)
            seen.add(pair)
        
        if duplicates:
            for source, target in duplicates:
                self._add_issue("DUPLICATE_EDGE", "warning", "/graph/edges", 
                              f"Duplicate edge: {source} -> {target}")
    
    def _validate_predicates(self, predicates: Dict[str, Any], edges: List[Dict]):
        """Validate predicates and their usage."""
        
        # Get all predicate IDs used in edges
        used_predicates = set(edge['predicate'] for edge in edges if 'predicate' in edge)
        defined_predicates = set(predicates.keys())
        
        # Check for missing predicates
        missing = used_predicates - defined_predicates
        if missing:
            self.gates['predicates_valid'] = False
            for pred_id in missing:
                self._add_issue("MISSING_PREDICATE", "error", "/predicates", 
                              f"Predicate '{pred_id}' used in edges but not defined")
        else:
            self.gates['predicates_valid'] = True
        
        # Check for unused predicates
        unused = defined_predicates - used_predicates
        if unused:
            for pred_id in unused:
                self._add_issue("UNUSED_PREDICATE", "info", "/predicates", 
                              f"Predicate '{pred_id}' defined but not used")
        
        # Validate predicate structure
        for pred_id, pred_data in predicates.items():
            if not isinstance(pred_data, dict):
                self._add_issue("INVALID_PREDICATE_STRUCTURE", "error", f"/predicates/{pred_id}",
                              "Predicate must be an object")
                continue
            
            if 'ast' not in pred_data:
                self._add_issue("MISSING_PREDICATE_AST", "error", f"/predicates/{pred_id}",
                              "Predicate missing 'ast' field")
    
    def _validate_schema_compliance(self, survey_dag_data: Dict[str, Any]):
        """Validate against JSON schema if available."""
        
        if not self.schema:
            self._add_issue("NO_SCHEMA", "info", "/", "No JSON schema available for validation")
            return
        
        try:
            jsonschema.validate(survey_dag_data, self.schema)
            self._add_issue("SCHEMA_VALID", "info", "/", "Passes JSON schema validation")
        except jsonschema.ValidationError as e:
            self._add_issue("SCHEMA_VIOLATION", "error", e.json_path or "/", 
                          f"Schema validation failed: {e.message}")
        except Exception as e:
            self._add_issue("SCHEMA_ERROR", "warning", "/", 
                          f"Schema validation error: {e}")
    
    def _add_issue(self, code: str, severity: str, where: str, message: str):
        """Add validation issue."""
        self.issues.append({
            "code": code,
            "severity": severity,
            "where": where,
            "message": message
        })
    
    def _determine_final_status(self) -> str:
        """Determine final validation status."""
        error_count = sum(1 for issue in self.issues if issue['severity'] == 'error')
        warning_count = sum(1 for issue in self.issues if issue['severity'] == 'warning')
        
        if error_count > 0:
            return "FAIL"
        elif warning_count > 0:
            return "OK_WITH_WARNINGS"
        else:
            return "OK"
    
    def print_validation_summary(self, validation_result: Dict[str, Any]):
        """Print formatted validation summary."""
        print("\\n" + "="*60)
        print("📋 MATHEMATICAL VALIDATION SUMMARY")
        print("="*60)
        
        status = validation_result['status']
        if status == "OK":
            print("🎉 STATUS: PERFECT - All validation gates passed!")
        elif status == "OK_WITH_WARNINGS":
            print("⚠️  STATUS: OK WITH WARNINGS - Minor issues found")
        else:
            print("❌ STATUS: FAILED - Critical issues found")
        
        print(f"\\n🚪 VALIDATION GATES:")
        gates = validation_result['gates']
        for gate, passed in gates.items():
            status_icon = "✅" if passed else "❌"
            print(f"   {status_icon} {gate}: {'PASS' if passed else 'FAIL'}")
        
        print(f"\\n📊 ISSUES SUMMARY:")
        issues = validation_result['issues']
        error_count = sum(1 for i in issues if i['severity'] == 'error')
        warning_count = sum(1 for i in issues if i['severity'] == 'warning')
        info_count = sum(1 for i in issues if i['severity'] == 'info')
        
        print(f"   🔴 Errors: {error_count}")
        print(f"   🟡 Warnings: {warning_count}")
        print(f"   🔵 Info: {info_count}")
        
        if issues:
            print(f"\\n📝 DETAILED ISSUES:")
            for issue in issues[:10]:  # Show first 10 issues
                severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[issue['severity']]
                print(f"   {severity_icon} {issue['code']}: {issue['message']}")
            
            if len(issues) > 10:
                print(f"   ... and {len(issues) - 10} more issues")
        
        print("="*60)
