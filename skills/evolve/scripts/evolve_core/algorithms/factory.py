"""Factory for sampler implementations."""

from __future__ import annotations

from .base import BaseSampler
from .greedy import GreedySampler
from .island import IslandSampler
from .random import RandomSampler
from .ucb1 import UCB1Sampler


def get_sampler(algorithm: str, **kwargs) -> BaseSampler:
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    samplers = {
        "greedy": GreedySampler,
        "island": IslandSampler,
        "random": RandomSampler,
        "ucb1": UCB1Sampler,
    }
    if algorithm not in samplers:
        raise ValueError(
            f"Unknown sampling algorithm: {algorithm}. Available: {sorted(samplers)}"
        )
    return samplers[algorithm](**kwargs)
