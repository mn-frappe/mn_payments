#!/usr/bin/env python3
"""
Test runner for mn_payments with mocked Frappe dependencies.
This allows running tests outside a full Frappe bench environment.
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
        self.amount = 0
        self.special_tax = 0
        self.city_tax = 0
        self.total = 0
        self.payer_type = "Individual"
        self.retain_sensitive = 0
        self.qr_text = None
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

# Mock frappe.tests.utils
frappe_mock.tests = MagicMock()
frappe_mock.tests.utils = MagicMock()

class MockFrappeTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

frappe_mock.tests.utils.FrappeTestCase = MockFrappeTestCase

# Apply all mocks BEFORE importing anything
sys.modules['frappe'] = frappe_mock
sys.modules['frappe.model.document'] = frappe_mock.model.document
sys.modules['frappe.utils'] = frappe_mock.utils
sys.modules['frappe.tests.utils'] = frappe_mock.tests.utils
sys.modules['qpay_client'] = qpay_mock
sys.modules['qpay_client.settings'] = qpay_mock

import unittest

# Mock frappe.tests.utils
frappe_mock.tests = MagicMock()
frappe_mock.tests.utils = MagicMock()

class MockFrappeTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

frappe_mock.tests.utils.FrappeTestCase = MockFrappeTestCase

if __name__ == '__main__':
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='mn_payments/tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)