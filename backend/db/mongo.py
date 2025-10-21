"""
MongoDB client utilities for backend persistence.
"""

import os
from typing import Optional, Dict, Any, List

try:
    from pymongo import MongoClient  # type: ignore
    from pymongo.collection import Collection  # type: ignore
    from pymongo.database import Database  # type: ignore
    from pymongo.errors import PyMongoError  # type: ignore
except Exception:  # pragma: no cover - environment might not have pymongo
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore
    Database = None  # type: ignore
    PyMongoError = Exception  # type: ignore


_client: Optional[MongoClient] = None  # type: ignore


def is_mongo_enabled() -> bool:
    return bool(os.environ.get("OPENVIDEOWALL_MONGO_URL"))


def get_mongo_client() -> Optional[MongoClient]:  # type: ignore
    global _client
    if not is_mongo_enabled():
        return None
    if _client is not None:
        return _client
    mongo_url = os.environ.get("OPENVIDEOWALL_MONGO_URL")
    if not mongo_url:
        return None
    try:
        _client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)  # type: ignore
        # Ping to verify
        _client.admin.command("ping")  # type: ignore
        return _client
    except Exception:
        _client = None
        return None


def get_mongo_db() -> Optional[Database]:  # type: ignore
    client = get_mongo_client()
    if client is None:
        return None
    db_name = os.environ.get("OPENVIDEOWALL_MONGO_DB", "openvideowall")
    return client[db_name]


def ensure_indexes():
    db = get_mongo_db()
    if db is None:
        return
    try:
        db["clients"].create_index("client_id", unique=True)
        db["groups"].create_index("id", unique=True)
        db["groups"].create_index("name", unique=True)
    except Exception:
        # Non-fatal
        pass


def upsert_one(collection: str, key: Dict[str, Any], doc: Dict[str, Any]) -> None:
    db = get_mongo_db()
    if db is None:
        return
    try:
        db[collection].update_one(key, {"$set": doc}, upsert=True)
    except Exception:
        pass


def delete_one(collection: str, key: Dict[str, Any]) -> None:
    db = get_mongo_db()
    if db is None:
        return
    try:
        db[collection].delete_one(key)
    except Exception:
        pass


def find_all(collection: str) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    if db is None:
        return []
    try:
        return list(db[collection].find({}, {"_id": 0}))  # exclude ObjectId
    except Exception:
        return []


