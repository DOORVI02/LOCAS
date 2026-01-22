"""Input validation utilities for LOCAS."""

import re

from locas.core.constants import AppConstants
from locas.core.exceptions import ValidationError


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate.

    Returns:
        True if valid.

    Raises:
        ValidationError: If email is invalid.
    """
    if not email:
        raise ValidationError("Email is required")

    if len(email) > AppConstants.EMAIL_MAX_LENGTH:
        raise ValidationError(f"Email must be at most {AppConstants.EMAIL_MAX_LENGTH} characters")

    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")

    return True


def validate_username(username: str) -> bool:
    """Validate username format.

    Requirements:
    - 4-50 characters
    - Alphanumeric, underscores, and dots allowed
    - Must start with a letter

    Args:
        username: Username to validate.

    Returns:
        True if valid.

    Raises:
        ValidationError: If username is invalid.
    """
    if not username:
        raise ValidationError("Username is required")

    if len(username) < AppConstants.USERNAME_MIN_LENGTH:
        raise ValidationError(
            f"Username must be at least {AppConstants.USERNAME_MIN_LENGTH} characters"
        )

    if len(username) > AppConstants.USERNAME_MAX_LENGTH:
        raise ValidationError(
            f"Username must be at most {AppConstants.USERNAME_MAX_LENGTH} characters"
        )

    # Must start with letter, then alphanumeric/underscore/dot
    pattern = r"^[a-zA-Z][a-zA-Z0-9_.]*$"
    if not re.match(pattern, username):
        raise ValidationError(
            "Username must start with a letter and contain only letters, "
            "numbers, underscores, and dots"
        )

    return True


def validate_isbn(isbn: str) -> bool:
    """Validate ISBN format.

    Accepts ISBN-10 or ISBN-13 format.

    Args:
        isbn: ISBN to validate.

    Returns:
        True if valid.

    Raises:
        ValidationError: If ISBN is invalid.
    """
    if not isbn:
        raise ValidationError("ISBN is required")

    # Remove hyphens and spaces
    clean_isbn = re.sub(r"[-\s]", "", isbn)

    if len(clean_isbn) == 10:
        return _validate_isbn10(clean_isbn)
    elif len(clean_isbn) == 13:
        return _validate_isbn13(clean_isbn)
    else:
        raise ValidationError("ISBN must be 10 or 13 digits")


def _validate_isbn10(isbn: str) -> bool:
    """Validate ISBN-10 checksum."""
    if not re.match(r"^\d{9}[\dXx]$", isbn):
        raise ValidationError("Invalid ISBN-10 format")

    total = 0
    for i, char in enumerate(isbn[:-1]):
        total += int(char) * (10 - i)

    check = isbn[-1].upper()
    if check == "X":
        total += 10
    else:
        total += int(check)

    if total % 11 != 0:
        raise ValidationError("Invalid ISBN-10 checksum")

    return True


def _validate_isbn13(isbn: str) -> bool:
    """Validate ISBN-13 checksum."""
    if not re.match(r"^\d{13}$", isbn):
        raise ValidationError("Invalid ISBN-13 format")

    total = 0
    for i, char in enumerate(isbn):
        if i % 2 == 0:
            total += int(char)
        else:
            total += int(char) * 3

    if total % 10 != 0:
        raise ValidationError("Invalid ISBN-13 checksum")

    return True


def validate_barcode(barcode: str) -> bool:
    """Validate barcode format.

    Args:
        barcode: Barcode to validate.

    Returns:
        True if valid.

    Raises:
        ValidationError: If barcode is invalid.
    """
    if not barcode:
        raise ValidationError("Barcode is required")

    if len(barcode) > AppConstants.BARCODE_MAX_LENGTH:
        raise ValidationError(
            f"Barcode must be at most {AppConstants.BARCODE_MAX_LENGTH} characters"
        )

    # Alphanumeric with optional hyphens
    pattern = r"^[a-zA-Z0-9-]+$"
    if not re.match(pattern, barcode):
        raise ValidationError("Barcode must contain only letters, numbers, and hyphens")

    return True


def validate_full_name(full_name: str) -> bool:
    """Validate full name.

    Args:
        full_name: Name to validate.

    Returns:
        True if valid.

    Raises:
        ValidationError: If name is invalid.
    """
    if not full_name or not full_name.strip():
        raise ValidationError("Full name is required")

    if len(full_name) > AppConstants.FULL_NAME_MAX_LENGTH:
        raise ValidationError(
            f"Full name must be at most {AppConstants.FULL_NAME_MAX_LENGTH} characters"
        )

    return True


def validate_required(value: str | None, field_name: str) -> bool:
    """Validate that a value is not empty.

    Args:
        value: Value to check.
        field_name: Name of field for error message.

    Returns:
        True if valid.

    Raises:
        ValidationError: If value is empty.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")

    return True
