import requests
import os
import time
import random
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

# Create reports folder if it doesn't exist
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_config(config_path: str) -> Dict[str, Any]:
    """Loads YAML configuration file."""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

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

def anonymize(text: str, anonymize_flag: bool) -> str:
    """Anonymizes text based on the user setting."""
    if not anonymize_flag:
        return text
    if "@" in text:
        return anonymize_email(text)
    return anonymize_account_id(text)

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

def generate_markdown_report(report_log, start_time, end_time, anonymize_flag):
    """Generates a markdown report summarizing the execution."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = os.path.join(REPORTS_DIR, f"cf_sync_{timestamp}.md")

    with open(report_file, "w") as f:
        f.write(f"# Cloudflare IP List Sync Report - {timestamp}\n\n")
        f.write(f"**Start Time:** {start_time}\n\n")
        f.write(f"**End Time:** {end_time}\n\n")
        f.write("## Summary\n")
        for log_entry in report_log:
            if anonymize_flag:
                log_entry = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', anonymize_email, log_entry)  # Mask emails
                log_entry = re.sub(r'[a-f0-9]{32}', anonymize_account_id, log_entry)  # Mask CF IDs
            f.write(f"{log_entry}\n")
    
    print(f"📄 Report saved: {report_file}")

def main():
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_log = []

    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    config_path = "config.yaml"

    if not api_token:
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    config = load_config(config_path)
    if not config:
        print("❌ Failed to load config file.")
        return

    anonymize_flag = config.get("anonymize", False)  # Default to False

    accounts = get_cloudflare_accounts(api_token)
    if not accounts:
        print("❌ No Cloudflare accounts found.")
        return

    for account in accounts:
        account_id = account["id"]
        account_name = account.get("name", "Unknown Account")

        masked_account_id = anonymize(account_id, anonymize_flag)
        masked_account_name = anonymize(account_name, anonymize_flag)

        print(f"📌 Managing IP lists for {masked_account_name} (ID: {masked_account_id})")
        report_log.append(f"### 📌 Managing IP lists for `{masked_account_name}` (ID: `{masked_account_id}`)")

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generate_markdown_report(report_log, start_time, end_time, anonymize_flag)

if __name__ == "__main__":
    main()
