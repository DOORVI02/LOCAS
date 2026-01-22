"""Login view for LOCAS."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SecurityManager, SessionManager
from locas.core.exceptions import AuthenticationError
from locas.repositories.user_repository import UserRepository
from locas.core.constants import AuditAction
from locas.repositories.audit_repository import AuditRepository


class LoginView(QWidget):
    """Login screen for user authentication.
    
    Emits login_successful signal when authentication succeeds.
    
    Signals:
        login_successful: Emitted after successful authentication.
    """
    
    login_successful = pyqtSignal()
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize login view.
        
        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.security_manager = SecurityManager(config)
        self.user_repo = UserRepository(db_manager)
        self.audit_repo = AuditRepository(db_manager)
        
        self._failed_attempts = 0
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Center the login container
        main_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        
        # Login container
        container = QFrame()
        container.setObjectName("loginContainer")
        container.setFixedWidth(400)
        container.setStyleSheet("""
            QFrame#loginContainer {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)
        
        # App title
        title_label = QLabel(self.config.app_name)
        title_label.setObjectName("appTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #1976D2;
        """)
        container_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Library for College Administration System")
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #757575;
            margin-bottom: 20px;
        """)
        container_layout.addWidget(subtitle_label)
        
        # Username field
        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(45)
        container_layout.addWidget(self.username_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(45)
        container_layout.addWidget(self.password_input)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #D32F2F; font-size: 13px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("loginButton")
        self.login_button.setMinimumHeight(45)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        container_layout.addWidget(self.login_button)
        
        # Center container horizontally
        container_row = QHBoxLayout()
        container_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        container_row.addWidget(container)
        container_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        main_layout.addLayout(container_row)
        
        main_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        
        # Version label at bottom
        version_label = QLabel(f"Version {self.config.app_version}")
        version_label.setStyleSheet("color: #9E9E9E; font-size: 12px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(version_label)
    
    def _setup_connections(self) -> None:
        """Connect signals to slots."""
        self.login_button.clicked.connect(self._handle_login)
        self.password_input.returnPressed.connect(self._handle_login)
        self.username_input.returnPressed.connect(
            lambda: self.password_input.setFocus()
        )
    
    def _handle_login(self) -> None:
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Validate inputs
        if not username:
            self._show_error("Please enter your username")
            self.username_input.setFocus()
            return
        
        if not password:
            self._show_error("Please enter your password")
            self.password_input.setFocus()
            return
        
        # Check attempt limit
        if self._failed_attempts >= self.config.login_attempt_limit:
            self._show_error("Too many failed attempts. Please try again later.")
            return
        
        # Attempt authentication
        try:
            user_data = self.user_repo.find_with_password(username)
            
            if user_data is None:
                raise AuthenticationError("Invalid username or password")
            
            if not user_data.get("is_active", False):
                raise AuthenticationError("Account is deactivated. Contact admin.")
            
            if not self.security_manager.verify_password(
                password, 
                user_data["password_hash"]
            ):
                raise AuthenticationError("Invalid username or password")
            
            # Authentication successful
            self._failed_attempts = 0
            self.error_label.hide()
            
            # Create session
            self.session_manager.create_session(
                user_id=user_data["user_id"],
                username=user_data["username"],
                role_id=user_data["role_id"],
                role_name=user_data["role_name"],
                full_name=user_data["full_name"]
            )
            
            # Update last login
            self.user_repo.update_last_login(user_data["user_id"])
            
            # Audit log
            self.audit_repo.log_action(
                user_id=user_data["user_id"],
                action=AuditAction.LOGIN,
                entity_type="user",
                entity_id=user_data["user_id"]
            )
            
            # Emit success signal
            self.login_successful.emit()
            
        except AuthenticationError as e:
            self._failed_attempts += 1
            self._show_error(str(e))
            self.password_input.clear()
            self.password_input.setFocus()
            
            # Log failed attempt if user exists
            if user_data is not None:
                try:
                    self.audit_repo.log_action(
                        user_id=user_data["user_id"],
                        action=AuditAction.LOGIN_FAILED,
                        entity_type="user",
                        entity_id=user_data["user_id"]
                    )
                except Exception:
                    pass  # Don't fail on audit log error
    
    def _show_error(self, message: str) -> None:
        """Display an error message.
        
        Args:
            message: Error message to display.
        """
        self.error_label.setText(message)
        self.error_label.show()
    
    def clear_form(self) -> None:
        """Clear the login form."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self._failed_attempts = 0
        self.username_input.setFocus()
