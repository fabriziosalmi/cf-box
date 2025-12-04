"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from cf_box.models import (
    CloudflareAccount,
    CloudflareZone,
    CloudflareDNSRecord,
    CloudflareAPIResponse,
    CloudflareAnalyticsMetrics,
)


class TestCloudflareAccount:
    """Test CloudflareAccount model."""

    def test_valid_account(self):
        """Test creating a valid account."""
        account = CloudflareAccount(id="1234567890abcdef", name="Test Account")
        assert account.id == "1234567890abcdef"
        assert account.name == "Test Account"

    def test_invalid_account_id(self):
        """Test that short account IDs are rejected."""
        with pytest.raises(ValidationError):
            CloudflareAccount(id="short", name="Test Account")


class TestCloudflareZone:
    """Test CloudflareZone model."""

    def test_valid_zone(self):
        """Test creating a valid zone."""
        zone = CloudflareZone(id="zone123", name="example.com", status="active")
        assert zone.id == "zone123"
        assert zone.name == "example.com"
        assert zone.status == "active"


class TestCloudfareDNSRecord:
    """Test CloudflareDNSRecord model."""

    def test_valid_dns_record(self):
        """Test creating a valid DNS record."""
        record = CloudflareDNSRecord(
            id="rec123",
            type="A",
            name="example.com",
            content="192.0.2.1",
            proxied=True,
            ttl=1,
        )
        assert record.id == "rec123"
        assert record.type == "A"
        assert record.proxied is True


class TestCloudflareAPIResponse:
    """Test CloudflareAPIResponse model."""

    def test_successful_response(self):
        """Test successful API response."""
        response = CloudflareAPIResponse(success=True, result={"data": "test"})
        assert response.success is True
        assert response.result == {"data": "test"}

    def test_failed_response(self):
        """Test failed API response."""
        response = CloudflareAPIResponse(
            success=False, errors=[{"code": 1000, "message": "Error"}]
        )
        assert response.success is False
        assert len(response.errors) == 1


class TestCloudflareAnalyticsMetrics:
    """Test CloudflareAnalyticsMetrics model."""

    def test_metrics_with_aliases(self):
        """Test metrics with camelCase aliases."""
        metrics = CloudflareAnalyticsMetrics(
            requests=100,
            cachedRequests=50,
            bytes=1024,
            encryptedRequests=90,
            wafEvents=5,
            rateLimitedRequests=2,
        )
        assert metrics.requests == 100
        assert metrics.cached_requests == 50
        assert metrics.bytes == 1024

    def test_metrics_with_snake_case(self):
        """Test metrics with snake_case field names."""
        metrics = CloudflareAnalyticsMetrics(
            requests=100, cached_requests=50, bytes=1024
        )
        assert metrics.requests == 100
        assert metrics.cached_requests == 50
