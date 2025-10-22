"""
MongoDB client utilities for backend persistence.
"""

import os
import time
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
        db["client_assignments"].create_index("hostname", unique=True)
        db["client_assignments"].create_index("client_id")
        db["client_assignments"].create_index("group_id")
        db["group_stream_ids"].create_index("group_id", unique=True)
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


def find_one(collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a single document in a collection"""
    db = get_mongo_db()
    if db is None:
        return None
    try:
        return db[collection].find_one(query, {"_id": 0})
    except Exception:
        return None


def save_client_assignment(client_id: str, hostname: str, group_id: str, screen_number: int, group_name: str, monitor_x: int = None, monitor_y: int = None) -> bool:
    """Save persistent client assignment to database"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        assignment = {
            "client_id": client_id,
            "hostname": hostname,
            "group_id": group_id,
            "screen_number": screen_number,
            "group_name": group_name,
            "monitor_x": monitor_x,
            "monitor_y": monitor_y,
            "assigned_at": int(time.time()),
            "last_seen": int(time.time())
        }
        
        # Upsert the assignment
        db["client_assignments"].update_one(
            {"hostname": hostname},
            {"$set": assignment},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving client assignment: {e}")
        return False


def get_client_assignment(hostname: str) -> Optional[Dict[str, Any]]:
    """Get persistent client assignment by hostname"""
    db = get_mongo_db()
    if db is None:
        return None
    
    try:
        return db["client_assignments"].find_one({"hostname": hostname}, {"_id": 0})
    except Exception as e:
        print(f"Error getting client assignment: {e}")
        return None


def update_client_last_seen(hostname: str) -> bool:
    """Update last seen timestamp for client assignment"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db["client_assignments"].update_one(
            {"hostname": hostname},
            {"$set": {"last_seen": int(time.time())}}
        )
        return True
    except Exception as e:
        print(f"Error updating client last seen: {e}")
        return False


def remove_client_assignment(hostname: str) -> bool:
    """Remove persistent client assignment"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db["client_assignments"].delete_one({"hostname": hostname})
        return True
    except Exception as e:
        print(f"Error removing client assignment: {e}")
        return False


def save_group_stream_ids(group_id: str, group_name: str, stream_ids: Dict[str, str]) -> bool:
    """Save stream IDs for a group to database"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        stream_data = {
            "group_id": group_id,
            "group_name": group_name,
            "stream_ids": stream_ids,
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        
        # Upsert the stream IDs
        db["group_stream_ids"].update_one(
            {"group_id": group_id},
            {"$set": stream_data},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving group stream IDs: {e}")
        return False


def get_group_stream_ids(group_id: str) -> Optional[Dict[str, str]]:
    """Get stream IDs for a group from database"""
    db = get_mongo_db()
    if db is None:
        return None
    
    try:
        result = db["group_stream_ids"].find_one({"group_id": group_id}, {"_id": 0})
        if result:
            return result.get("stream_ids", {})
        return None
    except Exception as e:
        print(f"Error getting group stream IDs: {e}")
        return None


def remove_group_stream_ids(group_id: str) -> bool:
    """Remove stream IDs for a group from database"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db["group_stream_ids"].delete_one({"group_id": group_id})
        return True
    except Exception as e:
        print(f"Error removing group stream IDs: {e}")
        return False


