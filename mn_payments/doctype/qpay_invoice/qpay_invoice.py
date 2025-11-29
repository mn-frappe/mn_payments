from __future__ import annotations

import frappe
from frappe.model.document import Document


class QpayInvoice(Document):
	"""Stores metadata returned by QPay for each Payment Request."""

	def before_save(self):
		self._ensure_unique_payment_request()

	def _ensure_unique_payment_request(self) -> None:
		if not self.payment_request or self.flags.in_import:
			return

		existing = frappe.db.get_value(
			"Qpay Invoice",
			{"payment_request": self.payment_request, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				frappe._("Payment Request {0} already has a QPay invoice ({1}).").format(
					self.payment_request, existing
				),
			)
