import unittest
from unittest.mock import patch, MagicMock
import frappe

from mn_payments.integrations.gs1.importer import import_from_url, _ensure_tax_type, _parse_workbook_bytes, _find_barcode_in_row


class TestGS1Importer(unittest.TestCase):
	@patch("mn_payments.integrations.gs1.importer.requests.get")
	@patch("mn_payments.integrations.gs1.importer._parse_workbook_bytes")
	def test_import_from_url_success(self, mock_parse, mock_get):
		mock_resp = MagicMock()
		mock_resp.content = b"fake_xlsx"
		mock_resp.raise_for_status.return_value = None
		mock_get.return_value = mock_resp

		mock_parse.return_value = [{"Barcode": "1234567890123", "Name": "Test Product"}]

		with patch("mn_payments.integrations.gs1.importer._ensure_tax_type", return_value="On tsgoi"), \
		     patch("mn_payments.integrations.gs1.importer._create_map_entry") as mock_create:
			result = import_from_url("http://example.com/test.xlsx")
			self.assertEqual(result["imported"], 1)
			mock_create.assert_called_once()

	@patch("mn_payments.integrations.gs1.importer.frappe.get_doc")
	def test_ensure_tax_type_new(self, mock_get_doc):
		mock_doc = MagicMock()
		mock_doc.name = "On tsgoi"
		mock_get_doc.return_value = mock_doc

		with patch("mn_payments.integrations.gs1.importer.frappe.db.get_value", return_value=None):
			name = _ensure_tax_type("On tsgoi", 3.0)
			self.assertEqual(name, "On tsgoi")
			mock_get_doc.assert_called_once()

	def test_find_barcode_in_row(self):
		row = {"GTIN": "1234567890123", "Name": "Product"}
		barcode = _find_barcode_in_row(row)
		self.assertEqual(barcode, "1234567890123")

		row_no_barcode = {"Name": "Product"}
		barcode = _find_barcode_in_row(row_no_barcode)
		self.assertIsNone(barcode)


if __name__ == "__main__":
	unittest.main()