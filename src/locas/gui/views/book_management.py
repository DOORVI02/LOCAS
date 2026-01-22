"""Book management view for LOCAS."""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QSplitter, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.book_service import BookService
from locas.models.book import Book, BookCreate, BookUpdate
from locas.gui.widgets.data_table import DataTable
from locas.gui.widgets.search_bar import SearchBar
from locas.gui.views.book_dialog import BookDialog
from locas.gui.views.copy_management import CopyManagementPanel


class BookManagementView(QWidget):
    """Book catalog management view.
    
    Features:
    - Book list with search
    - Add/Edit/Delete books
    - View book details
    - Manage copies
    """
    
    data_changed = pyqtSignal()
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize BookManagementView."""
        super().__init__(parent)
        
        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.book_service = BookService(config, db_manager, session_manager)
        
        self._selected_book: Optional[Book] = None
        
        self._setup_ui()
        self._setup_connections()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Book Management")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("+ Add Book")
        self.add_btn.setMinimumWidth(120)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Search bar
        categories = self.book_service.get_categories()
        self.search_bar = SearchBar(
            placeholder="Search by title, author, or ISBN...",
            categories=categories,
            debounce_ms=300
        )
        layout.addWidget(self.search_bar)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Book list
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.book_table = DataTable([
            {"key": "isbn", "label": "ISBN", "width": 120},
            {"key": "title", "label": "Title", "stretch": True},
            {"key": "author", "label": "Author", "width": 150},
            {"key": "category", "label": "Category", "width": 100},
            {"key": "available_copies", "label": "Available", "width": 80, "align": "center"},
            {"key": "total_copies", "label": "Total", "width": 70, "align": "center"},
        ])
        left_layout.addWidget(self.book_table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: #D32F2F; }
            QPushButton:hover { background-color: #C62828; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        action_layout.addWidget(self.delete_btn)
        
        action_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        action_layout.addWidget(self.refresh_btn)
        
        left_layout.addLayout(action_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Book details and copies
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        
        # Book details header
        self.detail_title = QLabel("Select a book")
        self.detail_title.setStyleSheet("font-size: 16px; font-weight: 600; border: none;")
        right_layout.addWidget(self.detail_title)
        
        self.detail_info = QLabel("")
        self.detail_info.setStyleSheet("color: #757575; border: none;")
        self.detail_info.setWordWrap(True)
        right_layout.addWidget(self.detail_info)
        
        # Copies tab
        self.copies_panel = CopyManagementPanel(
            self.config, self.db_manager, self.session_manager
        )
        right_layout.addWidget(self.copies_panel, 1)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter, 1)
    
    def _setup_connections(self) -> None:
        """Connect signals."""
        self.add_btn.clicked.connect(self._on_add_book)
        self.edit_btn.clicked.connect(self._on_edit_book)
        self.delete_btn.clicked.connect(self._on_delete_book)
        self.refresh_btn.clicked.connect(self._load_data)
        
        self.search_bar.search_triggered.connect(self._on_search)
        self.search_bar.cleared.connect(self._load_data)
        
        self.book_table.row_selected.connect(self._on_book_selected)
        self.book_table.row_double_clicked.connect(self._on_edit_book)
    
    def _load_data(self) -> None:
        """Load book data."""
        try:
            books = self.book_service.list_books(limit=500)
            data = [b.to_dict() for b in books]
            self.book_table.set_data(data)
            
            # Update categories
            categories = self.book_service.get_categories()
            self.search_bar.set_categories(categories)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_search(self, query: str, category: str) -> None:
        """Handle search."""
        try:
            if query:
                books = self.book_service.search_books(query=query, limit=500)
            elif category:
                books = self.book_service.search_books(category=category, limit=500)
            else:
                books = self.book_service.list_books(limit=500)
            
            data = [b.to_dict() for b in books]
            self.book_table.set_data(data)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_book_selected(self, row_data: dict) -> None:
        """Handle book selection."""
        book_id = row_data.get("book_id")
        if book_id:
            try:
                self._selected_book = self.book_service.get_book(book_id)
                self._update_detail_panel()
                self.edit_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                
                # Load copies
                self.copies_panel.set_book(self._selected_book)
                
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))
    
    def _update_detail_panel(self) -> None:
        """Update the detail panel with selected book."""
        if self._selected_book:
            book = self._selected_book
            self.detail_title.setText(book.title)
            
            info_parts = [
                f"<b>Author:</b> {book.author}",
                f"<b>ISBN:</b> {book.isbn}",
            ]
            if book.publisher:
                info_parts.append(f"<b>Publisher:</b> {book.publisher}")
            if book.publication_year:
                info_parts.append(f"<b>Year:</b> {book.publication_year}")
            if book.category:
                info_parts.append(f"<b>Category:</b> {book.category}")
            info_parts.append(
                f"<b>Copies:</b> {book.available_copies} available / {book.total_copies} total"
            )
            
            self.detail_info.setText("<br>".join(info_parts))
        else:
            self.detail_title.setText("Select a book")
            self.detail_info.setText("")
    
    def _on_add_book(self) -> None:
        """Handle add book."""
        dialog = BookDialog(self.book_service, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                book_data = BookCreate(
                    isbn=data["isbn"],
                    title=data["title"],
                    author=data["author"],
                    publisher=data.get("publisher"),
                    publication_year=data.get("publication_year"),
                    category=data.get("category"),
                    description=data.get("description")
                )
                
                book = self.book_service.create_book(book_data)
                QMessageBox.information(
                    self, "Success",
                    f"Book '{book.title}' created successfully!"
                )
                self._load_data()
                self.data_changed.emit()
                
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))
    
    def _on_edit_book(self, row_data: dict | None = None) -> None:
        """Handle edit book."""
        if self._selected_book is None:
            return
        
        dialog = BookDialog(
            self.book_service,
            book=self._selected_book,
            parent=self
        )
        if dialog.exec():
            data = dialog.get_data()
            try:
                update_data = BookUpdate(
                    isbn=data.get("isbn"),
                    title=data.get("title"),
                    author=data.get("author"),
                    publisher=data.get("publisher"),
                    publication_year=data.get("publication_year"),
                    category=data.get("category"),
                    description=data.get("description")
                )
                
                book = self.book_service.update_book(
                    self._selected_book.book_id,
                    update_data
                )
                self._selected_book = book
                self._update_detail_panel()
                self._load_data()
                
                QMessageBox.information(
                    self, "Success",
                    f"Book '{book.title}' updated successfully!"
                )
                self.data_changed.emit()
                
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))
    
    def _on_delete_book(self) -> None:
        """Handle delete book."""
        if self._selected_book is None:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{self._selected_book.title}'?\n\n"
            "This will also delete all copies of this book.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.book_service.delete_book(self._selected_book.book_id)
                QMessageBox.information(self, "Success", "Book deleted successfully!")
                self._selected_book = None
                self._update_detail_panel()
                self.copies_panel.clear()
                self.edit_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
                self._load_data()
                self.data_changed.emit()
                
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))
