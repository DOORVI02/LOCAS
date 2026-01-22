"""Search bar widget for LOCAS."""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBar(QWidget):
    """Search bar with optional category filter and debouncing.

    Signals:
        search_triggered: Emitted when search is performed (query, category).
        cleared: Emitted when search is cleared.
    """

    search_triggered = pyqtSignal(str, str)
    cleared = pyqtSignal()

    def __init__(
        self,
        placeholder: str = "Search...",
        categories: list[str] | None = None,
        debounce_ms: int = 300,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize SearchBar.

        Args:
            placeholder: Placeholder text for search input.
            categories: Optional list of filter categories.
            debounce_ms: Milliseconds to debounce search (0 to disable).
            parent: Parent widget.
        """
        super().__init__(parent)

        self.debounce_ms = debounce_ms
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)

        self._setup_ui(placeholder, categories)
        self._setup_connections()

    def _setup_ui(self, placeholder: str, categories: list[str] | None) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Category filter (optional)
        if categories:
            self.category_combo = QComboBox()
            self.category_combo.addItem("All Categories", "")
            for cat in categories:
                self.category_combo.addItem(cat, cat)
            self.category_combo.setMinimumWidth(150)
            layout.addWidget(self.category_combo)
        else:
            self.category_combo = None

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(36)
        layout.addWidget(self.search_input, 1)

        # Search button
        self.search_btn = QPushButton("Search")
        self.search_btn.setMinimumHeight(36)
        layout.addWidget(self.search_btn)

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.search_btn.clicked.connect(self._do_search)
        self.search_input.returnPressed.connect(self._do_search)

        # Optional debouncing on text change
        if self.debounce_ms > 0:
            self.search_input.textChanged.connect(self._on_text_changed)

        # Clear event
        self.search_input.textChanged.connect(self._on_text_changed_check_clear)

        # Category change triggers search
        if self.category_combo:
            self.category_combo.currentIndexChanged.connect(self._do_search)

    def _on_text_changed(self, text: str) -> None:
        """Handle text change with debounce."""
        if self.debounce_ms > 0:
            self._debounce_timer.start(self.debounce_ms)

    def _on_text_changed_check_clear(self, text: str) -> None:
        """Check if text was cleared."""
        if not text:
            self.cleared.emit()

    def _do_search(self) -> None:
        """Perform the search."""
        query = self.search_input.text().strip()
        category = ""

        if self.category_combo:
            category = self.category_combo.currentData() or ""

        self.search_triggered.emit(query, category)

    def get_query(self) -> str:
        """Get current search query."""
        return self.search_input.text().strip()

    def get_category(self) -> str:
        """Get current category filter."""
        if self.category_combo:
            return self.category_combo.currentData() or ""
        return ""

    def set_categories(self, categories: list[str]) -> None:
        """Update the category list.

        Args:
            categories: New list of categories.
        """
        if self.category_combo:
            current = self.category_combo.currentData()
            self.category_combo.clear()
            self.category_combo.addItem("All Categories", "")
            for cat in categories:
                self.category_combo.addItem(cat, cat)

            # Restore selection if still valid
            idx = self.category_combo.findData(current)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

    def clear(self) -> None:
        """Clear the search bar."""
        self.search_input.clear()
        if self.category_combo:
            self.category_combo.setCurrentIndex(0)

    def set_query(self, query: str) -> None:
        """Set the search query.

        Args:
            query: Query text.
        """
        self.search_input.setText(query)
