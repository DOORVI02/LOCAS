"""Date utility functions for LOCAS."""

from datetime import date, datetime, timedelta
from typing import Union


def calculate_due_date(
    issue_date: Union[date, datetime, None] = None,
    borrow_days: int = 14
) -> date:
    """Calculate due date for a book issue.
    
    Args:
        issue_date: Date of issue (defaults to today).
        borrow_days: Number of days to borrow.
        
    Returns:
        Due date.
    """
    if issue_date is None:
        issue_date = date.today()
    elif isinstance(issue_date, datetime):
        issue_date = issue_date.date()
    
    return issue_date + timedelta(days=borrow_days)


def calculate_days_overdue(
    due_date: Union[date, datetime],
    return_date: Union[date, datetime, None] = None
) -> int:
    """Calculate number of days a book is overdue.
    
    Args:
        due_date: Due date of the book.
        return_date: Actual return date (defaults to today).
        
    Returns:
        Number of days overdue (0 if not overdue).
    """
    if isinstance(due_date, datetime):
        due_date = due_date.date()
    
    if return_date is None:
        check_date = date.today()
    elif isinstance(return_date, datetime):
        check_date = return_date.date()
    else:
        check_date = return_date
    
    delta = (check_date - due_date).days
    return max(0, delta)


def is_overdue(
    due_date: Union[date, datetime],
    check_date: Union[date, datetime, None] = None
) -> bool:
    """Check if a due date has passed.
    
    Args:
        due_date: Due date to check.
        check_date: Date to check against (defaults to today).
        
    Returns:
        True if overdue.
    """
    if isinstance(due_date, datetime):
        due_date = due_date.date()
    
    if check_date is None:
        check_date = date.today()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    return check_date > due_date


def days_until_due(due_date: Union[date, datetime]) -> int:
    """Calculate days remaining until due date.
    
    Args:
        due_date: Due date.
        
    Returns:
        Days until due (negative if overdue).
    """
    if isinstance(due_date, datetime):
        due_date = due_date.date()
    
    delta = (due_date - date.today()).days
    return delta


def get_date_range(days_back: int = 30) -> tuple[date, date]:
    """Get a date range from N days ago to today.
    
    Args:
        days_back: Number of days to go back.
        
    Returns:
        Tuple of (start_date, end_date).
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date


def format_relative_date(dt: Union[date, datetime]) -> str:
    """Format a date relative to today.
    
    Args:
        dt: Date to format.
        
    Returns:
        Relative description (e.g., 'Today', 'Yesterday', '3 days ago').
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    today = date.today()
    delta = (today - dt).days
    
    if delta == 0:
        return "Today"
    elif delta == 1:
        return "Yesterday"
    elif delta == -1:
        return "Tomorrow"
    elif delta > 0:
        if delta < 7:
            return f"{delta} days ago"
        elif delta < 30:
            weeks = delta // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = delta // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        # Future dates
        abs_delta = abs(delta)
        if abs_delta < 7:
            return f"In {abs_delta} days"
        elif abs_delta < 30:
            weeks = abs_delta // 7
            return f"In {weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = abs_delta // 30
            return f"In {months} month{'s' if months > 1 else ''}"
