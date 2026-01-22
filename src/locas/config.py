"""Configuration Management for LOCAS."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration container.
    
    Loads configuration from environment variables with sensible defaults.
    """
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "locas_db"
    db_user: str = "root"
    db_password: str = ""
    
    # Application settings
    app_name: str = "LOCAS"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Library settings
    max_borrow_days: int = 14
    max_borrow_limit: int = 3
    fine_rate_per_day: float = 5.00
    max_fine_threshold: float = 100.00
    
    # Security settings
    password_min_length: int = 8
    login_attempt_limit: int = 5
    session_timeout_minutes: int = 30
    
    # Paths
    base_path: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load configuration from environment variables.
        
        Args:
            env_path: Optional path to .env file. Defaults to project root.
            
        Returns:
            Configured Config instance.
        """
        # Determine .env path
        if env_path is None:
            # Look for .env in project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / ".env"
        
        # Load .env file if it exists
        if env_path.exists():
            load_dotenv(env_path)
        
        def get_bool(key: str, default: bool) -> bool:
            value = os.getenv(key, str(default)).lower()
            return value in ("true", "1", "yes", "on")
        
        def get_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        def get_float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        return cls(
            # Database
            db_host=os.getenv("DB_HOST", "localhost"),
            db_port=get_int("DB_PORT", 3306),
            db_name=os.getenv("DB_NAME", "locas_db"),
            db_user=os.getenv("DB_USER", "root"),
            db_password=os.getenv("DB_PASSWORD", ""),
            
            # Application
            app_name=os.getenv("APP_NAME", "LOCAS"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            debug=get_bool("DEBUG", False),
            
            # Library settings
            max_borrow_days=get_int("MAX_BORROW_DAYS", 14),
            max_borrow_limit=get_int("MAX_BORROW_LIMIT", 3),
            fine_rate_per_day=get_float("FINE_RATE_PER_DAY", 5.00),
            max_fine_threshold=get_float("MAX_FINE_THRESHOLD", 100.00),
            
            # Security
            password_min_length=get_int("PASSWORD_MIN_LENGTH", 8),
            login_attempt_limit=get_int("LOGIN_ATTEMPT_LIMIT", 5),
            session_timeout_minutes=get_int("SESSION_TIMEOUT_MINUTES", 30),
            
            # Paths
            base_path=Path(__file__).parent.parent.parent,
        )
    
    @property
    def db_connection_string(self) -> dict:
        """Get database connection parameters as a dictionary.
        
        Returns:
            Dictionary with MySQL connection parameters.
        """
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "autocommit": False,
        }
