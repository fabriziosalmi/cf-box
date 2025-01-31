import unittest
from unittest.mock import patch, mock_open

from cloudflare_ip_list_manager import (
    load_config, anonymize_email, anonymize_account_id
)

class TestCloudflareIPListManager(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data="anonymize: true")
    def test_load_config(self, mock_file):
        config = load_config("config.yaml")
        self.assertEqual(config, {"anonymize": True})
        mock_file.assert_called_once_with("config.yaml", 'r')

    def test_anonymize_email(self):
        email = "test@example.com"
        anonymized_email = anonymize_email(email)
        self.assertEqual(anonymized_email, "t**t@e******.com")

    def test_anonymize_account_id(self):
        account_id = "1234567890abcdef1234567890abcdef"
        anonymized_id = anonymize_account_id(account_id)
        self.assertEqual(anonymized_id, "123456...cdef")

    def test_anonymize(self):
        email = "test@example.com"
        account_id = "1234567890abcdef1234567890abcdef"
        anonymized_email = anonymize_email(email)
        anonymized_id = anonymize_account_id(account_id)
        self.assertEqual(anonymized_email, "t**t@e******.com")
        self.assertEqual(anonymized_id, "123456...cdef")
