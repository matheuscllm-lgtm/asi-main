"""Shared utility helpers for ASI-Evolve."""

from .logger import EvolveLogger, get_logger, init_logger
from .prompt import PromptManager
from .structures import Node, CognitionItem, ExperimentConfig, LLMResponse
from .config import load_config
from .best_snapshot import BestSnapshotManager
from .atomic_io import atomic_write_json, atomic_write_text

try:
    from .llm import LLMClient, create_llm_client
except ModuleNotFoundError:
    # Optional at import time for environments that only run local-unit tests.
    LLMClient = None
    create_llm_client = None

__all__ = [
    "LLMClient",
    "create_llm_client",
    "EvolveLogger",
    "get_logger",
    "init_logger",
    "PromptManager",
    "Node",
    "CognitionItem",
    "ExperimentConfig",
    "LLMResponse",
    "load_config",
    "BestSnapshotManager",
    "atomic_write_json",
    "atomic_write_text",
]
