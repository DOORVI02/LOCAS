"""Book search view for students."""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QMessageBox
)
from PyQt6.QtCore import Qt

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.core.security import SessionManager
from locas.core.exceptions import LOCASError
from locas.services.book_service import BookService
from locas.models.book import Book
from locas.gui.widgets.data_table import DataTable
from locas.gui.widgets.search_bar import SearchBar


class BookSearchView(QWidget):
    """Book search view for students.
    
    Read-only view to search and browse the book catalog.
    Shows availability status.
    """
    
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None
    ) -> None:
        """Initialize BookSearchView."""
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
        header = QLabel("Search Books")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(header)
        
        # Search bar
        categories = self.book_service.get_categories()
        self.search_bar = SearchBar(
            placeholder="Search by title, author, or ISBN...",
            categories=categories,
            debounce_ms=300
        )
        layout.addWidget(self.search_bar)
        
        # Results table
        def format_availability(value, row):
            available = row.get("available_copies", 0)
            total = row.get("total_copies", 0)
            if available > 0:
                return f"✓ Available ({available}/{total})"
            else:
                return f"✗ Not Available (0/{total})"
        
        self.results_table = DataTable([
            {"key": "title", "label": "Title", "stretch": True},
            {"key": "author", "label": "Author", "width": 180},
            {"key": "isbn", "label": "ISBN", "width": 130},
            {"key": "category", "label": "Category", "width": 100},
            {"key": "available_copies", "label": "Availability", "width": 150, 
             "formatter": format_availability},
        ])
        layout.addWidget(self.results_table, 1)
        
        # Book details panel
        self.detail_panel = QFrame()
        self.detail_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 16px;
            }
        """)
        detail_layout = QVBoxLayout(self.detail_panel)
        
        self.detail_title = QLabel("Select a book to view details")
        self.detail_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        detail_layout.addWidget(self.detail_title)
        
        self.detail_info = QLabel("")
        self.detail_info.setStyleSheet("color: #424242;")
        self.detail_info.setWordWrap(True)
        detail_layout.addWidget(self.detail_info)
        
        layout.addWidget(self.detail_panel)
    
    def _setup_connections(self) -> None:
        """Connect signals."""
        self.search_bar.search_triggered.connect(self._on_search)
        self.search_bar.cleared.connect(self._load_data)
        self.results_table.row_selected.connect(self._on_book_selected)
    
    def _load_data(self) -> None:
        """Load initial book data."""
        try:
            books = self.book_service.list_books(limit=100)
            data = [b.to_dict() for b in books]
            self.results_table.set_data(data)
            
            # Update categories
            categories = self.book_service.get_categories()
            self.search_bar.set_categories(categories)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_search(self, query: str, category: str) -> None:
        """Handle search."""
        try:
            if query:
                books = self.book_service.search_books(query=query, limit=100)
            elif category:
                books = self.book_service.search_books(category=category, limit=100)
            else:
                books = self.book_service.list_books(limit=100)
            
            data = [b.to_dict() for b in books]
            self.results_table.set_data(data)
            
        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def _on_book_selected(self, row_data: dict) -> None:
        """Handle book selection."""
        book_id = row_data.get("book_id")
        if book_id:
            try:
                book = self.book_service.get_book(book_id)
                self._update_detail_panel(book)
            except LOCASError:
                pass
    
    def _update_detail_panel(self, book: Book) -> None:
        """Update the detail panel."""
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
        
        if book.available_copies > 0:
            info_parts.append(
                f"<b style='color: #388E3C;'>Available:</b> "
                f"{book.available_copies} of {book.total_copies} copies"
            )
        else:
            info_parts.append(
                f"<b style='color: #D32F2F;'>Currently Unavailable</b> "
                f"(0 of {book.total_copies} copies available)"
            )
        
        if book.description:
            info_parts.append(f"<br><b>Description:</b><br>{book.description}")
        
        self.detail_info.setText("<br>".join(info_parts))
