from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime
from qpay_client.v2.enums import ObjectType

from mn_payments.utils import (
    check_payment_status as check_payment_status_service,
    create_simple_invoice,
    get_qpay_config,
)

STATUS_MAP = {
    "PAID": "Paid",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}


@frappe.whitelist()
def create_invoice(
    payment_request: str,
    invoice_receiver_code: str | None = None,
    description: str | None = None,
    amount: float | int | None = None,
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Create a QPay invoice for the provided Payment Request."""

    _doc = _get_payment_request(payment_request)
    amount_value = _resolve_amount(_doc, amount)
    receiver = invoice_receiver_code or _guess_receiver_code(_doc)
    if not receiver:
        frappe.throw(_("Receiver code is required."))

    description = description or _guess_description(_doc)
    config = get_qpay_config()

    response = create_simple_invoice(
        sender_invoice_no=_doc.name,
        invoice_receiver_code=receiver,
        amount=Decimal(str(amount_value)),
        invoice_description=description,
        callback_url=callback_url,
        config=config,
    )

    invoice_doc = _upsert_invoice_doc(
        _doc,
        request_payload={
            "payment_request": _doc.name,
            "invoice_receiver_code": receiver,
            "invoice_description": description,
            "amount": amount_value,
            "callback_url": callback_url,
            "invoice_code": config.invoice_code,
        },
        invoice_response=response,
        amount=amount_value,
        currency=_doc.get("currency")
        or _doc.get("party_account_currency")
        or _doc.get("company_currency"),
    )

    return {
        "payment_request": _doc.name,
        "invoice": invoice_doc.name,
        "invoice_id": invoice_doc.invoice_id,
        "status": invoice_doc.status,
        "qr_text": invoice_doc.qr_text,
        "qr_image": invoice_doc.qr_image,
        "urls": invoice_doc.urls,
    }


@frappe.whitelist()
def get_invoice(payment_request: str | None = None, invoice_id: str | None = None) -> dict[str, Any]:
    """Return the stored QPay invoice metadata."""

    invoice_doc = _get_qpay_invoice(payment_request, invoice_id)
    return invoice_doc.as_dict()


@frappe.whitelist()
def check_payment(
    payment_request: str | None = None,
    invoice_id: str | None = None,
    page_number: int = 1,
    page_limit: int = 20,
) -> dict[str, Any]:
    """Call QPay's payment check endpoint and update local status."""

    invoice_doc = _get_qpay_invoice(payment_request, invoice_id)
    page_number = max(1, cint(page_number))
    page_limit = max(1, cint(page_limit))
    response = check_payment_status_service(
        object_id=invoice_doc.invoice_id,
        object_type=ObjectType.invoice,
        page_number=page_number,
        page_limit=page_limit,
    )
    data = _apply_payment_status(invoice_doc, response)
    return {
        "invoice_id": invoice_doc.invoice_id,
        "status": invoice_doc.status,
        "response": data,
    }


@frappe.whitelist(allow_guest=True)
def callback() -> dict[str, Any]:
    """Handle QPay callbacks (configured via DEFAULT_CALLBACK_PATH)."""

    payload = _get_request_json()
    invoice_id = payload.get("invoice_id") or payload.get("object_id")
    if not invoice_id:
        return {"status": "ignored", "reason": "missing-invoice"}

    invoice_name = frappe.db.get_value("Qpay Invoice", {"invoice_id": invoice_id})
    if not invoice_name:
        return {"status": "ignored", "reason": "unknown-invoice"}

    invoice_doc = frappe.get_doc("Qpay Invoice", invoice_name)
    invoice_doc.payment_result = _as_json(payload)
    invoice_doc.last_payment_check = now_datetime()
    status = _extract_status(payload)
    if status:
        invoice_doc.status = status
        if status == "Paid":
            _mark_payment_request_paid(invoice_doc.payment_request, payload)
    invoice_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success"}


def _apply_payment_status(invoice_doc, response):
    data = _model_dump(response)
    invoice_doc.payment_result = _as_json(data)
    invoice_doc.last_payment_check = now_datetime()
    rows = data.get("rows") or []
    if rows:
        row = rows[0]
        status = _extract_status(row)
        if status:
            invoice_doc.status = status
            if status == "Paid":
                _mark_payment_request_paid(invoice_doc.payment_request, row)
    invoice_doc.save(ignore_permissions=True)
    return data


def _get_qpay_invoice(payment_request: str | None, invoice_id: str | None):
    filters: dict[str, Any] = {}
    if payment_request:
        filters["payment_request"] = payment_request
    if invoice_id:
        filters["invoice_id"] = invoice_id
    if not filters:
        frappe.throw(_("Pass either payment_request or invoice_id."))

    name = frappe.db.get_value("Qpay Invoice", filters)
    if not name:
        frappe.throw(_("QPay invoice not found."))
    return frappe.get_doc("Qpay Invoice", name)


def _upsert_invoice_doc(
    payment_request_doc,
    *,
    request_payload,
    invoice_response,
    amount,
    currency=None,
):
    data = _model_dump(invoice_response)
    invoice_id = data.get("invoice_id")
    if not invoice_id:
        frappe.throw(_("QPay response did not include invoice_id."))
    fields = {
        "payment_request": payment_request_doc.name,
        "invoice_id": invoice_id,
        "invoice_code": request_payload.get("invoice_code"),
        "qr_text": data.get("qr_text"),
        "qr_image": data.get("qr_image"),
        "urls": data.get("urls") or [],
        "request_payload": _as_json(request_payload),
        "response_payload": _as_json(data),
        "payment_amount": flt(amount),
        "payment_currency": currency,
    }

    name = frappe.db.get_value("Qpay Invoice", {"payment_request": payment_request_doc.name})
    if name:
        doc = frappe.get_doc("Qpay Invoice", name)
        doc.update(fields)
        doc.status = doc.status or "Pending"
        doc.save(ignore_permissions=True)
        return doc

    doc = frappe.get_doc({"doctype": "Qpay Invoice", **fields})
    doc.status = "Pending"
    doc.insert(ignore_permissions=True)
    return doc


def _get_payment_request(docname: str):
    try:
        return frappe.get_doc("Payment Request", docname)
    except frappe.DoesNotExistError:
        frappe.throw(_("Payment Request {0} was not found.").format(docname))


def _resolve_amount(doc, override):
    if override not in (None, ""):
        return flt(override)
    for fieldname in (
        "grand_total",
        "total_amount",
        "base_grand_total",
        "amount",
        "outstanding_amount",
    ):
        value = doc.get(fieldname)
        if value:
            return flt(value)
    frappe.throw(_("Unable to determine amount for Payment Request {0}.").format(doc.name))


def _guess_receiver_code(doc) -> str | None:
    for fieldname in ("party", "customer", "supplier", "reference_name", "contact_person"):
        value = doc.get(fieldname)
        if value:
            return value
    return doc.name


def _guess_description(doc) -> str:
    return doc.get("subject") or doc.get("memo") or doc.get("reference_name") or doc.name


def _model_dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, Mapping):
        return dict(obj)
    return frappe._dict(obj)


def _as_json(data: Any) -> str:
    return frappe.as_json(data, indent=2, sort_keys=True)


def _get_request_json() -> dict[str, Any]:
    if frappe.request and frappe.request.data:
        try:
            return frappe.parse_json(frappe.request.data)
        except Exception:
            pass
    return frappe.local.form_dict or {}


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    status = (payload.get("payment_status") or payload.get("status") or "").upper()
    return STATUS_MAP.get(status)


def _mark_payment_request_paid(payment_request: str, payload: Mapping[str, Any]) -> None:
    try:
        doc = frappe.get_doc("Payment Request", payment_request)
    except frappe.DoesNotExistError:
        return

    if doc.status != "Paid":
        doc.db_set("status", "Paid")

    callback = getattr(doc, "on_payment_authorized", None)
    if callable(callback):
        try:
            callback("Paid")
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                _("Failed to notify document for Payment Request {0}").format(payment_request),
            )
