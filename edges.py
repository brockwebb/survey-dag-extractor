"""
Edge Extraction Module using LangExtract
Extracts routing logic and flow between nodes
"""

import langextract as lx
import textwrap
from pathlib import Path
from typing import List, Dict, Any
import hashlib
import PyPDF2

from .config import ExtractorConfig


class EdgeExtractor:
    """
    Extracts edges (routing logic) using LangExtract.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
        
    def extract(self, pdf_path: Path, nodes: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract routing logic between nodes.
        
        Args:
            pdf_path: Path to survey PDF
            nodes: List of extracted nodes
            
        Returns:
            List of edges matching schema format
        """
        # Extract text from PDF
        survey_text = self._extract_pdf_text(pdf_path)
        
        # Create node reference for context
        node_context = self._create_node_context(nodes)
        
        # Use primary model for routing logic
        model_id = self.config.get_model_id(use_secondary=False)
        
        # Define extraction prompt with node context
        prompt = textwrap.dedent(f"""
        Extract ALL routing logic and flow patterns from this survey.
        
        Survey contains these elements:
        {node_context}
        
        For each routing rule, extract:
        1. Source node (where flow comes FROM)
        2. Target node (where flow goes TO)
        3. Condition that triggers this route (EXACT text)
        4. Type of flow (continue, skip, branch, terminate)
        5. Priority (which condition is checked first)
        
        Include:
        - Default flow (Q1 → Q2 with no condition)
        - Conditional skips (If Q1==1, skip to Q5)
        - Terminal conditions (If ineligible, END_SURVEY)
        - Block transitions (Complete section A → Start section B)
        - Universe conditions that skip questions
        
        CRITICAL: Find long-distance skips across sections!
        """)
        
        # Define examples
        examples = self._create_edge_examples()
        
        # Extract using LangExtract
        result = lx.extract(
            text_or_documents=survey_text,
            prompt_description=prompt,
            examples=examples,
            model_id=model_id,
            max_char_buffer=self.config.max_char_buffer,
            max_workers=self.config.max_workers
        )
        
        # Convert to edges
        edges = []
        seen_edges = set()
        
        for doc in result.documents:
            for extraction in doc.extractions:
                if extraction.extraction_class == "routing":
                    edge = self._create_edge(extraction, nodes, seen_edges)
                    if edge:
                        edges.append(edge)
        
        # Ensure all nodes have outgoing edges
        edges = self._ensure_complete_flow(edges, nodes)
        
        if self.config.debug:
            print(f"   Debug: Extracted {len(edges)} unique edges")
            edge_types = {}
            for e in edges:
                t = e.get('subkind', 'unknown')
                edge_types[t] = edge_types.get(t, 0) + 1
            print(f"   Debug: Edge types: {edge_types}")
        
        return edges
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF."""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                text += f"\n\n--- Page {page_num + 1} ---\n\n"
                text += page.extract_text()
        return text
    
    def _create_node_context(self, nodes: List[Dict]) -> str:
        """Create readable node reference."""
        lines = []
        for i, node in enumerate(nodes):
            if i < 30:  # Limit for context
                text = node['metadata'].get('text', '')[:50]
                lines.append(f"{node['id']}: {text}...")
            elif i == 30:
                lines.append(f"... and {len(nodes) - 30} more nodes")
                break
        return "\n".join(lines)
    
    def _create_edge_examples(self) -> List[lx.data.ExampleData]:
        """Create examples for edge extraction."""
        return [
            lx.data.ExampleData(
                text="If Q1 == 1 (Yes) → Skip to ADDRESS_CONFIRM",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="routing",
                        extraction_text="Q1 → ADDRESS_CONFIRM",
                        attributes={
                            "source": "Q1",
                            "target": "ADDRESS_CONFIRM",
                            "condition": "Q1 == 1",
                            "condition_meaning": "If answer is Yes",
                            "flow_type": "skip",
                            "priority": 0
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="After FD1, continue to FD2",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="routing",
                        extraction_text="FD1 → FD2",
                        attributes={
                            "source": "FD1",
                            "target": "FD2",
                            "condition": "TRUE",
                            "condition_meaning": "Always continue",
                            "flow_type": "continue",
                            "priority": 0
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="If GET_NAME == 2 (End survey) → END_INELIGIBLE",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="routing",
                        extraction_text="GET_NAME → END_INELIGIBLE",
                        attributes={
                            "source": "GET_NAME",
                            "target": "END_INELIGIBLE",
                            "condition": "GET_NAME == 2",
                            "condition_meaning": "If choose to end survey",
                            "flow_type": "terminate",
                            "priority": 1
                        }
                    )
                ]
            )
        ]
    
    def _create_edge(self, extraction: lx.data.Extraction, nodes: List[Dict], seen: set) -> Dict[str, Any]:
        """Convert extraction to schema-compliant edge."""
        attrs = extraction.attributes
        
        # Get source and target
        source = attrs.get('source', '').strip()
        target = attrs.get('target', '').strip()
        condition = attrs.get('condition', 'TRUE')
        
        # Validate nodes exist
        node_ids = {n['id'] for n in nodes}
        if source not in node_ids or target not in node_ids:
            if self.config.debug:
                print(f"   Debug: Skipping edge {source} → {target} (invalid nodes)")
            return None
        
        # Deduplicate
        edge_key = (source, target, condition)
        if edge_key in seen:
            return None
        seen.add(edge_key)
        
        # Determine kind and subkind
        flow_type = attrs.get('flow_type', 'continue').lower()
        kind, subkind = self._determine_edge_types(flow_type, source, target, nodes)
        
        # Generate edge ID
        edge_id = f"E_{hashlib.md5(f'{source}_{target}_{condition}'.encode()).hexdigest()[:10].upper()}"
        
        return {
            "id": edge_id,
            "source": source,
            "target": target,
            "predicate": None,  # Will be filled by predicate generator
            "kind": kind,
            "priority": attrs.get('priority', 0 if kind == 'fallthrough' else 1),
            "subkind": subkind,
            "metadata": {
                "condition_text": condition,
                "condition_meaning": attrs.get('condition_meaning', '')
            },
            "provenance": {
                "source_id": "survey.pdf",
                "locators": [
                    {"type": "char_offset", "value": f"{extraction.char_start}-{extraction.char_end}"}
                ] if hasattr(extraction, 'char_start') else [],
                "confidence": 0.9,
                "method": "llm_extraction",
                "human_verified": False
            },
            "_condition": condition,  # For predicate generation
            "_condition_meaning": attrs.get('condition_meaning', '')
        }
    
    def _determine_edge_types(self, flow_type: str, source: str, target: str, nodes: List[Dict]) -> tuple:
        """Determine kind and subkind for edge."""
        
        # Get node info
        source_node = next((n for n in nodes if n['id'] == source), {})
        target_node = next((n for n in nodes if n['id'] == target), {})
        
        # Check if terminal
        if target_node.get('type') == 'terminal' or target.startswith('END_'):
            return ('terminate', 'terminal_exit')
        
        # Check flow type
        if flow_type in ['continue', 'default', 'next']:
            kind = 'fallthrough'
            subkind = 'sequence'
        elif flow_type in ['skip', 'jump', 'branch']:
            kind = 'branch'
            # Check if crossing blocks
            if source_node.get('block') != target_node.get('block'):
                subkind = 'block_trans'
            else:
                subkind = 'skip'
        elif flow_type == 'terminate':
            kind = 'terminate'
            subkind = 'terminal_exit'
        else:
            # Default
            kind = 'branch'
            subkind = 'skip'
        
        return (kind, subkind)
    
    def _ensure_complete_flow(self, edges: List[Dict], nodes: List[Dict]) -> List[Dict]:
        """Ensure all non-terminal nodes have at least one outgoing edge."""
        
        # Find nodes without outgoing edges
        nodes_with_outgoing = {e['source'] for e in edges}
        terminal_ids = {n['id'] for n in nodes if n['type'] == 'terminal'}
        
        orphaned = []
        for node in nodes:
            if node['id'] not in nodes_with_outgoing and node['id'] not in terminal_ids:
                orphaned.append(node)
        
        if not orphaned:
            return edges
        
        if self.config.debug:
            print(f"   Debug: Found {len(orphaned)} orphaned nodes, adding default edges")
        
        # Use secondary model for simple task
        if len(orphaned) > 5:
            # Too many orphans, add simple sequential flow
            for i, node in enumerate(orphaned):
                # Find next node by order
                next_node = None
                for n in nodes:
                    if n['order_index'] == node['order_index'] + 1:
                        next_node = n
                        break
                
                if next_node:
                    edge = {
                        "id": f"E_AUTO_{hashlib.md5(f'{node['id']}_{next_node['id']}'.encode()).hexdigest()[:8].upper()}",
                        "source": node['id'],
                        "target": next_node['id'],
                        "predicate": None,  # Will be P_TRUE
                        "kind": "fallthrough",
                        "priority": 0,
                        "subkind": "sequence",
                        "metadata": {
                            "condition_text": "always",
                            "condition_meaning": "Auto-generated sequential flow"
                        },
                        "provenance": {
                            "source_id": "auto-generated",
                            "locators": [],
                            "confidence": 0.7,
                            "method": "inference",
                            "human_verified": False
                        },
                        "_condition": "TRUE",
                        "_auto_generated": True
                    }
                    edges.append(edge)
        else:
            # Few orphans, use LLM to understand flow
            edges = self._infer_missing_edges(edges, nodes, orphaned)
        
        return edges
    
    def _infer_missing_edges(self, edges: List[Dict], nodes: List[Dict], orphaned: List[Dict]) -> List[Dict]:
        """Use LLM to infer missing edges."""
        
        # Use secondary model for this simpler task
        model_id = self.config.get_model_id(use_secondary=True)
        
        orphan_context = "\n".join([f"{n['id']}: {n['metadata']['text'][:50]}..." for n in orphaned])
        
        prompt = f"""
        These survey nodes have no clear outgoing flow:
        {orphan_context}
        
        Based on survey structure, what should happen after each?
        Consider normal survey flow (usually continues to next question).
        """
        
        examples = [
            lx.data.ExampleData(
                text="Q5: What is your age?\nQ6: What is your occupation?",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="inferred_flow",
                        extraction_text="Q5 → Q6",
                        attributes={
                            "source": "Q5",
                            "likely_target": "Q6",
                            "reasoning": "Sequential questions"
                        }
                    )
                ]
            )
        ]
        
        result = lx.extract(
            text_or_documents=prompt,
            prompt_description="Infer likely flow for orphaned nodes",
            examples=examples,
            model_id=model_id
        )
        
        for doc in result.documents:
            for extraction in doc.extractions:
                if extraction.extraction_class == "inferred_flow":
                    attrs = extraction.attributes
                    source = attrs.get('source')
                    target = attrs.get('likely_target')
                    
                    if source and target:
                        edge = {
                            "id": f"E_INFER_{hashlib.md5(f'{source}_{target}'.encode()).hexdigest()[:8].upper()}",
                            "source": source,
                            "target": target,
                            "predicate": None,
                            "kind": "fallthrough",
                            "priority": 0,
                            "subkind": "sequence",
                            "metadata": {
                                "condition_text": "always",
                                "condition_meaning": attrs.get('reasoning', 'Inferred flow')
                            },
                            "provenance": {
                                "source_id": "llm-inferred",
                                "locators": [],
                                "confidence": 0.8,
                                "method": "inference",
                                "human_verified": False
                            },
                            "_condition": "TRUE",
                            "_inferred": True
                        }
                        edges.append(edge)
        
        return edges
