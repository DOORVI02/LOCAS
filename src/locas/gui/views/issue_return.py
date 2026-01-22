"""Issue/Return view for LOCAS librarian operations."""

from typing import Optional
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QLineEdit, QComboBox, QTextEdit,
    QMessageBox, QGroupBox, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.transaction_service import TransactionService
from locas.services.book_service import BookService
from locas.services.user_service import UserService
from locas.models.book import Book
from locas.models.book_copy import BookCopy
from locas.models.user import User
from locas.models.transaction import Transaction
from locas.gui.widgets.data_table import DataTable
from locas.utils.formatters import format_date, format_currency
from locas.utils.date_utils import days_until_due


class IssueReturnView(QWidget):
    """Combined Issue/Return view for librarians.
    
    Uses ISBN/title search instead of barcode scanning.
    """
    
    data_changed = pyqtSignal()
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize IssueReturnView."""
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        
        self.trans_service = TransactionService(config, db_manager, session_manager)
        self.book_service = BookService(config, db_manager, session_manager)
        self.user_service = UserService(config, db_manager, session_manager)
        
        self._selected_book: Optional[Book] = None
        self._selected_copy: Optional[BookCopy] = None
        self._selected_student: Optional[User] = None
        self._selected_transaction: Optional[Transaction] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Issue & Return Books")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(header)
        
        # Tab widget for Issue and Return
        tabs = QTabWidget()
        
        # Issue Book Tab
        issue_widget = self._create_issue_tab()
        tabs.addTab(issue_widget, "📚 Issue Book")
        
        # Return Book Tab
        return_widget = self._create_return_tab()
        tabs.addTab(return_widget, "📖 Return Book")
        
        # Active Loans Tab
        loans_widget = self._create_active_loans_tab()
        tabs.addTab(loans_widget, "📋 Active Loans")
        
        layout.addWidget(tabs)
    
    # -------------------------------------------------------------------------
    # Issue Book Tab
    # -------------------------------------------------------------------------
    
    def _create_issue_tab(self) -> QWidget:
        """Create the issue book tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(16)
        
        # Left side - Book search
        book_group = QGroupBox("1. Find Book (by ISBN or Title)")
        book_layout = QVBoxLayout(book_group)
        
        # Search input
        search_layout = QHBoxLayout()
        self.issue_book_search = QLineEdit()
        self.issue_book_search.setPlaceholderText("Enter ISBN or book title...")
        self.issue_book_search.returnPressed.connect(self._search_book_for_issue)
        search_layout.addWidget(self.issue_book_search)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search_book_for_issue)
        search_layout.addWidget(search_btn)
        book_layout.addLayout(search_layout)
        
        # Book results table
        self.issue_book_table = DataTable([
            {"key": "title", "label": "Title", "stretch": True},
            {"key": "author", "label": "Author", "width": 150},
            {"key": "isbn", "label": "ISBN", "width": 120},
            {"key": "available_copies", "label": "Available", "width": 80},
        ])
        self.issue_book_table.row_selected.connect(self._on_issue_book_selected)
        book_layout.addWidget(self.issue_book_table, 1)
        
        # Copy selection
        copy_layout = QHBoxLayout()
        copy_layout.addWidget(QLabel("Select Copy:"))
        self.issue_copy_combo = QComboBox()
        self.issue_copy_combo.setMinimumWidth(200)
        copy_layout.addWidget(self.issue_copy_combo, 1)
        book_layout.addLayout(copy_layout)
        
        layout.addWidget(book_group, 1)
        
        # Right side - Student and confirmation
        right_layout = QVBoxLayout()
        
        # Student search
        student_group = QGroupBox("2. Find Student")
        student_layout = QVBoxLayout(student_group)
        
        student_search_layout = QHBoxLayout()
        self.issue_student_search = QLineEdit()
        self.issue_student_search.setPlaceholderText("Enter student username or ID...")
        self.issue_student_search.returnPressed.connect(self._search_student_for_issue)
        student_search_layout.addWidget(self.issue_student_search)
        
        student_search_btn = QPushButton("Find")
        student_search_btn.clicked.connect(self._search_student_for_issue)
        student_search_layout.addWidget(student_search_btn)
        student_layout.addLayout(student_search_layout)
        
        # Student info display
        self.issue_student_info = QLabel("No student selected")
        self.issue_student_info.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                padding: 12px;
                border-radius: 4px;
                min-height: 60px;
            }
        """)
        self.issue_student_info.setWordWrap(True)
        student_layout.addWidget(self.issue_student_info)
        
        right_layout.addWidget(student_group)
        
        # Issue summary and confirmation
        confirm_group = QGroupBox("3. Confirm Issue")
        confirm_layout = QVBoxLayout(confirm_group)
        
        self.issue_summary = QLabel("Select a book and student to issue")
        self.issue_summary.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #1976D2;
            }
        """)
        self.issue_summary.setWordWrap(True)
        confirm_layout.addWidget(self.issue_summary)
        
        # Remarks
        confirm_layout.addWidget(QLabel("Remarks (optional):"))
        self.issue_remarks = QTextEdit()
        self.issue_remarks.setMaximumHeight(60)
        confirm_layout.addWidget(self.issue_remarks)
        
        # Issue button
        self.issue_btn = QPushButton("✓ Issue Book")
        self.issue_btn.setStyleSheet("""
            QPushButton {
                background-color: #388E3C;
                color: white;
                font-size: 16px;
                font-weight: 600;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #2E7D32;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.issue_btn.setEnabled(False)
        self.issue_btn.clicked.connect(self._issue_book)
        confirm_layout.addWidget(self.issue_btn)
        
        right_layout.addWidget(confirm_group)
        right_layout.addStretch()
        
        layout.addLayout(right_layout, 1)
        
        return widget
    
    def _search_book_for_issue(self) -> None:
        """Search for books to issue."""
        query = self.issue_book_search.text().strip()
        if not query:
            return
        
        try:
            books = self.book_service.search_books(query=query, limit=50)
            # Filter to only show books with available copies
            available_books = [b for b in books if b.available_copies > 0]
            
            data = [b.to_dict() for b in available_books]
            self.issue_book_table.set_data(data)
            
            if not available_books:
                QMessageBox.information(
                    self, "No Available Books",
                    "No books with available copies found for your search."
                )
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_issue_book_selected(self, row_data: dict) -> None:
        """Handle book selection for issue."""
        book_id = row_data.get("book_id")
        if not book_id:
            return
        
        try:
            self._selected_book = self.book_service.get_book(book_id)
            
            # Load available copies into combo box
            copies = self.book_service.get_copies_by_book(book_id)
            available_copies = [c for c in copies if c.status.value == "available"]
            
            self.issue_copy_combo.clear()
            for copy in available_copies:
                self.issue_copy_combo.addItem(
                    f"{copy.barcode} ({copy.location or 'No location'})",
                    copy.copy_id
                )
            
            if available_copies:
                self._selected_copy = available_copies[0]
            
            self._update_issue_summary()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _search_student_for_issue(self) -> None:
        """Search for student to issue book to."""
        query = self.issue_student_search.text().strip()
        if not query:
            return
        
        try:
            # Try to find by username first
            students = self.user_service.list_users(search=query, role_id=3, limit=10)
            
            if not students:
                self.issue_student_info.setText("No student found")
                self._selected_student = None
                self._update_issue_summary()
                return
            
            # Use first matching student
            student = students[0]
            self._selected_student = student
            
            # Get borrowing info
            active_loans = self.trans_service.get_user_active_transactions(student.user_id)
            
            info_html = f"""
            <b>{student.full_name}</b><br>
            Username: {student.username}<br>
            Email: {student.email}<br>
            Currently borrowed: {len(active_loans)} / {self.config.max_borrow_limit} books
            """
            
            if len(active_loans) >= self.config.max_borrow_limit:
                info_html += "<br><span style='color: red;'>⚠ Borrow limit reached!</span>"
            
            self.issue_student_info.setText(info_html)
            self._update_issue_summary()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _update_issue_summary(self) -> None:
        """Update the issue summary and enable/disable button."""
        if self._selected_book and self._selected_student:
            copy_id = self.issue_copy_combo.currentData()
            if copy_id:
                summary = f"""
                <b>Book:</b> {self._selected_book.title}<br>
                <b>Author:</b> {self._selected_book.author}<br>
                <b>Copy:</b> {self.issue_copy_combo.currentText()}<br>
                <b>Student:</b> {self._selected_student.full_name} ({self._selected_student.username})<br>
                <b>Due Date:</b> {self.config.max_borrow_days} days from today
                """
                self.issue_summary.setText(summary)
                self.issue_btn.setEnabled(True)
            else:
                self.issue_summary.setText("No available copies selected")
                self.issue_btn.setEnabled(False)
        else:
            parts = []
            if not self._selected_book:
                parts.append("• Select a book")
            if not self._selected_student:
                parts.append("• Find a student")
            self.issue_summary.setText("Complete these steps:\n" + "\n".join(parts))
            self.issue_btn.setEnabled(False)
    
    def _issue_book(self) -> None:
        """Issue the selected book to the selected student."""
        copy_id = self.issue_copy_combo.currentData()
        if not copy_id or not self._selected_student:
            return
        
        remarks = self.issue_remarks.toPlainText().strip() or None
        
        try:
            transaction = self.trans_service.issue_book(
                copy_id=copy_id,
                student_id=self._selected_student.user_id,
                remarks=remarks
            )
            
            QMessageBox.information(
                self, "Book Issued Successfully",
                f"Book issued to {self._selected_student.full_name}\n\n"
                f"Due Date: {format_date(transaction.due_date)}\n"
                f"Transaction ID: {transaction.transaction_id}"
            )
            
            # Reset form
            self._reset_issue_form()
            self.data_changed.emit()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Issue Failed", str(e))
    
    def _reset_issue_form(self) -> None:
        """Reset the issue form."""
        self._selected_book = None
        self._selected_copy = None
        self._selected_student = None
        
        self.issue_book_search.clear()
        self.issue_book_table.set_data([])
        self.issue_copy_combo.clear()
        self.issue_student_search.clear()
        self.issue_student_info.setText("No student selected")
        self.issue_summary.setText("Select a book and student to issue")
        self.issue_remarks.clear()
        self.issue_btn.setEnabled(False)
    
    # -------------------------------------------------------------------------
    # Return Book Tab
    # -------------------------------------------------------------------------
    
    def _create_return_tab(self) -> QWidget:
        """Create the return book tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Search options
        search_group = QGroupBox("Find Book to Return")
        search_layout = QHBoxLayout(search_group)
        
        # Search by ISBN/barcode
        search_layout.addWidget(QLabel("Search by ISBN or Title:"))
        self.return_search = QLineEdit()
        self.return_search.setPlaceholderText("Enter ISBN, title, or student username...")
        self.return_search.returnPressed.connect(self._search_for_return)
        search_layout.addWidget(self.return_search, 1)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search_for_return)
        search_layout.addWidget(search_btn)
        
        layout.addWidget(search_group)
        
        # Active loans table
        loans_label = QLabel("Active Loans (select to return):")
        loans_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(loans_label)
        
        def format_due_status(value, row):
            days = days_until_due(row.get("due_date"))
            if days < 0:
                return f"⚠ Overdue by {abs(days)} days"
            elif days <= 2:
                return f"⏰ Due in {days} days"
            else:
                return f"{days} days left"
        
        self.return_loans_table = DataTable([
            {"key": "book_title", "label": "Book", "stretch": True},
            {"key": "book_author", "label": "Author", "width": 150},
            {"key": "username", "label": "Student", "width": 120},
            {"key": "issue_date", "label": "Issued", "width": 100},
            {"key": "due_date", "label": "Status", "width": 140, "formatter": format_due_status},
        ])
        self.return_loans_table.row_selected.connect(self._on_return_loan_selected)
        layout.addWidget(self.return_loans_table, 1)
        
        # Return confirmation
        confirm_layout = QHBoxLayout()
        
        self.return_info = QLabel("Select a loan to return")
        self.return_info.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #FF9800;
            }
        """)
        confirm_layout.addWidget(self.return_info, 1)
        
        self.return_btn = QPushButton("📖 Return Book")
        self.return_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-size: 16px;
                font-weight: 600;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.return_btn.setEnabled(False)
        self.return_btn.clicked.connect(self._return_book)
        confirm_layout.addWidget(self.return_btn)
        
        layout.addLayout(confirm_layout)
        
        # Load initial active loans
        self._load_active_loans_for_return()
        
        return widget
    
    def _load_active_loans_for_return(self) -> None:
        """Load all active loans."""
        try:
            transactions = self.trans_service.get_active_transactions(limit=100)
            data = [t.to_dict() for t in transactions]
            self.return_loans_table.set_data(data)
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _search_for_return(self) -> None:
        """Search for loans to return."""
        query = self.return_search.text().strip()
        
        try:
            if query:
                # Search by student username first
                students = self.user_service.list_users(search=query, role_id=3, limit=5)
                
                if students:
                    # Get active loans for matching students
                    all_loans = []
                    for student in students:
                        loans = self.trans_service.get_user_active_transactions(student.user_id)
                        all_loans.extend(loans)
                    
                    if all_loans:
                        data = [t.to_dict() for t in all_loans]
                        self.return_loans_table.set_data(data)
                        return
                
                # If no student match, search by book
                books = self.book_service.search_books(query=query, limit=10)
                if books:
                    # Get active loans for these books
                    all_transactions = self.trans_service.get_active_transactions(limit=200)
                    book_ids = {b.book_id for b in books}
                    
                    matching = []
                    for t in all_transactions:
                        # Check if transaction's book matches
                        if hasattr(t, 'book_id') and t.book_id in book_ids:
                            matching.append(t)
                        elif t.book_title and any(query.lower() in t.book_title.lower() for b in books):
                            matching.append(t)
                    
                    # Simpler approach: filter by title match
                    matching = [
                        t for t in all_transactions 
                        if t.book_title and query.lower() in t.book_title.lower()
                    ]
                    
                    data = [t.to_dict() for t in matching]
                    self.return_loans_table.set_data(data)
                    return
                
                QMessageBox.information(self, "Not Found", "No matching loans found.")
            else:
                # Empty search - show all active loans
                self._load_active_loans_for_return()
                
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_return_loan_selected(self, row_data: dict) -> None:
        """Handle loan selection for return."""
        transaction_id = row_data.get("transaction_id")
        if not transaction_id:
            return
        
        try:
            self._selected_transaction = self.trans_service.get_transaction(transaction_id)
            
            days = days_until_due(self._selected_transaction.due_date)
            
            info_html = f"""
            <b>{self._selected_transaction.book_title}</b> → {self._selected_transaction.borrower_username}<br>
            Issued: {format_date(self._selected_transaction.issue_date)}
            """
            
            if days < 0:
                fine_amount = abs(days) * self.config.fine_rate_per_day
                info_html += f"<br><span style='color: #D32F2F;'>⚠ Overdue by {abs(days)} days - Fine: ₹{fine_amount:.2f}</span>"
            
            self.return_info.setText(info_html)
            self.return_btn.setEnabled(True)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _return_book(self) -> None:
        """Process the book return."""
        if not self._selected_transaction:
            return
        
        try:
            transaction, fine_amount = self.trans_service.return_book(
                self._selected_transaction.transaction_id
            )
            
            msg = f"Book returned successfully!\n\nBook: {transaction.book_title}"
            
            if fine_amount:
                msg += f"\n\n⚠ Fine Generated: {format_currency(fine_amount)}"
            
            QMessageBox.information(self, "Book Returned", msg)
            
            # Reset and reload
            self._selected_transaction = None
            self.return_info.setText("Select a loan to return")
            self.return_info.setText("Select a loan to return")
            self.return_btn.setEnabled(False)
            self._load_active_loans_for_return()
            self.data_changed.emit()
            
        except LOCASError as e:
            QMessageBox.warning(self, "Return Failed", str(e))
    
    # -------------------------------------------------------------------------
    # Active Loans Tab
    # -------------------------------------------------------------------------
    
    def _create_active_loans_tab(self) -> QWidget:
        """Create the active loans overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_active_loans)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        
        self.loans_filter = QComboBox()
        self.loans_filter.addItems(["All Active Loans", "Overdue Only", "Due Today", "Due This Week"])
        self.loans_filter.currentIndexChanged.connect(self._refresh_active_loans)
        toolbar.addWidget(self.loans_filter)
        
        layout.addLayout(toolbar)
        
        # Stats
        stats_layout = QHBoxLayout()
        
        self.active_count_label = QLabel("Active: 0")
        self.active_count_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
            }
        """)
        stats_layout.addWidget(self.active_count_label)
        
        self.overdue_count_label = QLabel("Overdue: 0")
        self.overdue_count_label.setStyleSheet("""
            QLabel {
                background-color: #FFEBEE;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
                color: #C62828;
            }
        """)
        stats_layout.addWidget(self.overdue_count_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Loans table
        def format_overdue_status(value, row):
            days = days_until_due(row.get("due_date"))
            if days < 0:
                return f"🔴 Overdue ({abs(days)} days)"
            elif days == 0:
                return "🟡 Due Today"
            elif days <= 3:
                return f"🟠 Due Soon ({days} days)"
            else:
                return f"🟢 {days} days left"
        
        self.all_loans_table = DataTable([
            {"key": "book_title", "label": "Book", "stretch": True},
            {"key": "book_author", "label": "Author", "width": 140},
            {"key": "username", "label": "Student", "width": 100},
            {"key": "full_name", "label": "Name", "width": 140},
            {"key": "issue_date", "label": "Issued", "width": 90},
            {"key": "due_date", "label": "Status", "width": 130, "formatter": format_overdue_status},
        ])
        layout.addWidget(self.all_loans_table, 1)
        
        # Refresh on tab show
        self._refresh_active_loans()
        
        return widget
    
    def _refresh_active_loans(self) -> None:
        """Refresh the active loans display."""
        try:
            filter_idx = self.loans_filter.currentIndex()
            
            if filter_idx == 1:  # Overdue only
                transactions = self.trans_service.get_overdue_transactions(limit=200)
            else:
                transactions = self.trans_service.get_active_transactions(limit=200)
            
            # Apply additional filters
            if filter_idx == 2:  # Due today
                transactions = [t for t in transactions if days_until_due(t.due_date) == 0]
            elif filter_idx == 3:  # Due this week
                transactions = [t for t in transactions if 0 <= days_until_due(t.due_date) <= 7]
            
            data = [t.to_dict() for t in transactions]
            self.all_loans_table.set_data(data)
            
            # Update stats
            all_active = self.trans_service.get_active_transactions(limit=500)
            overdue = [t for t in all_active if days_until_due(t.due_date) < 0]
            
            self.active_count_label.setText(f"Active: {len(all_active)}")
            self.overdue_count_label.setText(f"Overdue: {len(overdue)}")
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def refresh(self) -> None:
        """Refresh all data in the view."""
        self._load_active_loans_for_return()
        self._refresh_active_loans()
