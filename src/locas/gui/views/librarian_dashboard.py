"""Librarian dashboard view for LOCAS."""

from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QTabWidget
)
from PyQt6.QtCore import Qt

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.repositories.book_repository import BookRepository
from locas.repositories.copy_repository import CopyRepository
from locas.repositories.transaction_repository import TransactionRepository
from locas.core.constants import BookCopyStatus


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
        self.setStyleSheet(f"""
            QFrame {{
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
        self.value_label.setText(value)


class LibrarianDashboard(QWidget):
    """Librarian dashboard view.
    
    Provides access to:
    - Book management
    - Copy management
    - Issue/Return operations
    - Reports
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        logout_callback: Callable[[], None],
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.logout_callback = logout_callback
        
        self.book_repo = BookRepository(db_manager)
        self.copy_repo = CopyRepository(db_manager)
        self.trans_repo = TransactionRepository(db_manager)
        
        self._setup_ui()
        self._load_statistics()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        welcome_label = QLabel("Librarian Dashboard")
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
        
        self.books_card = DashboardCard("Total Books", "0", "#1976D2")
        cards_layout.addWidget(self.books_card, 0, 0)
        
        self.available_card = DashboardCard("Available Copies", "0", "#388E3C")
        cards_layout.addWidget(self.available_card, 0, 1)
        
        self.issued_card = DashboardCard("Issued Books", "0", "#F57C00")
        cards_layout.addWidget(self.issued_card, 0, 2)
        
        self.overdue_card = DashboardCard("Overdue", "0", "#D32F2F")
        cards_layout.addWidget(self.overdue_card, 0, 3)
        
        main_layout.addLayout(cards_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Issue/Return tab - NOW FUNCTIONAL
        from locas.gui.views.issue_return import IssueReturnView
        self.issue_return = IssueReturnView(
            self.config, self.db_manager, self.session_manager
        )
        self.issue_return.data_changed.connect(self._load_statistics)
        self.tabs.addTab(self.issue_return, "Issue / Return")
        
        # Book Management tab
        from locas.gui.views.book_management import BookManagementView
        self.book_management = BookManagementView(
            self.config, self.db_manager, self.session_manager
        )
        self.book_management.data_changed.connect(self._load_statistics)
        self.tabs.addTab(self.book_management, "Books")
        
        # Fine Management tab
        from locas.gui.views.fine_management import FineManagementView
        self.fine_management = FineManagementView(
            self.config, self.db_manager, self.session_manager
        )
        self.tabs.addTab(self.fine_management, "Fines")
        
        # Reports tab
        from locas.gui.views.reports import ReportsView
        self.reports = ReportsView(
            self.config, self.db_manager, self.session_manager
        )
        self.tabs.addTab(self.reports, "Reports")
        
        main_layout.addWidget(self.tabs)
    
    def _load_statistics(self) -> None:
        """Load dashboard statistics."""
        try:
            # Total books
            book_count = self.book_repo.count_total()
            self.books_card.set_value(str(book_count))
            
            # Available copies
            avail_count = self.copy_repo.count_by_status(BookCopyStatus.AVAILABLE)
            self.available_card.set_value(str(avail_count))
            
            # Issued copies
            issued_count = self.copy_repo.count_by_status(BookCopyStatus.ISSUED)
            self.issued_card.set_value(str(issued_count))
            
            # Overdue
            overdue_count = self.trans_repo.count_overdue()
            self.overdue_card.set_value(str(overdue_count))
            
        except Exception as e:
            print(f"Error loading statistics: {e}")
