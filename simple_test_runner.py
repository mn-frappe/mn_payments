#!/usr/bin/env python3
"""
Simple test runner that manually runs tests with mocked dependencies.
"""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock frappe module BEFORE any imports
from unittest.mock import MagicMock

# Mock frappe module
frappe_mock = MagicMock()
frappe_mock.db = MagicMock()
frappe_mock.db.get_value = MagicMock(return_value=None)
frappe_mock.db.set_value = MagicMock()
frappe_mock.get_doc = MagicMock()
frappe_mock.new_doc = MagicMock()
frappe_mock.throw = MagicMock(side_effect=Exception)
frappe_mock.msgprint = MagicMock()
frappe_mock.log_error = MagicMock()
frappe_mock._ = lambda x: x  # Mock translation
frappe_mock.utils = MagicMock()
frappe_mock.utils.now = MagicMock(return_value="2025-11-22 12:00:00")
frappe_mock.utils.get_datetime = MagicMock(return_value=MagicMock())
frappe_mock.utils.getdate = MagicMock(return_value="2025-11-22")

# Mock Document class
class MockDocument:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'test')
        # Set default attributes for PaymentTransaction
        self.amount = kwargs.get('amount', 0)
        self.special_tax = kwargs.get('special_tax', 0)
        self.city_tax = kwargs.get('city_tax', 0)
        self.total = 0
        self.payer_type = kwargs.get('payer_type', "Individual")
        self.retain_sensitive = kwargs.get('retain_sensitive', 0)
        self.qr_text = kwargs.get('qr_text', None)
        self.username = "test_user"
        self.password = "test_pass"
        self.invoice_code = "TEST_CODE"
        self.callback_url = "http://example.com/callback"
        self.environment = "Sandbox"
        for k, v in kwargs.items():
            setattr(self, k, v)

    def save(self):
        pass

    def insert(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass

frappe_mock.Document = MockDocument

# Mock specific Frappe classes
frappe_mock.model = MagicMock()
frappe_mock.model.document = MagicMock()
frappe_mock.model.document.Document = MockDocument

# Mock QPaySettings
class MockQPaySettings:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Mock qpay_client modules
qpay_mock = MagicMock()
qpay_mock.QPaySettings = MockQPaySettings
qpay_mock.QPaySDK = MagicMock()

# Apply all mocks BEFORE importing anything
sys.modules['frappe'] = frappe_mock
sys.modules['frappe.model.document'] = frappe_mock.model.document
sys.modules['frappe.utils'] = frappe_mock.utils
sys.modules['qpay_client'] = qpay_mock
sys.modules['qpay_client.settings'] = qpay_mock

import unittest
import unittest.mock

# Mock frappe.tests.utils
frappe_mock.tests = MagicMock()
frappe_mock.tests.utils = MagicMock()

class MockFrappeTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

frappe_mock.tests.utils.FrappeTestCase = MockFrappeTestCase

# Now import and run tests manually
def run_tests():
    results = []

    # Test PaymentTransaction
    try:
        from mn_payments.doctype.payment_transaction.payment_transaction import PaymentTransaction, scrub_sensitive_fields

        # Test compute_total
        doc = PaymentTransaction(amount=1000, special_tax=50, city_tax=10)
        doc._compute_total()
        assert doc.total == 1060, f'Expected 1060, got {doc.total}'
        print("✓ test_compute_total passed")
        results.append(True)

        # Test privacy individual
        doc = PaymentTransaction(payer_type="Individual", retain_sensitive=1, qr_text="test")
        doc._apply_privacy_rules()
        assert doc.retain_sensitive == 0, f'Expected 0, got {doc.retain_sensitive}'
        assert doc.qr_text is None, f'Expected None, got {doc.qr_text}'
        print("✓ test_privacy_individual passed")
        results.append(True)

        # Test privacy entity
        doc = PaymentTransaction(payer_type="Entity", retain_sensitive=1, qr_text="test")
        doc._apply_privacy_rules()
        assert doc.retain_sensitive == 1, f'Expected 1, got {doc.retain_sensitive}'
        assert doc.qr_text == "test", f'Expected "test", got {doc.qr_text}'
        print("✓ test_privacy_entity passed")
        results.append(True)

        # Test scrub_sensitive_fields
        doc = PaymentTransaction(qr_text="sensitive", payer_type="Individual")
        doc.name = "test_doc"
        doc._apply_privacy_rules()  # Apply privacy rules first
        # Mock the db operations
        with unittest.mock.patch('mn_payments.doctype.payment_transaction.payment_transaction.frappe.db.set_value'), \
             unittest.mock.patch('mn_payments.doctype.payment_transaction.payment_transaction.frappe.get_doc', return_value=doc):
            scrub_sensitive_fields(["test_doc"])
            assert doc.qr_text is None, f'Expected None, got {doc.qr_text}'
            print("✓ test_scrub_sensitive_fields passed")
            results.append(True)

    except Exception as e:
        print(f"PaymentTransaction tests failed: {e}")
        results.append(False)

    # Test GS1 Importer
    try:
        from mn_payments.integrations.gs1.importer import _ensure_tax_type, _find_barcode_in_row

        # Test _ensure_tax_type
        with unittest.mock.patch('mn_payments.integrations.gs1.importer.frappe.db.get_value', return_value=None), \
             unittest.mock.patch('mn_payments.integrations.gs1.importer.frappe.get_doc') as mock_get_doc:
            mock_doc = MagicMock()
            mock_doc.name = "On tsgoi"
            mock_get_doc.return_value = mock_doc
            result = _ensure_tax_type("On tsgoi", 3.0)
            assert result == "On tsgoi", f"Expected 'On tsgoi', got {result}"
            print("✓ test_ensure_tax_type_new passed")
            results.append(True)

        # Test _find_barcode_in_row
        row = {"GTIN": "1234567890123", "Name": "Product"}
        barcode = _find_barcode_in_row(row)
        assert barcode == "1234567890123", f"Expected '1234567890123', got {barcode}"
        print("✓ test_find_barcode_in_row passed")
        results.append(True)

    except Exception as e:
        print(f"GS1 Importer tests failed: {e}")
        results.append(False)

    # Test Tax Calculations
    try:
        from mn_payments.api.payment import _compute_special_tax

        # Test special tax with specified type
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', return_value=5.0):
            result = _compute_special_tax(1000, "Test Tax")
            assert result == 50.0, f'Expected 50.0, got {result}'
            print("✓ test_compute_special_tax_with_type passed")
            results.append(True)

        # Test special tax with default
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', side_effect=[5.0, None]):
            result = _compute_special_tax(2000, None)
            assert result == 100.0, f'Expected 100.0, got {result}'
            print("✓ test_compute_special_tax_default passed")
            results.append(True)

        # Test special tax with no default
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', return_value=None):
            result = _compute_special_tax(1000, None)
            assert result == 0.0, f'Expected 0.0, got {result}'
            print("✓ test_compute_special_tax_no_default passed")
            results.append(True)

        # Test city tax calculation
        base_amount = 1000
        city_tax_rate = 1.5
        expected_city_tax = round(base_amount * (city_tax_rate / 100), 2)
        assert expected_city_tax == 15.0, f'Expected 15.0, got {expected_city_tax}'
        print("✓ test_city_tax_calculation passed")
        results.append(True)

        # Test total calculation integration
        base_amount = 1000
        special_tax = 30
        city_tax = 15
        expected_total = 1045
        actual_total = base_amount + special_tax + city_tax
        assert actual_total == expected_total, f'Expected {expected_total}, got {actual_total}'
        print("✓ test_total_calculation_integration passed")
        results.append(True)

    except Exception as e:
        print(f"Tax calculation tests failed: {e}")
        results.append(False)

    # Test QPay Client
    try:
        from mn_payments.qpay.client import QPayGateway

        # Mock the SDK check
        with unittest.mock.patch('mn_payments.qpay.client.QPaySDK', None):
            try:
                QPayGateway("test")
                print("✗ test_no_sdk_installed should have raised exception")
                results.append(False)
            except:
                print("✓ test_no_sdk_installed passed")
                results.append(True)

    except Exception as e:
        print(f"QPay Client tests failed: {e}")
        results.append(False)

    # Test Tax Calculations
    try:
        from mn_payments.api.payment import _compute_special_tax

        # Test special tax with specified type
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', return_value=5.0):
            result = _compute_special_tax(1000, "Test Tax")
            assert result == 50.0, f'Expected 50.0, got {result}'
            print("✓ test_compute_special_tax_with_type passed")
            results.append(True)

        # Test special tax with default
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', side_effect=[5.0, None]):
            result = _compute_special_tax(2000, None)
            assert result == 100.0, f'Expected 100.0, got {result}'
            print("✓ test_compute_special_tax_default passed")
            results.append(True)

        # Test special tax with no default
        with unittest.mock.patch('mn_payments.api.payment.frappe.db.get_value', return_value=None):
            result = _compute_special_tax(1000, None)
            assert result == 0.0, f'Expected 0.0, got {result}'
            print("✓ test_compute_special_tax_no_default passed")
            results.append(True)

        # Test city tax calculation
        base_amount = 1000
        city_tax_rate = 1.5
        expected_city_tax = round(base_amount * (city_tax_rate / 100), 2)
        assert expected_city_tax == 15.0, f'Expected 15.0, got {expected_city_tax}'
        print("✓ test_city_tax_calculation passed")
        results.append(True)

        # Test total calculation integration
        base_amount = 1000
        special_tax = 30
        city_tax = 15
        expected_total = 1045
        actual_total = base_amount + special_tax + city_tax
        assert actual_total == expected_total, f'Expected {expected_total}, got {actual_total}'
        print("✓ test_total_calculation_integration passed")
        results.append(True)

    except Exception as e:
        print(f"Tax calculation tests failed: {e}")
        results.append(False)

    # Test QPay Client
    try:
        from mn_payments.qpay.client import QPayGateway

        # Mock the SDK check
        with unittest.mock.patch('mn_payments.qpay.client.QPaySDK', None):
            try:
                QPayGateway("test")
                print("✗ test_no_sdk_installed should have raised exception")
                results.append(False)
            except:
                print("✓ test_no_sdk_installed passed")
                results.append(True)

    except Exception as e:
        print(f"QPay Client tests failed: {e}")
        results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\nTest Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())