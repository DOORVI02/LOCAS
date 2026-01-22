"""Base repository with common database operations."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from locas.core.database import DatabaseManager

T = TypeVar("T")


class BaseRepository[T](ABC):
    """Abstract base repository implementing common CRUD operations.

    Provides a template for entity-specific repositories with
    reusable query building and execution methods.

    Attributes:
        db: Database manager instance.
        table_name: Name of the database table.
        primary_key: Name of the primary key column.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize repository with database manager.

        Args:
            db: Database manager for executing queries.
        """
        self.db = db

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Get the table name for this repository."""
        pass

    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Get the primary key column name."""
        pass

    @abstractmethod
    def _from_row(self, row: dict[str, Any]) -> T:
        """Convert a database row to an entity instance.

        Args:
            row: Dictionary representing a database row.

        Returns:
            Entity instance.
        """
        pass

    def find_by_id(self, entity_id: int) -> T | None:
        """Find an entity by its primary key.

        Args:
            entity_id: Primary key value.

        Returns:
            Entity instance or None if not found.
        """
        query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = %s"
        row = self.db.execute_one(query, (entity_id,))

        if row is None:
            return None

        return self._from_row(row)

    def find_all(
        self, limit: int = 100, offset: int = 0, order_by: str | None = None, order_dir: str = "ASC"
    ) -> list[T]:
        """Find all entities with pagination.

        Args:
            limit: Maximum number of records.
            offset: Number of records to skip.
            order_by: Column to order by.
            order_dir: Order direction (ASC or DESC).

        Returns:
            List of entity instances.
        """
        order_clause = ""
        if order_by:
            order_dir = order_dir.upper()
            if order_dir not in ("ASC", "DESC"):
                order_dir = "ASC"
            order_clause = f" ORDER BY {order_by} {order_dir}"

        query = f"SELECT * FROM {self.table_name}{order_clause} LIMIT %s OFFSET %s"
        rows = self.db.execute(query, (limit, offset))

        return [self._from_row(row) for row in rows]

    def count(self, where: str | None = None, params: tuple | None = None) -> int:
        """Count entities matching criteria.

        Args:
            where: Optional WHERE clause (without the WHERE keyword).
            params: Query parameters for the WHERE clause.

        Returns:
            Count of matching entities.
        """
        query = f"SELECT COUNT(*) as cnt FROM {self.table_name}"
        if where:
            query += f" WHERE {where}"

        result = self.db.execute_one(query, params)
        return result["cnt"] if result else 0

    def exists(self, entity_id: int) -> bool:
        """Check if an entity exists by ID.

        Args:
            entity_id: Primary key value.

        Returns:
            True if entity exists.
        """
        query = f"SELECT 1 FROM {self.table_name} WHERE {self.primary_key} = %s LIMIT 1"
        result = self.db.execute_one(query, (entity_id,))
        return result is not None

    def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID.

        Args:
            entity_id: Primary key value.

        Returns:
            True if entity was deleted.
        """
        query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s"
        affected = self.db.execute_update(query, (entity_id,))
        return affected > 0

    def _build_insert_query(self, data: dict[str, Any]) -> tuple[str, tuple]:
        """Build an INSERT query from a dictionary.

        Args:
            data: Dictionary of column names to values.

        Returns:
            Tuple of (query string, parameter tuple).
        """
        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_list = ", ".join(columns)

        query = f"INSERT INTO {self.table_name} ({column_list}) VALUES ({placeholders})"
        params = tuple(data.values())

        return query, params

    def _build_update_query(self, entity_id: int, data: dict[str, Any]) -> tuple[str, tuple]:
        """Build an UPDATE query from a dictionary.

        Args:
            entity_id: Primary key of entity to update.
            data: Dictionary of column names to new values.

        Returns:
            Tuple of (query string, parameter tuple).
        """
        set_clauses = [f"{col} = %s" for col in data.keys()]
        set_clause = ", ".join(set_clauses)

        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.primary_key} = %s"
        params = tuple(data.values()) + (entity_id,)

        return query, params
