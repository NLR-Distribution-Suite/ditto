"""OpenDSS properties that are not represented by the core GDM schema.

The GDM load and transformer equipment models intentionally expose the common
electrical data, but OpenDSS also has solver-behaviour properties such as
Vminpu, CVR exponents, and magnetizing current.  These supplemental attributes
keep those source properties attached to a round-tripped component without
requiring them to become core GDM fields.
"""

from __future__ import annotations

from infrasys import SupplementalAttribute


class OpenDSSLoadProperties(SupplementalAttribute):
    """Source OpenDSS load behaviour properties."""

    model: int | None = None
    vminpu: float | None = None
    vmaxpu: float | None = None
    cvrwatts: float | None = None
    cvrvars: float | None = None
    zipv: list[float] | None = None


class OpenDSSTransformerProperties(SupplementalAttribute):
    """Source OpenDSS transformer properties not present in GDM equipment."""

    magnetizing_current_pct: float | None = None
