# Integration with Payments App

## Overview

The `payments` app provides a standardized payment gateway framework used by international gateways (Stripe, PayTM, Braintree, etc.). While `mn_payments` is **100% independent** and can work standalone, you can optionally integrate it to provide unified payment gateway selection.

## Architecture Comparison

### Payments App Architecture
```
payments/
├── payment_gateways/
│   ├── stripe_integration.py          # Gateway implementation
│   └── doctype/
│       ├── stripe_settings/           # Gateway settings DocType
│       │   └── stripe_settings.py     # Controller with create_request()
│       └── payment_gateway/           # Base gateway DocType
└── utils/
    └── create_payment_gateway()       # Helper function
```

### MN Payments Architecture (Current - Standalone)
```
mn_payments/
├── sdk/
│   ├── ebarimt.py                     # Ebarimt SDK
│   └── qpay.py                        # QPay SDK
└── mn_payments/
    └── doctype/
        ├── ebarimt_receipt/           # Tax receipt records
        ├── qpay_invoice/              # Payment invoice records
        └── qpay_payment_url/          # Payment URLs
```

## Integration Options

### Option 1: Standalone (Current - Recommended ✅)

**Use Case**: Direct integration in your app without payments app dependency

**Pros**:
- ✅ Zero dependencies (only frappe required)
- ✅ Simpler architecture
- ✅ Direct SDK access
- ✅ Faster performance
- ✅ Full control over implementation

**Implementation**:
```python
from mn_payments.sdk import QPayClient, EbarimtClient

# Direct SDK usage
qpay = QPayClient(client_id=..., client_secret=...)
invoice = qpay.create_invoice(amount=10000, ...)

ebarimt = EbarimtClient(pos_no=..., merchant_tin=...)
receipt = ebarimt.create_receipt(items=[...])
```

### Option 2: Payments App Integration (Optional)

**Use Case**: Unified payment gateway selection alongside Stripe, PayTM, etc.

**Pros**:
- ✅ Consistent UI for gateway selection
- ✅ Unified payment request workflow
- ✅ Standardized settings management
- ✅ Familiar for users of payments app

**Cons**:
- ❌ Adds dependency on payments app
- ❌ More complex architecture
- ❌ Requires adapter layer

**Implementation**: See below

## How to Integrate with Payments App

If you want to add QPay/Ebarimt as payment gateway options in the payments app:

### Step 1: Create Gateway Settings DocType

Create `QPay Settings` similar to `Stripe Settings`:

```python
# mn_payments/mn_payments/doctype/qpay_settings/qpay_settings.py

from frappe.model.document import Document
from frappe.integrations.utils import create_request_log
from payments.utils import create_payment_gateway
import frappe

class QPaySettings(Document):
    supported_currencies = ["MNT", "USD", "CNY"]
    
    def on_update(self):
        """Create/update payment gateway record"""
        create_payment_gateway(
            "QPay",
            settings="QPay Settings",
            controller=self.name
        )
    
    def validate_transaction_currency(self, currency):
        """Validate if currency is supported"""
        if currency not in self.supported_currencies:
            frappe.throw(
                f"Currency {currency} not supported. "
                f"Supported: {', '.join(self.supported_currencies)}"
            )
    
    def get_payment_url(self, **kwargs):
        """Generate payment URL for Payment Request"""
        from mn_payments.sdk import QPayClient
        
        # Initialize client
        client = QPayClient(
            client_id=self.client_id,
            client_secret=self.get_password("client_secret"),
            invoice_code=self.invoice_code,
            version=self.api_version or "v2"
        )
        
        # Create invoice
        response = client.create_invoice(
            amount=kwargs.get("amount"),
            description=kwargs.get("description"),
            callback_url=kwargs.get("callback_url")
        )
        
        # Log request
        create_request_log(
            kwargs, 
            service_name="QPay",
            name=response.invoice_id
        )
        
        # Save to database
        invoice_doc = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": response.invoice_id,
            "amount": response.amount,
            "currency": kwargs.get("currency", "MNT"),
            "qr_text": response.qr_text,
            "qr_image": response.qr_image,
            "invoice_status": "PENDING"
        })
        invoice_doc.insert(ignore_permissions=True)
        
        # Return primary payment URL
        return response.urls[0].link if response.urls else response.qr_text
```

### Step 2: Create Settings JSON Schema

```json
// qpay_settings.json
{
  "creation": "2025-11-18 14:00:00",
  "doctype": "DocType",
  "engine": "InnoDB",
  "field_order": [
    "client_id",
    "client_secret",
    "invoice_code",
    "api_version",
    "is_active"
  ],
  "fields": [
    {
      "fieldname": "client_id",
      "fieldtype": "Data",
      "label": "Client ID",
      "reqd": 1
    },
    {
      "fieldname": "client_secret",
      "fieldtype": "Password",
      "label": "Client Secret",
      "reqd": 1
    },
    {
      "fieldname": "invoice_code",
      "fieldtype": "Data",
      "label": "Invoice Code",
      "reqd": 1
    },
    {
      "fieldname": "api_version",
      "fieldtype": "Select",
      "label": "API Version",
      "options": "v1\nv2\nquick",
      "default": "v2"
    },
    {
      "fieldname": "is_active",
      "fieldtype": "Check",
      "label": "Is Active",
      "default": 1
    }
  ],
  "is_submittable": 0,
  "modified": "2025-11-18 14:00:00",
  "module": "MN Payments",
  "name": "QPay Settings",
  "owner": "Administrator"
}
```

### Step 3: Create Payment Integration Module

```python
# mn_payments/payment_gateways/qpay_integration.py

import frappe
from frappe import _
from frappe.integrations.utils import create_request_log
from mn_payments.sdk import QPayClient


def create_qpay_payment(gateway_controller, data):
    """
    Create QPay payment (called by payments app)
    
    Args:
        gateway_controller: Name of QPay Settings doc
        data: Payment request data
        
    Returns:
        dict: Payment response with redirect URL
    """
    qpay_settings = frappe.get_doc("QPay Settings", gateway_controller)
    qpay_settings.data = frappe._dict(data)
    
    try:
        # Create integration request log
        qpay_settings.integration_request = create_request_log(
            qpay_settings.data, 
            "Host", 
            "QPay"
        )
        
        # Create payment
        return create_payment_on_qpay(qpay_settings)
        
    except Exception as e:
        qpay_settings.log_error(f"QPay payment failed: {str(e)}")
        return {
            "redirect_to": frappe.redirect_to_message(
                _("Payment Error"),
                _(f"QPay payment creation failed: {str(e)}")
            ),
            "status": 401
        }


def create_payment_on_qpay(qpay_settings):
    """Create invoice on QPay"""
    # Initialize client
    client = QPayClient(
        client_id=qpay_settings.client_id,
        client_secret=qpay_settings.get_password("client_secret"),
        invoice_code=qpay_settings.invoice_code,
        version=qpay_settings.api_version
    )
    
    # Create invoice
    response = client.create_invoice(
        amount=float(qpay_settings.data.amount),
        description=qpay_settings.data.description or "Payment",
        callback_url=qpay_settings.data.get("callback_url")
    )
    
    # Save invoice to database
    invoice_doc = frappe.get_doc({
        "doctype": "QPay Invoice",
        "invoice_id": response.invoice_id,
        "amount": response.amount,
        "currency": qpay_settings.data.get("currency", "MNT"),
        "qr_text": response.qr_text,
        "qr_image": response.qr_image,
        "invoice_status": "PENDING",
        "reference_doctype": qpay_settings.data.reference_doctype,
        "reference_docname": qpay_settings.data.reference_docname
    })
    invoice_doc.insert(ignore_permissions=True)
    
    # Update integration request
    qpay_settings.integration_request.db_set(
        "status", 
        "Pending", 
        update_modified=False
    )
    
    # Return payment URL
    return {
        "redirect_to": response.urls[0].link if response.urls else None,
        "status": 200,
        "invoice_id": response.invoice_id
    }
```

### Step 4: Create Webhook Handler

```python
# mn_payments/api/webhooks.py

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def qpay_webhook():
    """Handle QPay payment callback"""
    try:
        data = frappe.request.get_json()
        invoice_id = data.get("invoice_id")
        payment_status = data.get("payment_status")
        
        # Update invoice status
        invoice = frappe.get_doc("QPay Invoice", invoice_id)
        invoice.invoice_status = payment_status
        
        if payment_status == "PAID":
            invoice.paid_date = frappe.utils.now()
            
            # Update integration request
            if invoice.reference_doctype and invoice.reference_docname:
                payment_request = frappe.get_doc(
                    invoice.reference_doctype,
                    invoice.reference_docname
                )
                
                # Mark as paid
                payment_request.run_method("on_payment_authorized", payment_status)
        
        invoice.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        frappe.log_error(f"QPay webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}
```

### Step 5: Register in hooks.py

```python
# mn_payments/hooks.py

# Payment Gateway Integration (optional)
# Uncomment to enable payments app integration

# payment_gateway_enabled = "QPay"
# 
# before_install = "mn_payments.setup.install.before_install"
# 
# def before_install():
#     from payments.utils import create_payment_gateway
#     create_payment_gateway(
#         "QPay",
#         settings="QPay Settings",
#         controller="QPay-MNT"
#     )
```

## Usage Examples

### With Payments App Integration

```python
# In ERPNext Sales Invoice or Payment Request
payment_gateway = frappe.get_doc({
    "doctype": "Payment Gateway",
    "gateway": "QPay",
    "settings": "QPay Settings",
    "controller": "QPay-MNT"
})

# Create payment request
payment_request = frappe.get_doc({
    "doctype": "Payment Request",
    "payment_gateway": "QPay",
    "amount": 50000,
    "currency": "MNT",
    "reference_doctype": "Sales Invoice",
    "reference_name": "SINV-2025-00001"
})
payment_request.insert()

# Get payment URL
payment_url = payment_request.get_payment_url()
```

### Standalone Usage (Recommended)

```python
# Direct SDK usage - simpler and more flexible
from mn_payments.sdk import QPayClient

qpay = QPayClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_SECRET",
    invoice_code="TEST_CODE"
)

# Create invoice
response = qpay.create_invoice(
    amount=50000,
    description="Sales Invoice SINV-2025-00001"
)

# Save to database
frappe.get_doc({
    "doctype": "QPay Invoice",
    "invoice_id": response.invoice_id,
    "amount": response.amount,
    "invoice_status": "PENDING"
}).insert()
```

## Decision Matrix

| Feature | Standalone | With Payments App |
|---------|-----------|-------------------|
| **Dependencies** | frappe only | frappe + payments |
| **Complexity** | Simple | Moderate |
| **Flexibility** | High | Medium |
| **UI Integration** | Custom | Standardized |
| **Performance** | Faster | Slight overhead |
| **Maintenance** | Lower | Higher |
| **Use Case** | Mongolia-specific apps | Multi-gateway apps |

## Recommendation

### Use Standalone (Current) When:
- ✅ Building Mongolia-specific application
- ✅ Only need QPay/Ebarimt
- ✅ Want maximum performance
- ✅ Prefer simpler architecture
- ✅ Don't need payments app features

### Integrate with Payments App When:
- ✅ Building international app with multiple gateways
- ✅ Need unified gateway selection UI
- ✅ Want standardized payment request workflow
- ✅ Already using payments app for Stripe/PayTM
- ✅ Need payment gateway abstraction layer

## Current Status

**mn_payments is currently standalone** (Option 1) and does NOT require the payments app. This is the **recommended approach** for most use cases.

If you need payments app integration later, you can add it without breaking existing code by:
1. Creating QPay Settings DocType
2. Adding payment integration module
3. Keeping SDK as the core engine

The SDK will remain the foundation either way! 🎉
