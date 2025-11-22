import unittest
import frappe
from frappe.tests.utils import FrappeTestCase

from mn_payments.doctype.payment_transaction.payment_transaction import PaymentTransaction, scrub_sensitive_fields


class TestPaymentTransaction(FrappeTestCase):
	def test_compute_total(self):
		doc = PaymentTransaction({
			"amount": 1000,
			"special_tax": 50,
			"city_tax": 10,
		})
		doc._compute_total()
		self.assertEqual(doc.total, 1060)

	def test_privacy_individual(self):
		doc = PaymentTransaction({
			"payer_type": "Individual",
			"retain_sensitive": 1,
			"qr_text": "test_qr",
			"qr_image": "test_image",
		})
		doc._apply_privacy_rules()
		self.assertEqual(doc.retain_sensitive, 0)
		self.assertIsNone(doc.qr_text)
		self.assertIsNone(doc.qr_image)

	def test_privacy_entity(self):
		doc = PaymentTransaction({
			"payer_type": "Entity",
			"retain_sensitive": 1,
			"qr_text": "test_qr",
		})
		doc._apply_privacy_rules()
		self.assertEqual(doc.retain_sensitive, 1)
		self.assertEqual(doc.qr_text, "test_qr")

	def test_scrub_sensitive_fields(self):
		# Mock doc creation
		doc = frappe.get_doc({
			"doctype": "Payment Transaction",
			"payer_type": "Individual",
			"retain_sensitive": 0,
			"qr_text": "should_be_scrubbed",
		})
		doc.insert(ignore_permissions=True)
		name = doc.name

		scrub_sensitive_fields([name])
		doc.reload()
		self.assertIsNone(doc.qr_text)

		doc.delete(ignore_permissions=True)


if __name__ == "__main__":
	unittest.main()