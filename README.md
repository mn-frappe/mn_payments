### MN Payments

Mongolian Payment Gateway Integration

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app mn_payments
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/mn_payments
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


# MN Payments - Mongolian Payment Integration for Frappe

Complete Python SDK for Mongolian payment systems and tax receipt integration with Frappe Framework.

## Features

✅ **Ebarimt POS 3.0 Integration**
- Tax receipt generation with automatic VAT & city tax calculations
- Support for all receipt types (B2C/B2B receipts & invoices)
- Automatic database persistence using Frappe DocTypes
- Email delivery with QR codes
- Full compliance with Mongolian tax regulations

✅ **QPay Payment Gateway**
- Multiple API versions (v1, v2, Quick)
- OAuth 2.0 authentication with automatic token refresh
- Invoice creation and payment verification
- QR code generation for mobile payments
- Support for MNT, USD, and CNY currencies

✅ **Frappe Integration**
- Native DocType persistence (no external database needed)
- Built-in email system integration
- Automatic QR code and barcode generation
- Full audit trail and change tracking
- Role-based access control

✅ **Production Ready**
- Comprehensive error handling
- Detailed logging
- Unit test coverage
- Type-safe with dataclasses
- Decimal precision for financial calculations

## Quick Start

### Installation

```bash
cd /Users/bg/frappe-bench

# Install Python dependencies
./env/bin/pip install qrcode[pil] python-barcode requests

# Install app
bench --site your-site install-app mn_payments
bench --site your-site migrate
bench restart
```

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

### Ebarimt Example

```python
import frappe
from mn_payments.sdk import (
    EbarimtClient, ReceiptItem, CreateReceiptRequest,
    TaxType, ReceiptType
)

# Initialize with all features
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_db=True,      # Auto-save to database
    enable_email=True    # Send email receipts
)

# Create receipt
items = [
    ReceiptItem(
        name="Coffee",
        bar_code="1234567890123",
        qty=2.0,
        total_amount=10000.0,
        tax_type=TaxType.VAT_ABLE,
        is_city_tax=True
    )
]

request = CreateReceiptRequest(
    branch_no="BR001",
    district_code="01",
    report_month="202412"
)

response = client.create_receipt(
    receipt_type=ReceiptType.B2C_RECEIPT,
    request=request,
    items=items,
    email_to="customer@example.com"
)

print(f"✅ Receipt: {response.id}")
print(f"🎰 Lottery: {response.lottery}")
```

### QPay Example

```python
from mn_payments.sdk import QPayClient, InvoiceRequest

client = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    invoice_code="YOUR_INVOICE_CODE",
    version="v2"
)

invoice = InvoiceRequest(
    amount=50000.0,
    sender_invoice_no="INV-2024-001",
    description="Payment for services"
)

response = client.create_invoice(invoice)
print(f"Invoice: {response.invoice_id}")
print(f"QR Code: {response.qr_text}")
```

## Documentation

- 📘 [Installation Guide](INSTALLATION.md) - Setup and dependencies
- 📗 [Usage Guide](USAGE_GUIDE.md) - Complete examples and API reference
- 📙 [Migration Guide](PYTHON_SDK_MIGRATION.md) - Go to Python migration notes

## Key Features

### VAT Calculations
```python
from mn_payments.sdk import VATCalculator

vat = VATCalculator.get_vat(10000.0)  # 10% VAT: 909.09
vat_city = VATCalculator.get_vat_with_city_tax(10000.0)  # 900.90
city = VATCalculator.get_city_tax(10000.0)  # 1% city tax: 99.10
```

### Database Integration

Receipts and invoices are automatically saved to Frappe DocTypes:

```python
# Query receipts
receipts = frappe.get_all(
    "Ebarimt Receipt",
    filters={"status": "SUCCESS"},
    fields=["bill_id", "lottery_number", "total_amount"]
)

# Get with items
receipt = frappe.get_doc("Ebarimt Receipt", "BILL12345")
for item in receipt.items:
    print(f"{item.item_name}: {item.total_amount}")
```

### Email Features

Professional HTML emails with:
- 🧾 Receipt details and breakdown
- 🎰 Lottery number display
- 📊 QR code for verification
- 🔗 Link to ebarimt.mn
- 📱 Mobile-responsive design

## Architecture

```
mn_payments/
├── sdk/                        # 📦 Standalone SDK
│   ├── __init__.py            # Public API
│   ├── ebarimt.py             # Ebarimt SDK
│   ├── qpay.py                # QPay SDK
│   ├── test_ebarimt.py        # Tests
│   └── README.md              # SDK docs
├── ebarimt/
│   └── sdk.py                 # Compatibility layer
├── qpay/
│   └── sdk.py                 # Compatibility layer
├── mn_payments/doctype/
│   ├── ebarimt_receipt/       # Receipt DocType
│   ├── ebarimt_receipt_item/
│   ├── qpay_invoice/          # Invoice DocType
│   └── qpay_payment_url/
└── templates/emails/
    └── ebarimt_receipt.html
```

## Comparison: Go SDK vs Python SDK

| Feature | Go SDK (Old) | Python SDK (New) |
|---------|--------------|------------------|
| Language | Go | Python |
| Frappe Integration | Microservice | Native |
| Database | SQLAlchemy | Frappe DocTypes |
| Email | SMTP | Frappe Email |
| QR Codes | External | Built-in |
| Deployment | Separate service | Single app |
| Maintenance | External dependency | Internal control |
| VAT Precision | ✅ Exact | ✅ Exact (Decimal) |

## Configuration

Add to `site_config.json`:

```json
{
    "ebarimt_pos_no": "POS12345",
    "ebarimt_merchant_tin": "1234567890",
    "qpay_client_id": "YOUR_CLIENT_ID",
    "qpay_client_secret": "YOUR_CLIENT_SECRET"
}
```

## Testing

```bash
bench --site your-site run-tests --app mn_payments
bench --site your-site run-tests --module mn_payments.ebarimt.test_sdk --coverage
```

## Requirements

- Python 3.10+
- Frappe Framework v15+
- MariaDB 10.6+
- Dependencies: `qrcode[pil]`, `python-barcode`, `requests`

## License

MIT License - see [LICENSE](license.txt)

## Credits

Developed by **Digital Consulting Service LLC**

---

**Made with ❤️ for Mongolian businesses using Frappe**
