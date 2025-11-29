from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime
from qpay_client.v2.enums import ObjectType

from mn_payments.utils import (
	check_payment_status as check_payment_status_service,
	"""Backwards-compatible shim for legacy import path.

	The application now exposes QPay APIs from ``mn_payments.api.qpay``. Keep the
	old module so any ``hooks.py`` references or integrations continue to work.
	"""

	from mn_payments.api.qpay import *  # noqa: F401,F403
	"CANCELLED": "Cancelled",
