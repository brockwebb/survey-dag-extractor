"""
Predicate Generation Module using LangExtract
Generates semantic predicates with AST representation
"""

import langextract as lx
import textwrap
from typing import List, Dict, Any
import hashlib
import json
import re

from .config import ExtractorConfig


class PredicateGenerator:
    """
    Generates predicates from conditions using LangExtract.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.predicates = {}
        
    def generate(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """
        Generate predicates for all conditions.
        
        Args:
            nodes: List of nodes (for universe conditions)
            edges: List of edges (for routing conditions)
            
        Returns:
            Dict of predicates matching schema format
        """
        # Always include P_TRUE
        self.predicates['P_TRUE'] = {
            "ast": ["TRUE"],
            "text": "Always true",
            "complexity": "trivial"
        }
        
        # Collect all conditions
        conditions = self._collect_conditions(nodes, edges)
        
        if self.config.debug:
            print(f"   Debug: Found {len(conditions)} unique conditions to process")
        
        # Use secondary model for simpler AST generation
        model_id = self.config.get_model_id(use_secondary=True)
        
        # Process conditions in batches
        for condition_text, context in conditions.items():
            if condition_text.lower() in ['true', 'always', '']:
                continue
            
            # Generate predicate
            predicate = self._generate_predicate(condition_text, context, model_id)
            if predicate:
                self.predicates[predicate['id']] = predicate
        
        # Update edges with predicate references
        self._update_edge_predicates(edges)
        
        # Update universe predicates
        self._update_universe_predicates(nodes)
        
        return self.predicates
    
    def _collect_conditions(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Dict]:
        """Collect all unique conditions."""
        conditions = {}
        
        # From edges
        for edge in edges:
            condition = edge.get('_condition', '')
            if condition and condition not in conditions:
                conditions[condition] = {
                    'usage': 'edge',
                    'source': edge['source'],
                    'target': edge['target'],
                    'meaning': edge.get('_condition_meaning', '')
                }
        
        # From universe conditions
        for node in nodes:
            universe = node.get('universe', {})
            expr = universe.get('expression', '')
            if expr and expr != 'always_show' and expr not in conditions:
                conditions[expr] = {
                    'usage': 'universe',
                    'node': node['id'],
                    'meaning': universe.get('natural_language', '')
                }
        
        return conditions
    
    def _generate_predicate(self, condition_text: str, context: Dict, model_id: str) -> Dict[str, Any]:
        """Generate a single predicate using LangExtract."""
        
        # First try simple parsing
        ast = self._simple_parse_to_ast(condition_text)
        
        # If simple parsing fails, use LLM
        if ast == ["TRUE"] and condition_text.upper() != "TRUE":
            ast = self._llm_parse_to_ast(condition_text, context, model_id)
        
        # Generate semantic ID
        pred_id = self._create_semantic_id(condition_text, ast)
        
        # Determine complexity
        complexity = self._determine_complexity(ast)
        
        # Extract dependencies
        depends_on = self._extract_dependencies(ast)
        
        return {
            "id": pred_id,
            "ast": ast,
            "text": condition_text,
            "depends_on": depends_on,
            "complexity": complexity,
            "semantic_meaning": context.get('meaning', '')
        }
    
    def _simple_parse_to_ast(self, condition: str) -> List:
        """Simple regex-based parsing for common patterns."""
        
        if not condition or condition.upper() in ['TRUE', 'ALWAYS']:
            return ["TRUE"]
        
        # Handle OR conditions
        if ' OR ' in condition.upper():
            parts = condition.split(' OR ')
            sub_asts = [self._simple_parse_to_ast(p.strip()) for p in parts]
            return ["OR"] + sub_asts
        
        # Handle AND conditions
        if ' AND ' in condition.upper():
            parts = condition.split(' AND ')
            sub_asts = [self._simple_parse_to_ast(p.strip()) for p in parts]
            return ["AND"] + sub_asts
        
        # Parse simple comparisons
        patterns = [
            (r'(\w+)\s*==\s*([0-9]+)', '=='),
            (r'(\w+)\s*!=\s*([0-9]+)', '!='),
            (r'(\w+)\s*>=\s*([0-9]+)', '>='),
            (r'(\w+)\s*<=\s*([0-9]+)', '<='),
            (r'(\w+)\s*>\s*([0-9]+)', '>'),
            (r'(\w+)\s*<\s*([0-9]+)', '<'),
        ]
        
        for pattern, op in patterns:
            match = re.match(pattern, condition.strip())
            if match:
                var, val = match.groups()
                return [op, var, int(val)]
        
        # Handle IN conditions
        match = re.match(r'(\w+)\s+IN\s+\[([^\]]+)\]', condition, re.IGNORECASE)
        if match:
            var, values_str = match.groups()
            values = [int(v.strip()) for v in values_str.split(',') if v.strip().isdigit()]
            return ["IN", var, values]
        
        return ["TRUE"]  # Fallback
    
    def _llm_parse_to_ast(self, condition: str, context: Dict, model_id: str) -> List:
        """Use LLM to parse complex conditions."""
        
        prompt = textwrap.dedent(f"""
        Convert this survey condition to AST (Abstract Syntax Tree) format.
        
        Condition: "{condition}"
        Context: {context.get('meaning', 'routing condition')}
        
        Convert to nested list format:
        - "Q1 == 1" → ["==", "Q1", 1]
        - "Q2 > 5" → [">", "Q2", 5]
        - "Q3 IN [1,2,3]" → ["IN", "Q3", [1,2,3]]
        - "Q4 == 1 OR Q4 == 2" → ["OR", ["==", "Q4", 1], ["==", "Q4", 2]]
        
        Return ONLY the AST as a JSON list.
        """)
        
        examples = [
            lx.data.ExampleData(
                text="D11 > 0",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="ast",
                        extraction_text='[">", "D11", 0]',
                        attributes={"ast": [">", "D11", 0]}
                    )
                ]
            )
        ]
        
        result = lx.extract(
            text_or_documents=prompt,
            prompt_description="Parse condition to AST",
            examples=examples,
            model_id=model_id
        )
        
        # Extract AST from result
        for doc in result.documents:
            for extraction in doc.extractions:
                if extraction.extraction_class == "ast":
                    ast = extraction.attributes.get('ast')
                    if ast:
                        return ast
        
        # Fallback
        return ["TRUE"]
    
    def _create_semantic_id(self, condition: str, ast: List) -> str:
        """Create meaningful predicate ID."""
        
        if ast == ["TRUE"]:
            return "P_TRUE"
        
        # Extract main variable and operation
        if len(ast) >= 3 and ast[0] in ["==", "!=", ">", ">=", "<", "<="]:
            var = str(ast[1]).upper()
            op = ast[0]
            val = ast[2]
            
            op_map = {
                "==": "EQ",
                "!=": "NEQ",
                ">": "GT",
                ">=": "GTE",
                "<": "LT",
                "<=": "LTE"
            }
            
            op_str = op_map.get(op, "CHECK")
            
            if isinstance(val, (int, float)):
                return f"P_{var}_{op_str}_{val}"
            else:
                val_hash = hashlib.md5(str(val).encode()).hexdigest()[:4].upper()
                return f"P_{var}_{op_str}_{val_hash}"
        
        # Handle IN
        if ast[0] == "IN" and len(ast) >= 3:
            var = str(ast[1]).upper()
            values = ast[2]
            if isinstance(values, list) and values:
                values_str = "_".join(str(v) for v in values[:2])
                return f"P_{var}_IN_{values_str}"
        
        # Handle AND/OR
        if ast[0] in ["AND", "OR"]:
            # Extract variables
            vars_found = set()
            
            def extract_vars(node):
                if isinstance(node, list) and len(node) > 1:
                    if node[0] in ["==", "!=", ">", ">=", "<", "<=", "IN"]:
                        if isinstance(node[1], str):
                            vars_found.add(node[1])
                    for item in node[1:]:
                        extract_vars(item)
            
            extract_vars(ast)
            
            if vars_found:
                vars_str = "_".join(sorted(vars_found)[:2])
                return f"P_{vars_str}_{ast[0]}"
        
        # Fallback to hash
        cond_hash = hashlib.md5(condition.encode()).hexdigest()[:8].upper()
        return f"P_{cond_hash}"
    
    def _determine_complexity(self, ast: List) -> str:
        """Determine predicate complexity."""
        
        if ast == ["TRUE"] or ast == ["FALSE"]:
            return "trivial"
        
        # Count operators
        op_count = 0
        
        def count_ops(node):
            nonlocal op_count
            if isinstance(node, list) and node:
                if node[0] in ["AND", "OR", "NOT", "==", "!=", ">", ">=", "<", "<=", "IN"]:
                    op_count += 1
                for item in node[1:]:
                    count_ops(item)
        
        count_ops(ast)
        
        if op_count <= 1:
            return "simple"
        elif op_count <= 3:
            return "moderate"
        else:
            return "complex"
    
    def _extract_dependencies(self, ast: List) -> List[str]:
        """Extract variable dependencies from AST."""
        deps = set()
        
        def extract(node):
            if isinstance(node, list) and len(node) > 1:
                if node[0] in ["==", "!=", ">", ">=", "<", "<=", "IN"]:
                    if isinstance(node[1], str):
                        deps.add(node[1])
                for item in node[1:]:
                    extract(item)
        
        extract(ast)
        return sorted(list(deps))
    
    def _update_edge_predicates(self, edges: List[Dict]):
        """Update edges with predicate references."""
        
        for edge in edges:
            condition = edge.get('_condition', 'TRUE')
            
            # Find matching predicate
            pred_id = None
            for pid, pred in self.predicates.items():
                if pred['text'] == condition:
                    pred_id = pid
                    break
            
            # If not found, it should be P_TRUE
            if not pred_id:
                if condition.upper() in ['TRUE', 'ALWAYS', '']:
                    pred_id = 'P_TRUE'
                else:
                    # This shouldn't happen, but handle it
                    if self.config.debug:
                        print(f"   Debug: No predicate found for condition: {condition}")
                    pred_id = 'P_TRUE'
            
            edge['predicate'] = pred_id
    
    def _update_universe_predicates(self, nodes: List[Dict]):
        """Update universe conditions with predicate references."""
        
        for node in nodes:
            universe = node.get('universe', {})
            expr = universe.get('expression', '')
            
            if expr and expr != 'always_show':
                # Find matching predicate
                pred_id = None
                for pid, pred in self.predicates.items():
                    if pred['text'] == expr:
                        pred_id = pid
                        break
                
                if pred_id:
                    universe['predicate'] = pred_id
