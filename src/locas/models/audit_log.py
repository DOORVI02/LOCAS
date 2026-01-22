"""Audit log data models."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from locas.core.constants import AuditAction


@dataclass
class AuditLog:
    """Represents an audit log entry.

    Tracks all privileged actions in the system for accountability.

    Attributes:
        log_id: Unique identifier.
        user_id: User who performed the action.
        action: Type of action performed.
        entity_type: Type of entity affected.
        entity_id: ID of the affected entity.
        old_value: Previous value (for updates).
        new_value: New value (for creates/updates).
        ip_address: Client IP (always localhost for desktop).
        timestamp: When the action occurred.
    """

    log_id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    ip_address: str | None = None
    timestamp: datetime | None = None
    # Joined fields
    username: str | None = None
    full_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditLog":
        """Create AuditLog from dictionary."""
        old_value = data.get("old_value")
        new_value = data.get("new_value")

        # Parse JSON if stored as string
        if isinstance(old_value, str):
            try:
                old_value = json.loads(old_value)
            except json.JSONDecodeError:
                old_value = None

        if isinstance(new_value, str):
            try:
                new_value = json.loads(new_value)
            except json.JSONDecodeError:
                new_value = None

        return cls(
            log_id=data["log_id"],
            user_id=data["user_id"],
            action=data["action"],
            entity_type=data["entity_type"],
            entity_id=data.get("entity_id"),
            old_value=old_value,
            new_value=new_value,
            ip_address=data.get("ip_address"),
            timestamp=data.get("timestamp"),
            username=data.get("username"),
            full_name=data.get("full_name"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
        }

    @property
    def action_display(self) -> str:
        """Get human-readable action name."""
        return self.action.replace("_", " ").title()


@dataclass
class AuditLogCreate:
    """DTO for creating an audit log entry.

    Attributes:
        user_id: User performing the action.
        action: Action type (use AuditAction enum).
        entity_type: Type of entity (e.g., "user", "book").
        entity_id: ID of the affected entity.
        old_value: Previous value (for updates).
        new_value: New value (for creates/updates).
    """

    user_id: int
    action: AuditAction
    entity_type: str
    entity_id: int | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None

    def to_insert_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            "user_id": self.user_id,
            "action": str(self.action),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "old_value": json.dumps(self.old_value) if self.old_value else None,
            "new_value": json.dumps(self.new_value) if self.new_value else None,
            "ip_address": "127.0.0.1",  # Desktop app, always localhost
        }
