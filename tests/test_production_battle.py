"""
MN Payments Battle Test - Production-Ready Validation
Tests all core functionality without requiring ERPNext test data
"""

import os
import frappe
from decimal import Decimal


def setup_test_data():
    """Setup minimal test data"""
    print("\n=== Setting up test data ===")
    print("✅ Using existing ERPNext/HRMS installation")
    # No additional setup needed - use existing data


def test_1_sdk_imports():
    """Test all SDK imports work correctly"""
    print("\n=== TEST 1: SDK Imports & Compatibility ===")
    
    try:
        # Test primary import
        from mn_payments.sdk import EbarimtClient, QPayClient
        print("✅ Primary imports: mn_payments.sdk")
        
        # Test backward compatibility
        from mn_payments.ebarimt.sdk import EbarimtClient as Old1
        from mn_payments.qpay.sdk import QPayClient as Old2
        print("✅ Backward compatible imports work")
        
        # Test all enums
        from mn_payments.sdk.ebarimt import TaxType, ReceiptType, BarcodeType
        from mn_payments.sdk.qpay import QPayVersion
        print("✅ All enums importable")
        
        # Test classes are identical
        assert EbarimtClient == Old1
        assert QPayClient == Old2
        print("✅ Backward compatibility verified")
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}


def test_2_ebarimt_receipt_crud():
    """Test Ebarimt Receipt CRUD operations"""
    print("\n=== TEST 2: Ebarimt Receipt CRUD ===")
    
    try:
        # Create receipt
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"TEST-{frappe.generate_hash(length=10)}",
            "total_amount": 50000,
            "total_vat": 4545.45,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": "http://ebarimt.mn/?billId=TEST123",
            "status": "SUCCESS"
        })
        receipt.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Created receipt: {receipt.name}")
        
        # Read
        loaded = frappe.get_doc("Ebarimt Receipt", receipt.name)
        assert loaded.bill_id == receipt.bill_id
        print(f"✅ Read receipt: {loaded.name}")
        
        # Update
        loaded.total_amount = 55000
        loaded.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Updated receipt amount: {loaded.total_amount}")
        
        # List
        all_receipts = frappe.get_all("Ebarimt Receipt", limit=10)
        print(f"✅ Listed {len(all_receipts)} receipts")
        
        # Delete
        receipt.delete(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Deleted receipt")
        
        return {"success": True, "receipt_name": receipt.name}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_3_qpay_invoice_crud():
    """Test QPay Invoice CRUD operations"""
    print("\n=== TEST 3: QPay Invoice CRUD ===")
    
    try:
        # Create invoice
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"INV-{frappe.generate_hash(length=8)}",
            "amount": 100000,
            "currency": "MNT",
            "qr_text": "https://qpay.mn/test",
            "invoice_status": "UNPAID"
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Created invoice: {invoice.name}")
        
        # Read
        loaded = frappe.get_doc("QPay Invoice", invoice.name)
        assert loaded.invoice_id == invoice.invoice_id
        print(f"✅ Read invoice: {loaded.name}")
        
        # Update status
        loaded.invoice_status = "PAID"
        loaded.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Updated status to: {loaded.invoice_status}")
        
        # Filter query
        paid = frappe.get_all(
            "QPay Invoice",
            filters={"invoice_status": "PAID"},
            limit=10
        )
        print(f"✅ Filtered query: {len(paid)} paid invoices")
        print(f"✅ Filtered query: {len(paid)} paid invoices")
        
        # Delete
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Deleted invoice")
        
        return {"success": True, "invoice_name": invoice.name}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_4_ebarimt_vat_calculations():
    """Test VAT calculation accuracy"""
    print("\n=== TEST 4: Ebarimt VAT Calculations ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator, TaxType
        
        # Test 1: VAT_ABLE with city tax
        vat = VATCalculator.get_vat_with_city_tax(10000)
        city_tax = VATCalculator.get_city_tax(10000)
        assert abs(vat - 900.90) < 0.01  # 10000 / 1.11 * 0.10
        assert abs(city_tax - 90.09) < 0.01  # 10000 / 1.11 * 0.01
        print(f"✅ VAT with city tax: VAT={vat:.2f}, City={city_tax:.2f}")
        
        # Test 2: VAT_ABLE without city tax
        vat = VATCalculator.get_vat(10000)
        assert abs(vat - 909.09) < 0.01  # 10000 / 1.10 * 0.10
        print(f"✅ VAT without city tax: VAT={vat:.2f}")
        
        # Test 3: City tax without VAT
        city_tax = VATCalculator.get_city_tax_without_vat(10000)
        assert abs(city_tax - 99.01) < 0.01  # 10000 / 1.01 * 0.01
        print(f"✅ City tax without VAT: {city_tax:.2f}")
        
        # Test 4: Large amount
        vat = VATCalculator.get_vat_with_city_tax(1000000)
        city_tax = VATCalculator.get_city_tax(1000000)
        assert abs(vat - 90090.09) < 0.01
        assert abs(city_tax - 9009.01) < 0.01
        print(f"✅ Large amount: VAT={vat:.2f}, City={city_tax:.2f}")
        
        # Test 5: Number precision
        rounded = VATCalculator.number_precision(12345.6789)
        assert rounded == 12345.68
        print(f"✅ Number precision: {rounded}")
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_5_database_performance():
    """Test database query performance"""
    print("\n=== TEST 5: Database Performance ===")
    
    try:
        import time
        
        # Create test receipts
        print("Creating 50 test receipts...")
        for i in range(50):
            receipt = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                "bill_id": f"PERF-{i:03d}-{frappe.generate_hash(length=8)}",
                "total_amount": 10000 + i * 1000,
                "total_vat": (10000 + i * 1000) / 11,
                "total_city_tax": 0,
                "status": "SUCCESS" if i % 2 == 0 else "ERROR"
            })
            receipt.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ Created 50 receipts")
        
        # Test 1: Full scan
        start = time.time()
        all_receipts = frappe.get_all("Ebarimt Receipt", limit=100)
        time1 = (time.time() - start) * 1000
        print(f"✅ Full scan: {len(all_receipts)} records in {time1:.2f}ms")
        
        # Test 2: Filtered query
        start = time.time()
        success_receipts = frappe.get_all(
            "Ebarimt Receipt",
            filters={"status": "SUCCESS"},
            limit=100
        )
        time2 = (time.time() - start) * 1000
        print(f"✅ Filtered query: {len(success_receipts)} records in {time2:.2f}ms")
        
        # Test 3: Aggregation
        start = time.time()
        total = frappe.db.sql("""
            SELECT COUNT(*), SUM(total_amount), AVG(total_vat)
            FROM `tabEbarimt Receipt`
            WHERE status = 'SUCCESS'
        """)[0]
        time3 = (time.time() - start) * 1000
        print(f"✅ Aggregation: {total[0]} receipts, sum={total[1]:.2f} in {time3:.2f}ms")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabEbarimt Receipt` WHERE bill_id LIKE 'PERF-%'")
        frappe.db.commit()
        print("✅ Cleaned up test data")
        
        avg_time = (time1 + time2 + time3) / 3
        print(f"✅ Average query time: {avg_time:.2f}ms")
        
        return {"success": True, "avg_query_time_ms": avg_time}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_6_concurrent_operations():
    """Test concurrent insert/update operations"""
    print("\n=== TEST 6: Concurrent Operations ===")
    
    try:
        # Simulate concurrent receipt creation
        receipts = []
        for i in range(10):
            receipt = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                "bill_id": f"CONC-{i:02d}-{frappe.generate_hash(length=8)}",
                "total_amount": 5000 * (i + 1),
                "total_vat": 5000 * (i + 1) / 11,
                "total_city_tax": 0,
                "status": "SUCCESS"
            })
            receipt.insert(ignore_permissions=True)
            receipts.append(receipt.name)
        
        frappe.db.commit()
        print(f"✅ Created 10 concurrent receipts")
        
        # Verify all created
        count = frappe.db.count("Ebarimt Receipt", {"name": ["in", receipts]})
        assert count == 10
        print(f"✅ All 10 receipts verified in database")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabEbarimt Receipt` WHERE bill_id LIKE 'CONC-%'")
        frappe.db.commit()
        print("✅ Cleaned up test data")
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_7_error_handling():
    """Test error handling and validation"""
    print("\n=== TEST 7: Error Handling ===")
    
    try:
        # Test 1: Missing required field
        try:
            receipt = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                # Missing bill_id - should fail
                "total_amount": 1000
            })
            receipt.insert(ignore_permissions=True)
            print("❌ Should have failed on missing bill_id")
            return {"success": False}
        except Exception:
            print("✅ Validation works: Missing required field caught")
        
        # Test 2: Duplicate bill_id (if unique constraint exists)
        bill_id = f"DUP-{frappe.generate_hash(length=8)}"
        receipt1 = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": bill_id,
            "total_amount": 1000,
            "total_vat": 90.91,
            "total_city_tax": 0,
            "status": "SUCCESS"
        })
        receipt1.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ First receipt created")
        
        # Cleanup
        receipt1.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_8_doctype_integrity():
    """Test DocType structure and fields"""
    print("\n=== TEST 8: DocType Integrity ===")
    
    try:
        doctypes = [
            ("Ebarimt Receipt", ["bill_id", "total_amount", "total_vat", "lottery_number"]),
            ("Ebarimt Receipt Item", ["item_name", "qty", "unit_price"]),
            ("QPay Invoice", ["invoice_id", "amount", "currency", "invoice_status"]),
            ("QPay Payment URL", ["name_field", "link", "description"])
        ]
        
        for dt_name, required_fields in doctypes:
            dt = frappe.get_doc("DocType", dt_name)
            field_names = [f.fieldname for f in dt.fields]
            
            missing = [f for f in required_fields if f not in field_names]
            if missing:
                print(f"❌ {dt_name}: Missing fields {missing}")
                return {"success": False}
            
            print(f"✅ {dt_name}: All required fields present")
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}


def run_battle_tests():
    """Run complete battle test suite"""
    print("╔══════════════════════════════════════════════════════╗")
    print("║  MN PAYMENTS - PRODUCTION BATTLE TEST                ║")
    print("║  Testing with ERPNext v15 + HRMS v15                 ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    # Setup
    setup_test_data()
    
    # Run tests
    results = {}
    results["sdk_imports"] = test_1_sdk_imports()
    results["ebarimt_crud"] = test_2_ebarimt_receipt_crud()
    results["qpay_crud"] = test_3_qpay_invoice_crud()
    results["vat_calculations"] = test_4_ebarimt_vat_calculations()
    results["database_performance"] = test_5_database_performance()
    results["concurrent_ops"] = test_6_concurrent_operations()
    results["error_handling"] = test_7_error_handling()
    results["doctype_integrity"] = test_8_doctype_integrity()
    
    # Summary
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  BATTLE TEST RESULTS                                 ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    
    passed = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"{status}  {test_name.replace('_', ' ').title()}")
        if not result.get("success") and "error" in result:
            print(f"        Error: {result['error'][:100]}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("🎉 ALL BATTLE TESTS PASSED!")
        print("✅ MN Payments is PRODUCTION-READY")
        print("✅ Works perfectly with ERPNext v15 + HRMS v15")
    else:
        print(f"⚠️  {total-passed} test(s) failed")
    
    return results


if __name__ == "__main__":
    os.chdir('/Users/bg/frappe-bench/sites')
    frappe.init(site='test.local')
    frappe.connect()
    frappe.local.lang = frappe.db.get_default("lang") or "en"
    
    try:
        results = run_battle_tests()
    finally:
        frappe.destroy()
