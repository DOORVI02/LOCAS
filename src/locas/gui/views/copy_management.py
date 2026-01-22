"""Copy management panel for LOCAS."""

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from locas.config import Config
from locas.core.constants import BookCopyStatus
from locas.core.database import DatabaseManager
from locas.core.exceptions import LOCASError
from locas.core.security import SessionManager
from locas.gui.widgets.data_table import DataTable
from locas.models.book import Book
from locas.models.book_copy import BookCopyCreate
from locas.services.book_service import BookService


class AddCopyDialog(QDialog):
    """Dialog for adding a new book copy."""

    def __init__(self, book: Book, parent: QWidget | None = None) -> None:
        """Initialize AddCopyDialog."""
        super().__init__(parent)

        self.book = book

        self.setWindowTitle(f"Add Copy - {book.title}")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Info
        info = QLabel(f"Adding copy for: <b>{self.book.title}</b>")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("e.g., LIB-001-2024")
        form.addRow("Barcode *:", self.barcode_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g., Shelf A-12")
        form.addRow("Location:", self.location_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #424242;
                border: 1px solid #E0E0E0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Add Copy")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self) -> None:
        """Handle save."""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "Error", "Barcode is required")
            return

        self.accept()

    def get_data(self) -> dict:
        """Get form data."""
        return {
            "barcode": self.barcode_input.text().strip(),
            "location": self.location_input.text().strip() or None,
        }


class CopyManagementPanel(QWidget):
    """Panel for managing book copies."""

    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        session_manager: SessionManager,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize CopyManagementPanel."""
        super().__init__(parent)

        self.config = config
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.book_service = BookService(config, db_manager, session_manager)

        self._book: Book | None = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()

        title = QLabel("Copies")
        title.setStyleSheet("font-size: 14px; font-weight: 600; border: none;")
        header.addWidget(title)

        header.addStretch()

        self.add_copy_btn = QPushButton("+ Add Copy")
        self.add_copy_btn.setEnabled(False)
        self.add_copy_btn.setStyleSheet("border: none;")
        header.addWidget(self.add_copy_btn)

        layout.addLayout(header)

        # Copy table
        def format_status(value, row):
            status = BookCopyStatus(value) if value else BookCopyStatus.AVAILABLE
            return status.display_name

        self.copy_table = DataTable(
            [
                {"key": "barcode", "label": "Barcode", "width": 120},
                {"key": "status", "label": "Status", "width": 80, "formatter": format_status},
                {"key": "location", "label": "Location", "stretch": True},
            ]
        )
        self.copy_table.setStyleSheet("border: none;")
        layout.addWidget(self.copy_table, 1)

        # Actions
        action_layout = QHBoxLayout()

        self.mark_lost_btn = QPushButton("Mark Lost")
        self.mark_lost_btn.setEnabled(False)
        self.mark_lost_btn.setStyleSheet("""
            QPushButton { background-color: #F57C00; border: none; }
            QPushButton:hover { background-color: #E65100; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        action_layout.addWidget(self.mark_lost_btn)

        self.mark_damaged_btn = QPushButton("Mark Damaged")
        self.mark_damaged_btn.setEnabled(False)
        self.mark_damaged_btn.setStyleSheet("""
            QPushButton { background-color: #D32F2F; border: none; }
            QPushButton:hover { background-color: #C62828; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        action_layout.addWidget(self.mark_damaged_btn)

        action_layout.addStretch()

        self.delete_copy_btn = QPushButton("Delete")
        self.delete_copy_btn.setEnabled(False)
        self.delete_copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #D32F2F;
                border: 1px solid #E0E0E0;
            }
            QPushButton:hover { background-color: #FFEBEE; }
            QPushButton:disabled { background-color: #F5F5F5; color: #BDBDBD; }
        """)
        action_layout.addWidget(self.delete_copy_btn)

        layout.addLayout(action_layout)

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.add_copy_btn.clicked.connect(self._on_add_copy)
        self.mark_lost_btn.clicked.connect(self._on_mark_lost)
        self.mark_damaged_btn.clicked.connect(self._on_mark_damaged)
        self.delete_copy_btn.clicked.connect(self._on_delete_copy)

        self.copy_table.row_selected.connect(self._on_copy_selected)

    def set_book(self, book: Book) -> None:
        """Set the current book and load copies.

        Args:
            book: Book to show copies for.
        """
        self._book = book
        self.add_copy_btn.setEnabled(True)
        self._load_copies()

    def clear(self) -> None:
        """Clear the panel."""
        self._book = None
        self.copy_table.clear()
        self.add_copy_btn.setEnabled(False)
        self._disable_actions()

    def _load_copies(self) -> None:
        """Load copies for current book."""
        if self._book is None:
            return

        try:
            copies = self.book_service.get_copies_by_book(self._book.book_id)
            data = [c.to_dict() for c in copies]
            self.copy_table.set_data(data)
            self._disable_actions()

        except LOCASError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_copy_selected(self, row_data: dict) -> None:
        """Handle copy selection."""
        status = row_data.get("status")

        # Enable actions based on status
        self.mark_lost_btn.setEnabled(status == "available")
        self.mark_damaged_btn.setEnabled(status == "available")
        self.delete_copy_btn.setEnabled(status != "issued")

    def _disable_actions(self) -> None:
        """Disable all action buttons."""
        self.mark_lost_btn.setEnabled(False)
        self.mark_damaged_btn.setEnabled(False)
        self.delete_copy_btn.setEnabled(False)

    def _on_add_copy(self) -> None:
        """Handle add copy."""
        if self._book is None:
            return

        dialog = AddCopyDialog(self._book, self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                copy_data = BookCopyCreate(
                    book_id=self._book.book_id,
                    barcode=data["barcode"],
                    location=data.get("location"),
                )

                copy = self.book_service.add_copy(copy_data)
                QMessageBox.information(
                    self, "Success", f"Copy '{copy.barcode}' added successfully!"
                )
                self._load_copies()

                # Refresh book to update counts
                self._book = self.book_service.get_book(self._book.book_id)

            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _get_selected_copy_id(self) -> int | None:
        """Get the selected copy ID."""
        row_data = self.copy_table.get_selected_row()
        return row_data.get("copy_id") if row_data else None

    def _on_mark_lost(self) -> None:
        """Handle mark as lost."""
        copy_id = self._get_selected_copy_id()
        if copy_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Mark this copy as lost?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.book_service.mark_copy_lost(copy_id)
                self._load_copies()
                QMessageBox.information(self, "Success", "Copy marked as lost.")
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _on_mark_damaged(self) -> None:
        """Handle mark as damaged."""
        copy_id = self._get_selected_copy_id()
        if copy_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Mark this copy as damaged?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.book_service.mark_copy_damaged(copy_id)
                self._load_copies()
                QMessageBox.information(self, "Success", "Copy marked as damaged.")
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _on_delete_copy(self) -> None:
        """Handle delete copy."""
        copy_id = self._get_selected_copy_id()
        if copy_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this copy?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.book_service.delete_copy(copy_id)
                self._load_copies()
                QMessageBox.information(self, "Success", "Copy deleted.")
            except LOCASError as e:
                QMessageBox.warning(self, "Error", str(e))
