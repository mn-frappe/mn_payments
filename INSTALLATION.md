# Python SDK Installation Requirements

## Required Python Packages

The mn_payments Python SDK requires the following packages to be installed:

```bash
# Navigate to your Frappe bench
cd /Users/bg/frappe-bench

# Install required Python packages
./env/bin/pip install qrcode[pil] python-barcode requests
```

### Package Details

1. **qrcode[pil]** - QR code generation
   - Used by both Ebarimt and QPay SDKs for generating QR codes
   - The `[pil]` extra includes Pillow for image generation
   
2. **python-barcode** - Barcode generation
   - Used for generating various barcode formats (GS1, ISBN, etc.)
   - Includes EAN, UPC, Code128, and other barcode types
   
3. **requests** - HTTP client library
   - Used for API communication with QPay and Ebarimt services
   - Industry-standard HTTP library

## Frappe DocTypes

The SDK uses the following custom DocTypes that need to be installed:

### Ebarimt Module
- **Ebarimt Receipt** - Stores tax receipts
- **Ebarimt Receipt Item** - Child table for receipt line items

### QPay Module  
- **QPay Invoice** - Stores payment invoices
- **QPay Payment URL** - Child table for payment URLs

## Installation Steps

1. Install Python dependencies:
```bash
cd /Users/bg/frappe-bench
./env/bin/pip install qrcode[pil] python-barcode requests
```

2. Install the mn_payments app:
```bash
cd /Users/bg/frappe-bench
bench get-app /Users/bg/frappe-bench/apps/mn_payments
bench --site your-site install-app mn_payments
```

3. Run database migrations to create DocTypes:
```bash
bench --site your-site migrate
```

4. Restart bench:
```bash
bench restart
```

## Verify Installation

Test that all dependencies are installed correctly:

```python
import frappe
from mn_payments.ebarimt.sdk import EbarimtClient, ReceiptItem, TaxType
from mn_payments.qpay.sdk import QPayClient

# Test QR code generation
import qrcode
qr = qrcode.QRCode()
qr.add_data("test")
qr.make()

# Test barcode generation
import barcode
from barcode.writer import ImageWriter
ean = barcode.get('ean13', '123456789012', writer=ImageWriter())

print("✅ All dependencies installed successfully!")
```

## Development vs Production

### Development
- Use `bench --site your-site console` to test SDK functionality
- Enable debug mode in Frappe for detailed error messages

### Production
- Ensure all packages are installed in the production environment
- Set proper API credentials in environment variables
- Configure email settings in Frappe for receipt delivery
- Set up proper file storage (S3, local, etc.) for QR codes

## Troubleshooting

### QR Code Generation Fails
```bash
pip install --upgrade pillow qrcode[pil]
```

### Barcode Generation Fails
```bash
pip install --upgrade python-barcode
```

### Import Errors
Make sure you're using the correct Python environment:
```bash
which python  # Should point to frappe-bench/env/bin/python
```

### Database Issues
If DocTypes don't appear after migration:
```bash
bench --site your-site migrate --skip-failing
bench clear-cache
bench restart
```
