import requests
import os
from datetime import datetime
import json
import yaml
from typing import Dict, List, Optional, Any

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

def sync_ip_list(account_id: str, list_id: str, ip_list: List[str], api_token: str) -> bool:
    """Syncs an IP list by replacing its content."""
    headers = { 'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json' }
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists/{list_id}/items"
    
    payload = [{"ip": ip} for ip in ip_list]
    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get('success', False)
    except requests.exceptions.RequestException as e:
        print(f"Error syncing IP list {list_id}: {e}")
        return False

def save_markdown_report(account_data):
    """Saves a markdown report with the latest Cloudflare IP list details."""
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(reports_dir, f"cf_ip_report_{timestamp}.md")

    with open(report_path, "w") as f:
        f.write(f"# Cloudflare IP List Report ({timestamp})\n\n")
        for account_id, details in account_data.items():
            f.write(f"## Account: {details['name']} (ID: {account_id})\n\n")
            for ip_list in details["lists"]:
                f.write(f"### {ip_list['name']} ({ip_list['kind']})\n")
                f.write(f"- **Items:** {ip_list['num_items']}\n")
                f.write(f"- **Last Modified:** {ip_list['modified_on']}\n\n")

    print(f"✅ Markdown report saved: {report_path}")

def main():
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    config = load_config("config.yaml")
    
    if not api_token:
        raise EnvironmentError("CLOUDFLARE_API_TOKEN not set")
    
    accounts = get_cloudflare_accounts(api_token)
    if not accounts:
        print("Failed to retrieve Cloudflare accounts. Exiting.")
        return
    
    for account in accounts:
        account_id = account.get('id')
        account_name = account.get('name', 'Unknown Account')
        
        print(f"Managing IP lists for {account_name} (ID: {account_id})")
        ip_lists = get_ip_lists(account_id, api_token)
        
        if not ip_lists:
            print(f"No IP lists found for account {account_name}")
            continue
        
        for list_entry in config.get('accounts', []):
            if list_entry['id'] == account_id:
                for target_list in list_entry.get('lists', []):
                    list_name = target_list['name']
                    ip_source = target_list.get('sync_from') or target_list.get('local_file')
                    
                    cf_list = next((l for l in ip_lists if l['name'] == list_name), None)
                    if not cf_list:
                        print(f"IP list {list_name} not found in account {account_name}")
                        continue
                    
                    ip_data = []
                    if 'sync_from' in target_list:
                        try:
                            ip_data = requests.get(target_list['sync_from']).text.strip().split('\n')
                        except requests.exceptions.RequestException:
                            print(f"Failed to fetch remote IPs from {target_list['sync_from']}")
                    elif 'local_file' in target_list:
                        try:
                            with open(target_list['local_file'], 'r') as f:
                                ip_data = f.read().strip().split('\n')
                        except FileNotFoundError:
                            print(f"Local file {target_list['local_file']} not found")
                    
                    if ip_data and sync_ip_list(account_id, cf_list['id'], ip_data, api_token):
                        print(f"Updated IP list {list_name} in {account_name}")
                    else:
                        print(f"Failed to update IP list {list_name} in {account_name}")

if __name__ == "__main__":
    main()
