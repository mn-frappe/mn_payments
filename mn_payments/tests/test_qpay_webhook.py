import hashlib
import hmac
import json
import unittest
from unittest.mock import MagicMock, patch

from mn_payments.qpay.webhook import handle


class TestQPayWebhook(unittest.TestCase):
    def setUp(self):
        self.payload = {"invoice_id": "inv_123", "status": "PAID"}
        self.provider_name = "TestProvider"
        self.secret = "wh-secret"

    def _sign(self, payload, secret):
        message = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    @patch("mn_payments.qpay.webhook.frappe")
    def test_verify_signature_success_and_handle(self, mock_fr):
        mock_provider = MagicMock()
        mock_provider.get_password.return_value = self.secret
        mock_fr.get_doc.return_value = mock_provider
        signature = self._sign(self.payload, self.secret)

        # Mock transaction lookup and tx doc
        mock_fr.get_all.return_value = [{"name": "TX001"}]
        tx_doc = MagicMock()
        mock_fr.get_doc.side_effect = [mock_provider, tx_doc]

        result = handle(self.payload, signature=signature, provider=self.provider_name)
        self.assertEqual(result.get("status"), "success")
        tx_doc.save.assert_called_once()

    @patch("mn_payments.qpay.webhook.frappe")
    def test_handle_invalid_signature(self, mock_fr):
        mock_provider = MagicMock()
        mock_provider.get_password.return_value = self.secret
        mock_fr.get_doc.return_value = mock_provider
        bad_signature = "000"

        with self.assertRaises(Exception):
            handle(self.payload, signature=bad_signature, provider=self.provider_name)


if __name__ == "__main__":
    unittest.main()
