"""Main application window for LOCAS."""

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget, QStatusBar, QWidget

from locas.config import Config
from locas.core.constants import AppConstants
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.gui.styles import Styles
from locas.gui.views.login_view import LoginView


class MainWindow(QMainWindow):
    """Main application window managing all views.

    Contains a stacked widget that switches between login and
    role-specific dashboard views.

    Attributes:
        config: Application configuration.
        db_manager: Database manager instance.
        session_manager: Session manager for auth state.
        stacked_widget: Container for switching views.
    """

    def __init__(
        self, config: Config, db_manager: DatabaseManager, parent: QWidget | None = None
    ) -> None:
        """Initialize main window.

        Args:
            config: Application configuration.
            db_manager: Database manager instance.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.config = config
        self.db_manager = db_manager
        self.session_manager = SessionManager(config)

        self._setup_ui()
        self._setup_connections()
        self._show_login()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Window properties
        self.setWindowTitle(f"{self.config.app_name} - LIBRARY FOR COLLEGE ADMINISTRATION SYSTEM")
        self.setMinimumSize(AppConstants.WINDOW_MIN_WIDTH, AppConstants.WINDOW_MIN_HEIGHT)

        # Apply stylesheet
        self.setStyleSheet(Styles.get_full_stylesheet())

        # Central widget with stacked layout
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create login view
        self.login_view = LoginView(self.config, self.db_manager, self.session_manager)
        self.stacked_widget.addWidget(self.login_view)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Placeholder for dashboard views (created on login)
        self.admin_dashboard = None
        self.librarian_dashboard = None
        self.student_dashboard = None

    def _setup_connections(self) -> None:
        """Connect signals to slots."""
        self.login_view.login_successful.connect(self._on_login_success)

    def _show_login(self) -> None:
        """Show the login view."""
        self.stacked_widget.setCurrentWidget(self.login_view)
        self.status_bar.showMessage("Please log in to continue")

    def _on_login_success(self) -> None:
        """Handle successful login."""
        session = self.session_manager.current_session
        if session is None:
            return

        self.status_bar.showMessage(f"Logged in as {session.full_name} ({session.role_name})")

        # Load appropriate dashboard based on role
        if session.is_admin():
            self._show_admin_dashboard()
        elif session.is_librarian():
            self._show_librarian_dashboard()
        elif session.is_student():
            self._show_student_dashboard()

    def _show_admin_dashboard(self) -> None:
        """Show admin dashboard view."""
        if self.admin_dashboard is None:
            from locas.gui.views.admin_dashboard import AdminDashboard

            self.admin_dashboard = AdminDashboard(
                self.config, self.db_manager, self.session_manager, self._handle_logout
            )
            self.stacked_widget.addWidget(self.admin_dashboard)

        self.stacked_widget.setCurrentWidget(self.admin_dashboard)

    def _show_librarian_dashboard(self) -> None:
        """Show librarian dashboard view."""
        if self.librarian_dashboard is None:
            from locas.gui.views.librarian_dashboard import LibrarianDashboard

            self.librarian_dashboard = LibrarianDashboard(
                self.config, self.db_manager, self.session_manager, self._handle_logout
            )
            self.stacked_widget.addWidget(self.librarian_dashboard)

        self.stacked_widget.setCurrentWidget(self.librarian_dashboard)

    def _show_student_dashboard(self) -> None:
        """Show student dashboard view."""
        if self.student_dashboard is None:
            from locas.gui.views.student_dashboard import StudentDashboard

            self.student_dashboard = StudentDashboard(
                self.config, self.db_manager, self.session_manager, self._handle_logout
            )
            self.stacked_widget.addWidget(self.student_dashboard)

        self.stacked_widget.setCurrentWidget(self.student_dashboard)

    def _handle_logout(self) -> None:
        """Handle user logout."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.end_session()
            self.login_view.clear_form()
            self._show_login()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.session_manager.is_authenticated():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        # Clean up
        self.session_manager.end_session()
        event.accept()
