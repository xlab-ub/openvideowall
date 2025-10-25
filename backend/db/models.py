"""
ORM models for persistence.
"""

from typing import Any, Dict, Optional
from sqlalchemy import Column, String, Float, Integer, Text, Boolean  # type: ignore

from .base import Base


class User(Base):
    __tablename__ = "users"

    # Primary identifier
    username = Column(String(255), primary_key=True, index=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'admin' or 'student-assistant'
    
    # Timestamps
    created_at = Column(Float, nullable=True)
    last_login = Column(Float, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            username=data.get("username"),
            password_hash=data.get("password_hash"),
            role=data.get("role"),
            created_at=data.get("created_at"),
            last_login=data.get("last_login"),
        )


class Client(Base):
    __tablename__ = "clients"

    # Primary identifier used across the system
    client_id = Column(String(255), primary_key=True, index=True)

    # Identity / display
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    platform = Column(String(255), nullable=True)

    # Status timestamps
    registered_at = Column(Float, nullable=True)
    last_seen = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)  # 'active' | 'inactive'

    # Assignment fields
    assignment_status = Column(String(50), nullable=True)
    group_id = Column(String(255), nullable=True)
    group_name = Column(String(255), nullable=True)
    stream_assignment = Column(String(255), nullable=True)
    stream_url = Column(Text, nullable=True)
    screen_number = Column(Integer, nullable=True)
    assigned_at = Column(Float, nullable=True)
    unassigned_at = Column(Float, nullable=True)
    srt_ip = Column(String(255), nullable=True)

    # Minimal to_dict for syncing with in-memory state
    def to_state_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "display_name": self.display_name,
            "platform": self.platform,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
            "status": self.status,
            "assignment_status": self.assignment_status,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "stream_assignment": self.stream_assignment,
            "stream_url": self.stream_url,
            "screen_number": self.screen_number,
            "assigned_at": self.assigned_at,
            "unassigned_at": self.unassigned_at,
            "srt_ip": self.srt_ip or "127.0.0.1",
        }

    @classmethod
    def from_state_dict(cls, data: Dict[str, Any]) -> "Client":
        return cls(
            client_id=data.get("client_id"),
            hostname=data.get("hostname", "unknown"),
            ip_address=data.get("ip_address"),
            display_name=data.get("display_name"),
            platform=data.get("platform"),
            registered_at=data.get("registered_at"),
            last_seen=data.get("last_seen"),
            status=data.get("status"),
            assignment_status=data.get("assignment_status"),
            group_id=data.get("group_id"),
            group_name=data.get("group_name"),
            stream_assignment=data.get("stream_assignment"),
            stream_url=data.get("stream_url"),
            screen_number=data.get("screen_number"),
            assigned_at=data.get("assigned_at"),
            unassigned_at=data.get("unassigned_at"),
            srt_ip=(data.get("srt_ip") or "127.0.0.1"),
        )

class Group(Base):
    __tablename__ = "groups"

    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    screen_count = Column(Integer, nullable=True)
    orientation = Column(String(50), nullable=True)
    streaming_mode = Column(String(50), nullable=True)
    created_at = Column(Float, nullable=True)

    # Docker/runtime metadata (optional; for caching)
    docker_running = Column(Boolean, nullable=True)
    docker_status = Column(String(255), nullable=True)
    container_id = Column(String(255), nullable=True)
    container_name = Column(String(255), nullable=True)
    srt_port = Column(Integer, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "screen_count": self.screen_count,
            "orientation": self.orientation,
            "streaming_mode": self.streaming_mode,
            "created_at": self.created_at,
            "docker_running": self.docker_running,
            "docker_status": self.docker_status,
            "container_id": self.container_id,
            "container_name": self.container_name,
            "srt_port": self.srt_port,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Group":
        return cls(
            id=data.get("id") or data.get("group_id") or data.get("name"),
            name=data.get("name"),
            description=data.get("description"),
            screen_count=data.get("screen_count"),
            orientation=data.get("orientation"),
            streaming_mode=data.get("streaming_mode"),
            created_at=data.get("created_at"),
            docker_running=data.get("docker_running"),
            docker_status=data.get("docker_status"),
            container_id=data.get("container_id"),
            container_name=data.get("container_name"),
            srt_port=(data.get("srt_port") or (data.get("ports", {}) or {}).get("srt_port")),
        )


