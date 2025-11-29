from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import frappe
from qpay_client.v2.schemas import InvoiceCreateResponse

from mn_payments.api.qpay import (
    _extract_status,
    _guess_description,
    _guess_receiver_code,
    _model_dump,
    _resolve_amount,
    create_invoice,
)


class TestQPayAPIHelpers(unittest.TestCase):
    def test_model_dump_with_pydantic(self):
        """Verify _model_dump handles pydantic models with model_dump()."""
        mock_obj = MagicMock()
        mock_obj.model_dump.return_value = {"invoice_id": "test123"}
        result = _model_dump(mock_obj)
        self.assertEqual(result, {"invoice_id": "test123"})
        mock_obj.model_dump.assert_called_once()

    def test_model_dump_fallback_dict(self):
        """Verify _model_dump falls back to dict() if no model_dump."""
        mock_obj = MagicMock()
        del mock_obj.model_dump  # Remove model_dump to trigger fallback
        mock_obj.dict.return_value = {"key": "value"}
        result = _model_dump(mock_obj)
        self.assertEqual(result, {"key": "value"})

    def test_extract_status_paid(self):
        """Verify _extract_status maps PAID correctly."""
        payload = {"payment_status": "PAID"}
        self.assertEqual(_extract_status(payload), "Paid")

    def test_extract_status_failed(self):
        """Verify _extract_status maps FAILED correctly."""
        payload = {"status": "failed"}
        self.assertEqual(_extract_status(payload), "Failed")

    def test_extract_status_unknown(self):
        """Verify _extract_status returns None for unknown status."""
        payload = {"status": "unknown"}
        self.assertIsNone(_extract_status(payload))

    def test_resolve_amount_explicit(self):
        """Verify _resolve_amount uses override when provided."""
        doc = frappe._dict({"grand_total": 100})
        self.assertEqual(_resolve_amount(doc, 50), 50.0)

    def test_resolve_amount_from_doc(self):
        """Verify _resolve_amount falls back to grand_total."""
        doc = frappe._dict({"grand_total": 123.45})
        self.assertEqual(_resolve_amount(doc, None), 123.45)

    def test_resolve_amount_missing_throws(self):
        """Verify _resolve_amount throws when no amount found."""
        doc = frappe._dict({})
        with self.assertRaises(frappe.ValidationError):
            _resolve_amount(doc, None)

    def test_guess_receiver_code_from_party(self):
        """Verify _guess_receiver_code picks party field."""
        doc = frappe._dict({"name": "PR-001", "party": "CUST-123"})
        self.assertEqual(_guess_receiver_code(doc), "CUST-123")

    def test_guess_receiver_code_fallback_name(self):
        """Verify _guess_receiver_code falls back to name."""
        doc = frappe._dict({"name": "PR-002"})
        self.assertEqual(_guess_receiver_code(doc), "PR-002")

    def test_guess_description_from_subject(self):
        """Verify _guess_description picks subject if present."""
        doc = frappe._dict({"name": "PR-001", "subject": "Payment for Order #42"})
        self.assertEqual(_guess_description(doc), "Payment for Order #42")

    def test_guess_description_fallback_name(self):
        """Verify _guess_description falls back to name."""
        doc = frappe._dict({"name": "PR-003"})
        self.assertEqual(_guess_description(doc), "PR-003")


class TestQPayAPIIntegration(unittest.TestCase):
    @patch("mn_payments.api.qpay.create_simple_invoice")
    @patch("mn_payments.api.qpay.get_qpay_config")
    @patch("mn_payments.api.qpay._get_payment_request")
    def test_create_invoice_success(self, mock_get_pr, mock_config, mock_create):
        """Verify create_invoice flow with mocked dependencies."""
        # Mock Payment Request doc
        mock_pr_doc = frappe._dict(
            {
                "name": "PAY-REQ-001",
                "grand_total": 5000,
                "party": "test-receiver",
                "subject": "Test Payment",
                "currency": "MNT",
            }
        )
        mock_get_pr.return_value = mock_pr_doc

        # Mock config
        mock_config.return_value = frappe._dict({"invoice_code": "TEST_CODE"})

        # Mock QPay response
        mock_response = MagicMock(spec=InvoiceCreateResponse)
        mock_response.model_dump.return_value = {
            "invoice_id": "inv-123",
            "qr_text": "qpay://test",
            "qr_image": "base64data",
            "urls": ["https://qpay.example"],
        }
        mock_create.return_value = mock_response

        with patch("mn_payments.api.qpay._upsert_invoice_doc") as mock_upsert:
            mock_invoice_doc = frappe._dict(
                {
                    "name": "QINV-001",
                    "invoice_id": "inv-123",
                    "status": "Pending",
                    "qr_text": "qpay://test",
                    "qr_image": "base64data",
                    "urls": ["https://qpay.example"],
                }
            )
            mock_upsert.return_value = mock_invoice_doc

            result = create_invoice(
                payment_request="PAY-REQ-001",
                invoice_receiver_code="custom-receiver",
                amount=4500,
            )

            self.assertEqual(result["payment_request"], "PAY-REQ-001")
            self.assertEqual(result["invoice_id"], "inv-123")
            self.assertEqual(result["status"], "Pending")
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            self.assertEqual(call_kwargs["amount"], Decimal("4500"))
            self.assertEqual(call_kwargs["invoice_receiver_code"], "custom-receiver")
