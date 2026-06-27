"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass):
    """Base class for all ORM models.

    Uses MappedAsDataclass for cleaner model definitions with
    type-annotated fields and automatic __init__/__repr__.
    """
