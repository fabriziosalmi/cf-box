import requests
import os
from datetime import datetime
import json
import yaml
from typing import Dict, List, Optional, Any
import time
import math
import random

def load_config(config_path: str) -> Dict[str, Any]:
    """Loads YAML configuration file."""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def get_cloudflare_accounts(api_token: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieves a list of Cloudflare accounts accessible with the API Token."""
    headers = { 'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json' }
    url = "https://api.cloudflare.com/client/v4/accounts"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('result', []) if data.get('success') else None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching accounts: {e}")
        return None

def get_ip_lists(account_id: str, api_token: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieves IP lists for a given Cloudflare account."""
    headers = { 'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json' }
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('result', []) if data.get('success') else None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP lists for {account_id}: {e}")
        return None

def chunk_list(data, chunk_size):
    """Splits a list into chunks of max chunk_size."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def get_current_ip_list(account_id: str, list_id: str, api_token: str) -> List[str]:
    """Fetch the existing IPs in a Cloudflare list to avoid unnecessary updates."""
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists/{list_id}/items"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [item['ip'] for item in data.get('result', [])]  # Extract IPs
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching current IPs for list {list_id}: {e}")
        return []

import requests
import time
import random

def get_ip_list_from_source(source_url: str, source_type: str) -> List[str]:
    """Fetches IPs from a remote source and handles JSON or plain text with retries and caching."""
    max_retries = 3
    base_retry_delay = 5  # Initial retry delay (seconds)
    cache_dir = "cache"
    cache_file = os.path.join(cache_dir, source_url.split('/')[-1])  # Store locally cached file

    # 🔥 Ensure `cache/` directory exists
    os.makedirs(cache_dir, exist_ok=True)

    for attempt in range(max_retries):
        try:
            response = requests.get(source_url, timeout=30)  # Increased timeout
            response.raise_for_status()

            if source_type == "json":
                data = response.json()
                ip_list = [entry['ip_prefix'] for entry in data.get('prefixes', [])]
            else:
                ip_list = list(set(response.text.strip().split('\n')))

            # ✅ Save a local cache of the successful fetch
            with open(cache_file, "w") as cache:
                cache.write("\n".join(ip_list))

            print(f"✅ Fetched {len(ip_list)} IPs from {source_url}")
            return ip_list[:10000]  # Trim to max 10,000

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt + 1}/{max_retries}: Failed to fetch {source_url} - {e}")
            retry_delay = min(base_retry_delay * (attempt + 1), 60)  # Increase retry time gradually
            time.sleep(retry_delay + random.uniform(1, 3))  # Add jitter to avoid API bans

    # 🔥 If all retries fail, try using a cached version
    if os.path.exists(cache_file):
        print(f"⚠️ Using cached IP list from {cache_file} due to fetch failure.")
        with open(cache_file, "r") as cache:
            cached_ips = cache.read().strip().split("\n")
            return cached_ips[:10000]

    print(f"❌ Failed to fetch IP list from {source_url} after {max_retries} attempts.")
    return []


def sync_ip_list(account_id: str, list_id: str, ip_list: list, api_token: str) -> bool:
    """Syncs an IP list only if changes exist, enforcing max 10K entries & handling rate limits."""
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists/{list_id}/items"

    existing_ips = set(get_current_ip_list(account_id, list_id, api_token))
    new_ips = set(ip_list)

    if existing_ips == new_ips:
        print(f"✅ No changes detected for list {list_id}, skipping update.")
        return True

    if len(new_ips) > 10000:
        print(f"⚠️ IP list too large ({len(new_ips)} entries)! Trimming to 10,000.")
        new_ips = list(new_ips)[:10000]

    chunk_size = 25  # 🔥 Keep small batches
    max_retries = 10
    base_retry_delay = 5  # 🔥 Base delay for retries
    base_throttle = 2  # 🔥 Base delay to prevent rate limits (in seconds)

    for chunk in chunk_list(list(new_ips), chunk_size):
        payload = [{"ip": ip} for ip in chunk]
        retry_delay = base_retry_delay  # Reset retry delay per chunk
        throttle_delay = base_throttle  # Reset throttle per chunk

        for attempt in range(max_retries):
            try:
                # 🔹 **Throttle Requests to Avoid Hitting the API Too Fast**
                time.sleep(throttle_delay + random.uniform(1, 3))  # 🔥 Add small random jitter

                response = requests.put(url, headers=headers, json=payload)

                # **Handle Rate Limiting**
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", retry_delay))  # Use Cloudflare's retry time
                    jitter = random.uniform(2, 5)  # 🔥 Add slight randomness
                    total_delay = min(retry_after + jitter, 180)  # 🔥 Cap at 3 min

                    print(f"⚠️ Rate limited! Retrying in {total_delay:.2f}s...")
                    time.sleep(total_delay)

                    # 🔥 Increase throttle for future requests to avoid hitting limits again
                    throttle_delay = min(throttle_delay + 2, 30)  # 🔥 Gradually increase throttle up to 30s

                    continue  # Retry the same chunk

                response.raise_for_status()
                print(f"✅ Synced {len(chunk)} IPs to list {list_id}")

                # 🔥 Adaptive Throttling: If request succeeds, slightly **reduce** the throttle delay
                throttle_delay = max(throttle_delay - 1, base_throttle)  # 🔥 Never below base

                break  # Exit retry loop if successful
            except requests.exceptions.RequestException as e:
                print(f"❌ Error syncing IP list {list_id}: {e}")
                return False
    return True


def main():
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    config_path = "config.yaml"

    if not api_token:
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    config = load_config(config_path)
    if not config:
        print("❌ Failed to load config file.")
        return

    accounts = get_cloudflare_accounts(api_token)
    if not accounts:
        print("❌ No Cloudflare accounts found.")
        return

    for account in accounts:
        account_id = account["id"]
        account_name = account.get("name", "Unknown Account")
        print(f"📌 Managing IP lists for {account_name} (ID: {account_id})")

        ip_lists = get_ip_lists(account_id, api_token)
        if not ip_lists:
            print(f"⚠️ No IP lists found for {account_name}")
            continue

        for list_entry in config["accounts"]:
            if list_entry["id"] != account_id:
                continue

            for target_list in list_entry.get("lists", []):
                list_name = target_list["name"]
                source_url = target_list.get("sync_from")
                source_type = target_list.get("type", "text")

                # Find the correct Cloudflare IP list
                cf_list = next((l for l in ip_lists if l["name"] == list_name), None)
                if not cf_list:
                    print(f"⚠️ IP list {list_name} not found in {account_name}")
                    continue

                if source_url:
                    ip_data = get_ip_list_from_source(source_url, source_type)
                    if ip_data:
                        sync_ip_list(account_id, cf_list["id"], ip_data, api_token)

if __name__ == "__main__":
    main()
