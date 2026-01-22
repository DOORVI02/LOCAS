"""Audit logging service for LOCAS."""

from datetime import date, datetime
from typing import Any, Optional

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import AuthorizationError
from locas.core.constants import AuditAction
from locas.models.audit_log import AuditLog, AuditLogCreate
from locas.repositories.audit_repository import AuditRepository


class AuditService:
    """Handles audit logging operations.
    
    Responsibilities:
    - Log user actions
    - Query audit history
    - Generate audit reports
    
    Attributes:
        config: Application configuration.
        session_manager: Session manager.
        audit_repo: Audit repository.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager
    ) -> None:
        """Initialize AuditService.
        
        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.session_manager = session_manager
        self.audit_repo = AuditRepository(db_manager)
    
    def _require_admin(self) -> int:
        """Require admin role and return current user ID."""
        session = self.session_manager.current_session
        if session is None or not session.is_admin():
            raise AuthorizationError("Administrator privileges required")
        return session.user_id
    
    # -------------------------------------------------------------------------
    # Logging Operations
    # -------------------------------------------------------------------------
    
    def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[int] = None,
        old_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None
    ) -> int:
        """Log an action from the current user.
        
        Args:
            action: Action being performed.
            entity_type: Type of entity affected.
            entity_id: ID of affected entity.
            old_value: Previous state (for updates).
            new_value: New state (for creates/updates).
            
        Returns:
            Created log ID.
        """
        session = self.session_manager.current_session
        if session is None:
            return -1  # Can't log without a session
        
        return self.audit_repo.log_action(
            user_id=session.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value
        )
    
    def log_for_user(
        self,
        user_id: int,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[int] = None,
        old_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None
    ) -> int:
        """Log an action for a specific user.
        
        Args:
            user_id: User performing the action.
            action: Action being performed.
            entity_type: Type of entity affected.
            entity_id: ID of affected entity.
            old_value: Previous state.
            new_value: New state.
            
        Returns:
            Created log ID.
        """
        return self.audit_repo.log_action(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value
        )
    
    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------
    
    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> list[AuditLog]:
        """Get audit logs with filters.
        
        Args:
            limit: Maximum records.
            offset: Records to skip.
            user_id: Filter by user.
            action: Filter by action.
            entity_type: Filter by entity type.
            start_date: Start of date range.
            end_date: End of date range.
            
        Returns:
            List of AuditLog instances.
            
        Raises:
            AuthorizationError: If not admin.
        """
        self._require_admin()
        
        return self.audit_repo.find_all_with_users(
            limit=limit,
            offset=offset,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> list[AuditLog]:
        """Get audit logs for a specific user.
        
        Args:
            user_id: User ID.
            limit: Maximum records.
            
        Returns:
            List of AuditLog instances.
        """
        self._require_admin()
        return self.audit_repo.find_by_user(user_id, limit=limit)
    
    def get_entity_logs(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50
    ) -> list[AuditLog]:
        """Get audit logs for a specific entity.
        
        Args:
            entity_type: Type of entity.
            entity_id: Entity ID.
            limit: Maximum records.
            
        Returns:
            List of AuditLog instances.
        """
        self._require_admin()
        return self.audit_repo.find_by_entity(entity_type, entity_id, limit=limit)
    
    def get_recent_activity(self, limit: int = 20) -> list[AuditLog]:
        """Get recent activity across all users.
        
        Args:
            limit: Number of records.
            
        Returns:
            List of recent AuditLog instances.
        """
        self._require_admin()
        return self.audit_repo.get_recent_activity(limit=limit)
    
    # -------------------------------------------------------------------------
    # Filter Options
    # -------------------------------------------------------------------------
    
    def get_action_types(self) -> list[str]:
        """Get list of all action types in logs.
        
        Returns:
            List of action type strings.
        """
        return self.audit_repo.get_action_types()
    
    def get_entity_types(self) -> list[str]:
        """Get list of all entity types in logs.
        
        Returns:
            List of entity type strings.
        """
        return self.audit_repo.get_entity_types()
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_login_count(self, days: int = 30) -> int:
        """Get login count for the last N days.
        
        Args:
            days: Number of days to look back.
            
        Returns:
            Login count.
        """
        return self.audit_repo.count_by_action("LOGIN", days=days)
    
    def get_action_count(self, action: str, days: int = 30) -> int:
        """Get count of a specific action.
        
        Args:
            action: Action name.
            days: Number of days to look back.
            
        Returns:
            Action count.
        """
        return self.audit_repo.count_by_action(action, days=days)
