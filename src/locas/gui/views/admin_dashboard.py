"""Admin dashboard view for LOCAS."""

from typing import Callable, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QTabWidget, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.repositories.user_repository import UserRepository
from locas.repositories.book_repository import BookRepository
from locas.repositories.transaction_repository import TransactionRepository
from locas.repositories.fine_repository import FineRepository


class DashboardCard(QFrame):
    """Reusable dashboard statistic card."""
    
    def __init__(
        self,
        title: str,
        value: str,
        color: str = "#1976D2",
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardCard")
        self.setStyleSheet(f"""
            QFrame#dashboardCard {{
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #757575; font-size: 14px;")
        layout.addWidget(title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 700;")
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str) -> None:
        """Update the card value."""
        self.value_label.setText(value)


class AdminDashboard(QWidget):
    """Admin dashboard view with statistics and quick actions.
    
    Provides access to:
    - User management
    - Reports
    - Audit logs
    - System statistics
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        logout_callback: Callable[[], None],
        parent: QWidget | None = None
    ) -> None:
        """Initialize admin dashboard.
        
        Args:
            config: Application configuration.
            db_manager: Database manager.
            session_manager: Session manager.
            logout_callback: Function to call on logout.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.logout_callback = logout_callback
        
        self.user_repo = UserRepository(db_manager)
        self.book_repo = BookRepository(db_manager)
        self.trans_repo = TransactionRepository(db_manager)
        self.fine_repo = FineRepository(db_manager)
        
        self._setup_ui()
        self._load_statistics()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        welcome_label = QLabel("Admin Dashboard")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: 600; color: #212121;")
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        session = self.session_manager.current_session
        if session:
            user_label = QLabel(f"Welcome, {session.full_name}")
            user_label.setStyleSheet("color: #757575; font-size: 14px;")
            header_layout.addWidget(user_label)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #424242;
                border: 1px solid #E0E0E0;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        logout_btn.clicked.connect(self.logout_callback)
        header_layout.addWidget(logout_btn)
        
        main_layout.addLayout(header_layout)
        
        # Statistics cards
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)
        
        self.users_card = DashboardCard("Total Users", "0", "#1976D2")
        cards_layout.addWidget(self.users_card, 0, 0)
        
        self.books_card = DashboardCard("Total Books", "0", "#388E3C")
        cards_layout.addWidget(self.books_card, 0, 1)
        
        self.overdue_card = DashboardCard("Overdue Books", "0", "#D32F2F")
        cards_layout.addWidget(self.overdue_card, 0, 2)
        
        self.fines_card = DashboardCard("Pending Fines", "₹0", "#F57C00")
        cards_layout.addWidget(self.fines_card, 0, 3)
        
        main_layout.addLayout(cards_layout)
        
        # Tab widget for different sections
        tabs = QTabWidget()
        
        # User Management tab
        from locas.gui.views.user_management import UserManagementView
        self.user_management = UserManagementView(
            self.config, self.db_manager, self.session_manager
        )
        self.user_management.data_changed.connect(self._load_statistics)
        tabs.addTab(self.user_management, "User Management")
        
        # Fine Management tab - Admin can waive fines
        from locas.gui.views.fine_management import FineManagementView
        self.fine_management = FineManagementView(
            self.config, self.db_manager, self.session_manager
        )
        tabs.addTab(self.fine_management, "Fines")
        
        # Reports tab
        from locas.gui.views.reports import ReportsView
        self.reports = ReportsView(
            self.config, self.db_manager, self.session_manager
        )
        tabs.addTab(self.reports, "Reports")
        
        # Audit Logs tab
        from locas.gui.views.audit_logs import AuditLogsView
        self.audit_logs = AuditLogsView(
            self.config, self.db_manager, self.session_manager
        )
        tabs.addTab(self.audit_logs, "Audit Logs")
        
        main_layout.addWidget(tabs)
    
    def _load_statistics(self) -> None:
        """Load and display dashboard statistics."""
        try:
            # User count
            user_count = self.user_repo.count()
            self.users_card.set_value(str(user_count))
            
            # Book count
            book_count = self.book_repo.count_total()
            self.books_card.set_value(str(book_count))
            
            # Overdue count
            overdue_count = self.trans_repo.count_overdue()
            self.overdue_card.set_value(str(overdue_count))
            
            # Pending fines
            pending_fines = self.fine_repo.get_total_pending()
            self.fines_card.set_value(f"₹{float(pending_fines):,.2f}")
            
        except Exception as e:
            print(f"Error loading statistics: {e}")
