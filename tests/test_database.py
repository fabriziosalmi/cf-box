"""Tests for database operations."""

import pytest
from pathlib import Path
import tempfile
import os

from cf_box.database import DatabaseManager, CloudflareAccount, CloudflareZone, CloudflareDNSRecord


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield db_path

    @pytest.fixture
    def db_manager(self, temp_db):
        """Create a test database manager."""
        return DatabaseManager(db_path=temp_db)

    def test_database_initialization(self, db_manager):
        """Test database initialization."""
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

    def test_save_accounts(self, db_manager):
        """Test saving accounts."""
        accounts = [
            {"id": "acc1", "name": "Account 1", "type": "standard"},
            {"id": "acc2", "name": "Account 2", "type": "enterprise"},
        ]
        db_manager.save_accounts(accounts)

        session = db_manager.get_session()
        saved_accounts = session.query(CloudflareAccount).all()
        assert len(saved_accounts) == 2
        assert saved_accounts[0].id == "acc1"
        session.close()

    def test_save_zones(self, db_manager):
        """Test saving zones."""
        zones = [
            {
                "id": "zone1",
                "name": "example.com",
                "status": "active",
                "account": {"id": "acc1"},
            }
        ]
        db_manager.save_zones(zones)

        session = db_manager.get_session()
        saved_zones = session.query(CloudflareZone).all()
        assert len(saved_zones) == 1
        assert saved_zones[0].name == "example.com"
        session.close()

    def test_save_dns_records(self, db_manager):
        """Test saving DNS records."""
        dns_records = [
            {
                "id": "rec1",
                "zone_id": "zone1",
                "type": "A",
                "name": "example.com",
                "content": "192.0.2.1",
                "proxied": True,
                "ttl": 1,
            }
        ]
        db_manager.save_dns_records(dns_records)

        session = db_manager.get_session()
        saved_records = session.query(CloudflareDNSRecord).all()
        assert len(saved_records) == 1
        assert saved_records[0].type == "A"
        session.close()

    def test_close(self, db_manager):
        """Test closing database connection."""
        db_manager.close()
        # Should not raise any errors
