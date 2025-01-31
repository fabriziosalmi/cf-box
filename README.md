# Cloudflare IP List Manager

## Overview
Cloudflare IP List Manager is a Python tool that automates the synchronization of IP lists across multiple Cloudflare accounts. It is designed to help Cloudflare users efficiently manage allowlists, blocklists, and trusted IP ranges while handling rate limits effectively.

> [!WARNING]
> Set your GitHub repository visibility to **private** before to populate config.yaml and execute the runner. A simple solution is to store zone ids as GitHub Actions secrets too, not just the Cloudflare API token.

## Features
- ✅ **Automatic IP list synchronization** with Cloudflare's API.
- ✅ **Supports multiple accounts and IP lists** via a YAML configuration.
- ✅ **Fetches IPs from external sources** (JSON and plaintext).
- ✅ **Caches IP lists locally** to avoid unnecessary API requests.
- ✅ **Optimized batch updates** to avoid concurrent modification limits.

## Requirements
- Python 3.7+
- `requests`
- `pyyaml`

### Install Dependencies
```sh
pip install -r requirements.txt
```

## Configuration
The script uses a `config.yaml` file to define accounts, IP lists, and sources.

### Example `config.yaml`
```yaml
accounts:
  - id: "1e7ed1e7e9b2dfdfb15ed609d30fbe52"
    name: "Example Cloudflare Account"
    lists:
      - name: "trusted_aws_ips"
        sync_from: "https://raw.githubusercontent.com/lord-alfred/ipranges/main/aws.json"
        type: "json"
      - name: "bad_ips"
        sync_from: "https://github.com/stamparm/ipsum/raw/refs/heads/master/levels/3.txt"
        type: "text"
    notifications:
      webhook: "https://your-webhook-url.com"
```

## Usage
### Set API Token
Ensure your Cloudflare API token is set as an environment variable or as GitHub Actions Repository Secret:
```sh
export CLOUDFLARE_API_TOKEN="your_cloudflare_api_token"
```

### Run the Script
```sh
python cloudflare_ip_list_manager.py
```

## How It Works
1. **Reads the `config.yaml`** for accounts and IP list definitions.
2. **Fetches the current Cloudflare IP lists** to compare with external sources.
3. **Downloads IPs from the specified sources** (JSON or plaintext files).
4. **Checks for changes** to avoid unnecessary API updates.
5. **Bulk updates Cloudflare IP lists** to comply with rate limits.
6. **Caches results** to minimize external requests.

## Cloudflare API Rate Limit Handling
- **Cloudflare limits API requests** to ~1,200 per 5 minutes per account.
- The script **uses a single bulk update instead of multiple small updates**.
- Implements **adaptive backoff when rate-limited**, using `Retry-After` if available.

## Contributing
Feel free to submit pull requests and improve the project.

## License
This project is licensed under the MIT License.

> [!INFO] Disclaimer
> This tool is not affiliated with or officially supported by Cloudflare.

