"""Shared domain model, settings and database session for Revix.

This package is imported by both the pipeline and the API and imports neither
of them. That one-way dependency is what keeps the write path and the read
path from tangling together.
"""

__version__ = "0.1.0"
