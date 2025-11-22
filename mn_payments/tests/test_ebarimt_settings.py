import unittest
from unittest.mock import patch, MagicMock

from mn_payments.ebarimt.client import EbarimtGateway

class TestEbarimtSettings(unittest.TestCase):
    @patch("mn_payments.ebarimt.client.fr")
    def test_get_client_config_missing_settings(self, mock_fr):
        mock_fr.get_single.return_value = None
        with self.assertRaises(Exception):
            EbarimtGateway()

    @patch("mn_payments.ebarimt.client.fr")
    @patch("mn_payments.ebarimt.client.SDKClient")
    def test_ebarimt_gateway_ok(self, mock_sdk_client, mock_fr):
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.get_client_config.return_value = {
            "endpoint": "http://localhost:7080",
            "pos_no": "POS1",
            "merchant_tin": "123",
            "save_to_db": True,
            "send_email": False,
        }
        mock_fr.get_single.return_value = mock_settings

        gw = EbarimtGateway()
        self.assertIsNotNone(gw)
        mock_sdk_client.assert_called_once()

if __name__ == "__main__":
    unittest.main()
