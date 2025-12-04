"""Tests for data export functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from cf_box.data_export import (
    load_config,
    anonymize_email,
    anonymize_account_id,
    anonymize_data,
    save_json,
    save_csv,
    save_excel,
)


class TestDataExport:
    """Test data export functions."""

    def test_anonymize_email(self):
        """Test email anonymization."""
        email = "test@example.com"
        anonymized = anonymize_email(email)
        assert anonymized == "t**t@e******.com"

    def test_anonymize_email_short(self):
        """Test email anonymization with short name."""
        email = "ab@example.com"
        anonymized = anonymize_email(email)
        assert "@" in anonymized
        assert anonymized != email

    def test_anonymize_account_id(self):
        """Test account ID anonymization."""
        account_id = "1234567890abcdef"
        anonymized = anonymize_account_id(account_id)
        assert anonymized == "123456...cdef"

    def test_anonymize_account_id_short(self):
        """Test that short IDs are not anonymized."""
        account_id = "short"
        anonymized = anonymize_account_id(account_id)
        assert anonymized == "short"

    def test_anonymize_data(self):
        """Test data anonymization."""
        data = {
            "accounts": [{"id": "1234567890abcdef", "name": "test@example.com"}],
            "zones": [],
        }
        anonymized = anonymize_data(data, anonymize_flag=True)
        assert anonymized["accounts"][0]["id"] == "123456...cdef"
        assert "@" in anonymized["accounts"][0]["name"]

    def test_anonymize_data_disabled(self):
        """Test that anonymization can be disabled."""
        data = {
            "accounts": [{"id": "1234567890abcdef", "name": "test@example.com"}],
            "zones": [],
        }
        not_anonymized = anonymize_data(data, anonymize_flag=False)
        assert not_anonymized["accounts"][0]["id"] == "1234567890abcdef"
        assert not_anonymized["accounts"][0]["name"] == "test@example.com"

    def test_save_json(self):
        """Test saving JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            data = {"key": "value"}
            save_json(data, filepath)
            assert os.path.exists(filepath)

    def test_save_csv(self):
        """Test saving CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.csv")
            data = [{"key": "value1"}, {"key": "value2"}]
            save_csv(data, filepath)
            assert os.path.exists(filepath)

    def test_save_excel(self):
        """Test saving Excel file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.xlsx")
            data = [{"key": "value1"}, {"key": "value2"}]
            save_excel(data, filepath)
            assert os.path.exists(filepath)

    def test_load_config(self):
        """Test loading config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("anonymize: true\n")
            f.write("test_key: test_value\n")
            config_path = f.name

        try:
            config = load_config(config_path)
            assert config["anonymize"] is True
            assert config["test_key"] == "test_value"
        finally:
            os.unlink(config_path)

    @pytest.mark.asyncio
    async def test_export_cloudflare_data_no_token(self):
        """Test that export fails without API token."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("cf_box.data_export.logger") as mock_logger:
                from cf_box.data_export import export_cloudflare_data

                await export_cloudflare_data()
                mock_logger.error.assert_called_once()
