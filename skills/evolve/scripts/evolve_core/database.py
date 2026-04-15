"""Persistent node database for skill-driven evolution runs."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from .algorithms import get_sampler
from .embedding import EmbeddingService
from .structures import Node
from .vector_index import FAISSIndex


class Database:
    """Persistent experiment database with sampler pluggability."""

    def __init__(
        self,
        storage_dir: Path,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim: int = 384,
        sampling_algorithm: str = "ucb1",
        sampling_kwargs: Optional[Dict[str, Any]] = None,
        faiss_index_type: str = "IP",
        max_size: Optional[int] = None,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.nodes: Dict[int, Node] = {}
        self.next_id = 0
        self.max_size = max_size
        self.embedding = EmbeddingService(
            model_name=embedding_model,
            dimension=embedding_dim,
        )
        self.faiss = FAISSIndex(
            dimension=embedding_dim,
            index_type=faiss_index_type,
            storage_path=self.storage_dir / "faiss",
        )
        self.sampling_algorithm = sampling_algorithm
        self.sampling_kwargs = sampling_kwargs or {}
        self.default_sampler = get_sampler(sampling_algorithm, **self.sampling_kwargs)
        self._load()

    def sample(self, n: int, algorithm: Optional[str] = None, **kwargs) -> List[Node]:
        with self.lock:
            nodes = list(self.nodes.values())
            sampler = (
                get_sampler(algorithm, **kwargs) if algorithm else self.default_sampler
            )
            selected = sampler.sample(nodes, n)
            self._save()
            return selected

    def add(self, node: Node) -> int:
        with self.lock:
            if self.max_size is not None and len(self.nodes) >= self.max_size:
                self._remove_worst_node()

            node.id = self.next_id
            self.next_id += 1
            self.nodes[node.id] = node
            self.default_sampler.on_node_added(node)

            context_text = node.get_context_text()
            if context_text:
                vector = self.embedding.encode(context_text)
                self.faiss.add(node.id, vector)

            self._save()
            return node.id

    def get_all(self) -> List[Node]:
        return list(self.nodes.values())

    def get(self, node_id: int) -> Optional[Node]:
        return self.nodes.get(node_id)

    def remove(self, node_id: int) -> bool:
        with self.lock:
            if node_id not in self.nodes:
                return False
            node = self.nodes[node_id]
            self.default_sampler.on_node_removed(node)
            del self.nodes[node_id]
            self.faiss.remove(node_id)
            self._save()
            return True

    def reset(self) -> None:
        with self.lock:
            if hasattr(self.default_sampler, "reset"):
                self.default_sampler.reset()
            self.nodes.clear()
            self.next_id = 0
            self.faiss.reset()
            data_file = self.storage_dir / "nodes.json"
            if data_file.exists():
                data_file.unlink()

    def get_sampler_stats(self) -> Optional[Dict[str, Any]]:
        if hasattr(self.default_sampler, "get_island_stats"):
            return self.default_sampler.get_island_stats(list(self.nodes.values()))
        return None

    def _remove_worst_node(self) -> None:
        if not self.nodes:
            return
        worst_id = min(self.nodes, key=lambda node_id: (self.nodes[node_id].score, node_id))
        self.remove(worst_id)

    def _save(self) -> None:
        payload = {
            "next_id": self.next_id,
            "nodes": {str(node_id): node.to_dict() for node_id, node in self.nodes.items()},
        }
        if hasattr(self.default_sampler, "get_state"):
            payload["sampler_state"] = self.default_sampler.get_state()
        with open(self.storage_dir / "nodes.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.faiss.save()

    def _load(self) -> None:
        data_file = self.storage_dir / "nodes.json"
        if not data_file.exists():
            return
        with open(data_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.next_id = payload.get("next_id", 0)
        for node_id, node_data in payload.get("nodes", {}).items():
            self.nodes[int(node_id)] = Node.from_dict(node_data)
        if hasattr(self.default_sampler, "load_state") and "sampler_state" in payload:
            self.default_sampler.load_state(payload["sampler_state"])
        if hasattr(self.default_sampler, "rebuild_from_nodes"):
            self.default_sampler.rebuild_from_nodes(list(self.nodes.values()))

    def __len__(self) -> int:
        return len(self.nodes)
