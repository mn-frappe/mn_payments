# Complete Python SDK Usage Guide

This guide demonstrates how to use the mn_payments Python SDK with all features including database integration, email functionality, and QR code generation.

## Table of Contents
- [Installation](#installation)
- [Ebarimt SDK](#ebarimt-sdk)
- [QPay SDK](#qpay-sdk)
- [Database Integration](#database-integration)
- [Email Functionality](#email-functionality)
- [QR Code Generation](#qr-code-generation)

## Installation

See [INSTALLATION.md](INSTALLATION.md) for detailed installation instructions.

Quick install:
```bash
cd /Users/bg/frappe-bench
./env/bin/pip install qrcode[pil] python-barcode requests
bench --site your-site install-app mn_payments
bench --site your-site migrate
```

## Ebarimt SDK

### Basic Usage

```python
import frappe
from mn_payments.ebarimt.sdk import (
    EbarimtClient,
    ReceiptItem,
    CreateReceiptRequest,
    TaxType,
    BarCodeType,
    ReceiptType
)

# Initialize client with all features enabled
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_db=True,      # Save to database
    enable_email=True    # Send email receipts
)

# Create receipt items
items = [
    ReceiptItem(
        name="Coffee",
        bar_code="1234567890123",
        bar_code_type=BarCodeType.GS1,
        classification_code="10110100",
        tax_product_code="1234567",
        measure_unit="pc",
        qty=2.0,
        total_amount=10000.0,
        tax_type=TaxType.VAT_ABLE,
        is_city_tax=True
    ),
    ReceiptItem(
        name="Book",
        bar_code="9781234567890",
        bar_code_type=BarCodeType.ISBN,
        classification_code="10110200",
        tax_product_code="1234568",
        measure_unit="pc",
        qty=1.0,
        total_amount=25000.0,
        tax_type=TaxType.VAT_FREE,
        is_city_tax=False
    )
]

# Create receipt request
request = CreateReceiptRequest(
    branch_no="BR001",
    district_code="01",
    report_month="202412",
    org_code="7654321098"  # Customer TIN (optional)
)

# Send receipt (automatically saves to DB and sends email)
response = client.create_receipt(
    receipt_type=ReceiptType.B2C_RECEIPT,
    request=request,
    items=items,
    email_to="customer@example.com"  # Optional email recipient
)

print(f"Receipt ID: {response.id}")
print(f"Lottery: {response.lottery}")
print(f"QR Data: {response.qr_data}")
print(f"Total: {response.total_amount}")
print(f"VAT: {response.total_vat}")
print(f"City Tax: {response.total_city_tax}")
```

### Working with Tax Types

```python
from mn_payments.ebarimt.sdk import TaxType, VATCalculator

# VAT-able items (10% VAT)
amount = 10000.0
vat = VATCalculator.get_vat(amount)
print(f"VAT: {vat}")  # 909.09

# VAT-able with city tax (10% VAT + 1% city tax)
total_vat = VATCalculator.get_vat_with_city_tax(amount)
city_tax = VATCalculator.get_city_tax(amount)
print(f"VAT: {total_vat}")  # 900.90
print(f"City Tax: {city_tax}")  # 99.10

# VAT-zero or VAT-free with city tax (1% city tax only)
city_tax = VATCalculator.get_city_tax_without_vat(amount)
print(f"City Tax: {city_tax}")  # 99.01

# Number precision
precise = VATCalculator.number_precision(123.456789)
print(f"Precise: {precise}")  # 123.46
```

### Database Integration

When `enable_db=True`, receipts are automatically saved to the **Ebarimt Receipt** DocType:

```python
# Receipts are automatically saved when created
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_db=True
)

response = client.create_receipt(receipt_type, request, items)

# Query saved receipts
receipts = frappe.get_all(
    "Ebarimt Receipt",
    filters={"merchant_tin": "1234567890"},
    fields=["bill_id", "lottery_number", "total_amount", "status"]
)

# Get specific receipt with items
receipt = frappe.get_doc("Ebarimt Receipt", "BILL12345")
print(f"Receipt: {receipt.bill_id}")
print(f"Lottery: {receipt.lottery_number}")
print(f"Total: {receipt.total_amount}")

for item in receipt.items:
    print(f"  - {item.item_name}: {item.total_amount}")
```

### Email Functionality

When `enable_email=True`, receipts are automatically emailed:

```python
client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_email=True
)

# Email automatically sent when email_to is provided
response = client.create_receipt(
    receipt_type=ReceiptType.B2C_RECEIPT,
    request=request,
    items=items,
    email_to="customer@example.com"
)
```

Email includes:
- ✅ Professional HTML template
- ✅ Receipt details (bill ID, date, amounts)
- ✅ Lottery number (if available)
- ✅ QR code for verification
- ✅ Link to ebarimt.mn for online verification

### QR Code Generation

QR codes are automatically generated and saved:

```python
# QR codes are generated automatically in _generate_qr_code_file
# They are:
# 1. Saved to Frappe file system
# 2. Attached to receipt documents
# 3. Included in email templates
# 4. Available for verification

# Access QR code
receipt = frappe.get_doc("Ebarimt Receipt", "BILL12345")
print(f"QR Data: {receipt.qr_data}")
print(f"QR Image URL: {receipt.qr_image}")

# QR code is also returned in response
response = client.create_receipt(receipt_type, request, items)
print(f"QR for scanning: {response.qr_data}")
```

## QPay SDK

### Basic Usage

```python
from mn_payments.qpay.sdk import (
    QPayClient,
    InvoiceRequest,
    PaymentType
)

# Initialize client
client = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    invoice_code="YOUR_INVOICE_CODE",
    version="v2"  # or "v1", "quick"
)

# Create invoice
invoice_request = InvoiceRequest(
    amount=50000.0,
    sender_invoice_no="INV-2024-001",
    description="Payment for services",
    callback_url="https://yoursite.com/callback"
)

response = client.create_invoice(invoice_request)

print(f"Invoice ID: {response.invoice_id}")
print(f"QR Text: {response.qr_text}")
print(f"QR Image: {response.qr_image}")

# Payment URLs for different banks
for url in response.urls:
    print(f"{url.name}: {url.link}")
```

### Check Payment Status

```python
# Check if invoice is paid
payment_check = client.check_payment(invoice_id=response.invoice_id)

if payment_check.payment_status == "PAID":
    print(f"Paid! Transaction ID: {payment_check.payment_id}")
    print(f"Paid amount: {payment_check.payment_amount}")
    print(f"Paid date: {payment_check.payment_date}")
else:
    print(f"Status: {payment_check.payment_status}")
```

### Cancel Invoice

```python
# Cancel unpaid invoice
cancel_response = client.cancel_invoice(invoice_id=response.invoice_id)
print(f"Canceled: {cancel_response.invoice_id}")
```

### OAuth Token Management

```python
# Tokens are automatically managed
# Manual refresh if needed:
client.refresh_token()
print(f"New access token: {client.access_token}")
```

### QPay Quick API

```python
# Use Quick API for instant payments
client = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    version="quick"
)

# Create quick invoice
response = client.create_simple_invoice(
    amount=10000.0,
    description="Quick payment"
)
```

## Database Integration

### Ebarimt Receipt DocType

Fields:
- `bill_id` - Unique receipt ID (primary key)
- `lottery_number` - Tax lottery number
- `receipt_date` - Receipt timestamp
- `receipt_type` - B2C_RECEIPT, B2B_RECEIPT, B2C_INVOICE, B2B_INVOICE
- `merchant_tin` - Merchant tax ID
- `pos_no` - POS terminal number
- `branch_no` - Branch number
- `district_code` - District code
- `customer_tin` - Customer tax ID
- `total_amount` - Total amount (MNT)
- `total_vat` - Total VAT (MNT)
- `total_city_tax` - Total city tax (MNT)
- `status` - SUCCESS, ERROR, PAYMENT
- `message` - Response message
- `qr_data` - QR code data
- `qr_image` - QR code image URL
- `items` - Child table of receipt items

### Ebarimt Receipt Item DocType (Child Table)

Fields:
- `item_name` - Product/service name
- `classification_code` - Product classification
- `tax_type` - VAT_ABLE, VAT_FREE, VAT_ZERO, NOT_VAT
- `qty` - Quantity
- `unit_price` - Price per unit
- `total_amount` - Line total
- `total_vat` - Line VAT
- `total_city_tax` - Line city tax
- `measure_unit` - Unit of measure
- `tax_product_code` - Tax authority product code
- `bar_code` - Product barcode
- `bar_code_type` - UNDEFINED, GS1, ISBN

### QPay Invoice DocType

Fields:
- `invoice_id` - Unique invoice ID (primary key)
- `invoice_code` - Invoice code
- `invoice_status` - UNPAID, PAID, CANCELED, etc.
- `amount` - Payment amount
- `currency` - MNT, USD, CNY
- `created_date` - Creation timestamp
- `paid_date` - Payment timestamp
- `sender_invoice_no` - Your invoice number
- `sender_name` - Sender name
- `sender_tin` - Sender TIN
- `description` - Payment description
- `callback_url` - Webhook URL
- `payment_urls` - Child table of payment URLs
- `deeplink_qr` - QR deeplink data
- `qr_text` - QR text
- `qr_image` - QR image URL

### Query Examples

```python
# Get today's receipts
from frappe.utils import today

receipts = frappe.get_all(
    "Ebarimt Receipt",
    filters={
        "receipt_date": [">=", today()],
        "status": "SUCCESS"
    },
    fields=["bill_id", "total_amount", "lottery_number"]
)

# Get receipts with high value
high_value = frappe.get_all(
    "Ebarimt Receipt",
    filters={"total_amount": [">", 100000]},
    order_by="total_amount DESC",
    limit=10
)

# Get paid QPay invoices
paid_invoices = frappe.get_all(
    "QPay Invoice",
    filters={"invoice_status": "PAID"},
    fields=["invoice_id", "amount", "paid_date"]
)
```

## Email Functionality

Email templates use Frappe's built-in email system with professional HTML formatting.

### Customizing Email Templates

Edit `/Users/bg/frappe-bench/apps/mn_payments/mn_payments/templates/emails/ebarimt_receipt.html`:

```html
<!-- Add your branding -->
<div class="header">
    <img src="/assets/your-logo.png" alt="Company Logo">
    <h1>🧾 Ebarimt Tax Receipt</h1>
</div>

<!-- Customize content -->
<div class="custom-message">
    <p>Thank you for your purchase!</p>
</div>
```

### Email Configuration

Configure Frappe email settings:

```bash
bench --site your-site set-config mail_server "smtp.gmail.com"
bench --site your-site set-config mail_port 587
bench --site your-site set-config use_tls 1
bench --site your-site set-config mail_login "your-email@gmail.com"
bench --site your-site set-config mail_password "your-app-password"
```

## QR Code Generation

### QR Code Features

- Automatic generation for both Ebarimt and QPay
- Saved to Frappe file system
- Attached to documents
- Included in emails
- Uses industry-standard qrcode library
- Configurable error correction
- High quality PNG output

### Manual QR Generation

```python
import qrcode
from io import BytesIO

def generate_custom_qr(data: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
        box_size=15,  # Larger boxes
        border=5,  # Wider border
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="blue", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
```

### Barcode Generation (Optional)

```python
from barcode import EAN13, Code128
from barcode.writer import ImageWriter
from io import BytesIO

# EAN-13 barcode
ean = EAN13('123456789012', writer=ImageWriter())
buffer = BytesIO()
ean.write(buffer)

# Code 128 barcode
code128 = Code128('INVOICE-2024-001', writer=ImageWriter())
buffer = BytesIO()
code128.write(buffer)
```

## Error Handling

```python
from requests.exceptions import RequestException

try:
    response = client.create_receipt(receipt_type, request, items)
except RequestException as e:
    frappe.log_error(f"API request failed: {str(e)}", "Ebarimt Error")
    frappe.throw("Failed to create receipt. Please try again.")
except Exception as e:
    frappe.log_error(f"Unexpected error: {str(e)}", "Ebarimt Error")
    frappe.throw("An unexpected error occurred.")
```

## Production Deployment

### Environment Variables

```bash
# Set in site_config.json or environment
{
    "ebarimt_pos_no": "POS12345",
    "ebarimt_merchant_tin": "1234567890",
    "ebarimt_api_url": "https://api.ebarimt.mn",
    "qpay_client_id": "YOUR_CLIENT_ID",
    "qpay_client_secret": "YOUR_CLIENT_SECRET",
    "qpay_invoice_code": "YOUR_INVOICE_CODE"
}
```

### Load from Config

```python
import frappe

# Load credentials from site config
ebarimt_client = EbarimtClient(
    base_url=frappe.conf.get("ebarimt_api_url"),
    pos_no=frappe.conf.get("ebarimt_pos_no"),
    merchant_tin=frappe.conf.get("ebarimt_merchant_tin"),
    enable_db=True,
    enable_email=True
)

qpay_client = QPayClient(
    client_id=frappe.conf.get("qpay_client_id"),
    client_secret=frappe.conf.get("qpay_client_secret"),
    invoice_code=frappe.conf.get("qpay_invoice_code")
)
```

## Testing

```python
# Run tests
bench --site your-site run-tests --app mn_payments

# Test specific module
bench --site your-site run-tests --module mn_payments.ebarimt.test_sdk

# Coverage
bench --site your-site run-tests --app mn_payments --coverage
```

## Support

For issues or questions:
- GitHub: [Your Repository]
- Email: support@yourcompany.com
- Documentation: [Your Docs Site]

## License

See [LICENSE](LICENSE) file for details.
