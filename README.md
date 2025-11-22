# MN Payments (clean scaffold)

- Frappe v15-ready payments app with QPay and ebarimt/PosAPI integration.
- Features: Payment Provider, Payment Transaction (with special/city tax), VAT Invoice with privacy for Individuals, webhook events/logs, subscription plans and special tax types, QPay wrapper (qpay_client), ebarimt gateway with TIN lookup, public `/pay` page.
- Mocks not included; keep dev minimal. Add adapters under `integrations/` as needed.

## Install (bench)
```
bench get-app /path/to/mn_payments_clean
bench --site <site> install-app mn_payments
```

Configure Payment Provider (QPay) and Ebarimt Settings, then open `/pay` on your site.

## Testing
```
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with bench (recommended)
bench run-tests --app mn_payments

# Or run basic tests outside bench (with mocks)
python3 simple_test_runner.py
```
