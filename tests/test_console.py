#!/usr/bin/env python3
"""
Battle Test Suite for mn_payments App - Bench Console Version
Run with: bench --site test.local console < test_console.py
"""

print("="*80)
print("🔥 MN PAYMENTS APP - BATTLE TEST SUITE")
print("="*80)

# Test 1: Verify installation
print("\nTEST 1: Verify Installation")
print("-"*80)
try:
    import frappe
    apps = frappe.get_installed_apps()
    assert 'mn_payments' in apps
    print(f"✅ Apps installed: {', '.join(apps)}")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: SDK Imports
print("\nTEST 2: SDK Imports")
print("-"*80)
try:
    from mn_payments.sdk import EbarimtClient, QPayClient
    from mn_payments.sdk.ebarimt import TaxType, ReceiptType, BarcodeType
    from mn_payments.sdk.qpay import QPayVersion
    print("✅ New import paths work")
    
    # Backward compatibility
    from mn_payments.ebarimt.sdk import EbarimtClient as OldEbarimt
    from mn_payments.qpay.sdk import QPayClient as OldQPay
    assert OldEbarimt is EbarimtClient
    assert OldQPay is QPayClient
    print("✅ Backward compatibility works")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: VAT Calculations
print("\nTEST 3: VAT Calculations")
print("-"*80)
try:
    from mn_payments.sdk.ebarimt import VATCalculator
    from decimal import Decimal
    
    # Test VAT calculation (10%)
    vat = VATCalculator.get_vat(10000.0)
    assert abs(vat - 909.09) < 0.01, f"VAT incorrect: {vat}"
    print(f"✅ VAT calculation: 10000 → VAT={vat}")
    
    # Test city tax (1%)
    city_tax = VATCalculator.get_city_tax(10000.0)
    assert abs(city_tax - 90.09) < 0.01, f"City tax incorrect: {city_tax}"
    print(f"✅ City tax: 10000 → {city_tax}")
    
    # Test VAT + City Tax
    vat_with_city = VATCalculator.get_vat_with_city_tax(10000.0)
    assert abs(vat_with_city - 900.90) < 0.01, f"VAT with city incorrect: {vat_with_city}"
    print(f"✅ VAT with city tax: 10000 → {vat_with_city}")
    
    print("✅ All VAT calculations correct")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 4: DocType Checks
print("\nTEST 4: DocType Availability")
print("-"*80)
try:
    import frappe
    doctypes = ['Ebarimt Receipt', 'Ebarimt Receipt Item', 'QPay Invoice', 'QPay Payment URL']
    for dt in doctypes:
        exists = frappe.db.exists("DocType", dt)
        if exists:
            print(f"✅ {dt}")
        else:
            print(f"❌ {dt} NOT FOUND")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 5: Create Test Receipt
print("\nTEST 5: Create Test Receipt")
print("-"*80)
try:
    import frappe
    frappe.set_user("Administrator")
    
    receipt = frappe.get_doc({
        "doctype": "Ebarimt Receipt",
        "pos_no": "TEST123",
        "bill_id": f"TEST_{frappe.utils.now()}",
        "lottery_number": "ABC12345",
        "total_amount": 10000.0,
        "total_vat": 909.09,
        "total_city_tax": 99.10,
        "qr_data": "TEST_QR_DATA"
    })
    receipt.insert(ignore_permissions=True)
    print(f"✅ Receipt created: {receipt.name}")
    
    # Verify
    saved = frappe.get_doc("Ebarimt Receipt", receipt.name)
    assert saved.total_amount == 10000.0
    print(f"✅ Receipt verified: amount={saved.total_amount}")
    
    # Cleanup
    frappe.db.rollback()
    print("✅ Test data rolled back")
except Exception as e:
    frappe.db.rollback()
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 6: QR Code Generation
print("\nTEST 6: QR Code Generation")
print("-"*80)
try:
    import qrcode
    from io import BytesIO
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data("TEST_QR_12345")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    assert len(buffer.getvalue()) > 0
    print(f"✅ QR code generated: {len(buffer.getvalue())} bytes")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 7: Performance Test
print("\nTEST 7: Performance Test")
print("-"*80)
try:
    import time
    from mn_payments.sdk.ebarimt import VATCalculator
    
    start = time.time()
    for i in range(1000):
        vat = VATCalculator.get_vat(10000.0)
    duration = time.time() - start
    
    per_calc = (duration / 1000) * 1000  # ms
    print(f"✅ 1000 VAT calculations: {duration:.2f}s ({per_calc:.3f}ms each)")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Summary
print("\n" + "="*80)
print("✅ BATTLE TEST COMPLETE!")
print("="*80)
print("\nRun unit tests with:")
print("bench --site test.local run-tests --module mn_payments.sdk.test_ebarimt")
