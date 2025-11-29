# mn_payments

**Professional Mongolian Payment & Tax Integrations for ERPNext**

Seamlessly integrate QPay payments and Ebarimt tax authority receipts into your ERPNext system with POS support.

---

## Features

### 🏦 QPay Payment Gateway
- **QR Invoice Generation**: Create QPay invoices with customizable templates
- **Real-time Payment Status**: Automated payment verification and callback handling
- **Payment Request Sync**: Automatic synchronization with ERPNext Payment Requests
- **Invoice Persistence**: Complete audit trail with Qpay Invoice DocType

### 🧾 Ebarimt Tax Authority Integration
- **Automatic Receipt Submission**: Auto-submit receipts to Mongolia's tax authority (PosAPI)
- **POS Integration**: Seamless integration with ERPNext POS - receipts submitted on invoice submit
- **Taxpayer Lookup**: Real-time taxpayer information verification via TPI service
- **District Codes**: Cached district reference data for compliance
- **Pharmacy Mode**: Special handling for pharmaceutical transactions
- **Tax Calculations**: Automatic city tax (1% on alcohol/tobacco/fuel) and VAT (10%) allocation

---

## Installation

### 1. Get the App
```bash
cd /opt/bench/frappe-bench
bench get-app https://github.com/YOUR_USERNAME/mn_payments.git
```

### 2. Install on Site
```bash
bench --site [sitename] install-app mn_payments
```

### 3. Migrate Database
```bash
bench --site [sitename] migrate
```

### 4. Restart Services
```bash
bench restart
```

---

## Configuration

You can configure mn_payments through **UI Settings** (recommended) or `site_config.json`.

### Option 1: UI Configuration (Recommended)

#### QPay Settings
Navigate to: **Desk → QPay Settings**

| Field | Description | Required |
|-------|-------------|----------|
| Enabled | Enable QPay integration | ✓ |
| QPay Username | Your QPay merchant username | ✓ when enabled |
| QPay Password | Your QPay merchant password | ✓ when enabled |
| Invoice Code | QPay invoice template code | ✓ when enabled |
| Sandbox Mode | Use QPay test environment | Optional |

#### Ebarimt Settings
Navigate to: **Desk → Ebarimt Settings**

| Field | Description | Required |
|-------|-------------|----------|
| Enabled | Enable Ebarimt integration | ✓ |
| PosAPI URL | Select environment:<br>• **Production**: `https://posapi.mta.mn`<br>• **Staging**: `https://staging.posapi.mta.mn`<br>• **Custom**: Enter your own URL | ✓ when enabled |
| TPI Service URL | Select environment:<br>• **Production**: `https://tpi.mta.mn`<br>• **Staging**: `https://staging.tpi.mta.mn`<br>• **Custom**: Enter your own URL | ✓ when enabled |
| TPI Username | TPI service username | ✓ when enabled |
| TPI Password | TPI service password | ✓ when enabled |
| Is Pharmacy | Enable pharmacy-specific handling | Optional |
| Auto Submit on POS Invoice | Auto-submit receipts when POS Invoice is submitted<br>**Default: Enabled** | Optional |

### Option 2: site_config.json

Add to `/opt/bench/frappe-bench/sites/[sitename]/site_config.json`:

```json
{
  "mn_payments": {
    "qpay": {
      "username": "your_qpay_username",
      "password": "your_qpay_password",
      "invoice_code": "YOUR_INVOICE_CODE",
      "callback_base_url": "https://yourdomain.com",
      "sandbox": false
    },
    "ebarimt": {
      "posapi_url": "https://posapi.mta.mn",
      "posapi_token": "your_posapi_token",
      "tpi_service_url": "https://tpi.mta.mn",
      "tpi_username": "your_tpi_username",
      "tpi_password": "your_tpi_password"
    }
  }
}
```

**Note**: UI settings (DocTypes) take precedence over `site_config.json` when both are configured.

---

## API Reference

All endpoints are whitelisted and accessible via `/api/method/mn_payments.api.*`

### QPay Endpoints

#### Create Invoice
```http
POST /api/method/mn_payments.api.qpay.create_invoice
```
**Parameters:**
- `payment_request` (str): Payment Request name
- `amount` (float): Invoice amount
- `description` (str, optional): Invoice description

**Returns:** QPay invoice details with QR URLs

#### Get Invoice
```http
GET /api/method/mn_payments.api.qpay.get_invoice?invoice_id={id}
```

#### Check Payment
```http
POST /api/method/mn_payments.api.qpay.check_payment
```
**Parameters:**
- `invoice_id` (str): QPay invoice ID

**Returns:** Payment status and details

#### Payment Callback (Guest Access)
```http
POST /api/method/mn_payments.api.qpay.callback
```
Automatically processes QPay payment notifications.

### Ebarimt Endpoints

#### Save Receipts
```http
POST /api/method/mn_payments.api.ebarimt.save_receipts
```
**Parameters:**
- `receipts` (list): Array of receipt objects conforming to PosAPI schema

#### Get District Codes
```http
GET /api/method/mn_payments.api.ebarimt.get_district_codes
```
**Returns:** Cached list of Mongolian district codes

#### Lookup Taxpayer
```http
POST /api/method/mn_payments.api.ebarimt.lookup_taxpayer_info
```
**Parameters:**
- `regno` (str): Taxpayer registration number

**Returns:** Taxpayer details from TPI service

---

## POS Integration

### Automatic Receipt Submission

When **Auto Submit on POS Invoice** is enabled (default), receipts are automatically submitted to Ebarimt when a POS Invoice is submitted.

**Features:**
- ✅ Automatic city tax calculation (1% for alcohol, tobacco, fuel)
- ✅ VAT allocation (10% standard rate)
- ✅ Pharmacy mode support
- ✅ Detailed receipt mapping from POS Invoice items

**Tax Calculation Logic:**
- **City Tax**: Applied to items in groups: Alcohol, Tobacco, Petroleum Products
- **VAT**: Standard 10% from invoice `taxes_and_charges`

**Configuration:**
1. Navigate to **Ebarimt Settings**
2. Enable **Auto Submit on POS Invoice** (enabled by default)
3. Configure PosAPI credentials
4. Submit POS Invoices as usual - receipts auto-submit to tax authority

---

## Testing

### Run All Tests
```bash
bench --site [sitename] run-tests --app mn_payments
```

### Run Specific Module Tests
```bash
# QPay utilities
bench --site [sitename] run-tests --module mn_payments.tests.test_qpay_utils

# QPay API
bench --site [sitename] run-tests --module mn_payments.tests.test_qpay_api

# Ebarimt utilities
bench --site [sitename] run-tests --module mn_payments.tests.test_ebarimt_utils

# Ebarimt API
bench --site [sitename] run-tests --module mn_payments.tests.test_ebarimt_api
```

**Test Coverage:** 35 comprehensive unit tests covering utilities and API layers.

---

## Dependencies

### Python Dependencies
Automatically installed via `pyproject.toml`:

```toml
[project]
dependencies = [
    "frappe",
    "qpay-client>=0.3.2",  # Official QPay client library
    "requests>=2.25.0"
]
```

### Required ERPNext Apps
- `erpnext` (for POS Invoice integration)

---

## Deployment Checklist

- [ ] Install app on production site
- [ ] Run database migration (`bench migrate`)
- [ ] Configure QPay credentials (UI or site_config.json)
- [ ] Configure Ebarimt credentials (UI or site_config.json)
- [ ] Select production URLs for PosAPI and TPI services
- [ ] Test QPay invoice creation and payment callback
- [ ] Test Ebarimt receipt submission (manual or POS)
- [ ] Verify POS auto-submit integration
- [ ] Run full test suite
- [ ] Monitor logs for any integration errors

---

## Troubleshooting

### QPay Issues
- **Invalid credentials**: Check username/password in QPay Settings
- **Callback not received**: Verify `callback_base_url` is publicly accessible
- **Invoice creation fails**: Ensure `invoice_code` is valid for your merchant account

### Ebarimt Issues
- **Receipt submission fails**: Verify PosAPI token and URL
- **Taxpayer lookup errors**: Check TPI service credentials
- **POS auto-submit not working**: Ensure **Auto Submit on POS Invoice** is enabled
- **City tax not calculated**: Verify item groups match: Alcohol, Tobacco, or Petroleum Products

### Logs
Check Frappe error logs:
```bash
tail -f /opt/bench/frappe-bench/sites/[sitename]/logs/error.log
```

---

## Contributing

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

---

## License

MIT

## Credits

- **QPay Client Library**: [Amraa1/qpay_client](https://github.com/Amraa1/qpay_client)
- **Frappe Framework**: [frappe/frappe](https://github.com/frappe/frappe)
- **ERPNext**: [frappe/erpnext](https://github.com/frappe/erpnext)

---

## Support

For issues and feature requests, please open an issue on GitHub.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
