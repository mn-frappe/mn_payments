import frappe
from frappe.model.document import Document


class PaymentTransaction(Document):
	"""Tracks gateway transaction and privacy flags."""

	def validate(self):
		self._compute_total()
		self._apply_privacy_rules()

	def _compute_total(self):
		self.total = (self.amount or 0) + (self.special_tax or 0) + (self.city_tax or 0)

	def _apply_privacy_rules(self):
		if self.payer_type == "Individual":
			self.retain_sensitive = 0
			self.qr_text = None
			self.qr_image = None


def scrub_sensitive_fields(names: list[str]):
	for name in names:
		try:
			doc = frappe.get_doc("Payment Transaction", name)
			if not doc.retain_sensitive:
				frappe.db.set_value("Payment Transaction", name, {"qr_text": None, "qr_image": None})
		except Exception as exc:
			frappe.log_error(message=str(exc), title="Scrub Payment Transaction")
