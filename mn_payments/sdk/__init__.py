"""
MN Payments SDK
===============

Python SDK for Mongolian payment systems and tax receipt integration.

This SDK can be used standalone or as part of the mn_payments Frappe app.

Example - Standalone Usage:
    >>> from mn_payments.sdk import EbarimtClient, QPayClient
    >>> 
    >>> # Ebarimt tax receipts
    >>> ebarimt = EbarimtClient(
    ...     base_url="https://api.ebarimt.mn",
    ...     pos_no="POS12345",
    ...     merchant_tin="1234567890"
    ... )
    >>> 
    >>> # QPay payment gateway
    >>> qpay = QPayClient(
    ...     client_id="YOUR_CLIENT_ID",
    ...     client_secret="YOUR_CLIENT_SECRET",
    ...     invoice_code="YOUR_INVOICE_CODE"
    ... )

Example - With Frappe Integration:
    >>> from mn_payments.sdk import EbarimtClient
    >>> 
    >>> client = EbarimtClient(
    ...     base_url="https://api.ebarimt.mn",
    ...     pos_no="POS12345",
    ...     merchant_tin="1234567890",
    ...     enable_db=True,      # Save to Frappe database
    ...     enable_email=True    # Send emails via Frappe
    ... )

Modules:
    ebarimt: Ebarimt POS 3.0 tax receipt SDK
    qpay: QPay payment gateway SDK
"""

# Ebarimt SDK exports
from mn_payments.sdk.ebarimt import (
    EbarimtClient,
    ReceiptItem,
    CreateReceiptRequest,
    ReceiptResponse,
    TaxType,
    ReceiptType,
    BarcodeType,
    VATCalculator,
)

# QPay SDK exports
from mn_payments.sdk.qpay import (
    QPayClient,
    QPayVersion,
    QPayConfig,
    QPayInvoice,
    QPayInvoiceDetails,
    QPayAuthToken,
)

__version__ = "1.0.0"
__author__ = "Digital Consulting Service LLC"
__all__ = [
    # Ebarimt
    "EbarimtClient",
    "ReceiptItem",
    "CreateReceiptRequest",
    "ReceiptResponse",
    "TaxType",
    "ReceiptType",
    "BarcodeType",
    "VATCalculator",
    # QPay
    "QPayClient",
    "QPayVersion",
    "QPayConfig",
    "QPayInvoice",
    "QPayInvoiceDetails",
    "QPayAuthToken",
]
