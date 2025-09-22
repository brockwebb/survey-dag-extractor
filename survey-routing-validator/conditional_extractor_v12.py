#!/usr/bin/env python3
"""
Enhanced Survey Routing Extractor v1.2
Focuses on detecting and extracting conditional routing patterns
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Condition:
    """Represents a single routing condition"""
    variable: str
    operator: str = "equals"
    value: str = ""
    
    def to_dict(self):
        return {
            "variable": self.variable,
            "operator": self.operator, 
            "value": self.value
        }

@dataclass 
class ConditionalEdge:
    """Represents a conditional routing edge"""
    id: str
    source: str
    target: str
    conditions: List[Condition] = field(default_factory=list)
    priority: int = 0
    kind: str = "branch"
    subkind: str = "conditional"
    confidence: float = 0.0
    condition_text: str = ""
    extraction_method: str = "automated"
    
    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "conditions": [c.to_dict() for c in self.conditions],
            "priority": self.priority,
            "kind": self.kind,
            "subkind": self.subkind,
            "metadata": {
                "confidence": self.confidence,
                "extraction_method": self.extraction_method,
                "condition_text": self.condition_text,
                "human_validated": False
            }
        }

class ConditionalRoutingExtractor:
    """Enhanced extractor for conditional routing patterns"""
    
    def __init__(self):
        self.conditional_patterns = [
            # Direct conditional references
            r"if\s+(?:you\s+)?(?:answered|answer|select(?:ed)?|chose)\s+(?:option\s+)?([0-9]+|[\"']([^\"']+)[\"'])\s+(?:to\s+)?(?:question\s+)?([A-Za-z0-9_]+)",
            r"if\s+([A-Za-z0-9_]+)\s*[=:]\s*([0-9]+|[\"']([^\"']+)[\"'])",
            
            # Skip logic patterns  
            r"skip\s+to\s+([A-Za-z0-9_]+)\s+if\s+(?:.*?)(?:answered|answer|select(?:ed)?)\s+([0-9]+|[\"']([^\"']+)[\"'])",
            r"go\s+to\s+([A-Za-z0-9_]+)\s+if\s+([A-Za-z0-9_]+)\s*[=:]\s*([0-9]+)",
            
            # Display logic patterns
            r"(?:show|display)\s+(?:this\s+)?(?:question\s+)?(?:only\s+)?if\s+([A-Za-z0-9_]+)\s*[=:]\s*([0-9]+)",
            r"only\s+(?:show|display|ask)\s+if\s+(?:previous\s+)?(?:answer|response)\s+(?:was\s+)?([0-9]+)",
            
            # Branch logic patterns
            r"depending\s+on\s+(?:your\s+)?(?:answer|response)\s+to\s+([A-Za-z0-9_]+)",
            r"based\s+on\s+(?:your\s+)?(?:answer|response)\s+(?:to\s+)?([A-Za-z0-9_]+)",
            
            # Multi-condition patterns
            r"if\s+([A-Za-z0-9_]+)\s*[=:]\s*([0-9]+)\s+and\s+([A-Za-z0-9_]+)\s*[=:]\s*([0-9]+)",
            r"when\s+([A-Za-z0-9_]+)\s+(?:is|equals?)\s+([0-9]+)\s+(?:and|&)\s+([A-Za-z0-9_]+)\s+(?:is|equals?)\s+([0-9]+)"
        ]
        
        self.simple_routing_patterns = [
            r"(?:go\s+to|continue\s+to|next\s+question\s+is|proceed\s+to)\s+([A-Za-z0-9_]+)",
            r"→\s*([A-Za-z0-9_]+)",
            r"then\s+([A-Za-z0-9_]+)",
            r"continue\s+with\s+([A-Za-z0-9_]+)"
        ]
        
        self.terminal_patterns = [
            r"(?:end\s+survey|terminate|thank\s+you|not\s+eligible|ineligible)",
            r"(?:close\s+browser|exit\s+survey|survey\s+(?:complete|finished))"
        ]
        
        self.edge_counter = 0
        
    def extract_routing_from_survey(self, survey_data: Dict) -> Dict:
        """Main extraction method - processes entire survey for conditional routing"""
        logger.info("🔍 Starting conditional routing extraction...")
        
        # Parse survey structure
        nodes = self._extract_nodes(survey_data)
        logger.info(f"📋 Extracted {len(nodes)} nodes")
        
        # Extract conditional edges
        edges = self._extract_conditional_edges(survey_data, nodes)
        logger.info(f"🔗 Extracted {len(edges)} conditional edges")
        
        # Build DAG structure
        dag = self._build_dag_v12(nodes, edges, survey_data)
        
        # Validate and analyze
        validation_results = self._validate_routing(dag)
        dag["survey_dag"]["validation"] = validation_results
        
        logger.info("✅ Conditional routing extraction complete")
        return dag
    
    def _extract_nodes(self, survey_data: Dict) -> List[Dict]:
        """Extract and enhance nodes with response options"""
        nodes = []
        
        # Extract from survey structure
        for block_name, block_data in survey_data.get("SurveyElements", {}).items():
            if isinstance(block_data, dict) and "Questions" in block_data:
                for q_id, q_data in block_data["Questions"].items():
                    node = self._process_question_node(q_id, q_data, block_name)
                    if node:
                        nodes.append(node)
        
        # Add terminal nodes
        nodes.extend(self._detect_terminal_nodes(survey_data))
        
        return nodes
    
    def _process_question_node(self, q_id: str, q_data: Dict, block_name: str) -> Optional[Dict]:
        """Process individual question into node format"""
        question_text = q_data.get("QuestionText", "")
        question_type = q_data.get("QuestionType", "unknown")
        
        # Determine node type
        if "instruction" in question_text.lower() or question_type == "DB":
            node_type = "instruction"
        else:
            node_type = "question"
        
        # Extract response options
        choices = q_data.get("Choices", {})
        response_options = []
        
        for choice_id, choice_data in choices.items():
            if isinstance(choice_data, dict):
                response_options.append({
                    "value": choice_id,
                    "label": choice_data.get("Display", f"Option {choice_id}")
                })
            else:
                response_options.append({
                    "value": choice_id, 
                    "label": str(choice_data)
                })
        
        # Build domain info
        domain = None
        if response_options:
            domain = {
                "kind": "single_choice" if len(response_options) <= 5 else "multiple_choice",
                "options": response_options
            }
        
        return {
            "id": q_id,
            "type": node_type,
            "text": question_text,
            "block": block_name,
            "variable": q_id,
            "domain": domain
        }
    
    def _detect_terminal_nodes(self, survey_data: Dict) -> List[Dict]:
        """Detect terminal/end nodes"""
        terminals = []
        
        # Look for common terminal patterns
        for block_name, block_data in survey_data.get("SurveyElements", {}).items():
            if isinstance(block_data, dict):
                block_text = str(block_data).lower()
                
                if any(pattern in block_text for pattern in ["end", "thank you", "complete", "ineligible"]):
                    terminal_id = f"TERMINAL_{block_name}".upper()
                    terminals.append({
                        "id": terminal_id,
                        "type": "terminal",
                        "text": f"Survey termination: {block_name}",
                        "block": block_name
                    })
        
        # Default terminals
        if not terminals:
            terminals = [
                {"id": "END", "type": "terminal", "text": "Survey complete", "block": "completion"},
                {"id": "TERMINATE", "type": "terminal", "text": "Survey terminated", "block": "termination"}
            ]
        
        return terminals
    
    def _extract_conditional_edges(self, survey_data: Dict, nodes: List[Dict]) -> List[Dict]:
        """Extract conditional routing edges using pattern matching"""
        edges = []
        
        # Create node lookup
        node_lookup = {node["id"]: node for node in nodes}
        
        # Process each node for outgoing routing
        for node in nodes:
            if node["type"] in ["question", "instruction"]:
                node_edges = self._extract_edges_from_node(node, survey_data, node_lookup)
                edges.extend(node_edges)
        
        # Process survey flow and skip logic
        flow_edges = self._extract_edges_from_flow(survey_data, node_lookup)
        edges.extend(flow_edges)
        
        return edges
    
    def _extract_edges_from_node(self, node: Dict, survey_data: Dict, node_lookup: Dict) -> List[Dict]:
        """Extract routing edges from individual node content"""
        edges = []
        node_id = node["id"]
        
        # Get all text content related to this node
        node_content = self._get_node_content(node_id, survey_data)
        
        # Look for conditional patterns
        for pattern in self.conditional_patterns:
            matches = re.finditer(pattern, node_content, re.IGNORECASE)
            for match in matches:
                edge = self._parse_conditional_match(match, node_id, node_lookup)
                if edge:
                    edges.append(edge.to_dict())
        
        # Look for simple routing if no conditionals found
        if not edges:
            for pattern in self.simple_routing_patterns:
                matches = re.finditer(pattern, node_content, re.IGNORECASE)
                for match in matches:
                    target = match.group(1)
                    if target in node_lookup:
                        edge = ConditionalEdge(
                            id=self._generate_edge_id(),
                            source=node_id,
                            target=target,
                            conditions=[],  # No conditions = always route
                            kind="sequence",
                            subkind="fallthrough",
                            confidence=0.8,
                            condition_text=f"Always route from {node_id} to {target}",
                            extraction_method="simple_pattern"
                        )
                        edges.append(edge.to_dict())
                        break
        
        # Generate response-based routing for questions with options
        if node.get("domain", {}).get("options") and not edges:
            edges.extend(self._generate_response_routing(node, node_lookup))
        
        return edges
    
    def _parse_conditional_match(self, match: re.Match, source_node: str, node_lookup: Dict) -> Optional[ConditionalEdge]:
        """Parse regex match into conditional edge"""
        groups = match.groups()
        
        # Different pattern types require different parsing
        if len(groups) >= 3:
            # Pattern: if VARIABLE = VALUE then TARGET
            variable = groups[2] if groups[2] else source_node  
            value = groups[0] or groups[1]
            target = self._find_target_in_text(match.group(0), node_lookup)
            
            if target:
                condition = Condition(variable=variable, value=value)
                return ConditionalEdge(
                    id=self._generate_edge_id(),
                    source=source_node,
                    target=target,
                    conditions=[condition],
                    confidence=0.85,
                    condition_text=match.group(0),
                    extraction_method="conditional_pattern"
                )
        
        return None
    
    def _find_target_in_text(self, text: str, node_lookup: Dict) -> Optional[str]:
        """Find target node ID mentioned in routing text"""
        text_upper = text.upper()
        
        # Look for node IDs in the text
        for node_id in node_lookup.keys():
            if node_id.upper() in text_upper:
                return node_id
        
        # Look for common keywords that map to terminals
        if any(term in text.lower() for term in ["end", "terminate", "ineligible"]):
            return "TERMINATE"
        
        return None
    
    def _generate_response_routing(self, node: Dict, node_lookup: Dict) -> List[Dict]:
        """Generate default routing based on response options"""
        edges = []
        options = node.get("domain", {}).get("options", [])
        
        if not options:
            return edges
        
        # For each response option, create a conditional edge
        for option in options:
            response_value = str(option["value"])
            
            # Try to infer target based on response text
            response_text = option["label"].lower()
            
            if "no" in response_text or "ineligible" in response_text:
                target = "TERMINATE"
            elif "end" in response_text or "exit" in response_text:
                target = "END"
            else:
                # Default: find next logical node (simplified)
                target = self._find_next_sequential_node(node["id"], node_lookup)
            
            if target:
                condition = Condition(variable=node["id"], value=response_value)
                edge = ConditionalEdge(
                    id=self._generate_edge_id(),
                    source=node["id"], 
                    target=target,
                    conditions=[condition],
                    confidence=0.7,  # Lower confidence for inferred routing
                    condition_text=f"If {node['id']} = {response_value} ({option['label']})",
                    extraction_method="inferred_from_responses"
                )
                edges.append(edge.to_dict())
        
        return edges
    
    def _find_next_sequential_node(self, current_node: str, node_lookup: Dict) -> Optional[str]:
        """Find the next node in sequence (simplified heuristic)"""
        # This is a simplified approach - in reality, you'd analyze survey flow
        node_ids = list(node_lookup.keys())
        try:
            current_idx = node_ids.index(current_node)
            if current_idx < len(node_ids) - 1:
                next_node = node_ids[current_idx + 1]
                if node_lookup[next_node]["type"] != "terminal":
                    return next_node
        except (ValueError, IndexError):
            pass
        
        return "END"  # Default fallback
    
    def _get_node_content(self, node_id: str, survey_data: Dict) -> str:
        """Get all text content related to a node"""
        content_parts = []
        
        # Search through survey structure
        for block_data in survey_data.get("SurveyElements", {}).values():
            if isinstance(block_data, dict):
                # Question text
                questions = block_data.get("Questions", {})
                if node_id in questions:
                    q_data = questions[node_id]
                    content_parts.append(q_data.get("QuestionText", ""))
                    
                    # Choice text
                    for choice_data in q_data.get("Choices", {}).values():
                        if isinstance(choice_data, dict):
                            content_parts.append(choice_data.get("Display", ""))
                        else:
                            content_parts.append(str(choice_data))
                
                # Flow and skip logic
                flow = block_data.get("Flow", [])
                for flow_item in flow:
                    if isinstance(flow_item, dict) and node_id in str(flow_item):
                        content_parts.append(str(flow_item))
        
        return " ".join(content_parts)
    
    def _extract_edges_from_flow(self, survey_data: Dict, node_lookup: Dict) -> List[Dict]:
        """Extract edges from Qualtrics flow logic"""
        edges = []
        
        # Process flow elements (Qualtrics-specific)
        for block_data in survey_data.get("SurveyElements", {}).values():
            if isinstance(block_data, dict) and "Flow" in block_data:
                flow_edges = self._parse_flow_logic(block_data["Flow"], node_lookup)
                edges.extend(flow_edges)
        
        return edges
    
    def _parse_flow_logic(self, flow_data: List, node_lookup: Dict) -> List[Dict]:
        """Parse Qualtrics flow logic into conditional edges"""
        edges = []
        
        for flow_item in flow_data:
            if isinstance(flow_item, dict):
                # Branch logic
                if "Type" in flow_item and flow_item["Type"] == "Branch":
                    branch_edges = self._parse_branch_logic(flow_item, node_lookup)
                    edges.extend(branch_edges)
                
                # Skip logic  
                elif "SkipTo" in flow_item:
                    skip_edges = self._parse_skip_logic(flow_item, node_lookup)
                    edges.extend(skip_edges)
        
        return edges
    
    def _parse_branch_logic(self, branch_item: Dict, node_lookup: Dict) -> List[Dict]:
        """Parse branch logic into conditional edges"""
        edges = []
        
        # This would be specific to Qualtrics format
        # Simplified implementation for now
        if "Condition" in branch_item and "Target" in branch_item:
            # Parse condition and create edge
            pass
        
        return edges
    
    def _parse_skip_logic(self, skip_item: Dict, node_lookup: Dict) -> List[Dict]:
        """Parse skip logic into conditional edges"""
        edges = []
        
        # Simplified skip logic parsing
        if "SkipTo" in skip_item and "Condition" in skip_item:
            # Parse and create conditional edge
            pass
        
        return edges
    
    def _build_dag_v12(self, nodes: List[Dict], edges: List[Dict], survey_data: Dict) -> Dict:
        """Build complete DAG in v1.2 format"""
        
        # Find start and terminal nodes
        start_node = nodes[0]["id"] if nodes else None
        terminal_nodes = [n["id"] for n in nodes if n["type"] == "terminal"]
        
        # Build predicates from edge conditions
        predicates = self._build_predicates(edges)
        
        # Metadata
        metadata = {
            "id": f"survey_dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": survey_data.get("SurveyEntry", {}).get("SurveyName", "Extracted Survey"),
            "version": "1.0",
            "schema_version": "1.2",
            "objective": "edge",
            "build": {
                "extractor_version": "conditional_v1.2",
                "extracted_at": datetime.now().isoformat(),
                "method": "automated",
                "source_format": "qualtrics_qsf",
                "validation_passed": False,
                "post_edit": False,
                "conditional_patterns_detected": len([e for e in edges if e.get("metadata", {}).get("extraction_method") == "conditional_pattern"])
            }
        }
        
        return {
            "survey_dag": {
                "metadata": metadata,
                "graph": {
                    "start": start_node,
                    "terminals": terminal_nodes,
                    "nodes": nodes,
                    "edges": edges
                },
                "predicates": predicates,
                "validation": {}  # Will be filled by validation
            }
        }
    
    def _build_predicates(self, edges: List[Dict]) -> Dict:
        """Build predicate definitions from edge conditions"""
        predicates = {}
        
        for edge in edges:
            conditions = edge.get("conditions", [])
            if conditions:
                predicate_id = f"P_{edge['source']}_{edge['target']}".upper()
                
                predicates[predicate_id] = {
                    "id": predicate_id,
                    "conditions": conditions,
                    "logic_operator": "AND",
                    "complexity": "moderate" if len(conditions) > 1 else "simple",
                    "text": edge.get("metadata", {}).get("condition_text", ""),
                    "depends_on": list(set(c["variable"] for c in conditions)),
                    "human_validated": False
                }
        
        return predicates
    
    def _validate_routing(self, dag: Dict) -> Dict:
        """Validate routing completeness and detect issues"""
        nodes = dag["survey_dag"]["graph"]["nodes"]
        edges = dag["survey_dag"]["graph"]["edges"]
        
        # Build adjacency map
        outgoing = {}
        incoming = {}
        
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            if source not in outgoing:
                outgoing[source] = []
            outgoing[source].append(edge)
            
            if target not in incoming:
                incoming[target] = []
            incoming[target].append(edge)
        
        # Find dead ends and unreachable nodes
        dead_ends = []
        unreachable_nodes = []
        
        for node in nodes:
            node_id = node["id"]
            
            # Dead end: no outgoing edges (except terminals)
            if node["type"] != "terminal" and node_id not in outgoing:
                dead_ends.append(node_id)
            
            # Unreachable: no incoming edges (except start)
            if node_id != dag["survey_dag"]["graph"]["start"] and node_id not in incoming:
                unreachable_nodes.append(node_id)
        
        # Calculate completeness
        nodes_with_routing = len([n for n in nodes if n["id"] in outgoing or n["type"] == "terminal"])
        routing_completeness = nodes_with_routing / len(nodes) if nodes else 0
        
        # Estimate conditional accuracy (based on extraction confidence)
        confidences = [e.get("metadata", {}).get("confidence", 0) for e in edges]
        conditional_accuracy = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "status": "EXTRACTED",
            "routing_completeness": routing_completeness,
            "conditional_accuracy": conditional_accuracy,
            "dead_ends": dead_ends,
            "unreachable_nodes": unreachable_nodes,
            "validation_notes": {}
        }
    
    def _generate_edge_id(self) -> str:
        """Generate unique edge ID"""
        self.edge_counter += 1
        return f"E_{self.edge_counter:06d}"

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Extract conditional routing from survey files")
    parser.add_argument("input_file", help="Input survey file (QSF or JSON)")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1
    
    logger.info(f"🔍 Loading survey from {input_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load survey file: {e}")
        return 1
    
    # Extract routing
    extractor = ConditionalRoutingExtractor()
    dag = extractor.extract_routing_from_survey(survey_data)
    
    # Save output
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_conditional_routing.json"
    
    logger.info(f"💾 Saving DAG to {output_path}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dag, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ Conditional routing extraction complete!")
        
        # Print summary
        stats = dag["survey_dag"]["validation"]
        metadata = dag["survey_dag"]["build"]
        
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   Nodes: {len(dag['survey_dag']['graph']['nodes'])}")
        print(f"   Edges: {len(dag['survey_dag']['graph']['edges'])}")
        print(f"   Conditional Patterns: {metadata['conditional_patterns_detected']}")
        print(f"   Routing Completeness: {stats['routing_completeness']:.1%}")
        print(f"   Dead Ends: {len(stats['dead_ends'])}")
        print(f"   Unreachable: {len(stats['unreachable_nodes'])}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
