"""Tests for async HTTP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from cf_box.client import CloudflareAPIClient


class TestCloudflareAPIClient:
    """Test CloudflareAPIClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return CloudflareAPIClient(api_token="test_token")

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.api_token == "test_token"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    async def test_fetch_all_pages(self, client):
        """Test fetching all pages."""
        # Mock responses for pagination
        responses = [
            {"success": True, "result": [{"id": "1"}, {"id": "2"}]},
            {"success": True, "result": []},  # Empty result indicates no more pages
        ]

        with patch.object(client, "request", AsyncMock(side_effect=responses)):
            results = await client.fetch_all_pages("accounts")
            assert len(results) == 2
            assert results[0]["id"] == "1"
            assert results[1]["id"] == "2"

    @pytest.mark.asyncio
    async def test_get_accounts(self, client):
        """Test getting accounts."""
        with patch.object(
            client,
            "fetch_all_pages",
            AsyncMock(return_value=[{"id": "acc1", "name": "Account 1"}]),
        ):
            accounts = await client.get_accounts()
            assert len(accounts) == 1
            assert accounts[0]["id"] == "acc1"

    @pytest.mark.asyncio
    async def test_get_zones(self, client):
        """Test getting zones."""
        with patch.object(
            client,
            "fetch_all_pages",
            AsyncMock(return_value=[{"id": "zone1", "name": "example.com"}]),
        ):
            zones = await client.get_zones()
            assert len(zones) == 1
            assert zones[0]["name"] == "example.com"

    @pytest.mark.asyncio
    async def test_get_dns_records(self, client):
        """Test getting DNS records."""
        with patch.object(
            client,
            "fetch_all_pages",
            AsyncMock(return_value=[{"id": "rec1", "type": "A", "name": "example.com"}]),
        ):
            records = await client.get_dns_records("zone123")
            assert len(records) == 1
            assert records[0]["type"] == "A"
