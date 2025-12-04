"""PDF report generation using Jinja2 templates and WeasyPrint."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from cf_box.logging_config import get_logger

logger = get_logger(__name__)


class PDFGenerator:
    """Generate PDF reports from templates."""

    def __init__(self, templates_dir: str = "cf_box/templates"):
        """Initialize PDF generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Create default template if it doesn't exist
        self._ensure_default_template()

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _ensure_default_template(self) -> None:
        """Create default PDF template if it doesn't exist."""
        template_path = self.templates_dir / "cloudflare_report.html"
        if not template_path.exists():
            default_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Cloudflare Data Export Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            line-height: 1.6;
        }
        h1 {
            color: #f38020;
            border-bottom: 2px solid #f38020;
            padding-bottom: 10px;
        }
        h2 {
            color: #404040;
            margin-top: 30px;
        }
        .meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f38020;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .summary {
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>Cloudflare Data Export Report</h1>
    <div class="meta">
        <p><strong>Generated:</strong> {{ timestamp }}</p>
        <p><strong>Anonymized:</strong> {{ anonymized }}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Accounts:</strong> {{ accounts_count }}</p>
        <p><strong>Zones:</strong> {{ zones_count }}</p>
        <p><strong>DNS Records:</strong> {{ dns_records_count }}</p>
    </div>

    {% if accounts %}
    <h2>Accounts</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
            </tr>
        </thead>
        <tbody>
            {% for account in accounts[:10] %}
            <tr>
                <td>{{ account.id }}</td>
                <td>{{ account.name }}</td>
                <td>{{ account.get('type', 'N/A') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% if accounts|length > 10 %}
    <p><em>Showing first 10 of {{ accounts|length }} accounts</em></p>
    {% endif %}
    {% endif %}

    {% if zones %}
    <h2>Zones</h2>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for zone in zones[:10] %}
            <tr>
                <td>{{ zone.name }}</td>
                <td>{{ zone.status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% if zones|length > 10 %}
    <p><em>Showing first 10 of {{ zones|length }} zones</em></p>
    {% endif %}
    {% endif %}

    {% if dns_records %}
    <h2>DNS Records (Sample)</h2>
    <table>
        <thead>
            <tr>
                <th>Type</th>
                <th>Name</th>
                <th>Content</th>
                <th>Proxied</th>
            </tr>
        </thead>
        <tbody>
            {% for record in dns_records[:20] %}
            <tr>
                <td>{{ record.type }}</td>
                <td>{{ record.name }}</td>
                <td>{{ record.content }}</td>
                <td>{{ '✓' if record.proxied else '✗' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% if dns_records|length > 20 %}
    <p><em>Showing first 20 of {{ dns_records|length }} DNS records</em></p>
    {% endif %}
    {% endif %}
</body>
</html>"""
            template_path.write_text(default_template)
            logger.info("default_template_created", path=str(template_path))

    def generate_report(
        self, data: Dict[str, Any], output_path: str, template_name: str = "cloudflare_report.html"
    ) -> None:
        """Generate a PDF report from data.

        Args:
            data: Dictionary containing report data
            output_path: Path where PDF should be saved
            template_name: Name of the template file to use
        """
        try:
            template = self.env.get_template(template_name)

            # Prepare context data
            context = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "anonymized": data.get("anonymized", True),
                "accounts": data.get("accounts", []),
                "zones": data.get("zones", []),
                "dns_records": data.get("dns_records", []),
                "accounts_count": len(data.get("accounts", [])),
                "zones_count": len(data.get("zones", [])),
                "dns_records_count": len(data.get("dns_records", [])),
            }

            # Render HTML
            html_content = template.render(**context)

            # Generate PDF
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            HTML(string=html_content).write_pdf(output_path)

            logger.info("pdf_generated", path=output_path)

        except Exception as e:
            logger.error("pdf_generation_failed", error=str(e), output_path=output_path)
            raise
