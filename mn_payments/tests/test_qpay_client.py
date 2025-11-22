import unittest
from unittest.mock import patch, MagicMock
import frappe

from mn_payments.qpay.client import QPayGateway


class TestQPayGateway(unittest.TestCase):
	@patch("mn_payments.qpay.client.QPaySDK")
	@patch("mn_payments.qpay.client.frappe.get_doc")
	def test_create_invoice_success(self, mock_get_doc, mock_sdk_class):
		mock_provider = MagicMock()
		mock_provider.username = "test_user"
		mock_provider.get_password.return_value = "test_pass"
		mock_provider.invoice_code = "TEST_CODE"
		mock_provider.callback_url = "http://example.com/callback"
		mock_provider.environment = "Sandbox"
		mock_get_doc.return_value = mock_provider

		mock_sdk = MagicMock()
		mock_invoice = MagicMock()
		mock_invoice.invoice_id = "inv_123"
		mock_invoice.qr_text = "qr_data"
		mock_invoice.qr_image = "qr_img"
		mock_sdk.invoice_create_simple.return_value = mock_invoice
		mock_sdk_class.return_value = mock_sdk

		gw = QPayGateway("test_provider")
		result = gw.create_invoice(sender_code="TX001", description="Test", amount=1000)

		self.assertEqual(result.invoice_id, "inv_123")
		mock_sdk.invoice_create_simple.assert_called_once()

	@patch("mn_payments.qpay.client.frappe.throw")
	@patch("mn_payments.qpay.client.QPaySDK", None)
	def test_no_sdk_installed(self, mock_throw):
		with self.assertRaises(Exception):
			QPayGateway("test_provider")


if __name__ == "__main__":
	unittest.main()