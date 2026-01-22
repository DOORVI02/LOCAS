"""Custom exceptions for LOCAS."""


class LOCASError(Exception):
    """Base exception for all LOCAS errors.

    All custom exceptions in the application inherit from this class.
    """

    def __init__(self, message: str = "An error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class AuthenticationError(LOCASError):
    """Raised when authentication fails.

    Examples:
    - Invalid username/password
    - Account locked
    - Account deactivated
    """

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AuthorizationError(LOCASError):
    """Raised when user lacks permission for an action.

    Examples:
    - Accessing admin-only features as student
    - Attempting to modify another user's data
    """

    def __init__(self, message: str = "You don't have permission for this action") -> None:
        super().__init__(message)


class ValidationError(LOCASError):
    """Raised when input validation fails.

    Examples:
    - Invalid email format
    - Password too weak
    - Required field missing
    """

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message)


class DatabaseError(LOCASError):
    """Raised when database operations fail.

    Examples:
    - Connection failure
    - Query execution error
    - Transaction failure
    """

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(message)


class NotFoundError(LOCASError):
    """Raised when a requested resource doesn't exist.

    Examples:
    - Book not found
    - User not found
    - Copy not found
    """

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class DuplicateError(LOCASError):
    """Raised when attempting to create a duplicate record.

    Examples:
    - Username already exists
    - ISBN already registered
    - Barcode already in use
    """

    def __init__(self, message: str = "Record already exists") -> None:
        super().__init__(message)


class BusinessRuleError(LOCASError):
    """Raised when a business rule is violated.

    Examples:
    - Student has too many books borrowed
    - Student has unpaid fines over threshold
    - Book copy not available for issue
    """

    def __init__(self, message: str = "Business rule violation") -> None:
        super().__init__(message)


class SessionError(LOCASError):
    """Raised for session-related issues.

    Examples:
    - Session expired
    - No active session
    """

    def __init__(self, message: str = "Session error") -> None:
        super().__init__(message)
