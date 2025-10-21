"""
Database package initialization for backend.

Exposes Base and SessionLocal for convenience.
"""

try:
    from .base import Base  # type: ignore
    from .session import SessionLocal  # type: ignore
except Exception:
    # Allow importing even if environment not fully set up
    Base = None  # type: ignore
    SessionLocal = None  # type: ignore

