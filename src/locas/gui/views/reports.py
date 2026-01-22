"""Reports view for LOCAS."""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QGroupBox, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.report_service import ReportService
from locas.gui.widgets.data_table import DataTable
from locas.utils.formatters import format_date, format_currency


class ReportsView(QWidget):
    """Reports view for librarians and admins.
    
    Shows various reports and statistics.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize ReportsView."""
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        
        self.report_service = ReportService(config, db_manager, session_manager)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        header = QLabel("Reports & Analytics")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Overview tab
        overview_widget = self._create_overview_tab()
        tabs.addTab(overview_widget, "📊 Overview")
        
        # Popular Books tab
        popular_widget = self._create_popular_books_tab()
        tabs.addTab(popular_widget, "📚 Popular Books")
        
        # Overdue Report tab
        overdue_widget = self._create_overdue_tab()
        tabs.addTab(overdue_widget, "⚠️ Overdue")
        
        # Fine Summary tab
        fines_widget = self._create_fines_tab()
        tabs.addTab(fines_widget, "💰 Fines")
        
        layout.addWidget(tabs)
    
    def _create_overview_tab(self) -> QWidget:
        """Create overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stats cards
        cards = QGroupBox("System Overview")
        cards_layout = QGridLayout(cards)
        cards_layout.setSpacing(16)
        
        self.stat_cards = {}
        
        stats = [
            ("total_books", "Total Books", "#1976D2"),
            ("total_copies", "Total Copies", "#388E3C"),
            ("active_loans", "Active Loans", "#F57C00"),
            ("overdue_books", "Overdue", "#D32F2F"),
            ("total_users", "Total Users", "#7B1FA2"),
            ("pending_fines", "Pending Fines", "#C62828"),
        ]
        
        for i, (key, label, color) in enumerate(stats):
            card = self._create_stat_card(label, "0", color)
            self.stat_cards[key] = card
            cards_layout.addWidget(card, i // 3, i % 3)
        
        layout.addWidget(cards)
        
        # Recent activity summary
        activity_group = QGroupBox("Recent Activity (Last 7 Days)")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_label = QLabel("Loading...")
        self.activity_label.setWordWrap(True)
        self.activity_label.setStyleSheet("padding: 12px; background-color: #F5F5F5; border-radius: 4px;")
        activity_layout.addWidget(self.activity_label)
        
        layout.addWidget(activity_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        """Create a stat card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #757575; font-size: 12px;")
        layout.addWidget(title_lbl)
        
        value_lbl = QLabel(value)
        value_lbl.setObjectName("value")
        value_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")
        layout.addWidget(value_lbl)
        
        return card
    
    def _create_popular_books_tab(self) -> QWidget:
        """Create popular books tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Most Borrowed Books"))
        
        self.popular_table = DataTable([
            {"key": "rank", "label": "#", "width": 50},
            {"key": "title", "label": "Title", "stretch": True},
            {"key": "author", "label": "Author", "width": 150},
            {"key": "borrow_count", "label": "Times Borrowed", "width": 120},
            {"key": "available_copies", "label": "Available", "width": 80},
        ])
        layout.addWidget(self.popular_table, 1)
        
        return widget
    
    def _create_overdue_tab(self) -> QWidget:
        """Create overdue report tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Overdue Books"))
        
        def format_days(value, row):
            days = row.get("days_overdue", 0)
            if days > 7:
                return f"🔴 {days} days"
            elif days > 3:
                return f"🟠 {days} days"
            else:
                return f"🟡 {days} days"
        
        self.overdue_table = DataTable([
            {"key": "book_title", "label": "Book", "stretch": True},
            {"key": "username", "label": "Student", "width": 100},
            {"key": "full_name", "label": "Name", "width": 150},
            {"key": "due_date", "label": "Due Date", "width": 100},
            {"key": "days_overdue", "label": "Overdue", "width": 100, "formatter": format_days},
            {"key": "estimated_fine", "label": "Est. Fine", "width": 100},
        ])
        layout.addWidget(self.overdue_table, 1)
        
        return widget
    
    def _create_fines_tab(self) -> QWidget:
        """Create fines summary tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Summary stats
        summary = QHBoxLayout()
        
        self.total_pending = QLabel("Total Pending: ₹0")
        self.total_pending.setStyleSheet("""
            QLabel {
                background-color: #FFEBEE;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 16px;
            }
        """)
        summary.addWidget(self.total_pending)
        
        self.total_collected = QLabel("Total Collected: ₹0")
        self.total_collected.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 16px;
            }
        """)
        summary.addWidget(self.total_collected)
        
        summary.addStretch()
        layout.addLayout(summary)
        
        layout.addWidget(QLabel("Students with Pending Fines"))
        
        self.fines_table = DataTable([
            {"key": "username", "label": "Username", "width": 120},
            {"key": "full_name", "label": "Name", "stretch": True},
            {"key": "fine_count", "label": "Fines", "width": 80},
            {"key": "total_amount", "label": "Total Amount", "width": 120},
        ])
        layout.addWidget(self.fines_table, 1)
        
        return widget
    
    def _load_data(self) -> None:
        """Load all report data."""
        try:
            # Load overview stats
            stats = self.report_service.get_system_overview()
            
            self.stat_cards["total_books"].findChild(QLabel, "value").setText(str(stats.get("total_books", 0)))
            self.stat_cards["total_copies"].findChild(QLabel, "value").setText(str(stats.get("total_copies", 0)))
            self.stat_cards["active_loans"].findChild(QLabel, "value").setText(str(stats.get("active_loans", 0)))
            self.stat_cards["overdue_books"].findChild(QLabel, "value").setText(str(stats.get("overdue_count", 0)))
            self.stat_cards["total_users"].findChild(QLabel, "value").setText(str(stats.get("total_users", 0)))
            self.stat_cards["pending_fines"].findChild(QLabel, "value").setText(
                format_currency(stats.get("total_pending_fines", 0))
            )
            
            # Activity summary
            activity = f"""
            📚 Books issued this week: {stats.get('issues_this_week', 0)}<br>
            📖 Books returned this week: {stats.get('returns_this_week', 0)}<br>
            ⚠️ Currently overdue: {stats.get('overdue_count', 0)}<br>
            💰 Fines collected this month: {format_currency(stats.get('fines_collected_month', 0))}
            """
            self.activity_label.setText(activity)
            
            # Popular books
            popular = self.report_service.get_popular_books_report(limit=20)
            popular_data = []
            for i, book in enumerate(popular, 1):
                book_dict = book if isinstance(book, dict) else book.to_dict()
                book_dict["rank"] = i
                popular_data.append(book_dict)
            self.popular_table.set_data(popular_data)
            
            # Overdue report
            overdue = self.report_service.get_overdue_books_report()
            overdue_data = []
            for item in overdue:
                item_dict = item if isinstance(item, dict) else item.to_dict()
                # Calculate estimated fine
                days = item_dict.get("days_overdue", 0)
                item_dict["estimated_fine"] = format_currency(days * self.config.fine_rate_per_day)
                overdue_data.append(item_dict)
            self.overdue_table.set_data(overdue_data)
            
            # Fines summary
            self.total_pending.setText(f"Total Pending: {format_currency(stats.get('total_pending_fines', 0))}")
            self.total_collected.setText(f"Total Collected: {format_currency(stats.get('total_collected_fines', 0))}")
            
            fines_by_user = self.report_service.get_users_with_fines_report()
            self.fines_table.set_data(fines_by_user)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            print(f"Report error: {e}")
    
    def refresh(self) -> None:
        """Refresh data."""
        self._load_data()
