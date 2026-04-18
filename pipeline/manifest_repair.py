"""Canonical manifest repair helpers for pipeline state."""

from __future__ import annotations

from typing import Iterable

from ..utils.structures import Node


def canonical_step_from_nodes(nodes: Iterable[Node]) -> int | None:
    """Return canonical pipeline step inferred from persisted nodes."""
    node_list = [node for node in nodes if node.id is not None]
    if not node_list:
        return None

    max_node_id = max(int(node.id) for node in node_list if node.id is not None)
    has_initial = any(
        node.name == "initial_program"
        or (isinstance(node.meta_info, dict) and node.meta_info.get("step_name") == "step_0_initial")
        for node in node_list
    )
    return max_node_id if has_initial else max_node_id + 1
