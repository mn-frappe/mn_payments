from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import frappe

from mn_payments.utils.qpay import (
    DEFAULT_CALLBACK_PATH,
    QPayConfig,
    resolve_callback_url,
    build_qpay_client,
    get_qpay_config,
)


class TestQPayConfig(unittest.TestCase):
    def test_qpay_config_creation(self):
        """Verify QPayConfig dataclass construction."""
        config = QPayConfig(
            username="test_user",
            password="test_pass",
            invoice_code="TEST_INV",
        )
        self.assertEqual(config.username, "test_user")
        self.assertEqual(config.invoice_code, "TEST_INV")

    def test_qpay_config_with_callback(self):
        """Verify QPayConfig with custom callback URL."""
        config = QPayConfig(
            username="user",
            password="pass",
            invoice_code="CODE",
            callback_url="https://example.com/callback",
        )
        self.assertEqual(config.callback_url, "https://example.com/callback")


class TestQPayUtilHelpers(unittest.TestCase):
    @patch("mn_payments.utils.qpay.get_url")
    def test_resolve_callback_url_default(self, mock_get_url):
        """Verify resolve_callback_url generates default path."""
        mock_get_url.return_value = f"https://example.com{DEFAULT_CALLBACK_PATH}"
        config = QPayConfig(username="test", password="pass", callback_url=None)
        result = resolve_callback_url(None, config=config)
        self.assertEqual(result, f"https://example.com{DEFAULT_CALLBACK_PATH}")
        mock_get_url.assert_called_once_with(DEFAULT_CALLBACK_PATH)

    def test_resolve_callback_url_custom(self):
        """Verify resolve_callback_url respects custom URL."""
        result = resolve_callback_url("https://custom.callback/hook")
        self.assertEqual(result, "https://custom.callback/hook")

    @patch("mn_payments.utils.qpay._load_site_qpay_mapping")
    def test_get_qpay_config_from_site_config(self, mock_load):
        """Verify get_qpay_config reads from site config."""
        mock_load.return_value = {
            "username": "site_user",
            "password": "site_pass",
            "invoice_code": "SITE_CODE",
        }

        config = get_qpay_config(force_refresh=True)
        self.assertEqual(config.username, "site_user")
        self.assertEqual(config.invoice_code, "SITE_CODE")

    def test_get_qpay_config_missing_throws(self):
        """Verify get_qpay_config throws when config incomplete."""
        source = {"username": "user"}
        with self.assertRaises(frappe.ValidationError):
            get_qpay_config(source=source)

    @patch("mn_payments.utils.qpay.QPayClientSync")
    def test_build_qpay_client_constructs_client(self, mock_client_class):
        """Verify build_qpay_client creates QPayClient with QPaySettings."""
        config = QPayConfig(
            username="test",
            password="secret",
            invoice_code="CODE",
        )
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        client = build_qpay_client(config=config, use_cache=False)
        mock_client_class.assert_called_once()
        self.assertEqual(client, mock_client_instance)
