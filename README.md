# cf-box: Cloudflare Management Toolkit

`cf-box` is a comprehensive suite of Python tools designed to streamline and automate interactions with the Cloudflare API, enabling efficient management of multiple Cloudflare accounts and their associated resources.

**Key Features:**

*   **IP List Manager:** Centrally manage multiple IP access rule lists across your Cloudflare accounts using a single, easy-to-maintain YAML configuration. [Link](https://github.com/fabriziosalmi/cf-box/blob/main/ip_list_manager.md)
*   **Data Export:** Export detailed data from all your Cloudflare accounts, including zones, DNS records, and settings, to various formats (e.g., JSON, CSV, YAML). [Link](https://github.com/fabriziosalmi/cf-box/blob/main/data_export.md)
*   **Backup via GitHub Actions:** Automate backups of your Cloudflare account configurations (zones, DNS records, page rules, etc.) using convenient GitHub Actions workflows. [Link](https://github.com/fabriziosalmi/cloudflare-backup-actions)
*   **WAF (Web Application Firewall) Control:** Manage WAF rules and settings consistently across multiple Cloudflare zones from a unified YAML configuration. [Link](https://github.com/fabriziosalmi/wafcontrol)
*   **Zone Control:** Simplify the management of settings for multiple Cloudflare zones through a centralized YAML configuration file. [Link](https://github.com/fabriziosalmi/zonecontrol)
*   **mTLS with AWS:** Provides scripts to generate and configure the necessary components for establishing mTLS (mutual TLS) authentication between Cloudflare and AWS services. [Link](https://github.com/fabriziosalmi/mtls-cloudflare-aws)
*   **DNS Redundancy with DNSControl and GitHub Actions:** Manage and maintain redundant DNS configurations across multiple providers using DNSControl and automated GitHub Actions workflows. [Link](https://github.com/fabriziosalmi/dnscontrol-actions)
