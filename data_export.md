## 📌 Data Export
Comprehensive Export Tool for Cloudflare Accounts, Zones & DNS Records.

This script **exports Cloudflare data** (Accounts, Zones, DNS Records) in multiple **formats**:  
✅ JSON  
✅ CSV  
✅ XLS (Excel)  
✅ PDF (Report)

It supports **pagination, rate-limiting handling, and anonymization** to protect sensitive data.

---

## ⚙️ **Installation**
Ensure you have **Python 3.12+** and required dependencies installed.

```bash
pip install requests pandas openpyxl reportlab pyyaml
```

---

## 🔑 **Environment Variables**
Set your **Cloudflare API Token**:
```bash
export CLOUDFLARE_API_TOKEN="your-cloudflare-api-token"
```

---

## 📜 **Configuration (`config.yaml`)**
```yaml
anonymize: true  # Set to 'false' if you want full email/account ID visibility
```
---

## 🛠️ **Usage**
Run the script:
```bash
python3 cloudflare_data_export.py
```

---

## 🔍 **Features**
### ✅ **Supports Large Exports**
- Automatically handles **pagination** (supports **100+ accounts**, **1,000+ zones**, and **50+ records per zone**).  
- Efficient **rate-limiting retries** using `Retry-After`.

### 🔥 **Incremental Updates**
- **Detects changes** before exporting, preventing redundant writes.  
- **If no changes** are found, export is skipped.

### 🔐 **Anonymization (Optional)**
- Emails & Account IDs are **masked** (`anonymize: true` in `config.yaml`).
- Example:
  ```
  📌 Exporting data for account: F************i@g****.com's Account (ID: 1e7ed1...0fbe52)
  ```

### 📤 **Export Formats**
| Format  | File | Purpose |
|---------|------|---------|
| **JSON** | `exports/cloudflare_export.json` | Full structured data |
| **CSV** | `exports/cloudflare_dns_records.csv` | Easy-to-read tabular format |
| **XLS (Excel)** | `exports/cloudflare_dns_records.xlsx` | Spreadsheet analysis |
| **PDF** | `exports/cloudflare_export.pdf` | Printable summary report |



