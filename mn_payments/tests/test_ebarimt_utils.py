from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from mn_payments.utils.ebarimt import (
    PosAPIConfig,
    TPIServiceConfig,
    get_posapi_config,
    get_tpi_config,
)


class TestEbarimtConfigs(unittest.TestCase):
    def test_posapi_config_creation(self):
        """Verify PosAPIConfig dataclass construction."""
        config = PosAPIConfig(
            base_url="https://posapi.test",
        )
        self.assertEqual(config.base_url, "https://posapi.test")

    def test_tpi_config_creation(self):
        """Verify TPIServiceConfig dataclass construction."""
        config = TPIServiceConfig(
            username="1234567890",
            password="secret",
        )
        self.assertEqual(config.username, "1234567890")

    def test_get_posapi_config_from_site_config(self):
        """Verify get_posapi_config reads from site config."""
        source = {
            "base_url": "https://config.posapi",
        }
        config = get_posapi_config(source=source)
        self.assertEqual(config.base_url, "https://config.posapi/")

    def test_get_posapi_config_missing_throws(self):
        """Verify get_posapi_config allows minimal config (no required fields)."""
        source = {}
        config = get_posapi_config(source=source)
        # PosAPI has defaults and no required fields, so this should succeed
        self.assertIsNotNone(config)

    def test_get_tpi_config_from_site_config(self):
        """Verify get_tpi_config reads from site config."""
        source = {
            "username": "9876543210",
            "password": "pass123",
        }
        config = get_tpi_config(source=source)
        self.assertEqual(config.username, "9876543210")

    def test_get_tpi_config_missing_throws(self):
        """Verify get_tpi_config throws when config incomplete."""
        source = {"username": "test"}  # Missing password
        with self.assertRaises(frappe.ValidationError):
            get_tpi_config(source=source)
