from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class SurveyModel:
    def __init__(self, document: dict[str, Any]):
        self.document = document
        self.survey = self._dict_or_empty(document.get("survey") if isinstance(document, dict) else None)
        self.questions = self._dict_or_empty(self.survey.get("questions"))
        self.terminals = self._dict_or_empty(self.survey.get("terminal_nodes"))
        self.dag = self._dict_or_empty(self.survey.get("dag"))
        self.edges = self._list_or_empty(self.dag.get("edges"))
        self._outgoing = self._index_edges("source")
        self._incoming = self._index_edges("target")

    @classmethod
    def from_path(cls, path: Path | str) -> "SurveyModel":
        with Path(path).open("r", encoding="utf-8") as file:
            return cls(json.load(file))

    @property
    def survey_id(self) -> str:
        return self.survey["id"]

    @property
    def entry_node(self) -> str | None:
        return self.dag.get("entry_node")

    @property
    def terminal_ids(self) -> list[str]:
        return list(self.dag.get("terminal_nodes", []))

    @property
    def node_ids(self) -> set[str]:
        return set(self.questions) | set(self.terminals)

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.node_ids

    def is_terminal(self, node_id: str) -> bool:
        return node_id in self.terminals

    def outgoing_edges(self, node_id: str) -> list[dict[str, Any]]:
        return sorted(self._outgoing.get(node_id, []), key=lambda edge: (self._priority_sort_value(edge), self._edge_id(edge)))

    def incoming_edges(self, node_id: str) -> list[dict[str, Any]]:
        return sorted(self._incoming.get(node_id, []), key=self._edge_id)

    def block_order(self) -> list[str]:
        ordered_blocks = sorted(self.survey.get("blocks", {}).values(), key=lambda block: block.get("order", 999))
        ordered: list[str] = []
        for block in ordered_blocks:
            ordered.extend(qid for qid in block.get("questions", []) if qid in self.questions)
        for qid in self.questions:
            if qid not in ordered:
                ordered.append(qid)
        return ordered

    def next_question_after(self, node_id: str) -> str | None:
        ordered = self.block_order()
        if node_id not in ordered:
            return None
        index = ordered.index(node_id)
        if index + 1 >= len(ordered):
            return None
        return ordered[index + 1]

    def _index_edges(self, key: str) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            if not isinstance(edge, dict):
                continue
            node_id = edge.get(key)
            if isinstance(node_id, str):
                index[node_id].append(edge)
        return dict(index)

    @staticmethod
    def _dict_or_empty(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _list_or_empty(value: Any) -> list[Any]:
        return list(value) if isinstance(value, list) else []

    @staticmethod
    def _edge_id(edge: dict[str, Any]) -> str:
        edge_id = edge.get("id", "")
        return edge_id if isinstance(edge_id, str) else str(edge_id)

    @staticmethod
    def _priority_sort_value(edge: dict[str, Any]) -> int:
        priority = edge.get("priority", 999)
        return priority if type(priority) is int else 999

    @staticmethod
    def condition_variables(condition: Any) -> set[str]:
        if condition is None or not isinstance(condition, list) or not condition:
            return set()
        op = condition[0]
        if op in {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains"} and len(condition) >= 2:
            return {condition[1]} if isinstance(condition[1], str) else set()
        variables: set[str] = set()
        for item in condition[1:]:
            variables |= SurveyModel.condition_variables(item)
        return variables
