from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping
from urllib.parse import urljoin

import frappe
import requests
from frappe import _

DEFAULT_POSAPI_BASE_URL = "http://localhost:7080/web/"
DEFAULT_TPI_BASE_URL = "https://st-api.ebarimt.mn/"
DEFAULT_TPI_AUTH_URL = (
	"https://st.auth.itc.gov.mn/auth/realms/Staging/protocol/openid-connect/token"
)
DEFAULT_TPI_CLIENT_ID = "vatps"


class EbarimtConfigurationError(frappe.ValidationError):
	"""Raised when the ebarimt integration is misconfigured."""


class EbarimtAPIError(frappe.ValidationError):
	"""Raised when a request to PosAPI or the national services fails."""


@dataclass(slots=True)
class PosAPIConfig:
	"""Configuration options for talking to a PosAPI instance."""

	base_url: str = DEFAULT_POSAPI_BASE_URL
	timeout: float = 10.0
	verify_ssl: bool = False
	username: str | None = None
	password: str | None = None
	api_key: str | None = None

	@classmethod
	def from_mapping(cls, payload: Mapping[str, Any] | None) -> "PosAPIConfig":
		payload = payload or {}
		base_url = _normalize_base_url(
			payload.get("base_url") or payload.get("url"), default=DEFAULT_POSAPI_BASE_URL
		)
		return cls(
			base_url=base_url,
			timeout=_coerce_number(payload.get("timeout"), float, "posapi.timeout", default=10.0),
			verify_ssl=_coerce_bool(payload.get("verify_ssl"), default=False),
			username=_coerce_text(payload.get("username")),
			password=_resolve_secret(payload.get("password")),
			api_key=_coerce_text(payload.get("api_key")),
		)


@dataclass(slots=True)
class TPIServiceConfig:
	"""Configuration for the national ebarimt APIs (a.k.a. TPI services)."""

	base_url: str = DEFAULT_TPI_BASE_URL
	auth_url: str = DEFAULT_TPI_AUTH_URL
	client_id: str = DEFAULT_TPI_CLIENT_ID
	username: str | None = None
	password: str | None = None
	api_key: str | None = None
	timeout: float = 15.0
	verify_ssl: bool = True
	token_leeway: float = 30.0

	@classmethod
	def from_mapping(cls, payload: Mapping[str, Any] | None) -> "TPIServiceConfig":
		payload = payload or {}
		username = _coerce_text(payload.get("username"))
		password = _resolve_secret(payload.get("password"))
		missing: list[str] = []
		if not username:
			missing.append("username")
		if not password:
			missing.append("password")
		if missing:
			raise EbarimtConfigurationError(
				_("Missing TPI configuration values: {0}").format(", ".join(missing))
			)

		return cls(
			base_url=_normalize_base_url(payload.get("base_url"), default=DEFAULT_TPI_BASE_URL),
			auth_url=_coerce_text(payload.get("auth_url")) or DEFAULT_TPI_AUTH_URL,
			client_id=_coerce_text(payload.get("client_id")) or DEFAULT_TPI_CLIENT_ID,
			username=username,
			password=password,
			api_key=_coerce_text(payload.get("api_key")),
			timeout=_coerce_number(payload.get("timeout"), float, "tpi.timeout", default=15.0),
			verify_ssl=_coerce_bool(payload.get("verify_ssl"), default=True),
			token_leeway=_coerce_number(
				payload.get("token_leeway"), float, "tpi.token_leeway", default=30.0
			),
		)


@dataclass(slots=True)
class _CachedToken:
	token: str
	expires_at: float


_TPI_TOKEN_CACHE: dict[str, _CachedToken] = {}


def get_posapi_config(
	*, source: Mapping[str, Any] | None = None, force_refresh: bool = False
) -> PosAPIConfig:
	"""Return cached PosAPI configuration for the active site."""

	if source is not None:
		return PosAPIConfig.from_mapping(source)

	site = getattr(frappe.local, "site", None)
	if force_refresh:
		_posapi_cache.cache_clear()

	return _posapi_cache(site)


def get_tpi_config(
	*, source: Mapping[str, Any] | None = None, force_refresh: bool = False
) -> TPIServiceConfig:
	"""Return cached configuration for the central ebarimt APIs."""

	if source is not None:
		return TPIServiceConfig.from_mapping(source)

	site = getattr(frappe.local, "site", None)
	if force_refresh:
		_tpi_cache.cache_clear()

	return _tpi_cache(site)


def request_posapi(
	path: str,
	*,
	method: str = "GET",
	params: Mapping[str, Any] | None = None,
	data: Any | None = None,
	json: Any | None = None,
	headers: Mapping[str, str] | None = None,
	timeout: float | None = None,
	config: PosAPIConfig | None = None,
	return_raw: bool = False,
) -> Any:
	"""Perform an HTTP request against the configured PosAPI instance."""

	cfg = config or get_posapi_config()
	header_map = dict(headers or {})
	if cfg.api_key and "X-API-KEY" not in header_map:
		header_map["X-API-KEY"] = cfg.api_key

	url = _join_url(cfg.base_url, path)

	try:
		response = requests.request(
			method,
			url,
			params=params,
			data=data,
			json=json,
			headers=header_map or None,
			timeout=timeout or cfg.timeout,
			verify=cfg.verify_ssl,
			auth=(cfg.username, cfg.password)
			if cfg.username and cfg.password
			else None,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		raise EbarimtAPIError(_("PosAPI request failed: {0}").format(exc)) from exc

	if return_raw:
		return response

	return _parse_response_payload(response)


def request_tpi(
	path: str,
	*,
	method: str = "GET",
	params: Mapping[str, Any] | None = None,
	data: Any | None = None,
	json: Any | None = None,
	headers: Mapping[str, str] | None = None,
	timeout: float | None = None,
	require_token: bool = True,
	config: TPIServiceConfig | None = None,
) -> Any:
	"""Perform an HTTP request against the national ebarimt services."""

	cfg = config or get_tpi_config()
	header_map = dict(headers or {})
	if cfg.api_key and "X-API-KEY" not in header_map:
		header_map["X-API-KEY"] = cfg.api_key

	if require_token and "Authorization" not in header_map:
		token = get_tpi_token(config=cfg)
		header_map["Authorization"] = f"Bearer {token}"

	url = _join_url(cfg.base_url, path)

	try:
		response = requests.request(
			method,
			url,
			params=params,
			data=data,
			json=json,
			headers=header_map or None,
			timeout=timeout or cfg.timeout,
			verify=cfg.verify_ssl,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		raise EbarimtAPIError(_("Ebarimt service request failed: {0}").format(exc)) from exc

	return _parse_response_payload(response)


def save_receipt(payload: Mapping[str, Any], *, config: PosAPIConfig | None = None) -> Any:
	"""Call ``POST /rest/receipt`` to store a batch of receipts."""

	return request_posapi("rest/receipt", method="POST", json=payload, config=config)


def invalidate_receipt(payload: Mapping[str, Any], *, config: PosAPIConfig | None = None) -> Any:
	"""Call ``DELETE /rest/receipt`` to invalidate a batch receipt."""

	return request_posapi("rest/receipt", method="DELETE", json=payload, config=config)


def get_posapi_info(*, config: PosAPIConfig | None = None) -> Any:
	"""Return the payload from ``GET /rest/info``."""

	return request_posapi("rest/info", config=config)


def trigger_send_data(*, config: PosAPIConfig | None = None) -> Any:
	"""Trigger ``GET /rest/sendData`` to push pending records to the tax service."""

	return request_posapi("rest/sendData", config=config)


def list_bank_accounts(
	*, tin: str | None = None, config: PosAPIConfig | None = None
) -> Any:
	"""Return bank accounts registered in the active PosAPI instance."""

	params = {"tin": tin} if tin else None
	return request_posapi("rest/bankAccounts", params=params, config=config)


def register_operator_merchants(
	payload: Mapping[str, Any], *, config: TPIServiceConfig | None = None
) -> Any:
	"""Call ``POST /api/tpi/receipt/saveOprMerchants`` to register merchants."""

	return request_tpi(
		"api/tpi/receipt/saveOprMerchants",
		method="POST",
		json=payload,
		config=config,
	)


def fetch_district_codes(*, config: TPIServiceConfig | None = None) -> Any:
	"""Return the district code reference list."""

	return request_tpi("api/info/check/getBranchInfo", config=config)


def lookup_taxpayer_info(
	*, tin: str, config: TPIServiceConfig | None = None
) -> Any:
	"""Fetch taxpayer status data via ``GET /api/info/check/getInfo``."""

	return request_tpi("api/info/check/getInfo", params={"tin": tin}, config=config)


def lookup_taxpayer_tin(
	*, register_number: str, config: TPIServiceConfig | None = None
) -> Any:
	"""Resolve a TIN using a registration number."""

	return request_tpi(
		"api/info/check/getTinInfo",
		params={"regNo": register_number},
		config=config,
	)


def fetch_stock_qr_info(
	*, qr_code: str, config: TPIServiceConfig | None = None
) -> Any:
	"""Lookup excise product metadata using ``GET /api/inventory/stock/getStockQr``."""

	return request_tpi(
		"api/inventory/stock/getStockQr",
		params={"stockQr": qr_code},
		config=config,
	)


def fetch_tax_product_codes(*, config: TPIServiceConfig | None = None) -> Any:
	"""Return VAT_FREE / VAT_ZERO product codes."""

	return request_tpi("api/receipt/receipt/getProductTaxCode", config=config)


def get_tpi_token(
	*, config: TPIServiceConfig | None = None, force_refresh: bool = False
) -> str:
	"""Return a cached bearer token for the TPI services."""

	cfg = config or get_tpi_config()
	site = getattr(frappe.local, "site", "__default__")
	if not force_refresh:
		cached = _TPI_TOKEN_CACHE.get(site)
		if cached and cached.expires_at - cfg.token_leeway > time.time():
			return cached.token

	payload = {
		"grant_type": "password",
		"client_id": cfg.client_id,
		"username": cfg.username,
		"password": cfg.password,
	}

	try:
		response = requests.post(
			cfg.auth_url,
			data=payload,
			timeout=cfg.timeout,
			verify=cfg.verify_ssl,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		raise EbarimtAPIError(_("Failed to fetch TPI token: {0}").format(exc)) from exc

	data = response.json()
	access_token = data.get("access_token")
	if not access_token:
		raise EbarimtAPIError(_("TPI token response did not contain access_token"))

	expires_in = _coerce_number(data.get("expires_in"), float, "token.expires_in", default=3600.0)
	expires_at = time.time() + expires_in
	_TPI_TOKEN_CACHE[site] = _CachedToken(token=access_token, expires_at=expires_at)
	return access_token


def clear_ebarimt_cache() -> None:
	"""Clear cached configuration and tokens for the ebarimt helpers."""

	_posapi_cache.cache_clear()
	_tpi_cache.cache_clear()
	_TPI_TOKEN_CACHE.clear()


@lru_cache(maxsize=8)
def _posapi_cache(_site: str | None) -> PosAPIConfig:
	return PosAPIConfig.from_mapping(_load_site_section().get("posapi"))


@lru_cache(maxsize=8)
def _tpi_cache(_site: str | None) -> TPIServiceConfig:
	section = _load_site_section().get("tpi")
	if not section:
		raise EbarimtConfigurationError(_("mn_payments.ebarimt.tpi is not configured."))
	return TPIServiceConfig.from_mapping(section)


def _load_site_section() -> Mapping[str, Any]:
	"""Load Ebarimt configuration from site_config or Ebarimt Settings DocType."""
	conf = getattr(frappe.local, "conf", None) or frappe.get_site_config()
	site_config_ebarimt = (conf.get("mn_payments") or {}).get("ebarimt") or {}
	
	# If site_config has values, use it
	if site_config_ebarimt:
		return site_config_ebarimt
	
	# Fallback to Ebarimt Settings DocType
	try:
		if frappe.db.exists("DocType", "Ebarimt Settings"):
			settings = frappe.get_single("Ebarimt Settings")
			result = {}
			
			# Build PosAPI config
			if settings.get("posapi_enabled"):
				posapi_url = settings.get("posapi_base_url")
				if posapi_url == "Custom":
					posapi_url = settings.get("posapi_custom_url")
				
				result["posapi"] = {
					"base_url": posapi_url,
					"timeout": settings.get("posapi_timeout"),
					"verify_ssl": settings.get("posapi_verify_ssl"),
					"username": settings.get("posapi_username"),
					"password": settings.get("posapi_password"),
					"api_key": settings.get("posapi_api_key"),
				}
			
			# Build TPI config
			if settings.get("tpi_enabled"):
				tpi_url = settings.get("tpi_base_url")
				if tpi_url == "Custom":
					tpi_url = settings.get("tpi_custom_url")
				
				tpi_auth = settings.get("tpi_auth_url")
				if tpi_auth == "Custom":
					tpi_auth = settings.get("tpi_custom_auth_url")
				
				result["tpi"] = {
					"base_url": tpi_url,
					"auth_url": tpi_auth,
					"client_id": settings.get("tpi_client_id"),
					"username": settings.get("tpi_username"),
					"password": settings.get("tpi_password"),
					"timeout": settings.get("tpi_timeout"),
					"verify_ssl": settings.get("tpi_verify_ssl"),
					"token_leeway": settings.get("tpi_token_leeway"),
				}
			
			return result
	except Exception:
		pass
	
	return {}


def _parse_response_payload(response: requests.Response) -> Any:
	content_type = response.headers.get("Content-Type", "")
	if "json" in content_type:
		return response.json()

	try:
		return response.json()
	except ValueError:
		return response.text


def _normalize_base_url(value: Any | None, *, default: str) -> str:
	base = _coerce_text(value) or default
	return base if base.endswith("/") else f"{base}/"


def _join_url(base: str, path: str) -> str:
	path = path.lstrip("/")
	base = base if base.endswith("/") else f"{base}/"
	return urljoin(base, path)


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


def _coerce_number(
	value: Any,
	cast: type,
	fieldname: str,
	*,
	default: float | int | None = None,
) -> Any:
	if value in (None, ""):
		return default
	try:
		return cast(value)
	except (TypeError, ValueError) as exc:
		raise EbarimtConfigurationError(
			_("Invalid numeric value for {0}").format(fieldname)
		) from exc


def _resolve_secret(value: Any) -> str | None:
	if isinstance(value, dict):
		env_name = value.get("env")
		if env_name:
			return os.getenv(str(env_name), "")
	return _coerce_text(value)


__all__ = [
	"DEFAULT_POSAPI_BASE_URL",
	"DEFAULT_TPI_BASE_URL",
	"DEFAULT_TPI_AUTH_URL",
	"DEFAULT_TPI_CLIENT_ID",
	"EbarimtAPIError",
	"EbarimtConfigurationError",
	"PosAPIConfig",
	"TPIServiceConfig",
	"clear_ebarimt_cache",
	"fetch_district_codes",
	"fetch_stock_qr_info",
	"fetch_tax_product_codes",
	"get_posapi_config",
	"get_posapi_info",
	"get_tpi_config",
	"get_tpi_token",
	"invalidate_receipt",
	"list_bank_accounts",
	"lookup_taxpayer_info",
	"lookup_taxpayer_tin",
	"register_operator_merchants",
	"request_posapi",
	"request_tpi",
	"save_receipt",
	"trigger_send_data",
]
