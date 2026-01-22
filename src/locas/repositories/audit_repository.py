"""Audit log repository for database operations."""

from datetime import datetime, date
from typing import Any, Optional
import json

from locas.core.database import DatabaseManager
from locas.core.constants import AuditAction
from locas.models.audit_log import AuditLog, AuditLogCreate
from locas.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog entity operations."""
    
    @property
    def table_name(self) -> str:
        return "audit_logs"
    
    @property
    def primary_key(self) -> str:
        return "log_id"
    
    def _from_row(self, row: dict[str, Any]) -> AuditLog:
        return AuditLog.from_dict(row)
    
    def find_all_with_users(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> list[AuditLog]:
        """Find audit logs with user information and filters.
        
        Args:
            limit: Maximum records.
            offset: Records to skip.
            user_id: Filter by user.
            action: Filter by action type.
            entity_type: Filter by entity type.
            start_date: Filter from date.
            end_date: Filter to date.
            
        Returns:
            List of AuditLog instances.
        """
        conditions = []
        params: list[Any] = []
        
        if user_id is not None:
            conditions.append("a.user_id = %s")
            params.append(user_id)
        
        if action:
            conditions.append("a.action = %s")
            params.append(action)
        
        if entity_type:
            conditions.append("a.entity_type = %s")
            params.append(entity_type)
        
        if start_date:
            conditions.append("DATE(a.timestamp) >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("DATE(a.timestamp) <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT a.*, u.username, u.full_name
            FROM audit_logs a
            JOIN users u ON a.user_id = u.user_id
            WHERE {where_clause}
            ORDER BY a.timestamp DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]
    
    def find_by_entity(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50
    ) -> list[AuditLog]:
        """Find audit logs for a specific entity.
        
        Args:
            entity_type: Type of entity.
            entity_id: Entity ID.
            limit: Maximum records.
            
        Returns:
            List of AuditLog instances.
        """
        query = """
            SELECT a.*, u.username, u.full_name
            FROM audit_logs a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.entity_type = %s AND a.entity_id = %s
            ORDER BY a.timestamp DESC
            LIMIT %s
        """
        rows = self.db.execute(query, (entity_type, entity_id, limit))
        return [self._from_row(row) for row in rows]
    
    def find_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """Find audit logs by user.
        
        Args:
            user_id: User who performed actions.
            limit: Maximum records.
            offset: Records to skip.
            
        Returns:
            List of AuditLog instances.
        """
        return self.find_all_with_users(
            limit=limit,
            offset=offset,
            user_id=user_id
        )
    
    def create(self, log_data: AuditLogCreate) -> int:
        """Create a new audit log entry.
        
        Args:
            log_data: Audit log creation DTO.
            
        Returns:
            New log ID.
        """
        data = log_data.to_insert_dict()
        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)
    
    def log_action(
        self,
        user_id: int,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[int] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None
    ) -> int:
        """Convenience method to log an action.
        
        Args:
            user_id: User performing the action.
            action: Action type.
            entity_type: Type of entity.
            entity_id: Entity ID.
            old_value: Previous state.
            new_value: New state.
            
        Returns:
            New log ID.
        """
        log_data = AuditLogCreate(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value
        )
        return self.create(log_data)
    
    def get_action_types(self) -> list[str]:
        """Get list of all action types in logs.
        
        Returns:
            List of unique action types.
        """
        query = """
            SELECT DISTINCT action
            FROM audit_logs
            ORDER BY action
        """
        rows = self.db.execute(query)
        return [row["action"] for row in rows]
    
    def get_entity_types(self) -> list[str]:
        """Get list of all entity types in logs.
        
        Returns:
            List of unique entity types.
        """
        query = """
            SELECT DISTINCT entity_type
            FROM audit_logs
            ORDER BY entity_type
        """
        rows = self.db.execute(query)
        return [row["entity_type"] for row in rows]
    
    def count_by_action(self, action: str, days: int = 30) -> int:
        """Count actions in the last N days.
        
        Args:
            action: Action type to count.
            days: Number of days to look back.
            
        Returns:
            Count of actions.
        """
        query = """
            SELECT COUNT(*) as cnt
            FROM audit_logs
            WHERE action = %s 
              AND timestamp >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
        """
        result = self.db.execute_one(query, (action, days))
        return result["cnt"] if result else 0
    
    def get_recent_activity(self, limit: int = 20) -> list[AuditLog]:
        """Get recent activity across all users.
        
        Args:
            limit: Number of recent entries.
            
        Returns:
            List of recent AuditLog instances.
        """
        query = """
            SELECT a.*, u.username, u.full_name
            FROM audit_logs a
            JOIN users u ON a.user_id = u.user_id
            ORDER BY a.timestamp DESC
            LIMIT %s
        """
        rows = self.db.execute(query, (limit,))
        return [self._from_row(row) for row in rows]

    def delete_by_user(self, user_id: int) -> int:
        """Delete all audit logs for a user.
        
        Args:
            user_id: User ID.
            
        Returns:
            Number of deleted logs.
        """
        query = "DELETE FROM audit_logs WHERE user_id = %s"
        return self.db.execute_update(query, (user_id,))
