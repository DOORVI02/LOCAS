"""Database Connection Management for LOCAS."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector.cursor import MySQLCursor

from locas.config import Config
from locas.core.exceptions import DatabaseError


class DatabaseManager:
    """Manages MySQL database connections with connection pooling.
    
    Provides thread-safe connection pooling and transaction management
    for the LOCAS application.
    
    Attributes:
        config: Application configuration instance.
        pool: MySQL connection pool instance.
    """
    
    POOL_NAME = "locas_pool"
    POOL_SIZE = 5
    
    def __init__(self, config: Config) -> None:
        """Initialize DatabaseManager.
        
        Args:
            config: Application configuration with database settings.
        """
        self.config = config
        self._pool: Optional[MySQLConnectionPool] = None
    
    def initialize(self) -> None:
        """Initialize the connection pool.
        
        Raises:
            DatabaseError: If connection pool creation fails.
        """
        try:
            pool_config = {
                **self.config.db_connection_string,
                "pool_name": self.POOL_NAME,
                "pool_size": self.POOL_SIZE,
                "pool_reset_session": True,
            }
            self._pool = MySQLConnectionPool(**pool_config)
        except MySQLError as e:
            raise DatabaseError(f"Failed to create connection pool: {e}") from e
    
    def get_connection(self) -> mysql.connector.MySQLConnection:
        """Get a connection from the pool.
        
        Returns:
            A MySQL connection from the pool.
            
        Raises:
            DatabaseError: If no pool is initialized or connection fails.
        """
        if self._pool is None:
            raise DatabaseError("Database pool not initialized. Call initialize() first.")
        
        try:
            return self._pool.get_connection()
        except MySQLError as e:
            raise DatabaseError(f"Failed to get connection from pool: {e}") from e
    
    @contextmanager
    def connection(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        """Context manager for database connections.
        
        Automatically returns connection to pool after use.
        
        Yields:
            MySQL connection instance.
            
        Example:
            with db_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def cursor(
        self, 
        dictionary: bool = True,
        buffered: bool = True
    ) -> Generator[MySQLCursor, None, None]:
        """Context manager for database cursors.
        
        Automatically handles connection and cursor lifecycle.
        Does NOT auto-commit; caller must commit explicitly.
        
        Args:
            dictionary: If True, return rows as dictionaries.
            buffered: If True, buffer all results immediately.
            
        Yields:
            MySQL cursor instance.
            
        Example:
            with db_manager.cursor() as cursor:
                cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
                book = cursor.fetchone()
        """
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=dictionary, buffered=buffered)
            try:
                yield cursor
            finally:
                cursor.close()
    
    @contextmanager
    def transaction(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        """Context manager for database transactions.
        
        Automatically commits on success or rolls back on exception.
        
        Yields:
            MySQL connection with active transaction.
            
        Example:
            with db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO books ...")
                cursor.execute("INSERT INTO book_copies ...")
                # Auto-commits if no exception
        """
        with self.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
        commit: bool = False
    ) -> list[dict[str, Any]]:
        """Execute a query and return results.
        
        Args:
            query: SQL query string with %s placeholders.
            params: Optional tuple of query parameters.
            commit: If True, commit after execution.
            
        Returns:
            List of result rows as dictionaries.
            
        Raises:
            DatabaseError: If query execution fails.
        """
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=True, buffered=True)
            try:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                
                if commit:
                    conn.commit()
                
                return results
            except MySQLError as e:
                conn.rollback()
                raise DatabaseError(f"Query execution failed: {e}") from e
            finally:
                cursor.close()
    
    def execute_one(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> Optional[dict[str, Any]]:
        """Execute a query and return a single result.
        
        Args:
            query: SQL query string.
            params: Optional query parameters.
            
        Returns:
            Single row as dictionary, or None if no results.
        """
        results = self.execute(query, params)
        return results[0] if results else None
    
    def execute_insert(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> int:
        """Execute an INSERT query and return the last inserted ID.
        
        Args:
            query: INSERT SQL query.
            params: Query parameters.
            
        Returns:
            Last inserted row ID.
            
        Raises:
            DatabaseError: If insertion fails.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.lastrowid
            except MySQLError as e:
                conn.rollback()
                raise DatabaseError(f"Insert failed: {e}") from e
            finally:
                cursor.close()
    
    def execute_update(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> int:
        """Execute an UPDATE/DELETE query and return affected row count.
        
        Args:
            query: UPDATE or DELETE SQL query.
            params: Query parameters.
            
        Returns:
            Number of affected rows.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
            except MySQLError as e:
                conn.rollback()
                raise DatabaseError(f"Update failed: {e}") from e
            finally:
                cursor.close()
    
    def test_connection(self) -> bool:
        """Test if database connection is working.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with self.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def close(self) -> None:
        """Close all connections in the pool.
        
        Note: MySQLConnectionPool doesn't have a close method,
        connections are returned to pool automatically.
        """
        self._pool = None
