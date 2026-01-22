"""User repository for database operations."""

from typing import Any

from locas.core.exceptions import DuplicateError
from locas.models.user import Role, User, UserCreate, UserUpdate
from locas.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""

    @property
    def table_name(self) -> str:
        return "users"

    @property
    def primary_key(self) -> str:
        return "user_id"

    def _from_row(self, row: dict[str, Any]) -> User:
        return User.from_dict(row)

    def find_by_id(self, user_id: int) -> User | None:
        """Find user by ID with role information."""
        query = """
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.user_id = %s
        """
        row = self.db.execute_one(query, (user_id,))
        return self._from_row(row) if row else None

    def find_by_username(self, username: str) -> User | None:
        """Find a user by username.

        Args:
            username: Username to search for.

        Returns:
            User instance or None.
        """
        query = """
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s
        """
        row = self.db.execute_one(query, (username,))
        return self._from_row(row) if row else None

    def find_by_email(self, email: str) -> User | None:
        """Find a user by email address.

        Args:
            email: Email to search for.

        Returns:
            User instance or None.
        """
        query = """
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.email = %s
        """
        row = self.db.execute_one(query, (email,))
        return self._from_row(row) if row else None

    def find_with_password(self, username: str) -> dict[str, Any] | None:
        """Find user with password hash for authentication.

        Args:
            username: Username to search for.

        Returns:
            Dictionary with user data including password_hash.
        """
        query = """
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s
        """
        return self.db.execute_one(query, (username,))

    def find_all_with_roles(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
        role_id: int | None = None,
        search: str | None = None,
    ) -> list[User]:
        """Find all users with role information and filters.

        Args:
            limit: Maximum records.
            offset: Records to skip.
            is_active: Filter by active status.
            role_id: Filter by role.
            search: Search in username, email, full_name.

        Returns:
            List of User instances.
        """
        conditions = []
        params: list[Any] = []

        if is_active is not None:
            conditions.append("u.is_active = %s")
            params.append(is_active)

        if role_id is not None:
            conditions.append("u.role_id = %s")
            params.append(role_id)

        if search:
            conditions.append("(u.username LIKE %s OR u.email LIKE %s OR u.full_name LIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = self.db.execute(query, tuple(params))
        return [self._from_row(row) for row in rows]

    def create(self, user_data: UserCreate, password_hash: str) -> int:
        """Create a new user.

        Args:
            user_data: User creation DTO.
            password_hash: Bcrypt hashed password.

        Returns:
            New user's ID.

        Raises:
            DuplicateError: If username or email already exists.
        """
        # Check for duplicates
        if self.find_by_username(user_data.username):
            raise DuplicateError(f"Username '{user_data.username}' already exists")

        if self.find_by_email(user_data.email):
            raise DuplicateError(f"Email '{user_data.email}' already exists")

        data = {
            "username": user_data.username,
            "password_hash": password_hash,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "role_id": user_data.role_id,
        }

        query, params = self._build_insert_query(data)
        return self.db.execute_insert(query, params)

    def update(self, user_id: int, update_data: UserUpdate) -> bool:
        """Update a user.

        Args:
            user_id: User ID to update.
            update_data: Update DTO with fields to change.

        Returns:
            True if updated.
        """
        data = update_data.to_update_dict()
        if not data:
            return False

        # Check for email duplicate if changing email
        if "email" in data:
            existing = self.find_by_email(data["email"])
            if existing and existing.user_id != user_id:
                raise DuplicateError(f"Email '{data['email']}' already exists")

        query, params = self._build_update_query(user_id, data)
        affected = self.db.execute_update(query, params)
        return affected > 0

    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update a user's password.

        Args:
            user_id: User ID.
            password_hash: New bcrypt hash.

        Returns:
            True if updated.
        """
        query = "UPDATE users SET password_hash = %s WHERE user_id = %s"
        affected = self.db.execute_update(query, (password_hash, user_id))
        return affected > 0

    def update_last_login(self, user_id: int) -> bool:
        """Update the last login timestamp.

        Args:
            user_id: User ID.

        Returns:
            True if updated.
        """
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s"
        affected = self.db.execute_update(query, (user_id,))
        return affected > 0

    def deactivate(self, user_id: int) -> bool:
        """Deactivate a user account.

        Args:
            user_id: User ID.

        Returns:
            True if updated.
        """
        query = "UPDATE users SET is_active = FALSE WHERE user_id = %s"
        affected = self.db.execute_update(query, (user_id,))
        return affected > 0

    def activate(self, user_id: int) -> bool:
        """Activate a user account.

        Args:
            user_id: User ID.

        Returns:
            True if updated.
        """
        query = "UPDATE users SET is_active = TRUE WHERE user_id = %s"
        affected = self.db.execute_update(query, (user_id,))
        return affected > 0

    def count_by_role(self, role_id: int) -> int:
        """Count users with a specific role.

        Args:
            role_id: Role ID.

        Returns:
            Count of users.
        """
        return self.count("role_id = %s", (role_id,))


class RoleRepository(BaseRepository[Role]):
    """Repository for Role entity operations."""

    @property
    def table_name(self) -> str:
        return "roles"

    @property
    def primary_key(self) -> str:
        return "role_id"

    def _from_row(self, row: dict[str, Any]) -> Role:
        return Role.from_dict(row)

    def find_by_name(self, role_name: str) -> Role | None:
        """Find a role by name.

        Args:
            role_name: Role name to search for.

        Returns:
            Role instance or None.
        """
        query = "SELECT * FROM roles WHERE role_name = %s"
        row = self.db.execute_one(query, (role_name,))
        return self._from_row(row) if row else None

    def get_all(self) -> list[Role]:
        """Get all roles.

        Returns:
            List of all Role instances.
        """
        query = "SELECT * FROM roles ORDER BY role_id"
        rows = self.db.execute(query)
        return [self._from_row(row) for row in rows]
