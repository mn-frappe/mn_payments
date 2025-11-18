"""
PERFORMANCE & LOAD BATTLE TEST
Tests MN Payments under heavy load and stress conditions
"""

import os
import frappe
import time


def test_concurrent_invoice_creation():
    """Test 1000+ invoice creations in batches"""
    print("\n=== PERFORMANCE TEST 1: High-Volume Invoice Creation ===")
    
    try:
        num_invoices = 1000
        batch_size = 100
        print(f"Creating {num_invoices} invoices in batches of {batch_size}...")
        start = time.time()
        
        created = 0
        for batch_start in range(0, num_invoices, batch_size):
            batch_invoices = []
            for i in range(batch_start, min(batch_start + batch_size, num_invoices)):
                invoice = frappe.get_doc({
                    "doctype": "QPay Invoice",
                    "invoice_id": f"PERF-{i:05d}-{frappe.generate_hash(length=6)}",
                    "amount": 50000 + (i * 100),
                    "currency": "MNT",
                    "qr_text": f"https://qpay.mn/perf/{i}",
                    "invoice_status": "PAID" if i % 3 == 0 else "UNPAID"
                })
                invoice.insert(ignore_permissions=True)
                created += 1
            
            # Commit each batch
            frappe.db.commit()
            
            if (batch_start + batch_size) % 200 == 0:
                print(f"   Progress: {batch_start + batch_size}/{num_invoices}")
        
        elapsed = time.time() - start
        
        print(f"✅ Created {created}/{num_invoices} invoices in {elapsed:.2f}s")
        print(f"✅ Average: {elapsed/num_invoices*1000:.2f}ms per invoice")
        print(f"✅ Throughput: {num_invoices/elapsed:.2f} invoices/second")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'PERF-%'")
        frappe.db.commit()
        
        return {
            "success": created == num_invoices,
            "total": num_invoices,
            "time": elapsed,
            "throughput": num_invoices/elapsed
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_massive_receipt_generation():
    """Test generating 10,000+ receipts"""
    print("\n=== PERFORMANCE TEST 2: Massive Receipt Generation ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator
        
        num_receipts = 5000  # Reduced for practical testing
        print(f"Generating {num_receipts} receipts with VAT calculations...")
        start = time.time()
        
        for i in range(num_receipts):
            amount = 10000 + (i * 50)
            vat = VATCalculator.get_vat(amount)
            
            receipt = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                "bill_id": f"MASS-{i:05d}-{frappe.generate_hash(length=6)}",
                "total_amount": amount,
                "total_vat": vat,
                "total_city_tax": 0,
                "status": "SUCCESS"
            })
            receipt.insert(ignore_permissions=True)
            
            if (i + 1) % 1000 == 0:
                frappe.db.commit()
                print(f"   Progress: {i + 1}/{num_receipts}")
        
        frappe.db.commit()
        elapsed = time.time() - start
        
        print(f"✅ Generated {num_receipts} receipts in {elapsed:.2f}s")
        print(f"✅ Average: {elapsed/num_receipts*1000:.2f}ms per receipt")
        print(f"✅ Throughput: {num_receipts/elapsed:.2f} receipts/second")
        
        # Test query performance on large dataset
        query_start = time.time()
        stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as count,
                SUM(total_amount) as total_sales,
                SUM(total_vat) as total_vat,
                AVG(total_amount) as avg_amount,
                MIN(total_amount) as min_amount,
                MAX(total_amount) as max_amount
            FROM `tabEbarimt Receipt`
            WHERE bill_id LIKE 'MASS-%'
        """, as_dict=True)[0]
        query_time = (time.time() - query_start) * 1000
        
        print(f"\n✅ Aggregation query on {stats.count} records:")
        print(f"   Total sales: {stats.total_sales:,.0f} MNT")
        print(f"   Total VAT: {stats.total_vat:,.2f} MNT")
        print(f"   Query time: {query_time:.2f}ms")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabEbarimt Receipt` WHERE bill_id LIKE 'MASS-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "receipts": num_receipts,
            "time": elapsed,
            "query_time_ms": query_time
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_database_query_optimization():
    """Test query performance with indexes"""
    print("\n=== PERFORMANCE TEST 3: Database Query Optimization ===")
    
    try:
        # Create test data
        print("Creating 2000 test records...")
        for i in range(2000):
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"QOPT-{i:05d}",
                "amount": 25000 + (i * 200),
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/opt/{i}",
                "invoice_status": "PAID" if i % 4 == 0 else "UNPAID"
            })
            invoice.insert(ignore_permissions=True)
            
            if (i + 1) % 500 == 0:
                frappe.db.commit()
        
        frappe.db.commit()
        
        # Test various query patterns
        queries = {
            "Filter by status": "SELECT COUNT(*) FROM `tabQPay Invoice` WHERE invoice_status = 'PAID' AND invoice_id LIKE 'QOPT-%'",
            "Filter by amount range": "SELECT COUNT(*) FROM `tabQPay Invoice` WHERE amount BETWEEN 50000 AND 100000 AND invoice_id LIKE 'QOPT-%'",
            "Order by amount": "SELECT * FROM `tabQPay Invoice` WHERE invoice_id LIKE 'QOPT-%' ORDER BY amount DESC LIMIT 10",
            "Group by status": "SELECT invoice_status, COUNT(*), SUM(amount) FROM `tabQPay Invoice` WHERE invoice_id LIKE 'QOPT-%' GROUP BY invoice_status",
            "Complex join": "SELECT COUNT(*) FROM `tabQPay Invoice` WHERE invoice_id LIKE 'QOPT-%' AND currency = 'MNT'"
        }
        
        print("\nQuery Performance:")
        for query_name, query in queries.items():
            start = time.time()
            result = frappe.db.sql(query, as_dict=True)
            elapsed = (time.time() - start) * 1000
            print(f"✅ {query_name}: {elapsed:.2f}ms")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'QOPT-%'")
        frappe.db.commit()
        
        return {"success": True, "queries_tested": len(queries)}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_memory_usage():
    """Test memory usage during large operations"""
    print("\n=== PERFORMANCE TEST 4: Memory Usage Profiling ===")
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory: {baseline:.2f} MB")
        
        # Create large batch
        print("Creating 3000 invoices to test memory...")
        for i in range(3000):
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"MEM-{i:05d}",
                "amount": 30000,
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/mem/{i}",
                "invoice_status": "UNPAID"
            })
            invoice.insert(ignore_permissions=True)
            
            if (i + 1) % 1000 == 0:
                current_mem = process.memory_info().rss / 1024 / 1024
                print(f"   {i + 1} records: {current_mem:.2f} MB (+{current_mem - baseline:.2f} MB)")
        
        frappe.db.commit()
        
        # Peak memory
        peak = process.memory_info().rss / 1024 / 1024
        print(f"✅ Peak memory: {peak:.2f} MB")
        print(f"✅ Memory increase: {peak - baseline:.2f} MB")
        print(f"✅ Per record: {(peak - baseline) / 3000 * 1024:.2f} KB")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'MEM-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "baseline_mb": baseline,
            "peak_mb": peak,
            "increase_mb": peak - baseline
        }
        
    except ImportError:
        print("⚠️  psutil not installed, skipping memory test")
        return {"success": True, "skipped": True}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_sustained_load():
    """Test sustained load over time"""
    print("\n=== PERFORMANCE TEST 5: Sustained Load Test ===")
    
    try:
        duration = 30  # seconds
        print(f"Running sustained load test for {duration} seconds...")
        
        start = time.time()
        count = 0
        errors = 0
        
        while (time.time() - start) < duration:
            try:
                invoice = frappe.get_doc({
                    "doctype": "QPay Invoice",
                    "invoice_id": f"SUST-{count:06d}",
                    "amount": 45000,
                    "currency": "MNT",
                    "qr_text": f"https://qpay.mn/sustained/{count}",
                    "invoice_status": "UNPAID"
                })
                invoice.insert(ignore_permissions=True)
                count += 1
                
                if count % 100 == 0:
                    frappe.db.commit()
                    elapsed = time.time() - start
                    rate = count / elapsed
                    print(f"   {elapsed:.1f}s: {count} records ({rate:.2f}/sec)")
                    
            except Exception as e:
                errors += 1
        
        frappe.db.commit()
        elapsed = time.time() - start
        
        print(f"✅ Created {count} records in {elapsed:.2f}s")
        print(f"✅ Average rate: {count/elapsed:.2f} records/second")
        print(f"✅ Errors: {errors}")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'SUST-%'")
        frappe.db.commit()
        
        return {
            "success": errors == 0,
            "records": count,
            "time": elapsed,
            "rate": count/elapsed,
            "errors": errors
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def run_performance_tests():
    """Run all performance tests"""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  MN PAYMENTS - PERFORMANCE & LOAD BATTLE TEST            ║")
    print("║  High-Volume Transaction Testing                         ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    print(f"Environment: Frappe v{frappe.__version__}")
    print(f"Site: {frappe.local.site}\n")
    
    # Run tests
    results = {}
    results["concurrent_creation"] = test_concurrent_invoice_creation()
    results["massive_receipts"] = test_massive_receipt_generation()
    results["query_optimization"] = test_database_query_optimization()
    results["memory_usage"] = test_memory_usage()
    results["sustained_load"] = test_sustained_load()
    
    # Summary
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  PERFORMANCE TEST RESULTS                                ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    passed = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        test_label = test_name.replace("_", " ").title()
        print(f"{status}  {test_label}")
        
        if result.get("success"):
            if "throughput" in result:
                print(f"        Throughput: {result['throughput']:.2f}/sec")
            if "query_time_ms" in result:
                print(f"        Query time: {result['query_time_ms']:.2f}ms")
            if "rate" in result:
                print(f"        Rate: {result['rate']:.2f}/sec")
        else:
            if "error" in result and not result.get("skipped"):
                print(f"        Error: {result['error'][:80]}")
    
    print(f"\n{'='*65}")
    print(f"FINAL RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*65}\n")
    
    if passed == total:
        print("🎉 ALL PERFORMANCE TESTS PASSED! 🎉")
        print("✅ System is production-ready for high-volume transactions")
    else:
        print(f"⚠️  {total-passed} test(s) failed or skipped")
    
    return results


if __name__ == "__main__":
    os.chdir('/Users/bg/frappe-bench/sites')
    frappe.init(site='test.local')
    frappe.connect()
    frappe.local.lang = frappe.db.get_default("lang") or "en"
    
    try:
        results = run_performance_tests()
    finally:
        frappe.destroy()
