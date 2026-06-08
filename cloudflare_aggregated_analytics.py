import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

# Cloudflare API Settings
CF_API_URL = "https://api.cloudflare.com/client/v4/graphql"
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# Export Directory
EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# ✅ Fetch Account Tags from Cloudflare API
def get_cloudflare_accounts():
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    url = "https://api.cloudflare.com/client/v4/accounts"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch accounts: {response.text}")
        return []

    data = response.json()
    if not data.get("success", False):
        print("❌ Cloudflare API returned an error:", json.dumps(data, indent=2))
        return []

    return [{"accountTag": acc["id"], "name": acc["name"]} for acc in data["result"]]

# ✅ Corrected GraphQL Query (No `id`, Only `name` & `zones`)
GRAPHQL_QUERY = """
query {
  viewer {
    accounts(filter: { accountTag: "%s" }) {
      name
      zones {
        name
        httpRequests1dGroups(
          limit: 100,
          filter: { datetime_geq: "%s", datetime_leq: "%s" }
        ) {
          dimensions {
            datetime
            clientCountryName
            clientRequestHTTPMethodName
          }
          sum {
            requests
            cachedRequests
            bytes
            encryptedRequests
            wafEvents
            rateLimitedRequests
          }
        }
      }
    }
  }
}
"""

# ✅ Fetch GraphQL Data for Each Account
def fetch_graphql_data(account_tag: str, start_time: str, end_time: str, max_retries=5):
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    query = GRAPHQL_QUERY % (account_tag, start_time, end_time)

    for attempt in range(max_retries):
        response = requests.post(CF_API_URL, headers=headers, json={"query": query})

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            print(f"⚠️ Rate Limited! Retrying in {retry_after}s...")
            time.sleep(retry_after)
            continue

        if response.status_code != 200:
            print(f"❌ API Request Failed: {response.status_code} - {response.text}")
            return None

        data = response.json()

        if not data.get("data"):
            print("⚠️ No valid data returned from API. Response:")
            print(json.dumps(data, indent=2))
            return None

        return data

    print("❌ Max retries reached. Failed to fetch data.")
    return None

# ✅ Process Data
def process_data(data):
    """Extracts useful insights from Cloudflare's GraphQL response."""
    if not data or "data" not in data:
        print("⚠️ No data available to process. Skipping export.")
        return [], {}

    # Initialize results and totals
    results = []
    account_totals = {}

    # Extract viewer data
    viewer_data = data["data"].get("viewer", {})
    accounts = viewer_data.get("accounts", [])

    for account in accounts:
        account_name = account["name"]
        zones = account.get("zones", [])

        # Initialize per-account total counters
        totals = {
            "requests": 0,
            "cachedRequests": 0,
            "bytes": 0,
            "wafEvents": 0,
            "rateLimitedRequests": 0
        }

        for zone in zones:
            zone_name = zone["name"]
            httpRequestsGroups = zone.get("httpRequests1dGroups", [])

            for entry in httpRequestsGroups:
                dimensions = entry["dimensions"]
                stats = entry["sum"]

                country = dimensions.get("clientCountryName", "Unknown")
                method = dimensions.get("clientRequestHTTPMethodName", "Unknown")
                requests = stats["requests"]
                cached_requests = stats["cachedRequests"]
                bytes_transferred = stats["bytes"]
                waf_events = stats["wafEvents"]
                rate_limited_requests = stats["rateLimitedRequests"]

                # Append zone details to results
                results.append({
                    "account_name": account_name,
                    "zone": zone_name,
                    "country": country,
                    "method": method,
                    "requests": requests,
                    "cached_requests": cached_requests,
                    "bytes": bytes_transferred,
                    "waf_events": waf_events,
                    "rate_limited_requests": rate_limited_requests
                })

                # Aggregate totals per account
                totals["requests"] += requests
                totals["cachedRequests"] += cached_requests
                totals["bytes"] += bytes_transferred
                totals["wafEvents"] += waf_events
                totals["rateLimitedRequests"] += rate_limited_requests

        account_totals[account_name] = totals

    return results, account_totals

# ✅ Save Data to JSON
def save_json(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ JSON exported: {path}")

# ✅ Main Function
def export_cloudflare_analytics():
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not api_token:
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    print("📌 Fetching Cloudflare Analytics (Last 24h)...")

    # ✅ Fetch Accounts
    accounts = get_cloudflare_accounts()
    if not accounts:
        print("❌ No accounts found. Exiting.")
        return

    # ✅ Define Time Range (Last 24 Hours)
    end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_results = []
    all_totals = {}

    # ✅ Fetch Data Per Account (One-by-One)
    for account in accounts:
        print(f"📌 Fetching data for {account['name']} (AccountTag: {account['accountTag']})...")
        raw_data = fetch_graphql_data(account["accountTag"], start_time, end_time)

        if raw_data:
            results, account_totals = process_data(raw_data)
            all_results.extend(results)
            all_totals.update(account_totals)

    if not all_results:
        print("⚠️ No analytics data to export. Exiting.")
        return

    # ✅ Export to JSON
    save_json(all_results, "cloudflare_aggregated_analytics.json")
    save_json(all_totals, "cloudflare_aggregated_accounts.json")

    print("✅ All exports completed.")

# ✅ Run Script
if __name__ == "__main__":
    export_cloudflare_analytics()
