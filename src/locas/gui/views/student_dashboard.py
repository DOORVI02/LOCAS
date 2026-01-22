"""Student dashboard view for LOCAS."""

from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt
from decimal import Decimal

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.repositories.transaction_repository import TransactionRepository
from locas.repositories.fine_repository import FineRepository
from locas.repositories.book_repository import BookRepository
from locas.utils.formatters import format_date, format_currency
from locas.utils.date_utils import days_until_due
from locas.gui.views.book_search import BookSearchView


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


class StudentDashboard(QWidget):
    """Student dashboard view.
    
    Provides access to:
    - My borrowed books
    - My fines
    - Book search
    - Book availability
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
        
        self.trans_repo = TransactionRepository(db_manager)
        self.fine_repo = FineRepository(db_manager)
        self.book_repo = BookRepository(db_manager)
        
        self._setup_ui()
        self._load_data()
    
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        welcome_label = QLabel("Student Dashboard")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: 600; color: #212121;")
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_data)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(refresh_btn)
        
        header_layout.addSpacing(10)
        
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
        
        self.borrowed_card = DashboardCard("Books Borrowed", "0", "#1976D2")
        cards_layout.addWidget(self.borrowed_card, 0, 0)
        
        self.limit_card = DashboardCard("Borrow Limit", str(self.config.max_borrow_limit), "#388E3C")
        cards_layout.addWidget(self.limit_card, 0, 1)
        
        self.fines_card = DashboardCard("Pending Fines", "₹0", "#D32F2F")
        cards_layout.addWidget(self.fines_card, 0, 2)
        
        main_layout.addLayout(cards_layout)
        
        # Tab widget
        tabs = QTabWidget()
        
        # My Books tab
        my_books_widget = QWidget()
        my_books_layout = QVBoxLayout(my_books_widget)
        
        self.books_table = QTableWidget()
        self.books_table.setColumnCount(5)
        self.books_table.setHorizontalHeaderLabels([
            "Title", "Author", "Barcode", "Due Date", "Status"
        ])
        self.books_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.books_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.books_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        my_books_layout.addWidget(self.books_table)
        
        tabs.addTab(my_books_widget, "My Books")
        
        # My Fines tab
        fines_widget = QWidget()
        fines_layout = QVBoxLayout(fines_widget)
        
        self.fines_table = QTableWidget()
        self.fines_table.setColumnCount(4)
        self.fines_table.setHorizontalHeaderLabels([
            "Book", "Amount", "Reason", "Status"
        ])
        self.fines_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.fines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        fines_layout.addWidget(self.fines_table)
        
        tabs.addTab(fines_widget, "My Fines")
        
        # Search Books tab
        self.book_search_view = BookSearchView(
            self.config,
            self.db_manager,
            self.session_manager
        )
        tabs.addTab(self.book_search_view, "Search Books")
        
        main_layout.addWidget(tabs)
    
    def _load_data(self) -> None:
        """Load student's data."""
        session = self.session_manager.current_session
        if session is None:
            return
        
        user_id = session.user_id
        
        try:
            # Load active transactions
            transactions = self.trans_repo.find_active_by_user(user_id)
            self.borrowed_card.set_value(str(len(transactions)))
            
            self.books_table.setRowCount(len(transactions))
            for row, trans in enumerate(transactions):
                self.books_table.setItem(row, 0, QTableWidgetItem(trans.book_title or ""))
                self.books_table.setItem(row, 1, QTableWidgetItem(trans.book_author or ""))
                self.books_table.setItem(row, 2, QTableWidgetItem(trans.barcode or ""))
                self.books_table.setItem(row, 3, QTableWidgetItem(format_date(trans.due_date)))
                
                days_left = days_until_due(trans.due_date)
                if days_left < 0:
                    status_text = f"Overdue by {abs(days_left)} days"
                    status_item = QTableWidgetItem(status_text)
                    status_item.setForeground(Qt.GlobalColor.red)
                elif days_left <= 2:
                    status_text = f"Due in {days_left} days"
                    status_item = QTableWidgetItem(status_text)
                    status_item.setForeground(Qt.GlobalColor.darkYellow)
                else:
                    status_item = QTableWidgetItem(f"{days_left} days left")
                
                self.books_table.setItem(row, 4, status_item)
            
            # Load fines
            fines = self.fine_repo.find_pending_by_user(user_id)
            total_fines = sum(f.amount for f in fines)
            self.fines_card.set_value(format_currency(total_fines))
            
            self.fines_table.setRowCount(len(fines))
            for row, fine in enumerate(fines):
                self.fines_table.setItem(row, 0, QTableWidgetItem(fine.book_title or ""))
                self.fines_table.setItem(row, 1, QTableWidgetItem(format_currency(fine.amount)))
                self.fines_table.setItem(row, 2, QTableWidgetItem(fine.reason))
                self.fines_table.setItem(row, 3, QTableWidgetItem(fine.status.display_name))
            
        except Exception as e:
            print(f"Error loading student data: {e}")
