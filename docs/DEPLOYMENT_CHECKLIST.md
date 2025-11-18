# Deployment Checklist

## Pre-Deployment

### 1. Install Dependencies ☐
```bash
cd /Users/bg/frappe-bench
./env/bin/pip install qrcode[pil] python-barcode requests
```

### 2. Verify Installation ☐
```bash
./env/bin/python -c "import qrcode; import barcode; import requests; print('✅ All dependencies installed')"
```

### 3. Check Frappe Version ☐
```bash
bench version
# Required: Frappe v15+ recommended
```

## Installation

### 1. Get App ☐
```bash
cd /Users/bg/frappe-bench
bench get-app /Users/bg/frappe-bench/apps/mn_payments
```

### 2. Install on Site ☐
```bash
bench --site your-site install-app mn_payments
```

### 3. Run Migrations ☐
```bash
bench --site your-site migrate
```

### 4. Verify DocTypes Created ☐
```bash
bench --site your-site console
```
```python
import frappe
frappe.get_doc("DocType", "Ebarimt Receipt")
frappe.get_doc("DocType", "Ebarimt Receipt Item")
frappe.get_doc("DocType", "QPay Invoice")
frappe.get_doc("DocType", "QPay Payment URL")
print("✅ All DocTypes exist")
```

## Configuration

### 1. Email Settings ☐
```bash
# Configure SMTP (if not already done)
bench --site your-site set-config mail_server "smtp.gmail.com"
bench --site your-site set-config mail_port 587
bench --site your-site set-config use_tls 1
bench --site your-site set-config mail_login "your-email@gmail.com"
bench --site your-site set-config mail_password "your-app-password"
```

### 2. API Credentials ☐

Add to `sites/your-site/site_config.json`:
```json
{
    "ebarimt_pos_no": "YOUR_POS_NUMBER",
    "ebarimt_merchant_tin": "YOUR_MERCHANT_TIN",
    "ebarimt_api_url": "https://api.ebarimt.mn",
    "qpay_client_id": "YOUR_QPAY_CLIENT_ID",
    "qpay_client_secret": "YOUR_QPAY_CLIENT_SECRET",
    "qpay_invoice_code": "YOUR_INVOICE_CODE"
}
```

### 3. File Storage ☐
```bash
# Ensure files directory is writable
ls -la sites/your-site/public/files/
# Should show drwxr-xr-x permissions
```

### 4. Restart Services ☐
```bash
bench restart
```

## Testing

### 1. Unit Tests ☐
```bash
bench --site your-site run-tests --app mn_payments
```

### 2. VAT Calculation Test ☐
```bash
bench --site your-site console
```
```python
from mn_payments.ebarimt.sdk import VATCalculator

# Test 10% VAT
assert VATCalculator.get_vat(10000.0) == 909.09, "VAT calculation failed"

# Test city tax
assert VATCalculator.get_city_tax(10000.0) == 99.10, "City tax failed"

print("✅ VAT calculations correct")
```

### 3. Database Test ☐
```python
import frappe
from mn_payments.ebarimt.sdk import EbarimtClient, ReceiptItem, CreateReceiptRequest, TaxType, ReceiptType

# Initialize with DB enabled
client = EbarimtClient(
    base_url=frappe.conf.get("ebarimt_api_url"),
    pos_no=frappe.conf.get("ebarimt_pos_no"),
    merchant_tin=frappe.conf.get("ebarimt_merchant_tin"),
    enable_db=True,
    enable_email=False
)

# Create test receipt (will fail API call but test DB logic)
items = [
    ReceiptItem(
        name="Test Item",
        bar_code="1234567890123",
        qty=1.0,
        total_amount=10000.0,
        tax_type=TaxType.VAT_ABLE,
        is_city_tax=True
    )
]

request = CreateReceiptRequest(
    branch_no="TEST01",
    district_code="01",
    report_month="202412"
)

try:
    response = client.create_receipt(
        receipt_type=ReceiptType.B2C_RECEIPT,
        request=request,
        items=items
    )
    print(f"✅ Receipt created: {response.id}")
except Exception as e:
    print(f"Expected API error (no valid credentials): {str(e)[:100]}")
```

### 4. Email Test ☐
```python
# Test email sending
frappe.sendmail(
    recipients=["test@example.com"],
    subject="Test Email",
    message="Testing Frappe email system",
    now=True
)
print("✅ Email sent (check inbox)")
```

### 5. QR Code Test ☐
```python
import qrcode
from io import BytesIO

qr = qrcode.QRCode()
qr.add_data("test")
qr.make()
img = qr.make_image()

buffer = BytesIO()
img.save(buffer, format="PNG")
print(f"✅ QR code generated: {len(buffer.getvalue())} bytes")
```

## Production Deployment

### 1. Set Production Config ☐
```bash
bench --site your-site set-config developer_mode 0
bench --site your-site set-config maintenance_mode 0
```

### 2. Clear Cache ☐
```bash
bench clear-cache
bench --site your-site clear-cache
```

### 3. Build Assets ☐
```bash
bench build --app mn_payments
```

### 4. Setup Supervisor ☐
```bash
bench setup supervisor
sudo supervisorctl reread
sudo supervisorctl update
```

### 5. Setup Nginx ☐
```bash
bench setup nginx
sudo service nginx reload
```

### 6. Enable SSL (Recommended) ☐
```bash
bench setup lets-encrypt your-site.com
```

## Monitoring

### 1. Check Error Logs ☐
```bash
# Watch Frappe logs
tail -f sites/your-site/logs/frappe.log

# Watch error logs
tail -f sites/your-site/logs/error.log
```

### 2. Monitor Database ☐
```sql
-- Check receipt count
SELECT COUNT(*) FROM `tabEbarimt Receipt`;

-- Check recent receipts
SELECT bill_id, lottery_number, total_amount, status 
FROM `tabEbarimt Receipt` 
ORDER BY creation DESC LIMIT 10;

-- Check QPay invoices
SELECT invoice_id, invoice_status, amount 
FROM `tabQPay Invoice` 
ORDER BY creation DESC LIMIT 10;
```

### 3. Monitor File Storage ☐
```bash
# Check QR code files
ls -lh sites/your-site/public/files/ | grep ebarimt_qr

# Check disk usage
du -sh sites/your-site/public/files/
```

## Post-Deployment

### 1. Create Test Receipt ☐
Use the Ebarimt SDK to create a real receipt with production credentials.

### 2. Verify Database Saved ☐
Check that receipt appears in `Ebarimt Receipt` DocType.

### 3. Verify Email Sent ☐
Confirm email received with QR code attached.

### 4. Verify QR Code ☐
Scan QR code and verify on ebarimt.mn website.

### 5. Create Test Invoice (QPay) ☐
Create invoice and verify payment URLs work.

## Rollback Plan

### If Issues Occur

1. **Uninstall App**
```bash
bench --site your-site uninstall-app mn_payments
```

2. **Restore Backup**
```bash
bench --site your-site restore /path/to/backup.sql.gz
```

3. **Remove Files**
```bash
rm -rf apps/mn_payments
bench restart
```

## Security Checklist

### 1. Credentials ☐
- [ ] API credentials stored in site_config.json (not in code)
- [ ] site_config.json has proper permissions (600)
- [ ] No credentials committed to Git
- [ ] Production credentials different from test

### 2. Permissions ☐
- [ ] Ebarimt Receipt DocType permissions set
- [ ] QPay Invoice DocType permissions set
- [ ] File upload permissions restricted
- [ ] Email permissions restricted

### 3. Network ☐
- [ ] HTTPS enabled (SSL certificate)
- [ ] Firewall configured
- [ ] API rate limiting enabled
- [ ] DDoS protection enabled

## Performance Checklist

### 1. Database ☐
- [ ] Indexes created on DocTypes
- [ ] Query performance acceptable
- [ ] Regular backups scheduled
- [ ] Archive old receipts plan

### 2. Files ☐
- [ ] CDN for file serving (optional)
- [ ] File cleanup job scheduled
- [ ] Storage limits configured
- [ ] Backup includes files directory

### 3. Email ☐
- [ ] Email queue size monitored
- [ ] SMTP connection pooling enabled
- [ ] Retry logic configured
- [ ] Bounce handling setup

## Documentation Review

### 1. Read All Docs ☐
- [ ] README.md
- [ ] INSTALLATION.md
- [ ] USAGE_GUIDE.md
- [ ] PYTHON_SDK_MIGRATION.md
- [ ] MIGRATION_COMPLETE.md

### 2. Understand APIs ☐
- [ ] Ebarimt SDK methods
- [ ] QPay SDK methods
- [ ] DocType structure
- [ ] Email templates

### 3. Know Troubleshooting ☐
- [ ] Common errors
- [ ] Log locations
- [ ] Debug mode
- [ ] Support contacts

## Final Verification

### All Systems Go ☐
- [ ] Dependencies installed
- [ ] App installed and migrated
- [ ] Configuration complete
- [ ] Tests passing
- [ ] Email working
- [ ] QR codes generating
- [ ] Database saving
- [ ] Production deployed
- [ ] Monitoring setup
- [ ] Documentation reviewed

## Success Criteria

✅ Can create Ebarimt receipt
✅ Receipt saved to database
✅ Email sent with QR code
✅ QR code verifiable on ebarimt.mn
✅ QPay invoice created
✅ Payment verification works
✅ No errors in logs
✅ Performance acceptable

---

**Deployment Status**: ☐ Not Started / ☐ In Progress / ☐ Complete

**Deployed By**: _________________

**Date**: _________________

**Notes**: _________________
