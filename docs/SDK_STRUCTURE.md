# SDK Structure Comparison

## ✅ Hybrid Approach - IMPLEMENTED

### New Directory Structure
```
mn_payments/
├── sdk/                          # 📦 Standalone SDK Package
│   ├── __init__.py              # ✨ Public API (new)
│   ├── ebarimt.py               # Moved from ebarimt/sdk.py
│   ├── qpay.py                  # Moved from qpay/sdk.py
│   ├── test_ebarimt.py          # Moved from ebarimt/test_sdk.py
│   └── README.md                # SDK-specific docs
│
├── ebarimt/
│   └── sdk.py                   # 🔄 Compatibility layer (re-exports)
│
├── qpay/
│   └── sdk.py                   # 🔄 Compatibility layer (re-exports)
│
└── mn_payments/
    └── doctype/                  # Frappe DocTypes
        ├── ebarimt_receipt/
        ├── ebarimt_receipt_item/
        ├── qpay_invoice/
        └── qpay_payment_url/
```

### Import Paths (Both Work!)

```python
# ✨ NEW - Recommended
from mn_payments.sdk import (
    EbarimtClient,
    QPayClient,
    ReceiptItem,
    InvoiceRequest,
    TaxType,
    VATCalculator
)

# 🔄 OLD - Still works (backward compatible)
from mn_payments.ebarimt.sdk import EbarimtClient
from mn_payments.qpay.sdk import QPayClient
```

## Benefits

### 1. Clean Public API ✨
```python
# Before: Multiple import paths
from mn_payments.ebarimt.sdk import EbarimtClient
from mn_payments.qpay.sdk import QPayClient
from mn_payments.ebarimt.sdk import TaxType, VATCalculator

# After: Single unified import
from mn_payments.sdk import (
    EbarimtClient,
    QPayClient,
    TaxType,
    VATCalculator
)
```

### 2. PyPI Ready 📦
```bash
# Future: Can publish SDK separately
pip install mn-payments-sdk

# Use without Frappe
from mn_payments.sdk import EbarimtClient
```

### 3. Backward Compatible 🔄
```python
# Old code continues to work
from mn_payments.ebarimt.sdk import EbarimtClient  # ✅ Works
from mn_payments.sdk import EbarimtClient          # ✅ Works
```

### 4. Modular Imports 🔧
```python
# Import entire SDK
import mn_payments.sdk as mps
client = mps.EbarimtClient(...)

# Import specific modules
from mn_payments.sdk.ebarimt import EbarimtClient
from mn_payments.sdk.qpay import QPayClient
```

## File Size Impact

| Component | Size |
|-----------|------|
| SDK Total | 40KB |
| ebarimt.py | 22KB |
| qpay.py | 18KB |
| Compatibility layers | 2KB |
| **Total Added** | **42KB** |

**Impact**: Negligible (42KB / 464KB = 9% increase)

## Usage Examples

### As Frappe App (Current Use)
```python
from mn_payments.sdk import EbarimtClient

client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890",
    enable_db=True,      # Frappe database integration
    enable_email=True    # Frappe email system
)
```

### As Standalone SDK (Future)
```python
# Without Frappe - just the SDK
from mn_payments.sdk import EbarimtClient

client = EbarimtClient(
    base_url="https://api.ebarimt.mn",
    pos_no="POS12345",
    merchant_tin="1234567890"
    # enable_db and enable_email require Frappe
)
```

## Migration Path

### Phase 1: Now ✅
- ✅ SDK in `sdk/` directory
- ✅ Compatibility layers maintain old imports
- ✅ New imports available
- ✅ Zero breaking changes

### Phase 2: Future (Optional)
- Extract SDK to separate package
- Publish to PyPI as `mn-payments-sdk`
- Update app to depend on published package

### Phase 3: Cleanup (Optional)
- Deprecate old import paths
- Remove compatibility layers
- Use only `mn_payments.sdk` imports

## Comparison Table

| Aspect | Before | Hybrid Approach |
|--------|--------|-----------------|
| Import Path | `mn_payments.ebarimt.sdk` | `mn_payments.sdk` |
| Single Import | ❌ No | ✅ Yes |
| PyPI Ready | ❌ No | ✅ Yes |
| Backward Compatible | N/A | ✅ Yes |
| App Size | 464KB | 506KB (+9%) |
| Standalone Use | ❌ No | ✅ Yes (future) |
| Breaking Changes | N/A | ✅ Zero |

## Testing Compatibility

```python
# Test both import methods work
def test_imports():
    # New method
    from mn_payments.sdk import EbarimtClient as Client1
    
    # Old method (compatibility)
    from mn_payments.ebarimt.sdk import EbarimtClient as Client2
    
    # Both should be the same class
    assert Client1 is Client2
    print("✅ Both import paths work!")

# Test SDK works standalone
def test_standalone():
    from mn_payments.sdk import VATCalculator
    
    vat = VATCalculator.get_vat(10000.0)
    assert abs(vat - 909.09) < 0.01
    print("✅ SDK works standalone!")
```

## Future: Publishing to PyPI

### Step 1: Create Package Structure
```bash
mn-payments-sdk/
├── setup.py
├── README.md
├── LICENSE
└── mn_payments/
    └── sdk/
        ├── __init__.py
        ├── ebarimt.py
        └── qpay.py
```

### Step 2: Setup.py
```python
setup(
    name="mn-payments-sdk",
    version="1.0.0",
    packages=["mn_payments.sdk"],
    install_requires=[
        "requests>=2.31.0",
        "qrcode[pil]>=7.4.2",
        "python-barcode>=0.15.1",
    ],
)
```

### Step 3: Publish
```bash
python setup.py sdist bdist_wheel
twine upload dist/*
```

### Step 4: Users Install
```bash
# Standalone usage
pip install mn-payments-sdk

# In any Python project
from mn_payments.sdk import EbarimtClient
```

## Conclusion

The hybrid approach provides:
- ✅ **Clean API**: Single import point
- ✅ **Future-proof**: PyPI ready
- ✅ **Backward compatible**: Zero breaking changes
- ✅ **Minimal overhead**: +42KB (9% increase)
- ✅ **Flexibility**: Use standalone or with Frappe

**Best of both worlds!** 🎉
