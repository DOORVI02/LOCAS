"""Authentication service for LOCAS."""

from locas.config import Config
from locas.core.constants import AuditAction
from locas.core.database import DatabaseManager
from locas.core.exceptions import AuthenticationError, AuthorizationError
from locas.core.security import SecurityManager, Session, SessionManager
from locas.models.user import User
from locas.repositories.audit_repository import AuditRepository
from locas.repositories.user_repository import UserRepository


class AuthService:
    """Handles authentication and authorization operations.

    Responsibilities:
    - User login/logout
    - Password verification
    - Password change
    - Session management
    - Role-based access control

    Attributes:
        config: Application configuration.
        db_manager: Database manager.
        security: Security manager for password operations.
        session_manager: Session manager.
        user_repo: User repository.
        audit_repo: Audit repository.
    """

    def __init__(
        self, config: Config, db_manager: DatabaseManager, session_manager: SessionManager
    ) -> None:
        """Initialize AuthService.

        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager for tracking sessions.
        """
        self.config = config
        self.db_manager = db_manager
        self.security = SecurityManager(config)
        self.session_manager = session_manager
        self.user_repo = UserRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)

    def authenticate(self, username: str, password: str) -> Session:
        """Authenticate a user with username and password.

        Args:
            username: User's username.
            password: User's plain text password.

        Returns:
            Session object for the authenticated user.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if not username or not password:
            raise AuthenticationError("Username and password are required")

        # Find user with password hash
        user_data = self.user_repo.find_with_password(username)

        if user_data is None:
            self._log_failed_login_attempt(username)
            raise AuthenticationError("Invalid username or password")

        # Check if user is active
        if not user_data.get("is_active", False):
            raise AuthenticationError("Account is deactivated. Please contact administrator.")

        # Verify password
        if not self.security.verify_password(password, user_data["password_hash"]):
            self._log_failed_login(user_data["user_id"])
            raise AuthenticationError("Invalid username or password")

        # Create session
        session = self.session_manager.create_session(
            user_id=user_data["user_id"],
            username=user_data["username"],
            role_id=user_data["role_id"],
            role_name=user_data["role_name"],
            full_name=user_data["full_name"],
        )

        # Update last login
        self.user_repo.update_last_login(user_data["user_id"])

        # Log successful login
        self.audit_repo.log_action(
            user_id=user_data["user_id"],
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=user_data["user_id"],
        )

        return session

    def logout(self) -> None:
        """Log out the current user.

        Ends the current session and logs the action.
        """
        session = self.session_manager.current_session

        if session:
            self.audit_repo.log_action(
                user_id=session.user_id,
                action=AuditAction.LOGOUT,
                entity_type="user",
                entity_id=session.user_id,
            )

        self.session_manager.end_session()

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change a user's password.

        Args:
            user_id: User ID.
            current_password: Current password for verification.
            new_password: New password to set.

        Returns:
            True if password changed successfully.

        Raises:
            AuthenticationError: If current password is incorrect.
            ValidationError: If new password doesn't meet requirements.
        """
        # Get user with password
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")

        user_data = self.user_repo.find_with_password(user.username)
        if user_data is None:
            raise AuthenticationError("User not found")

        # Verify current password
        if not self.security.verify_password(current_password, user_data["password_hash"]):
            raise AuthenticationError("Current password is incorrect")

        # Validate and hash new password
        new_hash = self.security.hash_password(new_password)

        # Update password
        success = self.user_repo.update_password(user_id, new_hash)

        if success:
            self.audit_repo.log_action(
                user_id=user_id,
                action=AuditAction.PASSWORD_CHANGED,
                entity_type="user",
                entity_id=user_id,
            )

        return success

    def reset_password(
        self, admin_user_id: int, target_user_id: int, new_password: str | None = None
    ) -> str:
        """Reset a user's password (admin only).

        Args:
            admin_user_id: Admin user performing the reset.
            target_user_id: User whose password is being reset.
            new_password: Optional new password. If not provided, generates one.

        Returns:
            The new password (plain text).

        Raises:
            AuthorizationError: If caller is not an admin.
        """
        # Verify admin role
        session = self.session_manager.current_session
        if session is None or not session.is_admin():
            raise AuthorizationError("Only administrators can reset passwords")

        # Generate password if not provided
        if new_password is None:
            new_password = self.security.generate_temporary_password()

        # Hash and update
        new_hash = self.security.hash_password(new_password)
        self.user_repo.update_password(target_user_id, new_hash)

        # Log action
        self.audit_repo.log_action(
            user_id=admin_user_id,
            action=AuditAction.PASSWORD_RESET,
            entity_type="user",
            entity_id=target_user_id,
        )

        return new_password

    def require_auth(self) -> Session:
        """Require authentication for an operation.

        Returns:
            Current session.

        Raises:
            AuthenticationError: If not authenticated.
        """
        session = self.session_manager.current_session
        if session is None:
            raise AuthenticationError("Authentication required")

        # Refresh session to extend timeout
        self.session_manager.refresh_session()

        return session

    def require_role(self, *roles: str) -> Session:
        """Require specific role(s) for an operation.

        Args:
            roles: Allowed role names.

        Returns:
            Current session.

        Raises:
            AuthenticationError: If not authenticated.
            AuthorizationError: If user doesn't have required role.
        """
        session = self.require_auth()

        if not session.has_role(*roles):
            raise AuthorizationError(
                f"This action requires one of the following roles: {', '.join(roles)}"
            )

        return session

    def require_admin(self) -> Session:
        """Require admin role.

        Returns:
            Current session.
        """
        return self.require_role("admin")

    def require_librarian(self) -> Session:
        """Require librarian role.

        Returns:
            Current session.
        """
        return self.require_role("librarian")

    def require_librarian_or_admin(self) -> Session:
        """Require librarian or admin role.

        Returns:
            Current session.
        """
        return self.require_role("librarian", "admin")

    def _log_failed_login_attempt(self, username: str) -> None:
        """Log a failed login attempt for unknown username.

        Args:
            username: Attempted username.
        """
        # We don't have a user_id, so we can't log to audit table
        # In production, you might log to a separate security log
        pass

    def _log_failed_login(self, user_id: int) -> None:
        """Log a failed login for known user.

        Args:
            user_id: User ID.
        """
        try:
            self.audit_repo.log_action(
                user_id=user_id,
                action=AuditAction.LOGIN_FAILED,
                entity_type="user",
                entity_id=user_id,
            )
        except Exception:
            # Don't fail on audit logging error
            pass

    def get_current_user(self) -> User | None:
        """Get the currently authenticated user.

        Returns:
            User object or None if not authenticated.
        """
        session = self.session_manager.current_session
        if session is None:
            return None

        return self.user_repo.find_by_id(session.user_id)

    def is_authenticated(self) -> bool:
        """Check if there's an active session.

        Returns:
            True if authenticated.
        """
        return self.session_manager.is_authenticated()
