"""Reusable data table widget for LOCAS."""

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DataTable(QWidget):
    """Reusable table widget with built-in pagination and actions.

    Features:
    - Column configuration
    - Row selection
    - Context menu actions
    - Pagination
    - Custom rendering

    Signals:
        row_selected: Emitted when a row is selected (row data).
        row_double_clicked: Emitted on double-click (row data).
        action_triggered: Emitted when action button clicked (action, row data).
    """

    row_selected = pyqtSignal(dict)
    row_double_clicked = pyqtSignal(dict)
    action_triggered = pyqtSignal(str, dict)

    def __init__(self, columns: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        """Initialize DataTable.

        Args:
            columns: List of column definitions:
                - key: Data key to display
                - label: Column header text
                - width: Optional column width
                - align: Optional alignment ('left', 'center', 'right')
                - formatter: Optional callable to format value
            parent: Parent widget.
        """
        super().__init__(parent)

        self.columns = columns
        self._data: list[dict[str, Any]] = []
        self._page = 0
        self._page_size = 25

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([c.get("label", c["key"]) for c in self.columns])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # Configure columns
        header = self.table.horizontalHeader()
        for i, col in enumerate(self.columns):
            if col.get("width"):
                self.table.setColumnWidth(i, col["width"])
            elif col.get("stretch", False):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Pagination
        pagination_layout = QHBoxLayout()

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)

        pagination_layout.addStretch()

        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("color: #757575;")
        pagination_layout.addWidget(self.page_label)

        pagination_layout.addStretch()

        self.next_btn = QPushButton("Next →")
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)

        layout.addLayout(pagination_layout)

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)

    def set_data(self, data: list[dict[str, Any]]) -> None:
        """Set the table data.

        Args:
            data: List of row data dictionaries.
        """
        self._data = data
        self._page = 0
        self._refresh_table()

    def get_data(self) -> list[dict[str, Any]]:
        """Get the current data."""
        return self._data

    def _refresh_table(self) -> None:
        """Refresh the table display."""
        # Calculate visible rows
        start = self._page * self._page_size
        end = min(start + self._page_size, len(self._data))
        visible_data = self._data[start:end]

        self.table.setRowCount(len(visible_data))

        for row_idx, row_data in enumerate(visible_data):
            for col_idx, col in enumerate(self.columns):
                key = col["key"]
                value = row_data.get(key, "")

                # Apply formatter if provided
                formatter = col.get("formatter")
                if formatter and callable(formatter):
                    display_value = formatter(value, row_data)
                else:
                    display_value = str(value) if value is not None else ""

                item = QTableWidgetItem(display_value)

                # Alignment
                align = col.get("align", "left")
                if align == "center":
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif align == "right":
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(row_idx, col_idx, item)

        # Update pagination
        total_pages = max(1, (len(self._data) + self._page_size - 1) // self._page_size)
        self.page_label.setText(f"Page {self._page + 1} of {total_pages}")
        self.prev_btn.setEnabled(self._page > 0)
        self.next_btn.setEnabled(end < len(self._data))

    def _on_selection_changed(self) -> None:
        """Handle row selection change."""
        row_data = self.get_selected_row()
        if row_data:
            self.row_selected.emit(row_data)

    def _on_double_click(self, row: int, col: int) -> None:
        """Handle double-click."""
        row_data = self.get_row_data(row)
        if row_data:
            self.row_double_clicked.emit(row_data)

    def get_selected_row(self) -> dict[str, Any] | None:
        """Get the currently selected row data.

        Returns:
            Row data or None if nothing selected.
        """
        selected = self.table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        return self.get_row_data(row)

    def get_row_data(self, row: int) -> dict[str, Any] | None:
        """Get data for a specific row.

        Args:
            row: Row index in visible table.

        Returns:
            Row data or None.
        """
        actual_idx = self._page * self._page_size + row
        if 0 <= actual_idx < len(self._data):
            return self._data[actual_idx]
        return None

    def _prev_page(self) -> None:
        """Go to previous page."""
        if self._page > 0:
            self._page -= 1
            self._refresh_table()

    def _next_page(self) -> None:
        """Go to next page."""
        max_page = (len(self._data) - 1) // self._page_size
        if self._page < max_page:
            self._page += 1
            self._refresh_table()

    def refresh(self) -> None:
        """Refresh the current display."""
        self._refresh_table()

    def clear(self) -> None:
        """Clear all data."""
        self._data = []
        self.table.setRowCount(0)
        self.page_label.setText("Page 1")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
