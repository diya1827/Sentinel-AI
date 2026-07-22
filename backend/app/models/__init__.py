"""Domain & API models (Pydantic).

Responsibility: the data contracts shared across layers. These types are the
common language between scanners, agents, services, and the API. They contain
no behavior beyond validation.

Contents:
    finding.py  — a single normalized security finding
    review.py   — a review request and its aggregated report
"""
