# 🌩️ Data Export

A powerful script to **export Cloudflare data** across multiple accounts, zones, and DNS records, supporting **incremental updates** and **anonymization**.

## 🚀 Features
- **Exports multiple accounts & zones** (Cloudflare UI doesn't allow this)
- **Incremental updates** to avoid full re-fetching
- **Anonymization** for emails & account IDs
- **Supports JSON, Markdown, and CSV exports**
- **Handles API rate limiting with retries**
- **GitHub Actions workflow** for automation

## 📦 Exported Data
| Format | File | Description |
|--------|------|-------------|
| JSON | `exports/cloudflare_export.json` | Structured export of accounts, zones, and records |
| Markdown | `exports/cloudflare_export.md` | Readable export summary |
| CSV | `exports/cloudflare_dns_records.csv` | DNS records export |

## 🛠️ Setup & Usage

### **1️⃣ Install Dependencies**
Ensure you have Python 3.8+ installed, then install required packages:
```bash
pip install -r requirements.txt
```

### **2️⃣ Set Cloudflare API Token**
Export your API token as an environment variable:
```bash
export CLOUDFLARE_API_TOKEN="your_cloudflare_api_token"
```
Or create a `.env` file:
```
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
```

### **3️⃣ Run the Export**
```bash
python3 cloudflare_data_export.py
```

### **4️⃣ Automate with GitHub Actions**
You can set up GitHub Actions to automatically export data daily. See `.github/workflows/export.yml`.

## 🔧 Configuration (Optional)
Edit `config.yaml` to enable or disable anonymization.

```yaml
anonymization: true  # Set to false if you want raw account details
export_path: "exports"  # Change directory if needed
```

## 🚨 Rate Limits & Best Practices
Cloudflare API rate limits apply! The script:
- Uses **adaptive retries** (`Retry-After` headers)
- **Throttles requests** to prevent bans
- **Fetches data incrementally** instead of full exports every time

## 📜 License
MIT – Free to use & modify.
