"""Ebarimt/PosAPI client wrapper with TIN lookup and privacy controls."""

from __future__ import annotations

import frappe
from frappe import _

from mn_payments.sdk.ebarimt import EbarimtClient as SDKClient, MerchantInfo


class EbarimtGateway:
	def __init__(self):
		settings = frappe.get_single("Ebarimt Settings")
		if not settings or not settings.enabled:
			frappe.throw(_("eBarimt is not enabled."))
		config = settings.get_client_config()
		self.sdk = SDKClient(**config)
		self.settings = settings

	def lookup_entity(self, tin: str) -> MerchantInfo:
		return self.sdk.get_info(tin)

	def create_receipt(self, payload: dict, retain_sensitive: bool = False):
		resp = self.sdk.create_receipt(payload)
		if not retain_sensitive:
			resp.pop("lottery", None)
			resp.pop("qr_code_base64", None)
			resp.pop("qrData", None)
		return resp

	def cancel_receipt(self, receipt_id: str):
		return self.sdk.cancel_receipt(receipt_id)
