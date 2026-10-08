"""
Pytest Global Fixtures and Database Lifecycle Setup.
"""

import pytest

from app.database.database import init_db


@pytest.fixture(autouse=True)
async def ensure_db_initialized():
    """Guarantee that tables are created before each test runs."""
    await init_db()
