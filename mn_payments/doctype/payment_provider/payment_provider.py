import frappe
from frappe.model.document import Document
from frappe import _


class PaymentProvider(Document):
	"""Stores gateway credentials."""

	def validate(self):
		self._set_api_base()
		if self.is_default and not self.enabled:
			frappe.throw(_("Default provider must be enabled"))

	def _set_api_base(self):
		base = ""
		if self.provider == "QPay":
			base = "https://merchant.qpay.mn"
		elif self.provider == "SocialPay":
			base = "https://api.socialpay.mn"
		if base:
			self.api_base_url = base


@frappe.whitelist()
def get_default_provider(provider: str = "QPay"):
	doc = frappe.get_all(
		"Payment Provider",
		filters={"provider": provider, "enabled": 1},
		or_filters={"is_default": 1},
		order_by="is_default desc, modified desc",
		limit=1,
	)
	if not doc:
		return None
	return frappe.get_doc("Payment Provider", doc[0].name)
