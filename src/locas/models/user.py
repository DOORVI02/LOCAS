"""User data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class User:
    """Represents a user in the system.
    
    Attributes:
        user_id: Unique identifier.
        username: Login username.
        email: User's email address.
        full_name: User's full name.
        role_id: Foreign key to roles table.
        role_name: Name of the user's role (from join).
        is_active: Whether the user account is active.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
        last_login: Last login timestamp.
    """
    
    user_id: int
    username: str
    email: str
    full_name: str
    role_id: int
    is_active: bool = True
    role_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Create User instance from dictionary.
        
        Args:
            data: Dictionary with user data (typically from DB query).
            
        Returns:
            User instance.
        """
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            full_name=data["full_name"],
            role_id=data["role_id"],
            is_active=data.get("is_active", True),
            role_name=data.get("role_name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login=data.get("last_login"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert User to dictionary.
        
        Returns:
            Dictionary representation (excludes None values).
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role_id": self.role_id,
            "is_active": self.is_active,
            "role_name": self.role_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
        }


@dataclass
class UserCreate:
    """DTO for creating a new user.
    
    Attributes:
        username: Login username.
        password: Plain text password (will be hashed).
        email: User's email address.
        full_name: User's full name.
        role_id: Role to assign.
    """
    
    username: str
    password: str
    email: str
    full_name: str
    role_id: int


@dataclass
class UserUpdate:
    """DTO for updating an existing user.
    
    All fields are optional - only non-None values will be updated.
    
    Attributes:
        email: New email address.
        full_name: New full name.
        role_id: New role ID.
        is_active: New active status.
    """
    
    email: Optional[str] = None
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    def to_update_dict(self) -> dict[str, Any]:
        """Get dictionary of non-None fields for update.
        
        Returns:
            Dictionary with only the fields to update.
        """
        result = {}
        if self.email is not None:
            result["email"] = self.email
        if self.full_name is not None:
            result["full_name"] = self.full_name
        if self.role_id is not None:
            result["role_id"] = self.role_id
        if self.is_active is not None:
            result["is_active"] = self.is_active
        return result


@dataclass
class Role:
    """Represents a user role.
    
    Attributes:
        role_id: Unique identifier.
        role_name: Name of the role.
        description: Role description.
        created_at: Creation timestamp.
    """
    
    role_id: int
    role_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        """Create Role from dictionary."""
        return cls(
            role_id=data["role_id"],
            role_name=data["role_name"],
            description=data.get("description"),
            created_at=data.get("created_at"),
        )
