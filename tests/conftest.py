"""Test configuration for LOCAS."""

import pytest
from locas.config import Config


@pytest.fixture
def config():
    """Provide a test configuration."""
    return Config(
        db_host="localhost",
        db_port=3306,
        db_name="locas_test",
        db_user="root",
        db_password="",
        max_borrow_days=14,
        max_borrow_limit=3,
        fine_rate_per_day=5.00,
    )
