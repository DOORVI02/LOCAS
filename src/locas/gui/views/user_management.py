"""User management view for LOCAS admin."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.exceptions import LOCASError
from locas.core.security import SessionManager
from locas.gui.widgets.data_table import DataTable
from locas.gui.widgets.form_dialog import FormDialog, FormField
from locas.models.user import User, UserCreate, UserUpdate
from locas.services.auth_service import AuthService
from locas.services.user_service import UserService
from locas.utils.formatters import format_date


class UserManagementView(QWidget):
    """User management view for administrators.

    Allows creating, editing, and managing system users.
    """

    data_changed = pyqtSignal()

    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize UserManagementView."""
        super().__init__(parent)

        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager

        self.user_service = UserService(config, db_manager, session_manager)
        self.auth_service = AuthService(config, db_manager, session_manager)

        self._selected_user: User | None = None

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("User Management")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        add_btn = QPushButton("+ Add User")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        add_btn.clicked.connect(self._add_user)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Toolbar
        toolbar = QHBoxLayout()

        # Search
        toolbar.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Username, name, or email...")
        self.search_input.setMaximumWidth(250)
        self.search_input.returnPressed.connect(self._search)
        toolbar.addWidget(self.search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search)
        toolbar.addWidget(search_btn)

        toolbar.addSpacing(20)

        # Role filter
        toolbar.addWidget(QLabel("Role:"))
        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "Admin", "Librarian", "Student"])
        self.role_filter.currentIndexChanged.connect(self._load_data)
        toolbar.addWidget(self.role_filter)

        # Status filter
        toolbar.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive"])
        self.status_filter.currentIndexChanged.connect(self._load_data)
        toolbar.addWidget(self.status_filter)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Main content
        content_layout = QHBoxLayout()

        # Users table
        def format_status(value, row):
            if row.get("is_active"):
                return "✓ Active"
            return "✗ Inactive"

        self.users_table = DataTable(
            [
                {"key": "username", "label": "Username", "width": 120},
                {"key": "full_name", "label": "Full Name", "stretch": True},
                {"key": "email", "label": "Email", "width": 200},
                {"key": "role_name", "label": "Role", "width": 100},
                {"key": "is_active", "label": "Status", "width": 100, "formatter": format_status},
                {"key": "created_at", "label": "Created", "width": 100},
            ]
        )
        self.users_table.row_selected.connect(self._on_user_selected)
        content_layout.addWidget(self.users_table, 2)

        # Details panel
        details_panel = QFrame()
        details_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        details_panel.setMinimumWidth(280)
        details_panel.setMaximumWidth(320)

        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(12)

        details_title = QLabel("User Details")
        details_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        details_layout.addWidget(details_title)

        self.user_details = QLabel("Select a user to view details")
        self.user_details.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                padding: 12px;
                border-radius: 4px;
            }
        """)
        self.user_details.setWordWrap(True)
        self.user_details.setMinimumHeight(150)
        details_layout.addWidget(self.user_details)

        # Action buttons
        self.edit_btn = QPushButton("✏️ Edit User")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit_user)
        details_layout.addWidget(self.edit_btn)

        self.toggle_btn = QPushButton("🔒 Toggle Status")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.clicked.connect(self._toggle_status)
        details_layout.addWidget(self.toggle_btn)

        self.reset_pwd_btn = QPushButton("🔑 Reset Password")
        self.reset_pwd_btn.setEnabled(False)
        self.reset_pwd_btn.clicked.connect(self._reset_password)
        details_layout.addWidget(self.reset_pwd_btn)

        self.delete_btn = QPushButton("🗑️ Delete User")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
            QPushButton:disabled {
                background-color: #EF9A9A;
            }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_user)
        details_layout.addWidget(self.delete_btn)

        details_layout.addStretch()

        # Stats
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("")
        stats_layout.addWidget(self.stats_label)
        details_layout.addWidget(stats_group)

        content_layout.addWidget(details_panel)

        layout.addLayout(content_layout, 1)

    def _load_data(self) -> None:
        """Load users data."""
        try:
            role_text = self.role_filter.currentText()
            role_id = None
            if role_text == "Admin":
                role_id = 1
            elif role_text == "Librarian":
                role_id = 2
            elif role_text == "Student":
                role_id = 3

            status_text = self.status_filter.currentText()
            is_active = None
            if status_text == "Active":
                is_active = True
            elif status_text == "Inactive":
                is_active = False

            users = self.user_service.list_users(role_id=role_id, is_active=is_active, limit=200)

            data = [u.to_dict() for u in users]
            self.users_table.set_data(data)

            # Update stats
            all_users = self.user_service.list_users(limit=500)
            active_count = sum(1 for u in all_users if u.is_active)

            role_counts = {}
            for u in all_users:
                role = u.role_name or "Unknown"
                role_counts[role] = role_counts.get(role, 0) + 1

            stats_parts = [f"Total: {len(all_users)}", f"Active: {active_count}"]
            for role, count in role_counts.items():
                stats_parts.append(f"{role.title()}: {count}")

            self.stats_label.setText("\n".join(stats_parts))

        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _search(self) -> None:
        """Search users."""
        query = self.search_input.text().strip()

        try:
            if query:
                users = self.user_service.list_users(search=query, limit=100)
            else:
                self._load_data()
                return

            data = [u.to_dict() for u in users]
            self.users_table.set_data(data)

        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_user_selected(self, row_data: dict) -> None:
        """Handle user selection."""
        user_id = row_data.get("user_id")
        if not user_id:
            return

        try:
            self._selected_user = self.user_service.get_user(user_id)

            details = f"""
            <b>Username:</b> {self._selected_user.username}<br>
            <b>Full Name:</b> {self._selected_user.full_name}<br>
            <b>Email:</b> {self._selected_user.email}<br>
            <b>Role:</b> {self._selected_user.role_name or "N/A"}<br>
            <b>Status:</b> {"Active" if self._selected_user.is_active else "Inactive"}<br>
            <b>Created:</b> {format_date(self._selected_user.created_at)}<br>
            """

            if self._selected_user.last_login:
                details += f"<b>Last Login:</b> {format_date(self._selected_user.last_login)}"
            else:
                details += "<b>Last Login:</b> Never"

            self.user_details.setText(details)

            # Enable buttons
            self.edit_btn.setEnabled(True)
            self.toggle_btn.setEnabled(True)
            self.reset_pwd_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

            # Update toggle button text
            if self._selected_user.is_active:
                self.toggle_btn.setText("🔒 Deactivate")
            else:
                self.toggle_btn.setText("🔓 Activate")

        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _add_user(self) -> None:
        """Add a new user."""
        dialog = FormDialog(
            title="Add New User",
            fields=[
                FormField("username", "Username", required=True),
                FormField("email", "Email", required=True),
                FormField("full_name", "Full Name", required=True),
                FormField("password", "Password", field_type="password", required=True),
                FormField(
                    "role_id",
                    "Role",
                    field_type="select",
                    required=True,
                    options=[("Admin", 1), ("Librarian", 2), ("Student", 3)],
                ),
            ],
            parent=self,
        )

        if dialog.exec():
            data = dialog.get_data()
            try:
                user_data = UserCreate(
                    username=data["username"],
                    email=data["email"],
                    full_name=data["full_name"],
                    password=data["password"],
                    role_id=data["role_id"],
                )

                user = self.user_service.create_user(user_data)

                QMessageBox.information(
                    self, "User Created", f"User '{user.username}' created successfully!"
                )

                self._load_data()
                self.data_changed.emit()

            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _edit_user(self) -> None:
        """Edit the selected user."""
        if not self._selected_user:
            return

        dialog = FormDialog(
            title=f"Edit User: {self._selected_user.username}",
            fields=[
                FormField("email", "Email", required=True, default=self._selected_user.email),
                FormField(
                    "full_name", "Full Name", required=True, default=self._selected_user.full_name
                ),
                FormField(
                    "role_id",
                    "Role",
                    field_type="select",
                    required=True,
                    options=[("Admin", 1), ("Librarian", 2), ("Student", 3)],
                    default=self._selected_user.role_id,
                ),
            ],
            parent=self,
        )

        if dialog.exec():
            data = dialog.get_data()
            try:
                update_data = UserUpdate(
                    email=data["email"], full_name=data["full_name"], role_id=data["role_id"]
                )

                self.user_service.update_user(self._selected_user.user_id, update_data)

                QMessageBox.information(self, "Success", "User updated successfully!")

                self._load_data()
                self.data_changed.emit()
                self._reset_selection()

            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _toggle_status(self) -> None:
        """Toggle user active status."""
        if not self._selected_user:
            return

        action = "deactivate" if self._selected_user.is_active else "activate"

        confirm = QMessageBox.question(
            self,
            f"Confirm {action.title()}",
            f"Are you sure you want to {action} user '{self._selected_user.username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            if self._selected_user.is_active:
                self.user_service.deactivate_user(self._selected_user.user_id)
            else:
                self.user_service.activate_user(self._selected_user.user_id)

            QMessageBox.information(self, "Success", f"User {action}d successfully!")

            self._load_data()
            self.data_changed.emit()
            self._reset_selection()

        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _reset_password(self) -> None:
        """Reset user password."""
        if not self._selected_user:
            return

        dialog = FormDialog(
            title=f"Reset Password: {self._selected_user.username}",
            fields=[
                FormField("password", "New Password", field_type="password", required=True),
                FormField("confirm", "Confirm Password", field_type="password", required=True),
            ],
            parent=self,
        )

        if dialog.exec():
            data = dialog.get_data()

            if data["password"] != data["confirm"]:
                QMessageBox.warning(self, "Error", "Passwords do not match!")
                return

            try:
                self.auth_service.reset_password(
                    admin_user_id=self.session_manager.current_session.user_id,
                    target_user_id=self._selected_user.user_id,
                    new_password=data["password"],
                )

                QMessageBox.information(
                    self,
                    "Success",
                    f"Password reset for '{self._selected_user.username}' successfully!",
                )

            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_user(self) -> None:
        """Delete the selected user."""
        if not self._selected_user:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to PERMANENTLY delete user '{self._selected_user.username}'?\n\n"
            "This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.user_service.delete_user(self._selected_user.user_id)

            QMessageBox.information(
                self, "Success", f"User '{self._selected_user.username}' deleted successfully!"
            )

            self._load_data()
            self.data_changed.emit()
            self._reset_selection()

        except LOCASError as e:
            # Check if this is a dependency error that allows force delete
            if "with associated data" in str(e):
                force_confirm = QMessageBox.warning(
                    self,
                    "Force Delete Required",
                    f"{str(e)}\n\nDo you want to FORCE DELETE this user?\n"
                    "WARNING: This will permanently wipe their transaction history and fines!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if force_confirm == QMessageBox.StandardButton.Yes:
                    try:
                        self.user_service.delete_user(self._selected_user.user_id, force=True)
                        QMessageBox.information(self, "Success", "User force deleted successfully!")
                        self._load_data()
                        self.data_changed.emit()
                        self._reset_selection()
                    except Exception as force_err:
                        QMessageBox.critical(self, "Error", f"Force delete failed: {force_err}")
            else:
                QMessageBox.warning(self, "Error", str(e))

    def _reset_selection(self) -> None:
        """Reset selection."""
        self._selected_user = None
        self.user_details.setText("Select a user to view details")
        self.edit_btn.setEnabled(False)
        self.toggle_btn.setEnabled(False)
        self.reset_pwd_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.toggle_btn.setText("🔒 Toggle Status")

    def refresh(self) -> None:
        """Refresh data."""
        self._load_data()
