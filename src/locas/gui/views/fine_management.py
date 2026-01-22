"""Fine management view for LOCAS."""

from typing import Optional
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.fine_service import FineService
from locas.services.user_service import UserService
from locas.models.fine import Fine
from locas.gui.widgets.data_table import DataTable
from locas.utils.formatters import format_date, format_currency


class FineManagementView(QWidget):
    """Fine management view for librarians and admins.
    
    Allows viewing, collecting payment, and waiving fines.
    Only admins can waive fines.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize FineManagementView."""
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        
        self.fine_service = FineService(config, db_manager, session_manager)
        self.user_service = UserService(config, db_manager, session_manager)
        
        self._selected_fine: Optional[Fine] = None
        self._is_admin = self._check_admin()
        
        self._setup_ui()
        self._load_data()
    
    def _check_admin(self) -> bool:
        """Check if current user is admin."""
        session = self.session_manager.current_session
        return session is not None and session.has_role("admin")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        header = QLabel("Fine Management")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Stats
        self.total_pending_label = QLabel("Total Pending: ₹0.00")
        self.total_pending_label.setStyleSheet("""
            QLabel {
                background-color: #FFEBEE;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
                color: #C62828;
            }
        """)
        header_layout.addWidget(self.total_pending_label)
        
        layout.addLayout(header_layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Search
        toolbar.addWidget(QLabel("Search Student:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter username or name...")
        self.search_input.setMaximumWidth(250)
        self.search_input.returnPressed.connect(self._search_fines)
        toolbar.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search_fines)
        toolbar.addWidget(search_btn)
        
        toolbar.addSpacing(20)
        
        # Filter
        toolbar.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Paid", "Waived"])
        self.status_filter.currentIndexChanged.connect(self._load_data)
        toolbar.addWidget(self.status_filter)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Fines table
        def format_amount(value, row):
            return format_currency(Decimal(str(value)) if value else Decimal("0"))
        
        def format_status(value, row):
            status = row.get("status", {})
            if hasattr(status, 'display_name'):
                return status.display_name
            return str(value)
        
        self.fines_table = DataTable([
            {"key": "full_name", "label": "Student", "width": 150},
            {"key": "username", "label": "Username", "width": 100},
            {"key": "book_title", "label": "Book", "stretch": True},
            {"key": "amount", "label": "Amount", "width": 100, "formatter": format_amount},
            {"key": "reason", "label": "Reason", "width": 150},
            {"key": "created_at", "label": "Date", "width": 100},
            {"key": "status", "label": "Status", "width": 80, "formatter": format_status},
        ])
        self.fines_table.row_selected.connect(self._on_fine_selected)
        content_layout.addWidget(self.fines_table, 2)
        
        # Action panel
        action_panel = QFrame()
        action_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        action_panel.setMinimumWidth(280)
        action_panel.setMaximumWidth(320)
        
        action_layout = QVBoxLayout(action_panel)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(12)
        
        action_title = QLabel("Fine Details")
        action_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        action_layout.addWidget(action_title)
        
        # Fine details display
        self.fine_details = QLabel("Select a fine to view details")
        self.fine_details.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                padding: 12px;
                border-radius: 4px;
            }
        """)
        self.fine_details.setWordWrap(True)
        self.fine_details.setMinimumHeight(150)
        action_layout.addWidget(self.fine_details)
        
        # Action buttons
        self.pay_btn = QPushButton("💰 Record Payment")
        self.pay_btn.setStyleSheet("""
            QPushButton {
                background-color: #388E3C;
                color: white;
                font-weight: 600;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2E7D32;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.pay_btn.setEnabled(False)
        self.pay_btn.clicked.connect(self._record_payment)
        action_layout.addWidget(self.pay_btn)
        
        self.waive_btn = QPushButton("🚫 Waive Fine")
        self.waive_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: 600;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.waive_btn.setEnabled(False)
        self.waive_btn.clicked.connect(self._waive_fine)
        
        if not self._is_admin:
            self.waive_btn.setToolTip("Only administrators can waive fines")
        
        action_layout.addWidget(self.waive_btn)
        
        action_layout.addStretch()
        
        # Summary
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        
        action_layout.addWidget(summary_group)
        
        content_layout.addWidget(action_panel)
        
        layout.addLayout(content_layout, 1)
    
    def _load_data(self) -> None:
        """Load fines data."""
        try:
            status_filter = self.status_filter.currentText().lower()
            
            if status_filter == "all":
                fines = self.fine_service.list_fines(limit=200)
            elif status_filter == "pending":
                fines = self.fine_service.list_pending_fines(limit=200)
            else:
                fines = self.fine_service.list_fines(limit=200)
                fines = [f for f in fines if f.status.value == status_filter]
            
            data = [f.to_dict() for f in fines]
            self.fines_table.set_data(data)
            
            # Update total pending using stats
            stats = self.fine_service.get_fine_stats()
            total = stats.get("total_pending", Decimal("0"))
            self.total_pending_label.setText(f"Total Pending: {format_currency(total)}")
            
            # Update summary
            pending_count = stats.get("pending_count", 0)
            self.summary_label.setText(
                f"Pending Fines: {pending_count}\n"
                f"Total Amount: {format_currency(total)}"
            )
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _search_fines(self) -> None:
        """Search fines by student."""
        query = self.search_input.text().strip()
        
        try:
            if query:
                # Search students first
                students = self.user_service.list_users(search=query, role_id=3, limit=10)
                
                if students:
                    all_fines = []
                    for student in students:
                        fines = self.fine_service.get_user_fines(student.user_id)
                        all_fines.extend(fines)
                    
                    data = [f.to_dict() for f in all_fines]
                    self.fines_table.set_data(data)
                else:
                    self.fines_table.set_data([])
                    QMessageBox.information(self, "Not Found", "No matching students found.")
            else:
                self._load_data()
                
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_fine_selected(self, row_data: dict) -> None:
        """Handle fine selection."""
        fine_id = row_data.get("fine_id")
        if not fine_id:
            return
        
        try:
            self._selected_fine = self.fine_service.get_fine(fine_id)
            
            details = f"""
            <b>Student:</b> {self._selected_fine.full_name or 'N/A'}<br>
            <b>Username:</b> {self._selected_fine.username or 'N/A'}<br>
            <b>Book:</b> {self._selected_fine.book_title or 'N/A'}<br>
            <hr>
            <b>Amount:</b> {format_currency(self._selected_fine.amount)}<br>
            <b>Reason:</b> {self._selected_fine.reason}<br>
            <b>Date:</b> {format_date(self._selected_fine.created_at)}<br>
            <b>Status:</b> {self._selected_fine.status.display_name}
            """
            
            if self._selected_fine.paid_at:
                details += f"<br><b>Paid At:</b> {format_date(self._selected_fine.paid_at)}"
            
            self.fine_details.setText(details)
            
            # Enable/disable buttons based on status
            is_pending = self._selected_fine.status.value == "pending"
            self.pay_btn.setEnabled(is_pending)
            self.waive_btn.setEnabled(is_pending and self._is_admin)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _record_payment(self) -> None:
        """Record payment for selected fine."""
        if not self._selected_fine:
            return
        
        confirm = QMessageBox.question(
            self, "Confirm Payment",
            f"Record payment of {format_currency(self._selected_fine.amount)} "
            f"from {self._selected_fine.full_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.fine_service.pay_fine(self._selected_fine.fine_id)
            
            QMessageBox.information(
                self, "Payment Recorded",
                f"Payment of {format_currency(self._selected_fine.amount)} recorded successfully!"
            )
            
            self._reset_selection()
            self._load_data()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _waive_fine(self) -> None:
        """Waive the selected fine (admin only)."""
        if not self._selected_fine or not self._is_admin:
            return
        
        confirm = QMessageBox.question(
            self, "Confirm Waive",
            f"Waive fine of {format_currency(self._selected_fine.amount)} "
            f"for {self._selected_fine.full_name}?\n\n"
            "This action will be logged in the audit trail.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.fine_service.waive_fine(self._selected_fine.fine_id)
            
            QMessageBox.information(
                self, "Fine Waived",
                f"Fine of {format_currency(self._selected_fine.amount)} waived successfully!"
            )
            
            self._reset_selection()
            self._load_data()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _reset_selection(self) -> None:
        """Reset the selection."""
        self._selected_fine = None
        self.fine_details.setText("Select a fine to view details")
        self.pay_btn.setEnabled(False)
        self.waive_btn.setEnabled(False)
    
    def refresh(self) -> None:
        """Refresh data."""
        self._load_data()
