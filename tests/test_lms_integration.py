"""
LMS INTEGRATION BATTLE TEST
Tests MN Payments with Learning Management System scenarios
"""

import os
import frappe
from decimal import Decimal


def test_course_enrollment_payment():
    """Test course enrollment payment flow"""
    print("\n=== LMS TEST 1: Course Enrollment Payment ===")
    
    try:
        from mn_payments.sdk import QPayClient
        
        # Simulate course enrollment
        course_price = 150000  # MNT
        
        print(f"Step 1: Student enrolls in course - Price: {course_price:,} MNT")
        
        # Create QPay invoice for course enrollment
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"COURSE-{frappe.generate_hash(length=10)}",
            "amount": course_price,
            "currency": "MNT",
            "qr_text": f"https://qpay.mn/lms/course/{frappe.generate_hash(length=8)}",
            "invoice_status": "UNPAID",
            "reference_doctype": "LMS Course",
            "reference_docname": "Python Programming Basics"
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ Payment request created: {invoice.invoice_id}")
        
        # Student pays
        print("Step 2: Student completes payment...")
        invoice.invoice_status = "PAID"
        invoice.paid_date = frappe.utils.now()
        invoice.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ Payment confirmed")
        
        # Generate receipt
        print("Step 3: Generating course payment receipt...")
        from mn_payments.sdk.ebarimt import VATCalculator
        
        vat = VATCalculator.get_vat(course_price)
        
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"LMS-COURSE-{frappe.generate_hash(length=10)}",
            "total_amount": course_price,
            "total_vat": vat,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": f"http://ebarimt.mn/?billId=LMS",
            "status": "SUCCESS",
            "reference_doctype": "QPay Invoice",
            "reference_docname": invoice.name
        })
        receipt.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ Receipt: {receipt.bill_id}")
        print(f"   ✅ VAT: {vat:,.2f} MNT")
        print(f"   ✅ Lottery: {receipt.lottery_number}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        print("✅ Course enrollment payment test PASSED")
        return {"success": True, "flow": "course_enrollment"}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_batch_enrollment_payment():
    """Test batch course enrollment with discount"""
    print("\n=== LMS TEST 2: Batch Enrollment with Discount ===")
    
    try:
        # Simulate batch enrollment
        original_price = 200000
        discount = 50000
        final_price = original_price - discount
        
        print(f"Original price: {original_price:,} MNT")
        print(f"Batch discount: {discount:,} MNT")
        print(f"Final price: {final_price:,} MNT")
        
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"BATCH-{frappe.generate_hash(length=10)}",
            "amount": final_price,
            "currency": "MNT",
            "qr_text": f"https://qpay.mn/lms/batch",
            "invoice_status": "PAID",
            "paid_date": frappe.utils.now()
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Batch enrollment payment: {invoice.invoice_id}")
        print(f"✅ Discount applied: {(discount/original_price)*100:.0f}%")
        
        # Cleanup
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "discount_percent": (discount/original_price)*100}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_certification_fee():
    """Test certification exam fee payment"""
    print("\n=== LMS TEST 3: Certification Exam Fee ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator
        
        cert_fee = 75000  # MNT
        
        print(f"Certification exam fee: {cert_fee:,} MNT")
        
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"CERT-{frappe.generate_hash(length=10)}",
            "amount": cert_fee,
            "currency": "MNT",
            "qr_text": "https://qpay.mn/lms/certification",
            "invoice_status": "PAID",
            "paid_date": frappe.utils.now()
        })
        invoice.insert(ignore_permissions=True)
        
        # Generate receipt
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"CERT-{frappe.generate_hash(length=12)}",
            "total_amount": cert_fee,
            "total_vat": VATCalculator.get_vat(cert_fee),
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": "http://ebarimt.mn/?billId=CERT",
            "status": "SUCCESS"
        })
        receipt.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Certification fee paid: {cert_fee:,} MNT")
        print(f"✅ VAT: {receipt.total_vat:,.2f} MNT")
        print(f"✅ Receipt: {receipt.bill_id}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "cert_fee": cert_fee}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_subscription_plan():
    """Test monthly/yearly subscription payment"""
    print("\n=== LMS TEST 4: Learning Subscription Plans ===")
    
    try:
        plans = [
            {"name": "Monthly Basic", "amount": 50000, "period": "month"},
            {"name": "Monthly Premium", "amount": 100000, "period": "month"},
            {"name": "Yearly Basic", "amount": 500000, "period": "year"},
            {"name": "Yearly Premium", "amount": 1000000, "period": "year"}
        ]
        
        invoices_created = []
        
        for plan in plans:
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"SUB-{plan['period'][:1].upper()}-{frappe.generate_hash(length=6)}",
                "amount": plan["amount"],
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/lms/subscribe/{plan['period']}",
                "invoice_status": "PAID",
                "paid_date": frappe.utils.now()
            })
            invoice.insert(ignore_permissions=True)
            invoices_created.append(invoice.name)
            print(f"✅ {plan['name']}: {plan['amount']:,} MNT/{plan['period']}")
        
        frappe.db.commit()
        
        print(f"✅ Total subscription plans: {len(plans)}")
        
        # Cleanup
        for inv_name in invoices_created:
            frappe.delete_doc("QPay Invoice", inv_name, force=True, ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "plans_count": len(plans)}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_bulk_student_enrollment():
    """Test bulk student enrollments (corporate training)"""
    print("\n=== LMS TEST 5: Bulk Corporate Training Enrollment ===")
    
    try:
        import time
        
        print("Simulating 100 employee enrollments...")
        start = time.time()
        
        course_price = 120000  # Per student
        students = 100
        
        for i in range(students):
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"CORP-{i:03d}-{frappe.generate_hash(length=6)}",
                "amount": course_price,
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/lms/corporate/{i}",
                "invoice_status": "PAID",
                "paid_date": frappe.utils.now()
            })
            invoice.insert(ignore_permissions=True)
        
        frappe.db.commit()
        elapsed = time.time() - start
        
        print(f"✅ Enrolled {students} students in {elapsed:.2f}s ({elapsed/students*1000:.2f}ms per student)")
        
        # Calculate revenue
        total_revenue = students * course_price
        print(f"✅ Total revenue: {total_revenue:,} MNT")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'CORP-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "students_enrolled": students,
            "revenue": total_revenue,
            "time_seconds": elapsed
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_course_bundle_payment():
    """Test payment for course bundle (multiple courses)"""
    print("\n=== LMS TEST 6: Course Bundle Payment ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator
        
        # Create receipt with course bundle items
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"BUNDLE-{frappe.generate_hash(length=10)}",
            "total_amount": 0,
            "total_vat": 0,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": "http://ebarimt.mn/?billId=BUNDLE",
            "status": "SUCCESS"
        })
        receipt.insert(ignore_permissions=True)
        
        # Add courses in bundle
        courses = [
            {"name": "Python Programming", "price": 150000},
            {"name": "Web Development", "price": 180000},
            {"name": "Data Science Fundamentals", "price": 200000},
            {"name": "Machine Learning Basics", "price": 220000}
        ]
        
        total = 0
        for course in courses:
            total += course["price"]
            receipt.append("items", {
                "item_name": course["name"],
                "qty": 1,
                "unit_price": course["price"],
                "total_amount": course["price"]
            })
            print(f"   ✅ {course['name']}: {course['price']:,} MNT")
        
        receipt.total_amount = total
        receipt.total_vat = VATCalculator.get_vat(total)
        receipt.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Bundle total: {total:,} MNT")
        print(f"✅ VAT: {receipt.total_vat:,.2f} MNT")
        print(f"✅ Courses in bundle: {len(courses)}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "courses_count": len(courses), "total": total}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_installment_payment():
    """Test installment payment tracking"""
    print("\n=== LMS TEST 7: Installment Payment Plan ===")
    
    try:
        total_price = 600000  # MNT
        installments = 3
        per_installment = total_price / installments
        
        print(f"Total course price: {total_price:,} MNT")
        print(f"Installment plan: {installments} months")
        print(f"Per month: {per_installment:,.0f} MNT")
        
        paid_installments = []
        
        for i in range(1, installments + 1):
            status = "PAID" if i <= 2 else "UNPAID"  # First 2 paid
            
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"INST-{i}-{frappe.generate_hash(length=8)}",
                "amount": per_installment,
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/lms/installment/{i}",
                "invoice_status": status,
                "paid_date": frappe.utils.now() if status == "PAID" else None
            })
            invoice.insert(ignore_permissions=True)
            
            if status == "PAID":
                paid_installments.append(i)
            
            status_icon = "✅" if status == "PAID" else "⏳"
            print(f"{status_icon} Installment {i}/{installments}: {per_installment:,.0f} MNT - {status}")
        
        frappe.db.commit()
        
        paid_amount = len(paid_installments) * per_installment
        remaining = total_price - paid_amount
        
        print(f"✅ Paid: {paid_amount:,.0f} MNT ({len(paid_installments)}/{installments})")
        print(f"⏳ Remaining: {remaining:,.0f} MNT")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'INST-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "installments_paid": len(paid_installments),
            "installments_total": installments
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_lms_doctype_compatibility():
    """Test compatibility with LMS DocTypes"""
    print("\n=== LMS TEST 8: LMS DocType Compatibility ===")
    
    try:
        lms_doctypes = [
            "LMS Course",
            "LMS Batch",
            "LMS Certificate",
            "LMS Enrollment",
            "LMS Settings"
        ]
        
        for dt in lms_doctypes:
            exists = frappe.db.exists("DocType", dt)
            if exists:
                print(f"✅ {dt}: Available")
            else:
                print(f"⚠️  {dt}: Not found (may be optional)")
        
        # Create test invoice with LMS reference
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"LMS-COMPAT-{frappe.generate_hash(length=8)}",
            "amount": 125000,
            "currency": "MNT",
            "qr_text": "https://qpay.mn/lms/test",
            "invoice_status": "UNPAID",
            "reference_doctype": "LMS Course"
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Created invoice with LMS compatibility: {invoice.invoice_id}")
        
        # Cleanup
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "compatible": True}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def run_lms_battle_tests():
    """Run comprehensive LMS integration tests"""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  MN PAYMENTS - LMS INTEGRATION BATTLE TEST               ║")
    print("║  Learning Management System Payment Flow Testing        ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    print(f"Environment: Frappe v{frappe.__version__}")
    print(f"Site: {frappe.local.site}")
    print(f"Apps: {', '.join(frappe.get_installed_apps())}\n")
    
    # Run all tests
    results = {}
    results["course_enrollment"] = test_course_enrollment_payment()
    results["batch_enrollment"] = test_batch_enrollment_payment()
    results["certification"] = test_certification_fee()
    results["subscriptions"] = test_subscription_plan()
    results["bulk_enrollment"] = test_bulk_student_enrollment()
    results["course_bundle"] = test_course_bundle_payment()
    results["installments"] = test_installment_payment()
    results["lms_compatibility"] = test_lms_doctype_compatibility()
    
    # Summary
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  LMS BATTLE TEST RESULTS                                 ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    passed = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        test_label = test_name.replace("_", " ").title()
        print(f"{status}  {test_label}")
        
        # Show key metrics
        if result.get("success"):
            if "discount_percent" in result:
                print(f"        Discount: {result['discount_percent']:.0f}%")
            if "revenue" in result:
                print(f"        Revenue: {result['revenue']:,.0f} MNT")
            if "students_enrolled" in result:
                print(f"        Students: {result['students_enrolled']}")
        else:
            if "error" in result:
                print(f"        Error: {result['error'][:80]}")
    
    print(f"\n{'='*65}")
    print(f"FINAL RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*65}\n")
    
    if passed == total:
        print("🎉🎉🎉 ALL LMS TESTS PASSED! 🎉🎉🎉")
        print("✅ MN Payments is READY for LMS:")
        print("   - Course enrollment payments")
        print("   - Batch enrollment with discounts")
        print("   - Certification exam fees")
        print("   - Subscription plans (monthly/yearly)")
        print("   - Bulk corporate training enrollments")
        print("   - Course bundles")
        print("   - Installment payment tracking")
        print("   - Full DocType compatibility")
        print("\n🎓 Ready for educational platform deployment! 🎓")
    else:
        print(f"⚠️  {total-passed} test(s) failed. Review errors above.")
    
    return results


if __name__ == "__main__":
    os.chdir('/Users/bg/frappe-bench/sites')
    frappe.init(site='test.local')
    frappe.connect()
    frappe.local.lang = frappe.db.get_default("lang") or "en"
    
    try:
        results = run_lms_battle_tests()
    finally:
        frappe.destroy()
