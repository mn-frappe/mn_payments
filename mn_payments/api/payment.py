from __future__ import annotations

import frappe
from frappe import _

from mn_payments.qpay.client import QPayGateway
from mn_payments.ebarimt.client import EbarimtGateway


@frappe.whitelist(allow_guest=True)
def create_payment(
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	amount: float | None = None,
	payer_email: str | None = None,
	payer_type: str = "Individual",
	entity_registration: str | None = None,
	entity_name: str | None = None,
	subscription_plan: str | None = None,
	special_tax_type: str | None = None,
	city_tax_rate: float = 1.0,
):
	if not payer_email:
		frappe.throw(_("Payer email is required"))
	if not amount:
		frappe.throw(_("Amount is required"))

	base_amount = float(amount)
	special_tax_amt = _compute_special_tax(base_amount, special_tax_type)
	city_tax_amt = round(base_amount * (city_tax_rate / 100), 2)
	total = round(base_amount + special_tax_amt + city_tax_amt, 2)

	retain_sensitive = 0 if payer_type == "Individual" else 1

	tx = frappe.get_doc(
		{
			"doctype": "Payment Transaction",
			"status": "Pending",
			"provider": _default_qpay_provider(),
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"payer_email": payer_email,
			"payer_type": payer_type,
			"entity_registration": entity_registration,
			"entity_name": entity_name,
			"subscription_plan": subscription_plan,
			"amount": base_amount,
			"special_tax": special_tax_amt,
			"city_tax": city_tax_amt,
			"total": total,
			"retain_sensitive": retain_sensitive,
		}
	)
	tx.insert(ignore_permissions=True)

	gw = QPayGateway(tx.provider)
	invoice = gw.create_invoice(
		sender_code=tx.name,
		description=_get_description(reference_doctype, reference_name) or "Payment",
		amount=int(total),
		callback_params={"txn": tx.name},
	)

	invoice_dict = invoice if isinstance(invoice, dict) else invoice.__dict__
	qpay_invoice_id = invoice_dict.get("invoice_id")
	qr_text = invoice_dict.get("qr_text")
	qr_image = invoice_dict.get("qr_image")

	frappe.db.set_value(
		"Payment Transaction",
		tx.name,
		{
			"qpay_invoice_id": qpay_invoice_id,
			"qr_text": qr_text if retain_sensitive else None,
			"qr_image": qr_image if retain_sensitive else None,
		},
	)

	return {
		"transaction": tx.name,
		"status": "Pending",
		"amount": total,
		"qpay_invoice_id": qpay_invoice_id,
		"qr_text": qr_text if retain_sensitive else None,
		"qr_image": qr_image if retain_sensitive else None,
	}


@frappe.whitelist(allow_guest=True)
def fetch_payment(transaction: str | None = None, qpay_invoice_id: str | None = None):
	filters = {}
	if transaction:
		filters["name"] = transaction
	if qpay_invoice_id:
		filters["qpay_invoice_id"] = qpay_invoice_id
	if not filters:
		frappe.throw(_("Provide transaction or qpay_invoice_id"))
	name = frappe.db.get_value("Payment Transaction", filters)
	if not name:
		return {"status": "Missing"}
	doc = frappe.get_doc("Payment Transaction", name)
	return {
		"transaction": doc.name,
		"status": doc.status,
		"amount": doc.total,
		"qpay_invoice_id": doc.qpay_invoice_id,
	}


@frappe.whitelist(allow_guest=True)
def lookup_entity(tin: str):
	"""Lookup entity info from ebarimt by TIN."""
	gw = EbarimtGateway()
	info = gw.lookup_entity(tin)
	return {
		"found": bool(getattr(info, "found", False)),
		"name": getattr(info, "name", None),
		"vat_payer": getattr(info, "vat_payer", None),
		"city_payer": getattr(info, "city_payer", None),
	}


def _compute_special_tax(amount: float, special_tax_type: str | None) -> float:
	if not special_tax_type:
		row = frappe.db.get_value("Special Tax Type", {"is_default": 1}, ["rate"])
		if row:
			rate = row[0] if isinstance(row, (list, tuple)) else row
		else:
			rate = 0
	else:
		rate = frappe.db.get_value("Special Tax Type", special_tax_type, "rate") or 0
	return round(amount * float(rate) / 100, 2)


def _default_qpay_provider() -> str:
	doc = frappe.get_all(
		"Payment Provider",
		filters={"provider": "QPay", "enabled": 1},
		or_filters={"is_default": 1},
		limit=1,
	)
	if not doc:
		frappe.throw(_("No QPay provider configured"))
	return doc[0].name


def _get_description(doctype: str | None, name: str | None) -> str:
	if doctype and name:
		return f"{doctype} {name}"
	return "Payment"
