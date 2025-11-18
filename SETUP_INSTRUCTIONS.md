# MN Payments Setup Instructions

## ✅ Environment Status (Verified Nov 18, 2025)

- ✅ Bench: v5.27.0
- ✅ Python: 3.12.12 (bench venv)
- ✅ Frappe: v15.88.2
- ✅ MariaDB: 10.6.24
- ✅ Redis: Running
- ✅ mn_payments: Installed (v0.0.1)
- ✅ Dependencies: requests (2.32.5), qrcode (8.2), python-barcode (0.16.1) ✅ INSTALLED

## 🚀 Create Test Site & Install App

### Step 1: Create a new site

```bash
cd /Users/bg/frappe-bench
bench new-site test.local --admin-password admin --install-app mn_payments
```

**You will be prompted for:**
- MariaDB root password (enter your password when prompted)

### Step 2: Verify installation

```bash
bench --site test.local list-apps
```

Should show:
```
frappe
mn_payments
```

### Step 3: Run migrations

```bash
bench --site test.local migrate
```

### Step 4: Check DocTypes created

```bash
bench --site test.local console
```

In Python console:
```python
import frappe
frappe.get_all("Ebarimt Receipt")
frappe.get_all("QPay Invoice")
exit()
```

## 🧪 Run Tests

### Option 1: Run all SDK tests
```bash
bench --site test.local run-tests --module mn_payments.sdk.test_ebarimt
```

### Option 2: Run specific test
```bash
bench --site test.local console
```

```python
from mn_payments.sdk.test_ebarimt import TestVATCalculations
import unittest

suite = unittest.TestLoader().loadTestsFromTestCase(TestVATCalculations)
unittest.TextTestRunner(verbosity=2).run(suite)
```

### Option 3: Test SDK directly
```bash
bench --site test.local console
```

```python
from mn_payments.sdk import EbarimtClient, QPayClient
from mn_payments.sdk.ebarimt import TaxType

# Test Ebarimt
client = EbarimtClient(
    pos_no="POS123",
    vat_regno="123456",
    api_url="https://api.ebarimt.mn/api"
)

# Test VAT calculation
vat_info = client.calculate_vat(10000.0, TaxType.VAT_ABLE)
print(f"Amount: {vat_info['amount']}")
print(f"VAT: {vat_info['vat']}")
print(f"City Tax: {vat_info['city_tax']}")

# Test QPay
qpay = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_SECRET",
    invoice_code="TEST_CODE"
)

# Test token (will fail without real credentials)
# token = qpay.get_access_token()
```

## 📊 Test Receipt Creation (Full Flow)

```python
from mn_payments.sdk import EbarimtClient
from mn_payments.sdk.ebarimt import TaxType
import frappe

frappe.init(site='test.local')
frappe.connect()

client = EbarimtClient(
    pos_no="POS123",
    vat_regno="123456"
)

# Create receipt
receipt = client.create_receipt(
    items=[
        {
            "name": "Test Product",
            "qty": 2,
            "unit_price": 5000.0,
            "tax_type": TaxType.VAT_ABLE
        }
    ],
    customer_name="Test Customer",
    save_to_db=True
)

print(f"Receipt ID: {receipt['id']}")
print(f"Lottery: {receipt['lottery']}")
print(f"QR Code: {receipt['qr_data']}")

# Check database
doc = frappe.get_doc("Ebarimt Receipt", receipt["id"])
print(f"DocType saved: {doc.name}")
print(f"QR Image: {doc.qr_code}")
```

## 🌐 Start Development Server

```bash
bench start
```

Access:
- **Desk**: http://localhost:8000/app
- **Login**: Administrator / admin

## 📝 Configure Credentials

### Via Site Config
```bash
bench --site test.local set-config ebarimt_pos_no "YOUR_POS_NO"
bench --site test.local set-config ebarimt_vat_regno "YOUR_VAT_REGNO"
bench --site test.local set-config qpay_client_id "YOUR_CLIENT_ID"
bench --site test.local set-config qpay_client_secret "YOUR_SECRET"
bench --site test.local set-config qpay_invoice_code "YOUR_CODE"
```

### Via DocTypes (Recommended)
Create configuration DocTypes in desk UI or use:

```python
import frappe

# Ebarimt config
config = frappe.get_doc({
    "doctype": "Ebarimt Config",
    "pos_no": "POS123",
    "vat_regno": "123456",
    "api_url": "https://api.ebarimt.mn/api"
})
config.insert()
```

## 🐛 Troubleshooting

### Database connection error
- Check MariaDB is running: `mariadb -u root -p`
- Verify root password is correct

### Site already exists
```bash
bench drop-site test.local --force
```

### Missing packages
```bash
cd /Users/bg/frappe-bench
env/bin/pip install "qrcode[pil]>=7.4.2" "python-barcode>=0.15.1"
```

### Permission errors
```bash
bench --site test.local add-system-manager your@email.com
```

## 📚 Next Steps

1. ✅ Create site: `bench new-site test.local --admin-password admin --install-app mn_payments`
2. ✅ Run tests: `bench --site test.local run-tests --module mn_payments.sdk.test_ebarimt`
3. 🔧 Configure credentials (via Site Config or create Config DocTypes)
4. 🧪 Test with real API credentials
5. 🚀 Deploy to production (see DEPLOYMENT_CHECKLIST.md)

## 🎯 Production Deployment

See detailed checklist in:
- `DEPLOYMENT_CHECKLIST.md` - Complete deployment guide
- `USAGE_GUIDE.md` - SDK usage examples
- `INTEGRATION_EXAMPLE.md` - Integration patterns
