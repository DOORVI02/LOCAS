"""Formatting utilities for LOCAS."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

from locas.core.constants import AppConstants


def format_date(
    dt: Optional[Union[date, datetime]],
    format_str: Optional[str] = None
) -> str:
    """Format a date for display.
    
    Args:
        dt: Date or datetime to format.
        format_str: Optional custom format string.
        
    Returns:
        Formatted date string, or empty string if None.
    """
    if dt is None:
        return ""
    
    if format_str:
        return dt.strftime(format_str)
    
    return dt.strftime(AppConstants.DISPLAY_DATE_FORMAT)


def format_datetime(
    dt: Optional[datetime],
    format_str: Optional[str] = None
) -> str:
    """Format a datetime for display.
    
    Args:
        dt: Datetime to format.
        format_str: Optional custom format string.
        
    Returns:
        Formatted datetime string, or empty string if None.
    """
    if dt is None:
        return ""
    
    if format_str:
        return dt.strftime(format_str)
    
    return dt.strftime(AppConstants.DISPLAY_DATETIME_FORMAT)


def format_currency(
    amount: Union[Decimal, float, int],
    symbol: str = "₹",
    decimal_places: int = 2
) -> str:
    """Format an amount as currency.
    
    Args:
        amount: Amount to format.
        symbol: Currency symbol (default: ₹).
        decimal_places: Number of decimal places.
        
    Returns:
        Formatted currency string.
    """
    if amount is None:
        return f"{symbol}0.00"
    
    # Convert to Decimal for precision
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Format with commas for Indian numbering (optional)
    formatted = f"{float(amount):,.{decimal_places}f}"
    
    return f"{symbol}{formatted}"


def format_status(status: str) -> str:
    """Format a status enum value for display.
    
    Args:
        status: Status string (e.g., 'active', 'pending').
        
    Returns:
        Title-cased status.
    """
    if not status:
        return ""
    return status.replace("_", " ").title()


def format_boolean(value: bool) -> str:
    """Format a boolean for display.
    
    Args:
        value: Boolean value.
        
    Returns:
        'Yes' or 'No'.
    """
    return "Yes" if value else "No"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to a maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to append if truncated.
        
    Returns:
        Truncated text.
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes.
        
    Returns:
        Formatted size string (e.g., '1.5 MB').
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(days: int) -> str:
    """Format a duration in days as human-readable.
    
    Args:
        days: Number of days.
        
    Returns:
        Formatted duration (e.g., '2 weeks, 3 days').
    """
    if days == 0:
        return "Today"
    
    if days == 1:
        return "1 day"
    
    if days < 7:
        return f"{days} days"
    
    weeks = days // 7
    remaining_days = days % 7
    
    if remaining_days == 0:
        return f"{weeks} week{'s' if weeks > 1 else ''}"
    
    return f"{weeks} week{'s' if weeks > 1 else ''}, {remaining_days} day{'s' if remaining_days > 1 else ''}"
