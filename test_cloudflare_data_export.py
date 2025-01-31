import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import json
import yaml
import pandas as pd

from cloudflare_data_export import (
    load_config,
    load_previous_export,
    save_json_if_changed,
    save_csv_if_changed,
    save_xls,
    save_pdf,
    clean_data_for_sql,
    save_to_sqlite,
    save_to_mysql_file,
    request_with_retries,
    fetch_all_pages,
    anonymize_email,
    anonymize_account_id,
    anonymize_data,
    export_cloudflare_data
)

class TestCloudflareDataExport(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data="anonymize: true")
    def test_load_config(self, mock_file):
        config = load_config("config.yaml")
        self.assertEqual(config, {"anonymize": True})
        mock_file.assert_called_with("config.yaml", 'r')

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    def test_load_previous_export(self, mock_file, mock_exists):
        data = load_previous_export("test.json")
        self.assertEqual(data, {"key": "value"})
        mock_file.assert_called_with(os.path.join("exports", "test.json"), "r")

    @patch("os.path.exists", return_value=False)
    def test_load_previous_export_no_file(self, mock_exists):
        data = load_previous_export("test.json")
        self.assertEqual(data, [])

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_json_if_changed(self, mock_json_dump, mock_file):
        data = {"key": "value"}
        with patch("cloudflare_data_export.load_previous_export", return_value={}):
            result = save_json_if_changed(data, "test.json")
            self.assertTrue(result)
            mock_file.assert_called_with(os.path.join("exports", "test.json"), "w")
            mock_json_dump.assert_called_with(data, mock_file(), indent=2)

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_save_csv_if_changed(self, mock_csv_writer, mock_file):
        data = [{"key": "value"}]
        with patch("cloudflare_data_export.load_previous_export", return_value={}):
            result = save_csv_if_changed(data, "test.csv")
            self.assertTrue(result)
            mock_file.assert_called_with(os.path.join("exports", "test.csv"), "w", newline="")
            mock_csv_writer().writeheader.assert_called_once()
            mock_csv_writer().writerows.assert_called_with(data)

    @patch("pandas.DataFrame.to_excel")
    def test_save_xls(self, mock_to_excel):
        data = [{"key": "value"}]
        save_xls(data, "test.xlsx")
        mock_to_excel.assert_called_once()

    @patch("reportlab.pdfgen.canvas.Canvas.save")
    def test_save_pdf(self, mock_save):
        data = {"section": [{"key": "value"}]}
        save_pdf(data, "test.pdf")
        mock_save.assert_called_once()

    def test_clean_data_for_sql(self):
        data = [{"key": {"nested": "value"}}]
        cleaned_data = clean_data_for_sql(data)
        self.assertEqual(cleaned_data, [{"key": '{"nested": "value"}'}])

    @patch("sqlite3.connect")
    @patch("pandas.DataFrame.to_sql")
    def test_save_to_sqlite(self, mock_to_sql, mock_connect):
        data = [{"key": "value"}]
        save_to_sqlite(data, "test.db", "test_table")
        mock_connect.assert_called_with(os.path.join("exports", "test.db"))
        mock_to_sql.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_save_to_mysql_file(self, mock_file):
        data = [{"key": "value"}]
        save_to_mysql_file(data, "test.sql", "test_table")
        mock_file.assert_called_with(os.path.join("exports", "test.sql"), "w")

    @patch("requests.request")
    def test_request_with_retries(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        result = request_with_retries("http://example.com", {})
        self.assertEqual(result, {"key": "value"})

    @patch("cloudflare_data_export.request_with_retries")
    def test_fetch_all_pages(self, mock_request_with_retries):
        mock_request_with_retries.side_effect = [
            {"success": True, "result": [{"key": "value"}]},
            {"success": True, "result": []}
        ]
        result = fetch_all_pages("http://example.com", {})
        self.assertEqual(result, [{"key": "value"}])

    def test_anonymize_email(self):
        email = "test@example.com"
        anonymized_email = anonymize_email(email)
        self.assertEqual(anonymized_email, "t**t@e******.com")

    def test_anonymize_account_id(self):
        account_id = "1234567890abcdef"
        anonymized_id = anonymize_account_id(account_id)
        self.assertEqual(anonymized_id, "123456...abcdef")

    def test_anonymize_data(self):
        data = {"accounts": [{"name": "test@example.com", "id": "1234567890abcdef"}]}
        anonymized_data = anonymize_data(data)
        self.assertEqual(anonymized_data, {"accounts": [{"name": "t**t@e******.com", "id": "123456...abcdef"}]})

    @patch("os.getenv", return_value="dummy_token")
    @patch("cloudflare_data_export.load_config", return_value={"anonymize": True})
    @patch("cloudflare_data_export.fetch_all_pages", return_value=[{"id": "1234567890abcdef", "name": "test@example.com"}])
    @patch("cloudflare_data_export.save_json_if_changed")
    @patch("cloudflare_data_export.save_csv_if_changed")
    @patch("cloudflare_data_export.save_xls")
    @patch("cloudflare_data_export.save_pdf")
    def test_export_cloudflare_data(self, mock_save_pdf, mock_save_xls, mock_save_csv, mock_save_json, mock_fetch_all_pages, mock_load_config, mock_getenv):
        export_cloudflare_data()
        mock_getenv.assert_called_with("CLOUDFLARE_API_TOKEN")
        mock_load_config.assert_called_with("config.yaml")
        mock_fetch_all_pages.assert_called()
        mock_save_json.assert_called()
        mock_save_csv.assert_called()
        mock_save_xls.assert_called()
        mock_save_pdf.assert_called()

if __name__ == "__main__":
    unittest.main()