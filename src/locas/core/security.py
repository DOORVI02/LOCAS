"""Security utilities for LOCAS."""

import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import bcrypt

from locas.config import Config
from locas.core.exceptions import ValidationError


class SecurityManager:
    """Handles password hashing, validation, and session management.
    
    Uses bcrypt for password hashing with configurable rounds.
    
    Attributes:
        config: Application configuration instance.
    """
    
    BCRYPT_ROUNDS = 12
    TOKEN_LENGTH = 32
    
    def __init__(self, config: Config) -> None:
        """Initialize SecurityManager.
        
        Args:
            config: Application configuration.
        """
        self.config = config
    
    def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password using bcrypt.
        
        Args:
            plain_password: The plain text password to hash.
            
        Returns:
            Bcrypt hash string.
            
        Raises:
            ValidationError: If password doesn't meet requirements.
        """
        self.validate_password_strength(plain_password)
        
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a bcrypt hash.
        
        Args:
            plain_password: The plain text password to verify.
            hashed_password: The stored bcrypt hash.
            
        Returns:
            True if password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception:
            return False
    
    def validate_password_strength(self, password: str) -> None:
        """Validate password meets strength requirements.
        
        Requirements:
        - Minimum length (from config)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        
        Args:
            password: Password to validate.
            
        Raises:
            ValidationError: If password doesn't meet requirements.
        """
        errors: list[str] = []
        
        if len(password) < self.config.password_min_length:
            errors.append(
                f"Password must be at least {self.config.password_min_length} characters"
            )
        
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def generate_temporary_password(self, length: int = 12) -> str:
        """Generate a secure temporary password.
        
        Args:
            length: Length of the password (default 12).
            
        Returns:
            Random password meeting strength requirements.
        """
        # Ensure at least one of each required character type
        password_chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
        ]
        
        # Fill remaining length with random characters
        alphabet = string.ascii_letters + string.digits
        remaining = length - len(password_chars)
        password_chars.extend(secrets.choice(alphabet) for _ in range(remaining))
        
        # Shuffle to randomize position of required characters
        secrets.SystemRandom().shuffle(password_chars)
        
        return "".join(password_chars)
    
    def generate_session_token(self) -> str:
        """Generate a secure session token.
        
        Returns:
            Cryptographically secure random token.
        """
        return secrets.token_urlsafe(self.TOKEN_LENGTH)


class Session:
    """Represents an active user session.
    
    Tracks the authenticated user and session expiration.
    
    Attributes:
        user_id: ID of the authenticated user.
        username: Username of the authenticated user.
        role_id: Role ID of the authenticated user.
        role_name: Role name of the authenticated user.
        token: Unique session token.
        created_at: Session creation timestamp.
        expires_at: Session expiration timestamp.
    """
    
    def __init__(
        self,
        user_id: int,
        username: str,
        role_id: int,
        role_name: str,
        full_name: str,
        timeout_minutes: int = 30
    ) -> None:
        """Initialize a new session.
        
        Args:
            user_id: Authenticated user's ID.
            username: Authenticated user's username.
            role_id: User's role ID.
            role_name: User's role name.
            full_name: User's full name.
            timeout_minutes: Session timeout in minutes.
        """
        self.user_id = user_id
        self.username = username
        self.role_id = role_id
        self.role_name = role_name
        self.full_name = full_name
        self.token = secrets.token_urlsafe(32)
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=timeout_minutes)
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired.
        
        Returns:
            True if session is expired, False otherwise.
        """
        return datetime.now() > self.expires_at
    
    def refresh(self, timeout_minutes: int = 30) -> None:
        """Refresh session expiration.
        
        Args:
            timeout_minutes: New timeout period in minutes.
        """
        self.expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role_name.lower() == "admin"
    
    def is_librarian(self) -> bool:
        """Check if user is a librarian."""
        return self.role_name.lower() == "librarian"
    
    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role_name.lower() == "student"
    
    def has_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles.
        
        Args:
            roles: Role names to check.
            
        Returns:
            True if user has any of the roles.
        """
        return self.role_name.lower() in [r.lower() for r in roles]


class SessionManager:
    """Manages active user sessions.
    
    Thread-safe session storage for the desktop application.
    Only one session is active at a time (single-user desktop app).
    
    Attributes:
        current_session: The currently active session, if any.
    """
    
    def __init__(self, config: Config) -> None:
        """Initialize SessionManager.
        
        Args:
            config: Application configuration.
        """
        self.config = config
        self._current_session: Optional[Session] = None
    
    @property
    def current_session(self) -> Optional[Session]:
        """Get the current active session.
        
        Returns:
            Active session if valid, None if expired or no session.
        """
        if self._current_session is not None and self._current_session.is_expired:
            self._current_session = None
        return self._current_session
    
    def create_session(
        self,
        user_id: int,
        username: str,
        role_id: int,
        role_name: str,
        full_name: str
    ) -> Session:
        """Create a new session for an authenticated user.
        
        Args:
            user_id: User's ID.
            username: User's username.
            role_id: User's role ID.
            role_name: User's role name.
            full_name: User's full name.
            
        Returns:
            Newly created Session instance.
        """
        self._current_session = Session(
            user_id=user_id,
            username=username,
            role_id=role_id,
            role_name=role_name,
            full_name=full_name,
            timeout_minutes=self.config.session_timeout_minutes
        )
        return self._current_session
    
    def end_session(self) -> None:
        """End the current session (logout)."""
        self._current_session = None
    
    def refresh_session(self) -> None:
        """Refresh the current session's expiration."""
        if self._current_session is not None:
            self._current_session.refresh(self.config.session_timeout_minutes)
    
    def is_authenticated(self) -> bool:
        """Check if there's an active, non-expired session.
        
        Returns:
            True if authenticated, False otherwise.
        """
        return self.current_session is not None
    
    def require_role(self, *roles: str) -> bool:
        """Check if current session has required role.
        
        Args:
            roles: Allowed role names.
            
        Returns:
            True if authenticated with required role.
        """
        session = self.current_session
        if session is None:
            return False
        return session.has_role(*roles)
