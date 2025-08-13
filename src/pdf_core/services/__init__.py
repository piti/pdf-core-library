"""
Service layer for storage abstraction.

Contains abstractions for:
- Storage backends (local filesystem)
"""

from .storage_abstraction import StorageInterface, LocalStorage

__all__ = [
    "StorageInterface",
    "LocalStorage"
]