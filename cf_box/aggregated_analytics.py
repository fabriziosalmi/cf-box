"""Refactored Cloudflare aggregated analytics with async support."""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf_box.client import CloudflareAPIClient
from cf_box.logging_config import configure_logging, get_logger
from cf_box.models import CloudflareAnalyticsGroup

logger = get_logger(__name__)

EXPORT_DIR = "exports"


def build_analytics_query(account_tag: str, start_time: str, end_time: str) -> str:
    """Build GraphQL query for analytics data.

    Args:
        account_tag: Cloudflare account tag
        start_time: Start time in ISO format
        end_time: End time in ISO format

    Returns:
        GraphQL query string
    """
    return f"""
query {{
  viewer {{
    accounts(filter: {{ accountTag: "{account_tag}" }}) {{
      name
      zones {{
        name
        httpRequests1dGroups(
          limit: 100,
          filter: {{ datetime_geq: "{start_time}", datetime_leq: "{end_time}" }}
        ) {{
          dimensions {{
            datetime
            clientCountryName
            clientRequestHTTPMethodName
          }}
          sum {{
            requests
            cachedRequests
            bytes
            encryptedRequests
            wafEvents
            rateLimitedRequests
          }}
        }}
      }}
    }}
  }}
}}
"""


def process_analytics_data(
    data: Dict[str, Any]
) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, int]]]:
    """Process GraphQL analytics response data.

    Args:
        data: Raw GraphQL response data

    Returns:
        Tuple of (detailed results, account totals)
    """
    if not data or "data" not in data:
        logger.warning("no_analytics_data")
        return [], {}

    results: List[Dict[str, Any]] = []
    account_totals: Dict[str, Dict[str, int]] = {}

    viewer_data = data["data"].get("viewer", {})
    accounts = viewer_data.get("accounts", [])

    for account in accounts:
        account_name = account["name"]
        zones = account.get("zones", [])

        totals = {
            "requests": 0,
            "cachedRequests": 0,
            "bytes": 0,
            "wafEvents": 0,
            "rateLimitedRequests": 0,
        }

        for zone in zones:
            zone_name = zone["name"]
            http_requests_groups = zone.get("httpRequests1dGroups", [])

            for entry in http_requests_groups:
                dimensions = entry["dimensions"]
                stats = entry["sum"]

                country = dimensions.get("clientCountryName", "Unknown")
                method = dimensions.get("clientRequestHTTPMethodName", "Unknown")

                result_entry = {
                    "account_name": account_name,
                    "zone": zone_name,
                    "country": country,
                    "method": method,
                    "requests": stats["requests"],
                    "cached_requests": stats["cachedRequests"],
                    "bytes": stats["bytes"],
                    "waf_events": stats["wafEvents"],
                    "rate_limited_requests": stats["rateLimitedRequests"],
                }

                results.append(result_entry)

                totals["requests"] += stats["requests"]
                totals["cachedRequests"] += stats["cachedRequests"]
                totals["bytes"] += stats["bytes"]
                totals["wafEvents"] += stats["wafEvents"]
                totals["rateLimitedRequests"] += stats["rateLimitedRequests"]

        account_totals[account_name] = totals

    return results, account_totals


def save_json(data: Any, filepath: str) -> None:
    """Save data to JSON file.

    Args:
        data: Data to save
        filepath: Output file path
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("json_saved", filepath=filepath)


async def export_cloudflare_analytics() -> None:
    """Export Cloudflare analytics data for the last 24 hours."""
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not api_token:
        logger.error("api_token_missing")
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    logger.info("analytics_export_started")

    client = CloudflareAPIClient(api_token)

    try:
        # Fetch accounts
        logger.info("fetching_accounts")
        accounts = await client.get_accounts()

        if not accounts:
            logger.warning("no_accounts_found")
            print("❌ No accounts found. Exiting.")
            return

        # Define time range (last 24 hours)
        end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        all_results: List[Dict[str, Any]] = []
        all_totals: Dict[str, Dict[str, int]] = {}

        # Fetch data for each account
        for account in accounts:
            account_tag = account["accountTag"] if "accountTag" in account else account["id"]
            account_name = account["name"]

            logger.info("fetching_analytics", account_name=account_name, account_tag=account_tag)

            query = build_analytics_query(account_tag, start_time, end_time)
            raw_data = await client.post_graphql(query)

            if raw_data:
                results, account_totals = process_analytics_data(raw_data)
                all_results.extend(results)
                all_totals.update(account_totals)

        if not all_results:
            logger.warning("no_analytics_data_to_export")
            print("⚠️ No analytics data to export. Exiting.")
            return

        # Save exports
        save_json(all_results, f"{EXPORT_DIR}/cloudflare_aggregated_analytics.json")
        save_json(all_totals, f"{EXPORT_DIR}/cloudflare_aggregated_accounts.json")

        logger.info("analytics_export_completed", total_results=len(all_results))

    except Exception as e:
        logger.error("analytics_export_failed", error=str(e))
        raise
    finally:
        await client.close()


def main() -> None:
    """Main entry point for analytics export."""
    configure_logging()
    asyncio.run(export_cloudflare_analytics())


if __name__ == "__main__":
    main()
