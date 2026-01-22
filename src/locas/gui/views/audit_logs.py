"""Audit logs view for LOCAS admin."""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QDateEdit, QMessageBox,
    QGroupBox
)
from PyQt6.QtCore import Qt, QDate

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.audit_service import AuditService
from locas.services.user_service import UserService
from locas.gui.widgets.data_table import DataTable
from locas.utils.formatters import format_date, format_datetime


class AuditLogsView(QWidget):
    """Audit logs view for administrators.
    
    Shows system audit trail with filtering.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize AuditLogsView."""
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        
        self.audit_service = AuditService(config, db_manager, session_manager)
        self.user_service = UserService(config, db_manager, session_manager)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        header = QLabel("Audit Logs")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        # User filter
        filter_layout.addWidget(QLabel("User:"))
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Username...")
        self.user_filter.setMaximumWidth(150)
        filter_layout.addWidget(self.user_filter)
        
        # Action filter
        filter_layout.addWidget(QLabel("Action:"))
        self.action_filter = QComboBox()
        self.action_filter.addItems([
            "All Actions",
            "LOGIN", "LOGOUT",
            "USER_CREATED", "USER_UPDATED", "USER_DELETED",
            "BOOK_CREATED", "BOOK_UPDATED", "BOOK_DELETED",
            "BOOK_ISSUED", "BOOK_RETURNED",
            "FINE_PAID", "FINE_WAIVED",
            "PASSWORD_CHANGED", "PASSWORD_RESET"
        ])
        filter_layout.addWidget(self.action_filter)
        
        # Entity filter
        filter_layout.addWidget(QLabel("Entity:"))
        self.entity_filter = QComboBox()
        self.entity_filter.addItems([
            "All Entities", "user", "book", "book_copy", 
            "transaction", "fine", "auth"
        ])
        filter_layout.addWidget(self.entity_filter)
        
        # Date range
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)
        
        filter_layout.addStretch()
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self._load_data)
        filter_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)
        
        layout.addWidget(filter_group)
        
        # Quick filters
        quick_layout = QHBoxLayout()
        
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: self._quick_filter(0))
        quick_layout.addWidget(today_btn)
        
        week_btn = QPushButton("Last 7 Days")
        week_btn.clicked.connect(lambda: self._quick_filter(7))
        quick_layout.addWidget(week_btn)
        
        month_btn = QPushButton("Last 30 Days")
        month_btn.clicked.connect(lambda: self._quick_filter(30))
        quick_layout.addWidget(month_btn)
        
        quick_layout.addStretch()
        
        self.count_label = QLabel("Showing 0 logs")
        self.count_label.setStyleSheet("color: #757575;")
        quick_layout.addWidget(self.count_label)
        
        layout.addLayout(quick_layout)
        
        # Logs table
        def format_timestamp(value, row):
            if value:
                if isinstance(value, str):
                    return value[:19]
                return format_datetime(value)
            return ""
        
        def format_values(value, row):
            if value:
                if isinstance(value, dict):
                    return str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            return "-"
        
        self.logs_table = DataTable([
            {"key": "timestamp", "label": "Time", "width": 150, "formatter": format_timestamp},
            {"key": "username", "label": "User", "width": 100},
            {"key": "action", "label": "Action", "width": 150},
            {"key": "entity_type", "label": "Entity", "width": 100},
            {"key": "entity_id", "label": "ID", "width": 60},
            {"key": "new_value", "label": "Details", "stretch": True, "formatter": format_values},
        ])
        layout.addWidget(self.logs_table, 1)
        
        # Details panel
        details_group = QGroupBox("Log Details (select a row)")
        details_layout = QVBoxLayout(details_group)
        
        self.details_label = QLabel("Select a log entry to view full details")
        self.details_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                padding: 12px;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        self.details_label.setWordWrap(True)
        self.details_label.setMinimumHeight(80)
        details_layout.addWidget(self.details_label)
        
        layout.addWidget(details_group)
        
        # Connect selection
        self.logs_table.row_selected.connect(self._on_log_selected)
    
    def _load_data(self) -> None:
        """Load audit logs."""
        try:
            # Get filter values
            username = self.user_filter.text().strip() or None
            
            action = self.action_filter.currentText()
            if action == "All Actions":
                action = None
            
            entity = self.entity_filter.currentText()
            if entity == "All Entities":
                entity = None
            
            date_from = self.date_from.date().toPyDate()
            date_to = self.date_to.date().toPyDate()
            
            # Convert to datetime for end of day
            from datetime import datetime
            start_date = datetime.combine(date_from, datetime.min.time())
            end_date = datetime.combine(date_to, datetime.max.time())
            
            user_id = None
            if username:
                try:
                    user = self.user_service.get_user_by_username(username)
                    user_id = user.user_id
                except LOCASError:
                    # User not found, return empty list immediately
                    self.logs_table.set_data([])
                    self.count_label.setText("Showing 0 logs")
                    return

            logs = self.audit_service.get_logs(
                user_id=user_id,
                action=action,
                entity_type=entity,
                start_date=start_date,
                end_date=end_date,
                limit=500
            )
            
            data = [log.to_dict() if hasattr(log, 'to_dict') else log for log in logs]
            self.logs_table.set_data(data)
            
            self.count_label.setText(f"Showing {len(data)} logs")
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            print(f"Audit log error: {e}")
            self.logs_table.set_data([])
    
    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.user_filter.clear()
        self.action_filter.setCurrentIndex(0)
        self.entity_filter.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate())
        self._load_data()
    
    def _quick_filter(self, days: int) -> None:
        """Apply quick date filter."""
        today = QDate.currentDate()
        self.date_to.setDate(today)
        self.date_from.setDate(today.addDays(-days))
        self._load_data()
    
    def _on_log_selected(self, row_data: dict) -> None:
        """Show log details."""
        details = f"""
<b>Time:</b> {row_data.get('timestamp', 'N/A')}<br>
<b>User:</b> {row_data.get('username', 'N/A')}<br>
<b>Action:</b> {row_data.get('action', 'N/A')}<br>
<b>Entity:</b> {row_data.get('entity_type', 'N/A')} (ID: {row_data.get('entity_id', '-')})<br>
<br>
<b>Old Value:</b><br>{row_data.get('old_value', '-')}<br>
<br>
<b>New Value:</b><br>{row_data.get('new_value', '-')}
        """
        self.details_label.setText(details)
    
    def refresh(self) -> None:
        """Refresh data."""
        self._load_data()
