from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Any, Mapping

import frappe
from frappe import _
from frappe.utils import get_url
from qpay_client.v2 import QPayClientSync, QPaySettings
from qpay_client.v2.enums import ObjectType
from qpay_client.v2.schemas import (
	InvoiceCreateResponse,
	InvoiceCreateSimpleRequest,
	Offset,
	PaymentCheckRequest,
	PaymentCheckResponse,
)
from qpay_client.v2.settings import SecretStr

DEFAULT_CALLBACK_PATH = "/api/method/mn_payments.api.qpay.callback"


class QPayConfigurationError(frappe.ValidationError):
	"""Raised when the QPay integration is misconfigured."""


@dataclass(slots=True)
class QPayConfig:
	"""Typed representation of the QPay section in site_config."""

	username: str
	password: str
	sandbox: bool = True
	invoice_code: str | None = None
	callback_url: str | None = None
	sender_branch_code: str | None = None
	token_leeway: float | None = None
	client_retries: int | None = None
	client_delay: float | None = None
	client_jitter: float | None = None
	payment_check_retries: int | None = None
	payment_check_delay: float | None = None
	payment_check_jitter: float | None = None

	@classmethod
	def from_mapping(cls, payload: Mapping[str, Any]) -> "QPayConfig":
		missing = []
		username = _coerce_text(payload.get("username"))
		password = _resolve_secret(payload.get("password"))
		if not username:
			missing.append("username")
		if not password:
			missing.append("password")
		if missing:
			raise QPayConfigurationError(
				_("Missing QPay configuration values: {0}").format(", ".join(missing))
			)

		return cls(
			username=username,
			password=password,
			sandbox=_coerce_bool(payload.get("sandbox"), default=True),
			invoice_code=_coerce_text(payload.get("invoice_code")),
			callback_url=_coerce_text(payload.get("callback_url")),
			sender_branch_code=_coerce_text(payload.get("sender_branch_code")),
			token_leeway=_coerce_number(payload.get("token_leeway"), float, "token_leeway"),
			client_retries=_coerce_number(payload.get("client_retries"), int, "client_retries"),
			client_delay=_coerce_number(payload.get("client_delay"), float, "client_delay"),
			client_jitter=_coerce_number(payload.get("client_jitter"), float, "client_jitter"),
			payment_check_retries=_coerce_number(
				payload.get("payment_check_retries"), int, "payment_check_retries"
			),
			payment_check_delay=_coerce_number(
				payload.get("payment_check_delay"), float, "payment_check_delay"
			),
			payment_check_jitter=_coerce_number(
				payload.get("payment_check_jitter"), float, "payment_check_jitter"
			),
		)

	def to_settings_kwargs(self) -> dict[str, Any]:
		kwargs: dict[str, Any] = {
			"username": self.username,
			"password": SecretStr(self.password),
			"sandbox": self.sandbox,
		}

		optional_fields = (
			"token_leeway",
			"client_retries",
			"client_delay",
			"client_jitter",
			"payment_check_retries",
			"payment_check_delay",
			"payment_check_jitter",
		)

		for field in optional_fields:
			value = getattr(self, field)
			if value is not None:
				kwargs[field] = value

		return kwargs


def get_qpay_config(*, source: Mapping[str, Any] | None = None, force_refresh: bool = False) -> QPayConfig:
	"""Return cached QPay configuration for the active site."""

	if source is not None:
		return QPayConfig.from_mapping(source)

	site = getattr(frappe.local, "site", None)
	if force_refresh:
		_config_cache.cache_clear()
		_settings_cache.cache_clear()

	return _config_cache(site)


def build_qpay_settings(
	*, config: QPayConfig | None = None, use_cache: bool = True
) -> QPaySettings:
	"""Build a `QPaySettings` object either from cache or a provided config."""

	if config is not None:
		return QPaySettings(**config.to_settings_kwargs())

	site = getattr(frappe.local, "site", None)
	if not use_cache:
		_settings_cache.cache_clear()

	return _settings_cache(site)


def build_qpay_client(
	*, config: QPayConfig | None = None, use_cache: bool = True
) -> QPayClientSync:
	"""Instantiate a synchronous QPay client."""

	settings = build_qpay_settings(config=config, use_cache=use_cache)
	return QPayClientSync(settings=settings)


@contextmanager
def qpay_client(
	*, config: QPayConfig | None = None, use_cache: bool = True
) -> QPayClientSync:
	"""Context manager that yields a ready-to-use QPay client."""

	client = build_qpay_client(config=config, use_cache=use_cache)
	try:
		yield client
	finally:
		client.close()


def resolve_callback_url(callback_url: str | None = None, *, config: QPayConfig | None = None) -> str:
	"""Resolve the callback URL using config or the default API endpoint."""

	if callback_url:
		return callback_url

	active_config = config or get_qpay_config()
	if active_config.callback_url:
		return active_config.callback_url

	return get_url(DEFAULT_CALLBACK_PATH)


def create_simple_invoice(
	*,
	sender_invoice_no: str,
	invoice_receiver_code: str,
	amount: Decimal | int | float | str,
	invoice_description: str,
	invoice_code: str | None = None,
	callback_url: str | None = None,
	sender_branch_code: str | None = None,
	client: QPayClientSync | None = None,
	config: QPayConfig | None = None,
) -> InvoiceCreateResponse:
	"""Create a simple QPay invoice and return the API response."""

	local_config = config or get_qpay_config()
	resolved_invoice_code = invoice_code or local_config.invoice_code
	resolved_callback_url = resolve_callback_url(callback_url, config=local_config)
	sender_branch_code = sender_branch_code or local_config.sender_branch_code

	if not resolved_invoice_code:
		raise QPayConfigurationError(_("QPay invoice_code is not configured."))

	invoice_amount = _as_decimal(amount)
	request = InvoiceCreateSimpleRequest(
		invoice_code=resolved_invoice_code,
		sender_invoice_no=sender_invoice_no,
		invoice_receiver_code=invoice_receiver_code,
		invoice_description=invoice_description,
		amount=invoice_amount,
		callback_url=resolved_callback_url,
		sender_branch_code=sender_branch_code,
	)

	owns_client = client is None
	active_client = client or build_qpay_client(config=local_config)
	try:
		return active_client.invoice_create(request)
	finally:
		if owns_client:
			active_client.close()


def check_payment_status(
	*,
	object_id: str,
	object_type: ObjectType = ObjectType.invoice,
	page_number: int = 1,
	page_limit: int = 20,
	client: QPayClientSync | None = None,
	config: QPayConfig | None = None,
) -> PaymentCheckResponse:
	"""Call `/payment/check` for a given invoice or QR object."""

	if page_number < 1 or page_limit < 1:
		raise QPayConfigurationError(_("page_number and page_limit must be positive integers."))

	request = PaymentCheckRequest(
		object_type=object_type,
		object_id=object_id,
		offset=Offset(page_number=page_number, page_limit=page_limit),
	)

	owns_client = client is None
	active_client = client or build_qpay_client(config=config)
	try:
		return active_client.payment_check(request)
	finally:
		if owns_client:
			active_client.close()


def clear_qpay_cache() -> None:
	"""Clear cached QPay configuration and settings."""

	_config_cache.cache_clear()
	_settings_cache.cache_clear()


@lru_cache(maxsize=8)
def _config_cache(_site: str | None) -> QPayConfig:
	return QPayConfig.from_mapping(_load_site_qpay_mapping())


@lru_cache(maxsize=8)
def _settings_cache(_site: str | None) -> QPaySettings:
	config = _config_cache(_site)
	return QPaySettings(**config.to_settings_kwargs())


def _load_site_qpay_mapping() -> Mapping[str, Any]:
	"""Load QPay configuration from site_config or Qpay Settings DocType."""
	conf = getattr(frappe.local, "conf", None) or {}
	if not conf:
		conf = frappe.get_site_config()

	app_conf = conf.get("mn_payments") or {}
	site_config_qpay = app_conf.get("qpay") or {}
	
	# If site_config has values, use it
	if site_config_qpay:
		return site_config_qpay
	
	# Fallback to Qpay Settings DocType
	try:
		if frappe.db.exists("DocType", "Qpay Settings"):
			settings = frappe.get_single("Qpay Settings")
			if settings.get("enabled"):
				return {
					"username": settings.get("username"),
					"password": settings.get("password"),
					"sandbox": settings.get("is_sandbox", True),
					"invoice_code": settings.get("invoice_code"),
					"callback_url": settings.get("callback_url"),
					"sender_branch_code": settings.get("sender_branch_code"),
					"token_leeway": settings.get("token_leeway"),
					"client_retries": settings.get("client_retries"),
					"client_delay": settings.get("client_delay"),
					"client_jitter": settings.get("client_jitter"),
					"payment_check_retries": settings.get("payment_check_retries"),
					"payment_check_delay": settings.get("payment_check_delay"),
					"payment_check_jitter": settings.get("payment_check_jitter"),
				}
	except Exception:
		pass
	
	return {}


def _coerce_text(value: Any) -> str | None:
	if value in (None, ""):
		return None
	return str(value).strip()


def _coerce_bool(value: Any, *, default: bool) -> bool:
	if value is None:
		return default
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "t", "yes", "y"}
	return bool(value)


def _coerce_number(value: Any, cast: type, fieldname: str) -> Any:
	if value in (None, ""):
		return None
	try:
		return cast(value)
	except (TypeError, ValueError) as exc:
		raise QPayConfigurationError(
			_("Invalid numeric value for {0}").format(fieldname)
		) from exc


def _resolve_secret(value: Any) -> str | None:
	if isinstance(value, SecretStr):
		return value.get_secret_value()
	if isinstance(value, dict):
		env_name = value.get("env")
		if env_name:
			return os.getenv(str(env_name), "")
	return _coerce_text(value)


def _as_decimal(value: Decimal | int | float | str) -> Decimal:
	if isinstance(value, Decimal):
		return value
	return Decimal(str(value))
