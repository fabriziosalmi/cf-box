import requests
import os
from datetime import datetime
import json
import yaml
from typing import Dict, List, Optional, Any
import time
import random

def load_config(config_path: str) -> Dict[str, Any]:
    """Loads YAML configuration file."""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def get_cloudflare_accounts(api_token: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieves a list of Cloudflare accounts accessible with the API Token."""
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
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
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('result', []) if data.get('success') else None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP lists for {account_id}: {e}")
        return None

def get_ip_list_from_source(source_url: str, source_type: str) -> List[str]:
    """Fetches IPs from a remote source and handles JSON or plain text."""
    try:
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        
        if source_type == "json":
            data = response.json()
            ip_list = [entry['ip_prefix'] for entry in data.get('prefixes', [])]
        else:
            ip_list = list(set(response.text.strip().split('\n')))
        
        print(f"✅ Fetched {len(ip_list)} IPs from {source_url}")
        return ip_list[:10000]
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch IP list from {source_url}: {e}")
        return []

def sync_ip_list(account_id: str, list_id: str, ip_list: list, api_token: str) -> bool:
    """Syncs an entire IP list at once to avoid Cloudflare's rate limits on incremental updates."""
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists/{list_id}/items"

    if len(ip_list) > 10000:
        print(f"⚠️ IP list too large ({len(ip_list)} entries)! Trimming to 10,000.")
        ip_list = ip_list[:10000]

    payload = [{"ip": ip} for ip in ip_list]

    for attempt in range(5):
        try:
            response = requests.put(url, headers=headers, json=payload)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", random.uniform(300, 600)))
                print(f"⚠️ Rate limited! Retrying in {retry_after}s...")
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            print(f"✅ Successfully updated IP list {list_id} with {len(ip_list)} entries")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error updating IP list {list_id}: {e}")
            return False
    return False

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
