"""User management service for LOCAS."""

from locas.config import Config
from locas.core.constants import AuditAction
from locas.core.database import DatabaseManager
from locas.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from locas.core.security import SecurityManager, SessionManager
from locas.models.user import Role, User, UserCreate, UserUpdate
from locas.repositories.audit_repository import AuditRepository
from locas.repositories.user_repository import RoleRepository, UserRepository
from locas.utils.validators import validate_email, validate_full_name, validate_username


class UserService:
    """Handles user management operations.

    Responsibilities:
    - User CRUD operations
    - Role assignment
    - User activation/deactivation
    - User search and listing

    Attributes:
        config: Application configuration.
        security: Security manager.
        session_manager: Session manager.
        user_repo: User repository.
        role_repo: Role repository.
        audit_repo: Audit repository.
    """

    def __init__(
        self, config: Config, db_manager: DatabaseManager, session_manager: SessionManager
    ) -> None:
        """Initialize UserService.

        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
        """
        self.config = config
        self.security = SecurityManager(config)
        self.session_manager = session_manager
        self.user_repo = UserRepository(db_manager)
        self.role_repo = RoleRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)

    def _require_admin(self) -> int:
        """Require admin role and return current user ID.

        Returns:
            Current user's ID.

        Raises:
            AuthorizationError: If not admin.
        """
        session = self.session_manager.current_session
        if session is None or not session.is_admin():
            raise AuthorizationError("Administrator privileges required")
        return session.user_id

    def get_user(self, user_id: int) -> User:
        """Get a user by ID.

        Args:
            user_id: User ID.

        Returns:
            User instance.

        Raises:
            NotFoundError: If user not found.
        """
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User with ID {user_id} not found")
        return user

    def get_user_by_username(self, username: str) -> User:
        """Get a user by username.

        Args:
            username: Username.

        Returns:
            User instance.

        Raises:
            NotFoundError: If user not found.
        """
        user = self.user_repo.find_by_username(username)
        if user is None:
            raise NotFoundError(f"User '{username}' not found")
        return user

    def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
        role_id: int | None = None,
        search: str | None = None,
    ) -> list[User]:
        """List users with optional filters.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            is_active: Filter by active status.
            role_id: Filter by role.
            search: Search term.

        Returns:
            List of User instances.
        """
        return self.user_repo.find_all_with_roles(
            limit=limit, offset=offset, is_active=is_active, role_id=role_id, search=search
        )

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: User creation data.

        Returns:
            Created User instance.

        Raises:
            AuthorizationError: If not admin.
            ValidationError: If validation fails.
            DuplicateError: If username/email exists.
        """
        admin_id = self._require_admin()

        # Validate inputs
        validate_username(user_data.username)
        validate_email(user_data.email)
        validate_full_name(user_data.full_name)

        # Validate role exists
        role = self.role_repo.find_by_id(user_data.role_id)
        if role is None:
            raise ValidationError(f"Invalid role ID: {user_data.role_id}")

        # Hash password
        password_hash = self.security.hash_password(user_data.password)

        # Create user
        user_id = self.user_repo.create(user_data, password_hash)

        # Log action
        self.audit_repo.log_action(
            user_id=admin_id,
            action=AuditAction.USER_CREATED,
            entity_type="user",
            entity_id=user_id,
            new_value={
                "username": user_data.username,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "role_id": user_data.role_id,
            },
        )

        return self.get_user(user_id)

    def update_user(self, user_id: int, update_data: UserUpdate) -> User:
        """Update a user.

        Args:
            user_id: User ID to update.
            update_data: Fields to update.

        Returns:
            Updated User instance.

        Raises:
            AuthorizationError: If not admin.
            NotFoundError: If user not found.
            ValidationError: If validation fails.
        """
        admin_id = self._require_admin()

        # Get existing user
        existing = self.get_user(user_id)
        old_value = existing.to_dict()

        # Validate inputs if provided
        if update_data.email is not None:
            validate_email(update_data.email)

        if update_data.full_name is not None:
            validate_full_name(update_data.full_name)

        if update_data.role_id is not None:
            role = self.role_repo.find_by_id(update_data.role_id)
            if role is None:
                raise ValidationError(f"Invalid role ID: {update_data.role_id}")

        # Update user
        self.user_repo.update(user_id, update_data)

        # Get updated user
        updated = self.get_user(user_id)

        # Log action
        self.audit_repo.log_action(
            user_id=admin_id,
            action=AuditAction.USER_UPDATED,
            entity_type="user",
            entity_id=user_id,
            old_value=old_value,
            new_value=updated.to_dict(),
        )

        return updated

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account.

        Args:
            user_id: User ID.

        Returns:
            True if deactivated.

        Raises:
            AuthorizationError: If not admin.
            NotFoundError: If user not found.
        """
        admin_id = self._require_admin()

        # Prevent self-deactivation
        if admin_id == user_id:
            raise ValidationError("Cannot deactivate your own account")

        # Verify user exists
        self.get_user(user_id)

        # Deactivate
        success = self.user_repo.deactivate(user_id)

        if success:
            self.audit_repo.log_action(
                user_id=admin_id,
                action=AuditAction.USER_DEACTIVATED,
                entity_type="user",
                entity_id=user_id,
                new_value={"is_active": False},
            )

        return success

    def activate_user(self, user_id: int) -> bool:
        """Activate a user account.

        Args:
            user_id: User ID.

        Returns:
            True if activated.

        Raises:
            AuthorizationError: If not admin.
            NotFoundError: If user not found.
        """
        admin_id = self._require_admin()

        # Verify user exists
        self.get_user(user_id)

        # Activate
        success = self.user_repo.activate(user_id)

        if success:
            self.audit_repo.log_action(
                user_id=admin_id,
                action=AuditAction.USER_ACTIVATED,
                entity_type="user",
                entity_id=user_id,
                new_value={"is_active": True},
            )

        return success

    def assign_role(self, user_id: int, role_id: int) -> User:
        """Assign a role to a user.

        Args:
            user_id: User ID.
            role_id: Role ID to assign.

        Returns:
            Updated User instance.

        Raises:
            AuthorizationError: If not admin.
            NotFoundError: If user or role not found.
        """
        admin_id = self._require_admin()

        # Verify role exists
        role = self.role_repo.find_by_id(role_id)
        if role is None:
            raise NotFoundError(f"Role with ID {role_id} not found")

        # Get existing user
        user = self.get_user(user_id)
        old_role_id = user.role_id

        # Update role
        update_data = UserUpdate(role_id=role_id)
        self.user_repo.update(user_id, update_data)

        # Log action
        self.audit_repo.log_action(
            user_id=admin_id,
            action=AuditAction.ROLE_ASSIGNED,
            entity_type="user",
            entity_id=user_id,
            old_value={"role_id": old_role_id},
            new_value={"role_id": role_id},
        )

        return self.get_user(user_id)

    def get_roles(self) -> list[Role]:
        """Get all available roles.

        Returns:
            List of Role instances.
        """
        return self.role_repo.get_all()

    def get_role_by_name(self, role_name: str) -> Role | None:
        """Get a role by name.

        Args:
            role_name: Role name.

        Returns:
            Role instance or None.
        """
        return self.role_repo.find_by_name(role_name)

    def count_users(self, is_active: bool | None = None) -> int:
        """Count users.

        Args:
            is_active: Optional filter by active status.

        Returns:
            User count.
        """
        if is_active is None:
            return self.user_repo.count()
        return self.user_repo.count("is_active = %s", (is_active,))

    def count_users_by_role(self, role_id: int) -> int:
        """Count users with a specific role.

        Args:
            role_id: Role ID.

        Returns:
            User count.
        """
        return self.user_repo.count_by_role(role_id)

    def get_students(self, limit: int = 100, search: str | None = None) -> list[User]:
        """Get all student users.

        Args:
            limit: Maximum records.
            search: Optional search term.

        Returns:
            List of student User instances.
        """
        student_role = self.role_repo.find_by_name("student")
        if student_role is None:
            return []

        return self.user_repo.find_all_with_roles(search=search)

    def delete_user(self, user_id: int, force: bool = False) -> bool:
        """Delete a user.

        Args:
            user_id: User ID.
            force: If True, delete/reassign associated data.

        Returns:
            True if deleted.

        Raises:
            AuthorizationError: If not admin.
            ValidationError: If trying to delete self or if deps exist without force.
            NotFoundError: If user not found.
        """
        admin_id = self._require_admin()

        # Prevent self-deletion
        if admin_id == user_id:
            raise ValidationError("Cannot delete your own account")

        # Verify user exists
        user = self.get_user(user_id)
        user_data = user.to_dict()

        # Check for dependencies (transactions & fines)
        from locas.repositories.fine_repository import FineRepository
        from locas.repositories.transaction_repository import TransactionRepository

        trans_repo = TransactionRepository(self.user_repo.db)
        fine_repo = FineRepository(self.user_repo.db)

        # Check active transactions (borrower)
        borrowing_count = trans_repo.count("user_id = %s", (user_id,))
        # Check issued transactions (librarian)
        issued_count = trans_repo.count("issued_by = %s", (user_id,))
        # Check fines
        fine_count = fine_repo.count("user_id = %s", (user_id,))

        has_deps = borrowing_count > 0 or issued_count > 0 or fine_count > 0

        if has_deps:
            if not force:
                msg = "Cannot delete user with associated data:\n"
                if borrowing_count > 0:
                    msg += f"- {borrowing_count} transactions (borrower)\n"
                if issued_count > 0:
                    msg += f"- {issued_count} transactions (issuer)\n"
                if fine_count > 0:
                    msg += f"- {fine_count} fines\n"
                msg += "\nUse Force Delete to wipe/reassign this data."
                raise ValidationError(msg)

            # FORCE DELETE LOGIC
            # 1. Delete fines
            fine_repo.delete_by_user(user_id)

            # 2. Delete borrowing history (wipes student history)
            trans_repo.delete_by_user(user_id)

            # 3. Reassign issued transactions (preserves librarian actions under admin)
            if issued_count > 0:
                trans_repo.reassign_issuer(user_id, admin_id)

        # Safe to delete: First clear audit logs
        self.audit_repo.delete_by_user(user_id)

        # Delete user
        success = self.user_repo.delete(user_id)

        if success:
            # Prepare data for JSON serialization (convert datetimes)
            from datetime import datetime

            serializable_data = {}
            for k, v in user_data.items():
                if isinstance(v, datetime):
                    serializable_data[k] = v.isoformat()
                else:
                    serializable_data[k] = v

            self.audit_repo.log_action(
                user_id=admin_id,
                action=AuditAction.USER_DELETED,
                entity_type="user",
                entity_id=user_id,
                old_value=serializable_data,
            )

        return success
