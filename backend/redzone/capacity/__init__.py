"""Deliverable 2 — carrying-capacity assessment.

STATUS: working stub. The four sub-capacities below are computed deterministically from the
habitation attributes, but the coefficients are provisional placeholders, NOT yet sourced to
BIS (water), IRC (road capacity), IPHS (health) and RTE (school) norms with citations. That
sourcing is the remaining work for this deliverable; the pipeline wiring and outputs are final.
"""

from redzone.capacity.deficit import assess_capacity

__all__ = ["assess_capacity"]
