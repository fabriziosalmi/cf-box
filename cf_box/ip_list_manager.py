"""Refactored Cloudflare IP list manager with async support."""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from cf_box.client import CloudflareAPIClient
from cf_box.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

REPORTS_DIR = "reports"


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


def anonymize(text: str, anonymize_flag: bool) -> str:
    """Anonymize text based on the user setting.

    Args:
        text: Text to anonymize
        anonymize_flag: Whether to anonymize

    Returns:
        Anonymized or original text
    """
    if not anonymize_flag:
        return text
    if "@" in text:
        return anonymize_email(text)
    return anonymize_account_id(text)


def generate_markdown_report(
    report_log: List[str], start_time: str, end_time: str, anonymize_flag: bool
) -> None:
    """Generate a markdown report summarizing the execution.

    Args:
        report_log: List of log entries
        start_time: Execution start time
        end_time: Execution end time
        anonymize_flag: Whether to anonymize the report
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = Path(REPORTS_DIR) / f"cf_sync_{timestamp}.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w") as f:
        f.write(f"# Cloudflare IP List Sync Report - {timestamp}\n\n")
        f.write(f"**Start Time:** {start_time}\n\n")
        f.write(f"**End Time:** {end_time}\n\n")
        f.write("## Summary\n")
        for log_entry in report_log:
            if anonymize_flag:
                log_entry = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", lambda m: anonymize_email(m.group()), log_entry)
                log_entry = re.sub(r"[a-f0-9]{32}", lambda m: anonymize_account_id(m.group()), log_entry)
            f.write(f"{log_entry}\n")

    logger.info("report_saved", report_file=str(report_file))


async def manage_ip_lists() -> None:
    """Manage Cloudflare IP lists."""
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_log: List[str] = []

    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not api_token:
        logger.error("api_token_missing")
        print("❌ CLOUDFLARE_API_TOKEN is not set.")
        return

    config = load_config("config.yaml")
    anonymize_flag = config.get("anonymize", False)

    client = CloudflareAPIClient(api_token)

    try:
        accounts = await client.get_accounts()

        if not accounts:
            logger.warning("no_accounts_found")
            print("❌ No Cloudflare accounts found.")
            return

        for account in accounts:
            account_id = account["id"]
            account_name = account.get("name", "Unknown Account")

            masked_account_id = anonymize(account_id, anonymize_flag)
            masked_account_name = anonymize(account_name, anonymize_flag)

            logger.info(
                "managing_account",
                account_id=masked_account_id,
                account_name=masked_account_name,
            )
            report_log.append(
                f"### 📌 Managing IP lists for `{masked_account_name}` (ID: `{masked_account_id}`)"
            )

    except Exception as e:
        logger.error("ip_list_management_failed", error=str(e))
        raise
    finally:
        await client.close()

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generate_markdown_report(report_log, start_time, end_time, anonymize_flag)


def main() -> None:
    """Main entry point for IP list manager."""
    configure_logging()
    asyncio.run(manage_ip_lists())


if __name__ == "__main__":
    main()
