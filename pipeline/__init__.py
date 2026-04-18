"""Pipeline entry points for ASI-Evolve."""

__all__ = [
    "Pipeline",
]


def __getattr__(name):
    if name == "Pipeline":
        from .main import Pipeline

        return Pipeline
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
