"""Book create/edit dialog for LOCAS."""

from typing import Optional
from PyQt6.QtWidgets import QWidget

from locas.services.book_service import BookService
from locas.models.book import Book
from locas.gui.widgets.form_dialog import FormDialog, FormField
from locas.utils.validators import validate_isbn


def _validate_isbn_field(value: str) -> tuple[bool, str]:
    """Validate ISBN field."""
    try:
        validate_isbn(value)
        return True, ""
    except Exception as e:
        return False, str(e)


class BookDialog(FormDialog):
    """Dialog for creating or editing a book."""
    
    def __init__(
        self,
        book_service: BookService,
        book: Optional[Book] = None,
        parent: QWidget | None = None
    ) -> None:
        """Initialize BookDialog.
        
        Args:
            book_service: Book service for categories.
            book: Optional book for edit mode.
            parent: Parent widget.
        """
        self.book_service = book_service
        self.book = book
        
        # Get categories for dropdown
        categories = book_service.get_categories()
        category_options = [("", "")] + [(c, c) for c in categories]
        
        # Define form fields
        fields = [
            FormField(
                key="isbn",
                label="ISBN",
                field_type="text",
                required=True,
                placeholder="978-0-123456-78-9",
                validator=_validate_isbn_field
            ),
            FormField(
                key="title",
                label="Title",
                field_type="text",
                required=True,
                placeholder="Enter book title"
            ),
            FormField(
                key="author",
                label="Author",
                field_type="text",
                required=True,
                placeholder="Author name(s)"
            ),
            FormField(
                key="publisher",
                label="Publisher",
                field_type="text",
                required=False,
                placeholder="Publisher name"
            ),
            FormField(
                key="publication_year",
                label="Publication Year",
                field_type="year",
                required=False,
                min_value=1800,
                max_value=2100,
                default=2024
            ),
            FormField(
                key="category",
                label="Category",
                field_type="select",
                required=False,
                options=category_options,
                editable=True,
                placeholder="Select or type new category"
            ),
            FormField(
                key="description",
                label="Description",
                field_type="textarea",
                required=False,
                placeholder="Brief description of the book"
            ),
        ]
        
        # Prepare initial data for edit mode
        initial_data = {}
        if book:
            initial_data = {
                "isbn": book.isbn,
                "title": book.title,
                "author": book.author,
                "publisher": book.publisher,
                "publication_year": book.publication_year,
                "category": book.category,
                "description": book.description,
            }
        
        title = "Edit Book" if book else "Add New Book"
        
        super().__init__(title, fields, initial_data, parent)
