"""Book data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class Book:
    """Represents a book in the catalog.
    
    Attributes:
        book_id: Unique identifier.
        isbn: International Standard Book Number.
        title: Book title.
        author: Book author(s).
        publisher: Publisher name.
        publication_year: Year of publication.
        category: Book category/genre.
        description: Book description.
        total_copies: Total number of physical copies.
        available_copies: Number of copies currently available.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """
    
    book_id: int
    isbn: str
    title: str
    author: str
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    total_copies: int = 0
    available_copies: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        """Create Book instance from dictionary.
        
        Args:
            data: Dictionary with book data.
            
        Returns:
            Book instance.
        """
        return cls(
            book_id=data["book_id"],
            isbn=data["isbn"],
            title=data["title"],
            author=data["author"],
            publisher=data.get("publisher"),
            publication_year=data.get("publication_year"),
            category=data.get("category"),
            description=data.get("description"),
            total_copies=data.get("total_copies", 0),
            available_copies=data.get("available_copies", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert Book to dictionary."""
        return {
            "book_id": self.book_id,
            "isbn": self.isbn,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "publication_year": self.publication_year,
            "category": self.category,
            "description": self.description,
            "total_copies": self.total_copies,
            "available_copies": self.available_copies,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @property
    def issued_copies(self) -> int:
        """Get number of currently issued copies."""
        return self.total_copies - self.available_copies
    
    @property
    def is_available(self) -> bool:
        """Check if any copies are available."""
        return self.available_copies > 0


@dataclass
class BookCreate:
    """DTO for creating a new book.
    
    Attributes:
        isbn: ISBN (13 or 10 digit).
        title: Book title.
        author: Author name(s).
        publisher: Publisher name.
        publication_year: Year of publication.
        category: Book category.
        description: Book description.
    """
    
    isbn: str
    title: str
    author: str
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None


@dataclass
class BookUpdate:
    """DTO for updating a book.
    
    All fields optional - only non-None values updated.
    """
    
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    
    def to_update_dict(self) -> dict[str, Any]:
        """Get dictionary of non-None fields."""
        result = {}
        for field_name in ["isbn", "title", "author", "publisher", 
                          "publication_year", "category", "description"]:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result
