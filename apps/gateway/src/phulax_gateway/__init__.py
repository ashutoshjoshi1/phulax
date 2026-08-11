"""Phulax local gateway.

The enforcement point. Runs inside the customer environment (ADR-0001):
agents call tools through it, a deterministic policy engine (ADR-0003)
produces a verdict, and a metadata-first decision event (ADR-0002) is
recorded. Tool credentials never leave this side of the boundary.
"""

__version__ = "0.0.1"
