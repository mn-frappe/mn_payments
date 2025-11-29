from __future__ import annotations

from typing import Any, Callable

import frappe
from frappe import _
from frappe.utils import cint

from mn_payments.utils import (
    EbarimtAPIError,
    EbarimtConfigurationError,
    fetch_district_codes as fetch_district_codes_service,
    fetch_stock_qr_info as fetch_stock_qr_info_service,
    fetch_tax_product_codes as fetch_tax_product_codes_service,
    get_posapi_info as get_posapi_info_service,
    invalidate_receipt as invalidate_receipt_service,
    list_bank_accounts as list_bank_accounts_service,
    lookup_taxpayer_info as lookup_taxpayer_info_service,
    lookup_taxpayer_tin as lookup_taxpayer_tin_service,
    register_operator_merchants as register_operator_merchants_service,
    save_receipt as save_receipt_service,
    trigger_send_data as trigger_send_data_service,
)

_CACHE_KEYS = {
    "district_codes": "mn_payments:ebarimt:district_codes",
    "tax_product_codes": "mn_payments:ebarimt:tax_product_codes",
}


def _with_guard(handler: Callable[..., Any], message: str, *args, **kwargs) -> Any:
    try:
        return handler(*args, **kwargs)
    except (EbarimtConfigurationError, EbarimtAPIError):
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        frappe.log_error(frappe.get_traceback(), title=message)
        frappe.throw(_("{0}: {1}").format(message, exc))


def _ensure_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        try:
            payload = frappe.parse_json(payload)
        except Exception as exc:  # pragma: no cover - frappe handles message
            frappe.throw(_("Invalid JSON payload: {0}").format(exc))

    if not isinstance(payload, dict):
        frappe.throw(_("Payload must be a JSON object."))
    return payload


@frappe.whitelist()
def get_posapi_info() -> Any:
    """Expose ``GET /rest/info`` from the configured PosAPI instance."""

    return _with_guard(get_posapi_info_service, "Failed to fetch PosAPI info")


@frappe.whitelist()
def trigger_posapi_send_data() -> Any:
    """Trigger the PosAPI ``/rest/sendData`` endpoint to flush pending receipts."""

    return _with_guard(trigger_send_data_service, "Failed to trigger PosAPI sendData")


@frappe.whitelist()
def save_receipts(payload: str | dict[str, Any]) -> Any:
    """Proxy ``POST /rest/receipt`` (batch save)."""

    data = _ensure_mapping(payload)
    return _with_guard(save_receipt_service, "Failed to save receipts", data)


@frappe.whitelist()
def invalidate_receipts(payload: str | dict[str, Any]) -> Any:
    """Proxy ``DELETE /rest/receipt`` (batch invalidation)."""

    data = _ensure_mapping(payload)
    return _with_guard(invalidate_receipt_service, "Failed to invalidate receipts", data)


@frappe.whitelist()
def list_bank_accounts(tin: str | None = None) -> Any:
    """Return merchant bank accounts from PosAPI."""

    return _with_guard(list_bank_accounts_service, "Failed to fetch bank accounts", tin=tin)


@frappe.whitelist()
def get_district_codes(force_refresh: int = 0) -> Any:
    """Fetch and cache TPI district/branch codes."""

    cache = frappe.cache()
    cache_key = _CACHE_KEYS["district_codes"]
    if not cint(force_refresh):
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    data = _with_guard(fetch_district_codes_service, "Failed to fetch district codes")
    cache.set_value(cache_key, data, expires_in=3600)
    return data


@frappe.whitelist()
def get_tax_product_codes(force_refresh: int = 0) -> Any:
    """Fetch and cache VAT_FREE/VAT_ZERO product codes."""

    cache = frappe.cache()
    cache_key = _CACHE_KEYS["tax_product_codes"]
    if not cint(force_refresh):
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    data = _with_guard(fetch_tax_product_codes_service, "Failed to fetch tax product codes")
    cache.set_value(cache_key, data, expires_in=3600)
    return data


@frappe.whitelist()
def lookup_taxpayer_info(tin: str) -> Any:
    """Lookup taxpayer metadata by TIN."""

    if not tin:
        frappe.throw(_("TIN is required."))
    return _with_guard(lookup_taxpayer_info_service, "Failed to lookup taxpayer info", tin=tin)


@frappe.whitelist()
def lookup_taxpayer_tin(register_number: str) -> Any:
    """Resolve TIN by citizen/company registration number."""

    if not register_number:
        frappe.throw(_("Registration number is required."))
    return _with_guard(
        lookup_taxpayer_tin_service,
        "Failed to resolve taxpayer TIN",
        register_number=register_number,
    )


@frappe.whitelist()
def register_operator_merchants(payload: str | dict[str, Any]) -> Any:
    """Call ``POST /api/tpi/receipt/saveOprMerchants`` with provided payload."""

    data = _ensure_mapping(payload)
    return _with_guard(
        register_operator_merchants_service,
        "Failed to register operator merchants",
        payload=data,
    )


@frappe.whitelist()
def fetch_stock_qr(qr_code: str) -> Any:
    """Lookup excise product metadata by QR code."""

    if not qr_code:
        frappe.throw(_("QR code is required."))
    return _with_guard(
        fetch_stock_qr_info_service,
        "Failed to fetch stock QR info",
        qr_code=qr_code,
    )
