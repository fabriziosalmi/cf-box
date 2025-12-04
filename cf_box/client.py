"""Async HTTP client for Cloudflare API interactions."""

import asyncio
import random
from typing import Any, Dict, List, Optional

import aiohttp

from cf_box.logging_config import get_logger
from cf_box.models import CloudflareAPIResponse

logger = get_logger(__name__)


class CloudflareAPIClient:
    """Async HTTP client for Cloudflare API."""

    def __init__(self, api_token: str, base_url: str = "https://api.cloudflare.com/client/v4"):
        """Initialize the Cloudflare API client.

        Args:
            api_token: Cloudflare API token
            base_url: Base URL for Cloudflare API
        """
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def request(
        self,
        method: str,
        url: str,
        max_retries: int = 5,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make an async HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            max_retries: Maximum number of retries
            payload: Optional request payload

        Returns:
            Response JSON data or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method, url, headers=self.headers, json=payload
                    ) as response:
                        if response.status == 429:
                            retry_after = int(
                                response.headers.get("Retry-After", random.uniform(5, 10))
                            )
                            logger.warning(
                                "rate_limited",
                                attempt=attempt,
                                retry_after=retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        response.raise_for_status()
                        return await response.json()

            except aiohttp.ClientError as e:
                logger.error("request_failed", error=str(e), attempt=attempt, url=url)
                await asyncio.sleep(random.uniform(5, 15))

        logger.error("max_retries_reached", url=url)
        return None

    async def fetch_all_pages(
        self, endpoint: str, per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch all paginated data from an endpoint.

        Args:
            endpoint: API endpoint
            per_page: Results per page

        Returns:
            List of all results from all pages
        """
        page = 1
        all_results: List[Dict[str, Any]] = []
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        while True:
            separator = "&" if "?" in url else "?"
            paginated_url = f"{url}{separator}per_page={per_page}&page={page}"

            data = await self.request("GET", paginated_url)

            if not data or not data.get("success") or not data.get("result"):
                break

            results = data["result"]
            if isinstance(results, list):
                all_results.extend(results)
                if len(results) < per_page:
                    break
            else:
                all_results.append(results)
                break

            page += 1

        logger.info("fetch_completed", endpoint=endpoint, total_results=len(all_results))
        return all_results

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all Cloudflare accounts.

        Returns:
            List of account dictionaries
        """
        return await self.fetch_all_pages("accounts")

    async def get_zones(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get zones, optionally filtered by account.

        Args:
            account_id: Optional account ID to filter zones

        Returns:
            List of zone dictionaries
        """
        endpoint = "zones"
        if account_id:
            endpoint = f"zones?account.id={account_id}"
        return await self.fetch_all_pages(endpoint)

    async def get_dns_records(self, zone_id: str) -> List[Dict[str, Any]]:
        """Get DNS records for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            List of DNS record dictionaries
        """
        return await self.fetch_all_pages(f"zones/{zone_id}/dns_records")

    async def post_graphql(
        self, query: str, max_retries: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Make a GraphQL request to Cloudflare API.

        Args:
            query: GraphQL query string
            max_retries: Maximum number of retries

        Returns:
            Response data or None if failed
        """
        url = "https://api.cloudflare.com/client/v4/graphql"
        payload = {"query": query}
        return await self.request("POST", url, max_retries=max_retries, payload=payload)

    async def close(self) -> None:
        """Close the client session."""
        # aiohttp sessions are created per request, so nothing to close
        pass
