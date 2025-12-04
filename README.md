# cf-box: Cloudflare Management Toolkit

`cf-box` is a comprehensive, production-ready suite of Python tools designed to streamline and automate interactions with the Cloudflare API, enabling efficient management of multiple Cloudflare accounts and their associated resources.

## Features

*   **IP List Manager:** Centrally manage multiple IP access rule lists across your Cloudflare accounts using a single, easy-to-maintain YAML configuration. [Link](https://github.com/fabriziosalmi/cf-box/blob/main/ip_list_manager.md)
*   **Data Export:** Export detailed data from all your Cloudflare accounts, including zones, DNS records, and settings, to various formats (JSON, CSV, Excel, PDF). [Link](https://github.com/fabriziosalmi/cf-box/blob/main/data_export.md)
*   **Analytics Export:** Fetch and export aggregated analytics data from Cloudflare using GraphQL
*   **Async/Await Support:** Modern async architecture using aiohttp for improved performance
*   **Structured Logging:** Professional logging with structlog for better observability
*   **Type Safety:** Pydantic models for API response validation
*   **SQLAlchemy Integration:** Secure database operations with parameterized queries

## Installation

### From Source

```bash
git clone https://github.com/fabriziosalmi/cf-box.git
cd cf-box
pip install -e ".[dev]"
```

### Using Docker

```bash
docker build -t cf-box .
docker run -e CLOUDFLARE_API_TOKEN=your_token cf-box
```

Or using Docker Compose:

```bash
docker-compose up cf-data-export
```

## Quick Start

1. Set your Cloudflare API token:

```bash
export CLOUDFLARE_API_TOKEN=your_api_token_here
```

2. Configure `config.yaml` with your settings

3. Run the tools:

```bash
# Export Cloudflare data
cf-data-export

# Manage IP lists
cf-ip-manager

# Export analytics
cf-analytics
```

## Development

### Setup Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black cf_box/

# Lint code
ruff check cf_box/

# Type checking
mypy cf_box/
```

## Architecture

The project follows a modern Python package structure:

- `cf_box/` - Main package directory
  - `client.py` - Async HTTP client for Cloudflare API
  - `models.py` - Pydantic models for type safety
  - `database.py` - SQLAlchemy database operations
  - `pdf_generator.py` - Template-based PDF generation
  - `logging_config.py` - Structured logging configuration
  - `data_export.py` - Data export module
  - `ip_list_manager.py` - IP list management
  - `aggregated_analytics.py` - Analytics export

## Related Projects

*   **Backup via GitHub Actions:** [cloudflare-backup-actions](https://github.com/fabriziosalmi/cloudflare-backup-actions)
*   **WAF Control:** [wafcontrol](https://github.com/fabriziosalmi/wafcontrol)
*   **Zone Control:** [zonecontrol](https://github.com/fabriziosalmi/zonecontrol)
*   **mTLS with AWS:** [mtls-cloudflare-aws](https://github.com/fabriziosalmi/mtls-cloudflare-aws)
*   **DNS Redundancy:** [dnscontrol-actions](https://github.com/fabriziosalmi/dnscontrol-actions)
