# MN Payments SDK

Python SDK for Mongolian payment systems and tax receipt integration.

## Installation

### As Part of Frappe App (Recommended)
```bash
cd frappe-bench
bench get-app mn_payments
bench --site your-site install-app mn_payments
```

### Standalone (Future - if published to PyPI)
```bash
pip install mn-payments-sdk
```

## Quick Start

### Ebarimt Tax Receipts

```python
from mn_payments.sdk import EbarimtClient, ReceiptItem, TaxType, ReceiptType

# Initialize client
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890"
)

# Create receipt items
items = [
    ReceiptItem(
        name="Coffee",
        qty=2.0,
        total_amount=10000.0,
        tax_type=TaxType.VAT_ABLE,
        is_city_tax=True
    )
]

# Generate receipt
from mn_payments.sdk import CreateReceiptRequest

request = CreateReceiptRequest(
    branch_no="BR001",
    district_code="01",
    report_month="202411"
)

response = client.create_receipt(
    receipt_type=ReceiptType.B2C_RECEIPT,
    request=request,
    items=items
)

print(f"Receipt ID: {response.id}")
print(f"Lottery: {response.lottery}")
```

### QPay Payment Gateway

```python
from mn_payments.sdk import QPayClient, InvoiceRequest

# Initialize client
client = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    invoice_code="YOUR_INVOICE_CODE",
    version="v2"
)

# Create invoice
invoice = InvoiceRequest(
    amount=50000.0,
    sender_invoice_no="INV-001",
    description="Payment for services"
)

response = client.create_invoice(invoice)
print(f"Invoice ID: {response.invoice_id}")
print(f"QR Code: {response.qr_text}")

# Check payment
payment = client.check_payment(response.invoice_id)
if payment.payment_status == "PAID":
    print("Payment successful!")
```

## Frappe Integration

When used within a Frappe app, additional features are available:

```python
from mn_payments.sdk import EbarimtClient

# Enable Frappe features
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_db=True,      # Auto-save to Frappe database
    enable_email=True    # Send emails via Frappe
)

# Receipt is automatically:
# 1. Saved to "Ebarimt Receipt" DocType
# 2. Emailed to customer with QR code
# 3. QR code saved to file system
response = client.create_receipt(
    receipt_type=ReceiptType.B2C_RECEIPT,
    request=request,
    items=items,
    email_to="customer@example.com"
)
```

## Features

### Ebarimt SDK
- ✅ VAT calculation (10%)
- ✅ City tax calculation (1%)
- ✅ Tax type support (VAT_ABLE, VAT_FREE, VAT_ZERO, NOT_VAT)
- ✅ Receipt types (B2C/B2B receipts & invoices)
- ✅ Barcode support (GS1, ISBN)
- ✅ QR code generation
- ✅ Decimal precision for financial accuracy
- ✅ Database persistence (when used with Frappe)
- ✅ Email delivery (when used with Frappe)

### QPay SDK
- ✅ OAuth 2.0 authentication
- ✅ Multiple API versions (v1, v2, Quick)
- ✅ Invoice creation and management
- ✅ Payment verification
- ✅ Invoice cancellation
- ✅ QR code generation
- ✅ Multi-currency (MNT, USD, CNY)

## API Reference

See [USAGE_GUIDE.md](../../USAGE_GUIDE.md) for complete API documentation.

## Dependencies

Required packages:
```
requests>=2.31.0
qrcode[pil]>=7.4.2
python-barcode>=0.15.1
```

Optional (for Frappe integration):
```
frappe>=15.0.0
```

## Testing

```python
# Run tests
python -m pytest mn_payments/sdk/test_ebarimt.py

# Or with Frappe
bench --site your-site run-tests --module mn_payments.sdk.test_ebarimt
```

## License

MIT License - see [LICENSE](../../license.txt)

## Support

- Documentation: [Full Guide](../../USAGE_GUIDE.md)
- Issues: GitHub Issues
- Email: support@yourcompany.com
