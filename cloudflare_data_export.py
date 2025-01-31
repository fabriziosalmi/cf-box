import requests
import os
import csv
import json
import time
import random
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any

# Ensure export directory exists
EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Load configuration
def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Read previous data if available, handling empty/corrupt files
def load_previous_export(filename):
    path = os.path.join(EXPORT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️ Warning: Previous export {filename} is empty or corrupted. Resetting file.")
            return []
    return []

# Save JSON export only if changed
def save_json_if_changed(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    previous_data = load_previous_export(filename)

    if data == previous_data:
        print(f"✅ No changes detected in {filename}, skipping write.")
        return False

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ JSON exported: {path}")
    return True

# Save CSV export dynamically, handling extra/missing fields
def save_csv_if_changed(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    previous_data = load_previous_export(filename)

    # Dynamically determine headers from the data
    all_keys = set()
    for record in data:
        all_keys.update(record.keys())

    # Convert set to sorted list (consistent order)
    headers = sorted(list(all_keys))

    if data == previous_data:
        print(f"✅ No changes detected in {filename}, skipping write.")
        return False

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ CSV exported: {path}")
    return True

# Rate-limit handling with retries
def request_with_retries(url, headers, method="GET", payload=None, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url, headers=headers, json=payload)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", random.uniform(5, 10)))
                print(f"⚠️ Rate limited! Retrying in {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ Error in request: {e}")
            time.sleep(random.uniform(5, 15))  # Randomized backoff

    print("❌ Max retries reached, skipping request.")
    return None

# Auto-pagination helper
def fetch_all_pages(url, headers, per_page=50):
    page = 1
    all_results = []

    while True:
        paginated_url = f"{url}?per_page={per_page}&page={page}" if "?" not in url else f"{url}&per_page={per_page}&page={page}"
        data = request_with_retries(paginated_url, headers)

        if not data or not data.get('success') or not data.get('result'):
            break

        all_results.extend(data['result'])

        if len(data['result']) < per_page:
            break  # Last page reached

        page += 1  # Move to next page

    return all_results

# Fetch all accounts with pagination
def get_cloudflare_accounts(api_token: str) -> Optional[List[Dict[str, Any]]]:
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = "https://api.cloudflare.com/client/v4/accounts"

    return fetch_all_pages(url, headers, per_page=50)

# Fetch all zones for an account with pagination
def get_cloudflare_zones(account_id: str, api_token: str) -> Optional[List[Dict[str, Any]]]:
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/zones?account.id={account_id}"

    return fetch_all_pages(url, headers, per_page=200)

# Fetch all DNS records for a zone with pagination
def get_dns_records(zone_id: str, api_token: str) -> Optional[List[Dict[str, Any]]]:
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

    return fetch_all_pages(url, headers, per_page=100)

# Anonymization Helpers
def anonymize_email(email: str) -> str:
    """Anonymizes an email address by masking part of it."""
    if "@" not in email:
        return email
    name, domain = email.split("@")
    masked_name = name[0] + "*" * (len(name) - 2) + name[-1] if len(name) > 2 else name + "*"
    masked_domain = domain[0] + "*" * (domain.index(".") - 1) + domain[domain.index("."):]
    return f"{masked_name}@{masked_domain}"

def anonymize_account_id(account_id: str) -> str:
    """Anonymizes an account ID by keeping only the first and last 6 characters."""
    return f"{account_id[:6]}...{account_id[-6:]}"

def anonymize_data(data, anonymize_flag=True):
    """Applies anonymization to emails and account IDs if enabled."""
    if not anonymize_flag:
        return data

    for account in data["accounts"]:
        account["name"] = anonymize_email(account["name"])
        account["id"] = anonymize_account_id(account["id"])

    return data

# Main export function
def export_cloudflare_data():
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not api_token:
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    print("📌 Fetching Cloudflare data...")

    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}

    all_data = {
        "accounts": fetch_all_pages("https://api.cloudflare.com/client/v4/accounts", headers),
        "zones": [],
        "dns_records": []
    }

    for account in all_data["accounts"]:
        account_id = account["id"]
        print(f"📌 Exporting data for account: {anonymize_email(account['name'])} (ID: {anonymize_account_id(account_id)})")

        zones = fetch_all_pages(f"https://api.cloudflare.com/client/v4/zones?account.id={account_id}", headers)
        all_data["zones"].extend(zones)

        for zone in zones:
            zone_id = zone["id"]
            dns_records = fetch_all_pages(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers)
            all_data["dns_records"].extend(dns_records)

    # 🔥 Apply Incremental Updates + Anonymization
    anonymized_data = anonymize_data(all_data)

    changed_json = save_json_if_changed(anonymized_data, "cloudflare_export.json")
    changed_csv = save_csv_if_changed(anonymized_data["dns_records"], "cloudflare_dns_records.csv")

    if changed_json or changed_csv:
        print("✅ Changes detected, export updated.")
    else:
        print("✅ No changes detected, skipping unnecessary exports.")

if __name__ == "__main__":
    export_cloudflare_data()
