# validators/structure.py
from __future__ import annotations
from jsonschema import Draft7Validator, validate
from pathlib import Path
import json
from collections import Counter

def validate_structure_doc(doc: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(schema)
    validate(instance=doc, schema=schema)

    s = doc["survey_dag_structure"]
    ids = [n["id"] for n in s["nodes"] if n.get("id")]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        raise ValueError(f"Duplicate node ids in structure: {dup}")

    node_set = set(ids)
    for e in s["edges"]:
        if e["source"] not in node_set or e["target"] not in node_set:
            raise ValueError(f"Edge references unknown node: {e}")

    for pid, p in s["predicates"].items():
        if not pid or not isinstance(p, dict):
            raise ValueError(f"Bad predicate: {pid}")

def validate_content_doc(doc: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(schema)
    validate(instance=doc, schema=schema)

    ids = [n["id"] for n in doc["survey_content"]["nodes"] if n.get("id")]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        raise ValueError(f"Duplicate node ids in content: {dup}")

    for n in doc["survey_content"]["nodes"]:
        if n["response_type"] in ("enum","set"):
            opts = n.get("response_options") or []
            if not opts:
                raise ValueError(f"Enum/set with no options: {n['id']}")
