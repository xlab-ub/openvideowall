"""
SQLAlchemy engine and session factory.
"""

import os
from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore


def _default_db_path() -> str:
    # Place SQLite DB in backend directory by default
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(base_dir)
    return os.path.join(backend_dir, "app.db")


SQLALCHEMY_DATABASE_URL = os.environ.get(
    "OPENVIDEOWALL_DATABASE_URL",
    f"sqlite:///{_default_db_path()}"
)

# SQLite needs check_same_thread=False for multi-threaded Flask
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Simple context manager helper (optional)
class session_scope:
    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()


