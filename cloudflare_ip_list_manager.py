import requests
import os
from datetime import datetime
import json
import yaml
from typing import Dict, List, Optional, Any
import time
import math

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

def get_ip_list_from_source(source_url: str) -> List[str]:
    """Fetches IPs from a remote source and filters valid IPv4 addresses."""
    try:
        response = requests.get(source_url, timeout=10)
        response.raise_for_status()
        ip_list = list(set(response.text.strip().split('\n')))
        print(f"✅ Fetched {len(ip_list)} IPs from {source_url}")
        return ip_list[:10000]  # Trim to max 10,000
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch IP list from {source_url}: {e}")
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

    chunk_size = 100
    max_retries = 5
    retry_delay = 5

    for chunk in chunk_list(list(new_ips), chunk_size):
        payload = [{"ip": ip} for ip in chunk]
        for attempt in range(max_retries):
            try:
                response = requests.put(url, headers=headers, json=payload)
                if response.status_code == 429:
                    print(f"⚠️ Rate limited! Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 120)
                    continue
                response.raise_for_status()
                print(f"✅ Synced {len(chunk)} IPs to list {list_id}")
                break
            except requests.exceptions.RequestException as e:
                print(f"❌ Error syncing IP list {list_id}: {e}")
                return False
    return True
