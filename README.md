# MN Payments (clean scaffold)

- Frappe v15-ready payments app with QPay and ebarimt/PosAPI integration.
- Features: Payment Provider, Payment Transaction (with special/city tax), VAT Invoice with privacy for Individuals, webhook events/logs, subscription plans and special tax types, QPay wrapper (qpay_client), ebarimt gateway with TIN lookup, public `/pay` page.
- Mocks not included; keep dev minimal. Add adapters under `integrations/` as needed.

## Install (bench)
```
bench get-app /path/to/mn_payments_clean
bench --site <site> install-app mn_payments
```

Configure Payment Provider (QPay) and `Ebarimt Settings`, then open `/pay` on your site.

Security & setup notes:
- Webhook signature verification (HMAC-SHA256) is enforced using the `Webhook Secret` from `Payment Provider`. Ensure you configure this secret in the provider record.
- `Ebarimt Settings` DocType is required for Ebarimt/PosAPI features (receipt generation and TIN lookup); the app includes a patch to create a default settings document on install.

## Testing
```
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with bench (recommended)
bench run-tests --app mn_payments

# Or run basic tests outside bench (with mocks)
python3 simple_test_runner.py
```
