import unittest
from unittest.mock import MagicMock, patch

import frappe

from mn_payments.api.payment import create_payment, fetch_payment
from mn_payments.qpay.webhook import handle


class TestIntegrationFlow(unittest.TestCase):
    @patch("mn_payments.api.payment.QPayGateway")
    @patch("mn_payments.api.payment.EbarimtGateway")
    def test_end_to_end_flow(self, mock_ebarimt_gw_class, mock_qpay_gw_class):
        # Prepare mocks
        mock_qpay_gw = MagicMock()
        mock_qpay_gw.create_invoice.return_value = MagicMock(invoice_id="inv_001", qr_text="qr", qr_image="img")
        mock_qpay_gw_class.return_value = mock_qpay_gw

        mock_ebarimt_gw = MagicMock()
        mock_ebarimt_gw.create_receipt.return_value = {"receipt_id": "r_001"}
        mock_ebarimt_gw_class.return_value = mock_ebarimt_gw

        # Create a default provider to avoid provider lookup errors
        provider = frappe.get_doc(
            {
                "doctype": "Payment Provider",
                "provider": "QPay",
                "environment": "Sandbox",
                "username": "user",
                "password": "pass",
                "invoice_code": "TEST",
                "callback_url": "https://example.com/callback",
                "enabled": 1,
                "is_default": 1,
            }
        )
        provider.insert(ignore_permissions=True)

        # Call create_payment
        ret = create_payment(reference_doctype=None, reference_name=None, amount=1000, payer_email="test@test.com")
        self.assertEqual(ret["status"], "Pending")
        ticket = ret["transaction"]

        # Fetch payment should return pending
        f = fetch_payment(transaction=ticket)
        self.assertEqual(f["status"], "Pending")

        # Build webhook payload and signature
        payload = {"invoice_id": "inv_001", "status": "PAID"}
        provider_doc = frappe.get_doc("Payment Provider", provider.name)
        # For signature, use provider webhook_secret
        provider_doc.webhook_secret = "secret"

        # Call webhook handle - signature checks are validated in their own tests, skipping here
        _ = handle(payload, signature=None, provider=provider.name)

        # After webhook, check transaction status updated to 'Paid'
        f2 = fetch_payment(transaction=ticket)
        self.assertEqual(f2["status"], "Paid")

        # eBarimt create_receipt should not be automatically called in webhook (we may call separately)
        # cleanup
        frappe.db.delete("Payment Provider", provider.name)


if __name__ == "__main__":
    unittest.main()
