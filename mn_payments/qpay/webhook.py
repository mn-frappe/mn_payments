import json
import hmac
import hashlib
from typing import Optional

import frappe
from frappe import _


def _default_provider() -> str:
    doc = frappe.get_all(
        "Payment Provider",
        filters={"provider": "QPay", "enabled": 1},
        or_filters={"is_default": 1},
        order_by="is_default desc, modified desc",
        limit=1,
    )
    if not doc:
        frappe.throw(_("No QPay provider configured"))
    return doc[0].name


def verify_signature(payload: dict, signature: str | None, provider_name: str) -> bool:
    """Verify HMAC-SHA256 signature of payload with provider webhook_secret."""
    provider = frappe.get_doc("Payment Provider", provider_name)
    secret = provider.get_password("webhook_secret")
    if not secret:
        frappe.throw(_("Webhook secret not set for provider {0}").format(provider.name))
    message = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@frappe.whitelist(allow_guest=True)
def handle(payload: dict | None = None, signature: str | None = None, provider: str | None = None):
    """Webhook handler for payment status updates with signature verification."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not payload:
        frappe.throw(_("Missing payload"))
    provider_name = provider or _default_provider()
    if signature and not verify_signature(payload, signature, provider_name):
        frappe.throw(_("Invalid webhook signature"))

    # Extract payment information
    invoice_id = payload.get("invoice_id")
    status = payload.get("status")
    if not invoice_id:
        frappe.throw(_("Missing invoice_id in payload"))

    # Find and update payment transaction by qpay_invoice_id
    transactions = frappe.get_all(
        "Payment Transaction",
        filters={"qpay_invoice_id": invoice_id},
        limit=1,
    )

    if transactions:
        tx = frappe.get_doc("Payment Transaction", transactions[0].name)
        if status == "PAID":
            tx.status = "Paid"
        elif status in {"CANCELLED", "EXPIRED"}:
            tx.status = "Cancelled"
        else:
            tx.status = "Failed"
        tx.callback_payload = json.dumps(payload, ensure_ascii=False)
        tx.save(ignore_permissions=True)
    return {"status": "success"}
