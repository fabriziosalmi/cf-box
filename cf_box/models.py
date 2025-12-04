"""Pydantic models for Cloudflare API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CloudflareAccount(BaseModel):
    """Cloudflare account model."""

    id: str
    name: str
    type: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate account ID format."""
        if not v or len(v) < 8:
            raise ValueError("Invalid account ID")
        return v


class CloudflareZone(BaseModel):
    """Cloudflare zone model."""

    id: str
    name: str
    status: str
    account: Optional[Dict[str, Any]] = None
    name_servers: Optional[List[str]] = None
    development_mode: Optional[int] = None


class CloudflareDNSRecord(BaseModel):
    """Cloudflare DNS record model."""

    id: str
    type: str
    name: str
    content: str
    proxied: bool = False
    ttl: int = 1
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None


class CloudflareAPIResponse(BaseModel):
    """Generic Cloudflare API response model."""

    success: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Any] = None
    result_info: Optional[Dict[str, Any]] = None


class CloudflareIPList(BaseModel):
    """Cloudflare IP list model."""

    id: str
    name: str
    description: Optional[str] = None
    kind: str
    num_items: int = 0
    num_referencing_filters: int = 0
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class CloudflareIPListItem(BaseModel):
    """Cloudflare IP list item model."""

    id: str
    ip: str
    comment: Optional[str] = None
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class CloudflareAnalyticsMetrics(BaseModel):
    """Cloudflare analytics metrics model."""

    requests: int = 0
    cached_requests: int = Field(default=0, alias="cachedRequests")
    bytes: int = 0
    encrypted_requests: int = Field(default=0, alias="encryptedRequests")
    waf_events: int = Field(default=0, alias="wafEvents")
    rate_limited_requests: int = Field(default=0, alias="rateLimitedRequests")

    class Config:
        populate_by_name = True


class CloudflareAnalyticsDimensions(BaseModel):
    """Cloudflare analytics dimensions model."""

    datetime: Optional[str] = None
    client_country_name: Optional[str] = Field(default=None, alias="clientCountryName")
    client_request_http_method_name: Optional[str] = Field(
        default=None, alias="clientRequestHTTPMethodName"
    )

    class Config:
        populate_by_name = True


class CloudflareAnalyticsGroup(BaseModel):
    """Cloudflare analytics group model."""

    dimensions: CloudflareAnalyticsDimensions
    sum: CloudflareAnalyticsMetrics = Field(alias="sum")

    class Config:
        populate_by_name = True
