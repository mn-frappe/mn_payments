"""QPay wrapper leveraging qpay_client package."""

from __future__ import annotations

import frappe
from frappe import _

try:
	from qpay_client.v2 import QPayClient as QPaySDK, QPaySettings
	from qpay_client.v2.schemas import InvoiceCreateSimpleRequest, PaymentCheckRequest, Offset
	from qpay_client.v2.enums import ObjectType
except Exception:  # pragma: no cover
	QPaySDK = None  # type: ignore
	QPaySettings = None  # type: ignore
	InvoiceCreateSimpleRequest = None  # type: ignore
	PaymentCheckRequest = None  # type: ignore
	Offset = None  # type: ignore
	ObjectType = None  # type: ignore


class QPayGateway:
	def __init__(self, provider_name: str | None = None):
		self.provider = provider_name or _get_default_provider_name()
		self.sdk = self._build_sdk(self.provider)

	def _build_sdk(self, provider_name: str):
		if not QPaySDK or not QPaySettings:
			frappe.throw(_("qpay_client library is not installed"))
		doc = frappe.get_doc("Payment Provider", provider_name)
		settings = QPaySettings(
			username=doc.username,
			password=doc.get_password("password"),
			sandbox=doc.environment == "Sandbox",
		)
		return QPaySDK(settings=settings)

	def create_invoice(self, *, sender_code: str, description: str, amount: int, callback_params: dict | None = None):
		doc = frappe.get_doc("Payment Provider", self.provider)
		params = callback_params or {}
		
		# Build callback URL with params
		callback_url = doc.callback_url
		if params:
			from urllib.parse import urlencode
			callback_url += "?" + urlencode(params)
		
		request = InvoiceCreateSimpleRequest(
			invoice_code=doc.invoice_code,
			sender_invoice_no=sender_code,
			invoice_receiver_code="terminal",  # Default receiver code
			invoice_description=description,
			amount=amount,
			callback_url=callback_url,
		)
		return self.sdk.invoice_create(request)

	def check_payment(self, invoice_id: str):
		request = PaymentCheckRequest(
			object_type=ObjectType.invoice,
			object_id=invoice_id,
			offset=Offset(page_number=1, page_limit=100),
		)
		return self.sdk.payment_check(request)


def _get_default_provider_name() -> str:
	doc = frappe.get_all(
		"Payment Provider",
		filters={"provider": "QPay", "enabled": 1},
		or_filters={"is_default": 1},
		order_by="is_default desc, modified desc",
		limit=1,
	)
	if not doc:
		frappe.throw(_("No default QPay provider configured"))
	return doc[0].name
