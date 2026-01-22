"""Form dialog widget for LOCAS."""

from typing import Any, Callable, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QPushButton,
    QWidget, QMessageBox
)
from PyQt6.QtCore import Qt


class FormField:
    """Definition for a form field."""
    
    def __init__(
        self,
        key: str,
        label: str,
        field_type: str = "text",
        required: bool = False,
        placeholder: str = "",
        options: list[tuple[str, Any]] | None = None,
        min_value: int = 0,
        max_value: int = 9999,
        default: Any = None,
        editable: bool = False,
        validator: Callable[[Any], tuple[bool, str]] | None = None
    ):
        """Initialize FormField.
        
        Args:
            key: Data key for this field.
            label: Display label.
            field_type: Type ('text', 'password', 'textarea', 'select', 'number', 'year').
            required: Whether field is required.
            placeholder: Placeholder text.
            options: Options for select field [(display, value), ...].
            min_value: Minimum value for number fields.
            max_value: Maximum value for number fields.
            default: Default value.
            default: Default value.
            editable: Whether the field is editable (for select/combobox).
            validator: Optional validation function returning (is_valid, error_message).
        """
        self.key = key
        self.label = label
        self.field_type = field_type
        self.required = required
        self.placeholder = placeholder
        self.options = options or []
        self.min_value = min_value
        self.max_value = max_value
        self.default = default
        self.editable = editable
        self.validator = validator


class FormDialog(QDialog):
    """Reusable form dialog for create/edit operations.
    
    Supports various field types and validation.
    """
    
    def __init__(
        self,
        title: str,
        fields: list[FormField],
        data: dict[str, Any] | None = None,
        parent: QWidget | None = None
    ) -> None:
        """Initialize FormDialog.
        
        Args:
            title: Dialog title.
            fields: List of FormField definitions.
            data: Optional initial data for edit mode.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.fields = fields
        self.initial_data = data or {}
        self._widgets: dict[str, QWidget] = {}
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        for field in self.fields:
            label_text = field.label
            if field.required:
                label_text += " *"
            
            label = QLabel(label_text)
            widget = self._create_field_widget(field)
            self._widgets[field.key] = widget
            form_layout.addRow(label, widget)
        
        layout.addLayout(form_layout)
        
        # Required fields note
        required_fields = [f for f in self.fields if f.required]
        if required_fields:
            note = QLabel("* Required fields")
            note.setStyleSheet("color: #757575; font-size: 12px;")
            layout.addWidget(note)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #424242;
                border: 1px solid #E0E0E0;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_field_widget(self, field: FormField) -> QWidget:
        """Create appropriate widget for field type."""
        if field.field_type == "text":
            widget = QLineEdit()
            widget.setPlaceholderText(field.placeholder)
            return widget
        
        elif field.field_type == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.setPlaceholderText(field.placeholder)
            return widget
        
        elif field.field_type == "textarea":
            widget = QTextEdit()
            widget.setPlaceholderText(field.placeholder)
            widget.setMaximumHeight(100)
            return widget
        
        elif field.field_type == "select":
            widget = QComboBox()
            widget.setEditable(field.editable)
            for display, value in field.options:
                widget.addItem(display, value)
            return widget
        
        elif field.field_type in ("number", "year"):
            widget = QSpinBox()
            widget.setMinimum(field.min_value)
            widget.setMaximum(field.max_value)
            if field.field_type == "year":
                widget.setMinimum(1800)
                widget.setMaximum(2100)
                widget.setValue(2024)
            return widget
        
        else:
            return QLineEdit()
    
    def _load_data(self) -> None:
        """Load initial data into form fields."""
        for field in self.fields:
            widget = self._widgets.get(field.key)
            value = self.initial_data.get(field.key, field.default)
            
            if value is None:
                continue
            
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))
            elif isinstance(widget, QComboBox):
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setCurrentText(str(value))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value) if value else 0)
    
    def _get_field_value(self, field: FormField) -> Any:
        """Get value from a field widget."""
        widget = self._widgets.get(field.key)
        
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        elif isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        elif isinstance(widget, QComboBox):
            if widget.isEditable():
                return widget.currentText().strip()
            return widget.currentData()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        
        return None
    
    def _on_save(self) -> None:
        """Handle save button click."""
        # Validate
        errors = []
        
        for field in self.fields:
            value = self._get_field_value(field)
            
            # Check required
            if field.required:
                if value is None or (isinstance(value, str) and not value):
                    errors.append(f"{field.label} is required")
                    continue
            
            # Custom validation
            if field.validator and value:
                is_valid, error = field.validator(value)
                if not is_valid:
                    errors.append(f"{field.label}: {error}")
        
        if errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "\n".join(errors)
            )
            return
        
        self.accept()
    
    def get_data(self) -> dict[str, Any]:
        """Get form data as dictionary.
        
        Returns:
            Dictionary of field values.
        """
        data = {}
        for field in self.fields:
            value = self._get_field_value(field)
            # Don't include empty optional fields
            if value is not None and (value != "" or field.required):
                data[field.key] = value
        return data
