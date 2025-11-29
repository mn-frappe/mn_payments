from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from mn_payments.api.ebarimt import (
    _ensure_mapping,
    _with_guard,
    get_district_codes,
    lookup_taxpayer_info,
)


class TestEbarimtAPIHelpers(unittest.TestCase):
    def test_ensure_mapping_with_dict(self):
        """Verify _ensure_mapping passes through dict unchanged."""
        payload = {"key": "value"}
        result = _ensure_mapping(payload)
        self.assertEqual(result, {"key": "value"})

    def test_ensure_mapping_with_json_string(self):
        """Verify _ensure_mapping parses JSON strings."""
        payload = '{"register_no": "12345"}'
        result = _ensure_mapping(payload)
        self.assertEqual(result, {"register_no": "12345"})

    def test_ensure_mapping_invalid_type_throws(self):
        """Verify _ensure_mapping throws on non-dict/non-string."""
        with self.assertRaises(frappe.ValidationError):
            _ensure_mapping(123)

    def test_with_guard_success(self):
        """Verify _with_guard calls handler and returns result on success."""
        handler = MagicMock(return_value={"status": "ok"})
        result = _with_guard(handler, "Test operation", arg1="val1")
        self.assertEqual(result, {"status": "ok"})
        handler.assert_called_once_with(arg1="val1")

    @patch("mn_payments.api.ebarimt.frappe.log_error")
    def test_with_guard_logs_generic_errors(self, mock_log_error):
        """Verify _with_guard logs and re-throws generic exceptions."""
        handler = MagicMock(side_effect=RuntimeError("Test error"))
        with self.assertRaises(frappe.ValidationError):
            _with_guard(handler, "Failed operation")
        mock_log_error.assert_called_once()


class TestEbarimtAPIEndpoints(unittest.TestCase):
    @patch("mn_payments.api.ebarimt.fetch_district_codes_service")
    @patch("mn_payments.api.ebarimt.frappe.cache")
    def test_get_district_codes_cached(self, mock_cache, mock_fetch):
        """Verify get_district_codes returns cached result when available."""
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.get_value.return_value = [{"code": "01", "name": "UB"}]

        result = get_district_codes(force_refresh=0)
        self.assertEqual(result, [{"code": "01", "name": "UB"}])
        mock_fetch.assert_not_called()

    @patch("mn_payments.api.ebarimt.fetch_district_codes_service")
    @patch("mn_payments.api.ebarimt.frappe.cache")
    def test_get_district_codes_force_refresh(self, mock_cache, mock_fetch):
        """Verify get_district_codes bypasses cache on force_refresh=1."""
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_fetch.return_value = [{"code": "02", "name": "Darkhan"}]

        result = get_district_codes(force_refresh=1)
        self.assertEqual(result, [{"code": "02", "name": "Darkhan"}])
        mock_cache_instance.get_value.assert_not_called()
        mock_cache_instance.set_value.assert_called_once()

    @patch("mn_payments.api.ebarimt.lookup_taxpayer_info_service")
    def test_lookup_taxpayer_info_success(self, mock_lookup):
        """Verify lookup_taxpayer_info calls service with tin."""
        mock_lookup.return_value = {"tin": "1234567890", "name": "Test Company"}
        result = lookup_taxpayer_info(tin="1234567890")
        self.assertEqual(result["tin"], "1234567890")
        mock_lookup.assert_called_once_with(tin="1234567890")

    def test_lookup_taxpayer_info_no_tin_throws(self):
        """Verify lookup_taxpayer_info throws when tin is missing."""
        with self.assertRaises(frappe.ValidationError):
            lookup_taxpayer_info(tin="")
