"""Shared application state for the DiTTo MCP server.

The ``AppState`` dataclass is yielded by the server lifespan and made available
to every tool via ``ctx.request_context.lifespan_context``.  It holds a
registry of loaded ``DistributionSystem`` instances keyed by user-provided
name, enabling interactive multi-step workflows (load → inspect → export)
within a single MCP session.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gdm.distribution import DistributionSystem


@dataclass
class AppState:
    """In-memory registry of loaded distribution system models."""

    systems: dict[str, DistributionSystem] = field(default_factory=dict)

    def store(self, name: str, system: DistributionSystem) -> str:
        """Store a system under *name*, overwriting any previous entry."""
        self.systems[name] = system
        return name

    def get(self, name: str) -> DistributionSystem:
        """Retrieve a system by name. Raises ``KeyError`` if not found."""
        if name not in self.systems:
            available = ", ".join(self.systems.keys()) or "(none)"
            raise KeyError(
                f"No system loaded with name '{name}'. " f"Available systems: {available}"
            )
        return self.systems[name]

    def summary(self, name: str) -> dict:
        """Return a concise summary dict for the named system."""
        system = self.get(name)
        component_types = system.get_component_types()
        counts: dict[str, int] = {}
        for ct in component_types:
            counts[ct.__name__] = len(list(system.get_components(ct)))

        info = {
            "name": name,
            "component_types": counts,
            "total_components": sum(counts.values()),
        }
        return info
