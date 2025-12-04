"""Refactored Cloudflare data export with async support and proper architecture."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from cf_box.client import CloudflareAPIClient
from cf_box.database import DatabaseManager
from cf_box.logging_config import configure_logging, get_logger
from cf_box.models import CloudflareAccount, CloudflareDNSRecord, CloudflareZone
from cf_box.pdf_generator import PDFGenerator

logger = get_logger(__name__)

EXPORT_DIR = "exports"


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


def anonymize_email(email: str) -> str:
    """Anonymize an email address.

    Args:
        email: Email address to anonymize

    Returns:
        Anonymized email address
    """
    if "@" not in email:
        return email
    name, domain = email.split("@")
    masked_name = name[0] + "*" * (len(name) - 2) + name[-1] if len(name) > 2 else name + "*"
    domain_parts = domain.split(".")
    if len(domain_parts) >= 2:
        masked_domain = (
            domain_parts[0][0] + "*" * (len(domain_parts[0]) - 1) + "." + ".".join(domain_parts[1:])
        )
    else:
        masked_domain = domain
    return f"{masked_name}@{masked_domain}"


def anonymize_account_id(account_id: str) -> str:
    """Anonymize an account ID.

    Args:
        account_id: Account ID to anonymize

    Returns:
        Anonymized account ID
    """
    if not isinstance(account_id, str) or len(account_id) < 10:
        return account_id
    return f"{account_id[:6]}...{account_id[-4:]}"


def anonymize_data(data: Dict[str, Any], anonymize_flag: bool = True) -> Dict[str, Any]:
    """Anonymize sensitive data in the export.

    Args:
        data: Data dictionary to anonymize
        anonymize_flag: Whether to perform anonymization

    Returns:
        Anonymized data dictionary
    """
    if not anonymize_flag:
        return data

    for account in data.get("accounts", []):
        if "name" in account:
            account["name"] = anonymize_email(account["name"])
        if "id" in account:
            account["id"] = anonymize_account_id(account["id"])

    return data


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


def save_csv(data: List[Dict[str, Any]], filepath: str) -> None:
    """Save data to CSV file.

    Args:
        data: List of dictionaries to save
        filepath: Output file path
    """
    if not data:
        logger.warning("no_data_to_save", filepath=filepath)
        return

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    logger.info("csv_saved", filepath=filepath, rows=len(data))


def save_excel(data: List[Dict[str, Any]], filepath: str) -> None:
    """Save data to Excel file.

    Args:
        data: List of dictionaries to save
        filepath: Output file path
    """
    if not data:
        logger.warning("no_data_to_save", filepath=filepath)
        return

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    logger.info("excel_saved", filepath=filepath, rows=len(data))


async def export_cloudflare_data() -> None:
    """Export Cloudflare data including accounts, zones, and DNS records.

    This async function fetches data from the Cloudflare API using the provided API token,
    anonymizes the data if specified in the configuration, and saves the data in
    multiple formats (JSON, CSV, Excel, PDF, SQLite).
    """
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not api_token:
        logger.error("api_token_missing")
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    config = load_config("config.yaml")
    anonymize_flag = config.get("anonymize", True)

    logger.info("export_started", anonymize=anonymize_flag)

    # Initialize clients
    client = CloudflareAPIClient(api_token)
    db_manager = DatabaseManager()
    pdf_generator = PDFGenerator()

    try:
        # Fetch data
        logger.info("fetching_accounts")
        accounts = await client.get_accounts()

        all_zones: List[Dict[str, Any]] = []
        all_dns_records: List[Dict[str, Any]] = []

        for account in accounts:
            account_id = account["id"]
            account_name = account.get("name", "Unknown")

            logger.info(
                "processing_account",
                account_id=anonymize_account_id(account_id),
                account_name=anonymize_email(account_name) if anonymize_flag else account_name,
            )

            zones = await client.get_zones(account_id)
            all_zones.extend(zones)

            for zone in zones:
                zone_id = zone["id"]
                dns_records = await client.get_dns_records(zone_id)
                all_dns_records.extend(dns_records)

        # Prepare export data
        export_data = {"accounts": accounts, "zones": all_zones, "dns_records": all_dns_records}

        # Anonymize if needed
        anonymized_data = anonymize_data(export_data.copy(), anonymize_flag)

        # Save to various formats
        logger.info("saving_exports")

        save_json(anonymized_data, f"{EXPORT_DIR}/cloudflare_export.json")
        save_csv(anonymized_data["dns_records"], f"{EXPORT_DIR}/cloudflare_dns_records.csv")
        save_excel(anonymized_data["dns_records"], f"{EXPORT_DIR}/cloudflare_dns_records.xlsx")

        # Generate PDF report
        pdf_generator.generate_report(
            anonymized_data, f"{EXPORT_DIR}/cloudflare_export.pdf"
        )

        # Save to database (using original data, not anonymized)
        db_manager.save_accounts(accounts)
        db_manager.save_zones(all_zones)
        db_manager.save_dns_records(all_dns_records)

        logger.info("export_completed", total_accounts=len(accounts), total_zones=len(all_zones), total_dns_records=len(all_dns_records))

    except Exception as e:
        logger.error("export_failed", error=str(e))
        raise
    finally:
        await client.close()
        db_manager.close()


def main() -> None:
    """Main entry point for data export."""
    configure_logging()
    asyncio.run(export_cloudflare_data())


if __name__ == "__main__":
    main()
