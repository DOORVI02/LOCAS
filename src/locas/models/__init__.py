"""Data models for LOCAS."""

from locas.models.audit_log import AuditLog, AuditLogCreate
from locas.models.book import Book, BookCreate, BookUpdate
from locas.models.book_copy import BookCopy, BookCopyCreate, BookCopyUpdate
from locas.models.fine import Fine, FineCreate
from locas.models.transaction import Transaction, TransactionCreate
from locas.models.user import User, UserCreate, UserUpdate

__all__ = [
    # User
    "User",
    "UserCreate",
    "UserUpdate",
    # Book
    "Book",
    "BookCreate",
    "BookUpdate",
    # BookCopy
    "BookCopy",
    "BookCopyCreate",
    "BookCopyUpdate",
    # Transaction
    "Transaction",
    "TransactionCreate",
    # Fine
    "Fine",
    "FineCreate",
    # AuditLog
    "AuditLog",
    "AuditLogCreate",
]
