# Example Configuration

This file contains example configurations for mn_payments. Choose the configuration method that works best for your deployment.

---

## UI Configuration (Recommended)

The easiest way to configure mn_payments is through the ERPNext UI:

### QPay Settings
1. Navigate to **Desk → QPay Settings**
2. Fill in the following fields:

```
Enabled: ✓ (Check)
QPay Username: merchant_username
QPay Password: ••••••••••••••
Invoice Code: INVOICE_TEMPLATE_001
Sandbox Mode: ☐ (Uncheck for production)
```

### Ebarimt Settings
1. Navigate to **Desk → Ebarimt Settings**
2. Fill in the following fields:

```
Enabled: ✓ (Check)
PosAPI URL: Production (https://posapi.mta.mn)
TPI Service URL: Production (https://tpi.mta.mn)
TPI Username: tpi_username
TPI Password: ••••••••••••••
Is Pharmacy: ☐ (Check only if pharmacy)
Auto Submit on POS Invoice: ✓ (Checked by default)
```

---

## site_config.json Configuration

For automated deployments or legacy setups, add configuration to:
`/opt/bench/frappe-bench/sites/[sitename]/site_config.json`

### Full Configuration Example

```json
{
  "db_name": "your_database",
  "db_password": "your_db_password",
  "mn_payments": {
    "qpay": {
      "username": "merchant_username",
      "password": "merchant_password",
      "invoice_code": "INVOICE_TEMPLATE_001",
      "callback_base_url": "https://yourdomain.com",
      "sandbox": false
    },
    "ebarimt": {
      "posapi_url": "https://posapi.mta.mn",
      "posapi_token": "your_long_posapi_token_here",
      "tpi_service_url": "https://tpi.mta.mn",
      "tpi_username": "tpi_username",
      "tpi_password": "tpi_password"
    }
  }
}
```

### QPay Only

```json
{
  "mn_payments": {
    "qpay": {
      "username": "merchant_username",
      "password": "merchant_password",
      "invoice_code": "INVOICE_TEMPLATE_001",
      "callback_base_url": "https://yourdomain.com",
      "sandbox": false
    }
  }
}
```

### Ebarimt Only

```json
{
  "mn_payments": {
    "ebarimt": {
      "posapi_url": "https://posapi.mta.mn",
      "posapi_token": "your_long_posapi_token_here",
      "tpi_service_url": "https://tpi.mta.mn",
      "tpi_username": "tpi_username",
      "tpi_password": "tpi_password"
    }
  }
}
```

### Sandbox/Testing Configuration

```json
{
  "mn_payments": {
    "qpay": {
      "username": "test_merchant",
      "password": "test_password",
      "invoice_code": "TEST_TEMPLATE",
      "callback_base_url": "https://staging.yourdomain.com",
      "sandbox": true
    },
    "ebarimt": {
      "posapi_url": "https://staging.posapi.mta.mn",
      "posapi_token": "staging_token",
      "tpi_service_url": "https://staging.tpi.mta.mn",
      "tpi_username": "staging_tpi_user",
      "tpi_password": "staging_tpi_pass"
    }
  }
}
```

---

## Environment-Specific Notes

### Production
- **PosAPI URL**: `https://posapi.mta.mn`
- **TPI Service URL**: `https://tpi.mta.mn`
- **QPay Sandbox**: `false`
- **Callback URL**: Must be publicly accessible HTTPS endpoint

### Staging
- **PosAPI URL**: `https://staging.posapi.mta.mn`
- **TPI Service URL**: `https://staging.tpi.mta.mn`
- **QPay Sandbox**: `true`
- **Callback URL**: Can be staging domain

### Development/Local
- **QPay Sandbox**: `true`
- **Callback URL**: Use ngrok or similar tunnel for local testing
- **Ebarimt**: Use staging URLs to avoid production submissions

---

## Configuration Priority

When both UI settings and site_config.json exist:

1. **UI Settings take precedence** (Qpay Settings, Ebarimt Settings DocTypes)
2. **site_config.json is used as fallback** if UI settings are empty/disabled

This allows gradual migration from file-based to UI-based configuration.

---

## Security Best Practices

- ✅ Never commit `site_config.json` with real credentials to version control
- ✅ Use environment variables or secrets management in production
- ✅ Rotate PosAPI tokens and passwords regularly
- ✅ Restrict callback URL to known domains only
- ✅ Enable HTTPS for all production endpoints
- ✅ Use Role Permissions to limit access to Settings DocTypes

---

## Verification

After configuration, verify setup:

```bash
# Check QPay configuration
bench --site [sitename] console
>>> from mn_payments.utils.qpay import build_qpay_client
>>> client = build_qpay_client()
>>> print(client)

# Check Ebarimt configuration
>>> from mn_payments.utils.ebarimt import _load_site_section
>>> config = _load_site_section("ebarimt")
>>> print(config)
```

Both should return configuration objects without errors.
