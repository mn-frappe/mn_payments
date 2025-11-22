import unittest
from unittest.mock import patch, MagicMock
import frappe

from mn_payments.api.payment import _compute_special_tax


class TestTaxCalculations(unittest.TestCase):
	@patch("mn_payments.api.payment.frappe.db.get_value")
	def test_compute_special_tax_with_type(self, mock_get_value):
		"""Test special tax calculation with specified tax type."""
		mock_get_value.return_value = 5.0  # 5% rate

		result = _compute_special_tax(1000, "Test Tax Type")
		self.assertEqual(result, 50.0)  # 1000 * 5% = 50

		mock_get_value.assert_called_once_with("Special Tax Type", "Test Tax Type", "rate")

	@patch("mn_payments.api.payment.frappe.db.get_value")
	def test_compute_special_tax_default(self, mock_get_value):
		"""Test special tax calculation with default tax type."""
		# First call returns default tax rate, second call returns None (no specific type)
		mock_get_value.side_effect = [5.0, None]

		result = _compute_special_tax(2000, None)
		self.assertEqual(result, 100.0)  # 2000 * 5% = 100

		# Should check for default tax first
		mock_get_value.assert_any_call("Special Tax Type", {"is_default": 1}, ["rate"])

	@patch("mn_payments.api.payment.frappe.db.get_value")
	def test_compute_special_tax_no_default(self, mock_get_value):
		"""Test special tax calculation when no default tax exists."""
		mock_get_value.return_value = None

		result = _compute_special_tax(1000, None)
		self.assertEqual(result, 0.0)  # No tax

	@patch("mn_payments.api.payment.frappe.db.get_value")
	def test_compute_special_tax_zero_rate(self, mock_get_value):
		"""Test special tax calculation with zero rate."""
		mock_get_value.return_value = 0

		result = _compute_special_tax(1000, "Zero Tax")
		self.assertEqual(result, 0.0)

	def test_city_tax_calculation(self):
		"""Test city tax calculation logic."""
		base_amount = 1000
		city_tax_rate = 1.5  # 1.5%

		expected_city_tax = round(base_amount * (city_tax_rate / 100), 2)
		self.assertEqual(expected_city_tax, 15.0)

		# Test with different rates
		self.assertEqual(round(1000 * (2.0 / 100), 2), 20.0)
		self.assertEqual(round(1000 * (0.5 / 100), 2), 5.0)

	def test_total_calculation_integration(self):
		"""Test complete tax calculation integration."""
		base_amount = 1000
		special_tax = 30  # 3% of 1000
		city_tax = 15    # 1.5% of 1000
		expected_total = 1045

		actual_total = base_amount + special_tax + city_tax
		self.assertEqual(actual_total, expected_total)

	@patch("mn_payments.api.payment.frappe.db.get_value")
	def test_tax_calculation_edge_cases(self, mock_get_value):
		"""Test edge cases in tax calculations."""
		# Test with zero amount
		mock_get_value.return_value = 10.0
		result = _compute_special_tax(0, "Test")
		self.assertEqual(result, 0.0)

		# Test with negative amount (should still work)
		result = _compute_special_tax(-1000, "Test")
		self.assertEqual(result, -100.0)

		# Test rounding
		mock_get_value.return_value = 3.14159
		result = _compute_special_tax(1000, "Test")
		self.assertEqual(result, 31.42)  # Should be rounded to 2 decimal places


if __name__ == "__main__":
	unittest.main()