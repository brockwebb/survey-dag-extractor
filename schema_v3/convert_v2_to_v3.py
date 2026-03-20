#!/usr/bin/env python3
"""
Convert Survey JSON from v2 (string expressions) to v3 (AST edges).

Usage:
    python convert_v2_to_v3.py input.json output.json
"""

import json
import re
import sys
from typing import Any, Optional


def parse_expression_to_ast(expr: str) -> Optional[list]:
    """
    Parse a string expression into an AST array.
    
    Examples:
        "always_show" -> None
        "D11 > 0" -> [">", "D11", 0]
        "EMP1 == 2" -> ["=", "EMP1", 2]
        "D11 > 0 AND EMP1 = 2" -> ["AND", [">", "D11", 0], ["=", "EMP1", 2]]
        "D12 includes 1" -> ["IN", "D12", 1]
    """
    if not expr:
        return None
    
    expr = expr.strip()
    
    # Handle special cases
    if expr.lower() in ('always_show', 'all respondents', 'always', 'entry point question'):
        return None
    
    # Handle AND/OR at top level (simple split - doesn't handle nested parens fully)
    # Check for AND first (higher precedence issues, but simple surveys usually don't nest deeply)
    if ' AND ' in expr.upper():
        parts = re.split(r'\s+AND\s+', expr, flags=re.IGNORECASE)
        if len(parts) == 2:
            left = parse_expression_to_ast(parts[0].strip('() '))
            right = parse_expression_to_ast(parts[1].strip('() '))
            if left and right:
                return ["AND", left, right]
    
    if ' OR ' in expr.upper():
        parts = re.split(r'\s+OR\s+', expr, flags=re.IGNORECASE)
        if len(parts) == 2:
            left = parse_expression_to_ast(parts[0].strip('() '))
            right = parse_expression_to_ast(parts[1].strip('() '))
            if left and right:
                return ["OR", left, right]
    
    # Handle "not includes" for multi-select (check before "includes")
    not_includes_match = re.match(r'(\w+)\s+not\s+includes\s+(\d+)', expr, re.IGNORECASE)
    if not_includes_match:
        var = not_includes_match.group(1)
        val = int(not_includes_match.group(2))
        return ["NOT_IN", var, val]
    
    # Handle "includes" for multi-select
    includes_match = re.match(r'(\w+)\s+includes\s+(\d+)', expr, re.IGNORECASE)
    if includes_match:
        var = includes_match.group(1)
        val = int(includes_match.group(2))
        return ["IN", var, val]
    
    # Handle comparison operators
    # Order matters: check == before =, >= before >, <= before <
    patterns = [
        (r'(\w+)\s*==\s*(\d+)', '='),
        (r'(\w+)\s*!=\s*(\d+)', '!='),
        (r'(\w+)\s*>=\s*(\d+)', '>='),
        (r'(\w+)\s*<=\s*(\d+)', '<='),
        (r'(\w+)\s*>\s*(\d+)', '>'),
        (r'(\w+)\s*<\s*(\d+)', '<'),
        (r'(\w+)\s*=\s*(\d+)', '='),  # Single = also means equality
    ]
    
    for pattern, op in patterns:
        match = re.match(pattern, expr)
        if match:
            var = match.group(1)
            val = int(match.group(2))
            return [op, var, val]
    
    # If we can't parse, return a placeholder that flags for manual review
    print(f"WARNING: Could not parse expression: '{expr}'", file=sys.stderr)
    return ["UNPARSED", expr]


def get_question_order(survey: dict) -> list[str]:
    """
    Get ordered list of question IDs based on block order.
    """
    blocks = survey.get('blocks', {})
    questions = survey.get('questions', {})
    
    # Sort blocks by order
    sorted_blocks = sorted(blocks.items(), key=lambda x: x[1].get('order', 999))
    
    ordered_ids = []
    for block_id, block in sorted_blocks:
        for qid in block.get('questions', []):
            if qid in questions:
                ordered_ids.append(qid)
    
    # Add any questions not in blocks
    for qid in questions:
        if qid not in ordered_ids:
            ordered_ids.append(qid)
    
    return ordered_ids


def generate_edges(survey: dict) -> list[dict]:
    """
    Generate DAG edges from questions with universe conditions.
    """
    questions = survey.get('questions', {})
    ordered_ids = get_question_order(survey)
    
    edges = []
    edge_counter = 1
    
    # Build a map of question -> dependencies
    # and question -> universe expression
    universes = {}
    for qid, q in questions.items():
        universe = q.get('universe', {})
        expr = universe.get('expression', 'always_show')
        deps = universe.get('dependencies', [])
        universes[qid] = {
            'expression': expr,
            'dependencies': deps,
            'ast': parse_expression_to_ast(expr)
        }
    
    # For each question, create edges based on:
    # 1. Universe condition dependencies (conditional edges)
    # 2. Sequential flow within blocks (fallthrough edges)
    
    # Track which questions have incoming edges
    has_incoming = set()
    
    # First pass: create conditional edges from universe dependencies
    for qid in ordered_ids:
        universe = universes.get(qid, {})
        ast = universe.get('ast')
        deps = universe.get('dependencies', [])
        expr_text = universe.get('expression', '')
        
        if ast is None:
            # Unconditional - will get fallthrough from previous
            continue
        
        if deps:
            # Create edge from each dependency
            for dep in deps:
                if dep in questions:
                    edge = {
                        "id": f"E{edge_counter:03d}",
                        "source": dep,
                        "target": qid,
                        "condition": ast,
                        "condition_text": expr_text,
                        "priority": 1,
                        "type": "branch"
                    }
                    edges.append(edge)
                    edge_counter += 1
                    has_incoming.add(qid)
    
    # Second pass: create fallthrough edges for sequential flow
    for i, qid in enumerate(ordered_ids[:-1]):
        next_qid = ordered_ids[i + 1]
        
        # Check if there's already a conditional edge to next_qid
        # If next_qid has a universe condition, it might skip this question
        next_universe = universes.get(next_qid, {})
        next_ast = next_universe.get('ast')
        
        if next_ast is None:
            # Next question is unconditional - add fallthrough
            edge = {
                "id": f"E{edge_counter:03d}",
                "source": qid,
                "target": next_qid,
                "condition": None,
                "condition_text": "fallthrough",
                "priority": 999,
                "type": "fallthrough"
            }
            edges.append(edge)
            edge_counter += 1
            has_incoming.add(next_qid)
    
    # Add fallthrough edges where conditional questions need a skip path
    # This handles: D11 -> D12 (if D11 > 0) but also D11 -> FD1 (fallthrough if D11 = 0)
    # We need to identify where fallthroughs should go when conditions aren't met
    
    # For now, this basic implementation creates the structure.
    # Complex fallthrough logic may need manual review.
    
    return edges


def convert_v2_to_v3(input_data: dict) -> dict:
    """
    Convert v2 schema (universe strings) to v3 schema (AST edges).
    """
    survey = input_data.get('survey', input_data)
    
    # Generate edges
    edges = generate_edges(survey)
    
    # Remove universe from questions (routing now in edges)
    questions_v3 = {}
    for qid, q in survey.get('questions', {}).items():
        q_copy = dict(q)
        q_copy.pop('universe', None)  # Remove universe - now in edges
        questions_v3[qid] = q_copy
    
    # Build v3 structure
    output = {
        "survey": {
            "id": survey.get('id', 'unknown'),
            "title": survey.get('title', ''),
            "version": "3.0",
            "metadata": survey.get('metadata', {}),
            "blocks": survey.get('blocks', {}),
            "questions": questions_v3,
            "dag": {
                "edges": edges,
                "metadata": {
                    "total_edges": len(edges),
                    "generated_from": "convert_v2_to_v3.py",
                    "source_version": survey.get('metadata', {}).get('schema_version', '2.0')
                }
            }
        }
    }
    
    # Update metadata
    output['survey']['metadata']['schema_version'] = '3.0'
    
    return output


def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_v2_to_v3.py input.json output.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    print(f"Reading {input_path}...")
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    print("Converting to v3 schema...")
    result = convert_v2_to_v3(data)
    
    edge_count = len(result['survey']['dag']['edges'])
    question_count = len(result['survey']['questions'])
    print(f"Generated {edge_count} edges for {question_count} questions")
    
    print(f"Writing {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print("Done.")


if __name__ == '__main__':
    main()
