import requests
import os
import csv
import json
import time
import random
import yaml
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Load configuration
def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Read previous data for incremental updates
def load_previous_export(filename):
    path = os.path.join(EXPORT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️ Warning: {filename} is empty or corrupted. Resetting file.")
            return []
    return []

# Save JSON if changed
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

# Save CSV dynamically
def save_csv_if_changed(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    previous_data = load_previous_export(filename)

    headers = sorted({key for record in data for key in record.keys()})

    if data == previous_data:
        print(f"✅ No changes detected in {filename}, skipping write.")
        return False

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ CSV exported: {path}")
    return True

# Save XLS
def save_xls(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)
    print(f"✅ XLS exported: {path}")

# Save PDF
def save_pdf(data, filename):
    path = os.path.join(EXPORT_DIR, filename)
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica", 10)

    margin = 40
    y_position = 750

    c.drawString(margin, y_position, f"Cloudflare Data Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y_position -= 20

    for section, items in data.items():
        c.drawString(margin, y_position, f"Section: {section}")
        y_position -= 20

        for item in items[:5]:  # Avoid overflowing PDF (first 5 items)
            c.drawString(margin + 10, y_position, json.dumps(item, indent=2)[:100])
            y_position -= 15
            if y_position < 50:
                c.showPage()
                y_position = 750

    c.save()
    print(f"✅ PDF exported: {path}")

# Convert lists/dicts to JSON strings for database storage
def clean_data_for_sql(data):
    for row in data:
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                row[key] = json.dumps(value)
    return data

# Save to SQLite
def save_to_sqlite(data, filename, table_name):
    if not data:
        print(f"⚠️ No data to save for {table_name}, skipping SQLite export.")
        return

    path = os.path.join(EXPORT_DIR, filename)
    conn = sqlite3.connect(path)

    data = clean_data_for_sql(data)

    df = pd.DataFrame(data)
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.close()
    print(f"✅ SQLite exported: {path} (Table: {table_name})")

# Save to MySQL (as file)
def save_to_mysql_file(data, filename, table_name):
    if not data:
        print(f"⚠️ No data to save for {table_name}, skipping MySQL export.")
        return

    path = os.path.join(EXPORT_DIR, filename)

    all_keys = set()
    for record in data:
        all_keys.update(record.keys())
    columns = sorted(list(all_keys))

    data = clean_data_for_sql(data)

    with open(path, "w") as f:
        f.write(f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n")
        f.write(",\n".join([f"`{col}` TEXT" for col in columns]))
        f.write("\n);\n\n")

        for record in data:
            values = [json.dumps(record.get(col, "")) if isinstance(record.get(col), (dict, list)) else record.get(col, "") for col in columns]
            values_escaped = ', '.join(f"'{str(v).replace("'", "''")}'" for v in values)

            f.write(f"INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)}) VALUES ({values_escaped});\n")

    print(f"✅ MySQL export saved: {path}")

# Handle rate limits
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
            time.sleep(random.uniform(5, 15))

    print("❌ Max retries reached, skipping request.")
    return None

# Fetch all paginated data
def fetch_all_pages(url, headers, per_page=50):
    page = 1
    all_results = []

    while True:
        paginated_url = f"{url}?per_page={per_page}&page={page}" if "?" not in url else f"{url}&per_page={per_page}"
        data = request_with_retries(paginated_url, headers)

        if not data or not data.get('success') or not data.get('result'):
            break

        all_results.extend(data['result'])

        if len(data['result']) < per_page:
            break

        page += 1

    return all_results

# Anonymization Helpers
def anonymize_email(email: str) -> str:
    if "@" not in email:
        return email
    name, domain = email.split("@")
    masked_name = name[0] + "*" * (len(name) - 2) + name[-1] if len(name) > 2 else name + "*"
    masked_domain = domain[0] + "*" * (domain.index(".") - 1) + domain[domain.index("."):]
    return f"{masked_name}@{masked_domain}"

def anonymize_account_id(account_id: str) -> str:
    return f"{account_id[:6]}...{account_id[-6:]}" if isinstance(account_id, str) else account_id

def anonymize_data(data, anonymize_flag=True):
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

    config = load_config("config.yaml")
    anonymize_flag = config.get("anonymize", True)

    print("📌 Fetching Cloudflare data...")

    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}

    all_data = {
        "accounts": fetch_all_pages("https://api.cloudflare.com/client/v4/accounts", headers),
        "zones": [],
        "dns_records": []
    }

    for account in all_data["accounts"]:
        account_id = account["id"]
        account_name = account.get("name", "Unknown")

        anonymized_id = anonymize_account_id(account_id)
        anonymized_name = anonymize_email(account_name)

        print(f"📌 Exporting data for account: {anonymized_name} (ID: {anonymized_id})")

        zones = fetch_all_pages(f"https://api.cloudflare.com/client/v4/zones?account.id={account_id}", headers)
        all_data["zones"].extend(zones)

        for zone in zones:
            zone_id = zone["id"]
            dns_records = fetch_all_pages(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers)
            all_data["dns_records"].extend(dns_records)

    anonymized_data = anonymize_data(all_data, anonymize_flag)

    save_json_if_changed(anonymized_data, "cloudflare_export.json")
    save_csv_if_changed(anonymized_data["dns_records"], "cloudflare_dns_records.csv")
    save_xls(anonymized_data["dns_records"], "cloudflare_dns_records.xlsx")
    save_pdf(anonymized_data, "cloudflare_export.pdf")

if __name__ == "__main__":
    export_cloudflare_data()
