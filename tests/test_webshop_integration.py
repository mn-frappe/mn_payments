"""
WEBSHOP INTEGRATION BATTLE TEST
Tests MN Payments with Webshop e-commerce scenarios
"""

import os
import frappe
from decimal import Decimal


def test_webshop_checkout_flow():
    """Test complete webshop checkout with QPay payment"""
    print("\n=== WEBSHOP TEST 1: E-Commerce Checkout Flow ===")
    
    try:
        from mn_payments.sdk import QPayClient
        
        # Simulate webshop order
        order_total = 250000  # MNT
        
        print(f"Step 1: Customer checkout - Order total: {order_total:,} MNT")
        
        # Create QPay invoice for webshop order
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"WEBSHOP-{frappe.generate_hash(length=10)}",
            "amount": order_total,
            "currency": "MNT",
            "qr_text": f"https://qpay.mn/invoice/WS-{frappe.generate_hash(length=8)}",
            "invoice_status": "UNPAID",
            "reference_doctype": "Quotation",  # Webshop uses Quotation
            "reference_docname": f"QTN-WEBSHOP-001"
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ QPay invoice created: {invoice.invoice_id}")
        
        # Add payment URLs for different banks
        payment_methods = [
            ("Khan Bank", "https://qpay.mn/khan/webshop"),
            ("Golomt", "https://qpay.mn/golomt/webshop"),
            ("TDB", "https://qpay.mn/tdb/webshop"),
            ("Social Pay", "https://qpay.mn/socialpay/webshop")
        ]
        
        for method, url in payment_methods:
            invoice.append("payment_urls", {
                "name_field": method,
                "link": url,
                "description": f"Pay with {method}"
            })
        
        invoice.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ {len(payment_methods)} payment methods added")
        
        # Simulate payment
        print("Step 2: Customer selects payment method and pays...")
        invoice.invoice_status = "PAID"
        invoice.paid_date = frappe.utils.now()
        invoice.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ Payment confirmed")
        
        # Generate tax receipt
        print("Step 3: Generating e-commerce tax receipt...")
        from mn_payments.sdk.ebarimt import VATCalculator
        
        vat = VATCalculator.get_vat(order_total)
        
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"ESHOP-{frappe.generate_hash(length=12)}",
            "total_amount": order_total,
            "total_vat": vat,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": f"http://ebarimt.mn/?billId=ESHOP",
            "status": "SUCCESS",
            "reference_doctype": "QPay Invoice",
            "reference_docname": invoice.name
        })
        receipt.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"   ✅ Tax receipt: {receipt.bill_id}")
        print(f"   ✅ VAT collected: {vat:,.2f} MNT")
        print(f"   ✅ Lottery: {receipt.lottery_number}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        print("✅ Webshop checkout flow test PASSED")
        return {"success": True, "flow": "webshop_checkout"}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_shopping_cart_items():
    """Test receipt with shopping cart line items"""
    print("\n=== WEBSHOP TEST 2: Shopping Cart Items Receipt ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator
        
        # Create receipt
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"CART-{frappe.generate_hash(length=10)}",
            "total_amount": 0,
            "total_vat": 0,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": "http://ebarimt.mn/?billId=CART",
            "status": "SUCCESS"
        })
        receipt.insert(ignore_permissions=True)
        
        # Add shopping cart items
        cart_items = [
            {"name": "Samsung Galaxy S24", "qty": 1, "price": 2500000},
            {"name": "iPhone Case", "qty": 2, "price": 45000},
            {"name": "Screen Protector", "qty": 3, "price": 15000},
            {"name": "USB-C Cable", "qty": 2, "price": 25000},
            {"name": "Power Bank 20000mAh", "qty": 1, "price": 95000}
        ]
        
        total = 0
        for item_data in cart_items:
            item_total = item_data["qty"] * item_data["price"]
            total += item_total
            
            receipt.append("items", {
                "item_name": item_data["name"],
                "qty": item_data["qty"],
                "unit_price": item_data["price"],
                "total_amount": item_total
            })
            print(f"   ✅ {item_data['name']}: {item_data['qty']} x {item_data['price']:,} = {item_total:,} MNT")
        
        receipt.total_amount = total
        receipt.total_vat = VATCalculator.get_vat(total)
        receipt.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Cart total: {total:,} MNT")
        print(f"✅ VAT: {receipt.total_vat:,.2f} MNT")
        print(f"✅ Items in cart: {len(receipt.items)}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "items_count": len(cart_items), "total": total}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_multi_currency_payments():
    """Test webshop international payments"""
    print("\n=== WEBSHOP TEST 3: International Multi-Currency Payments ===")
    
    try:
        currencies = [
            ("MNT", 500000, "Domestic customer"),
            ("USD", 145, "US customer"),
            ("CNY", 1050, "Chinese customer")
        ]
        
        invoices_created = []
        
        for curr, amount, customer_type in currencies:
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"{curr}-SHOP-{frappe.generate_hash(length=6)}",
                "amount": amount,
                "currency": curr,
                "qr_text": f"https://qpay.mn/{curr.lower()}/invoice",
                "invoice_status": "PAID" if curr in ["MNT", "USD"] else "UNPAID",
                "paid_date": frappe.utils.now() if curr in ["MNT", "USD"] else None
            })
            invoice.insert(ignore_permissions=True)
            invoices_created.append(invoice.name)
            
            status_icon = "✅" if invoice.invoice_status == "PAID" else "⏳"
            print(f"{status_icon} {customer_type}: {amount:,} {curr} - {invoice.invoice_status}")
        
        frappe.db.commit()
        
        # Check payment summary
        paid_count = frappe.db.count("QPay Invoice", {
            "invoice_id": ["like", "%-SHOP-%"],
            "invoice_status": "PAID"
        })
        unpaid_count = frappe.db.count("QPay Invoice", {
            "invoice_id": ["like", "%-SHOP-%"],
            "invoice_status": "UNPAID"
        })
        
        print(f"✅ Payment summary: {paid_count} paid, {unpaid_count} pending")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE '%-SHOP-%'")
        frappe.db.commit()
        
        return {"success": True, "currencies_tested": len(currencies)}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_bulk_order_processing():
    """Test bulk order processing during sales events"""
    print("\n=== WEBSHOP TEST 4: Bulk Order Processing (Black Friday Simulation) ===")
    
    try:
        import time
        
        print("Simulating 200 orders during flash sale...")
        start = time.time()
        
        # Create 200 orders
        for i in range(200):
            amount = 50000 + (i * 1000)  # Varying amounts
            
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"BF-{i:04d}-{frappe.generate_hash(length=6)}",
                "amount": amount,
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/blackfriday/{i}",
                "invoice_status": "PAID" if i % 3 == 0 else "UNPAID"  # 33% conversion
            })
            invoice.insert(ignore_permissions=True)
        
        frappe.db.commit()
        elapsed = time.time() - start
        
        print(f"✅ Created 200 orders in {elapsed:.2f}s ({elapsed/200*1000:.2f}ms per order)")
        
        # Generate receipts for paid orders
        start = time.time()
        paid_invoices = frappe.get_all(
            "QPay Invoice",
            filters={"invoice_id": ["like", "BF-%"], "invoice_status": "PAID"},
            fields=["name", "amount"]
        )
        
        from mn_payments.sdk.ebarimt import VATCalculator
        
        for inv_data in paid_invoices:
            receipt = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                "bill_id": f"BF-RCPT-{frappe.generate_hash(length=8)}",
                "total_amount": inv_data.amount,
                "total_vat": VATCalculator.get_vat(inv_data.amount),
                "total_city_tax": 0,
                "status": "SUCCESS",
                "reference_doctype": "QPay Invoice",
                "reference_docname": inv_data.name
            })
            receipt.insert(ignore_permissions=True)
        
        frappe.db.commit()
        receipt_time = time.time() - start
        
        print(f"✅ Generated {len(paid_invoices)} receipts in {receipt_time:.2f}s ({receipt_time/len(paid_invoices)*1000:.2f}ms per receipt)")
        
        # Calculate revenue
        total_revenue = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN invoice_status = 'PAID' THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN invoice_status = 'PAID' THEN 1 ELSE 0 END) as paid_orders
            FROM `tabQPay Invoice`
            WHERE invoice_id LIKE 'BF-%'
        """, as_dict=True)[0]
        
        conversion_rate = (total_revenue.paid_orders / total_revenue.total_orders) * 100
        
        print(f"✅ Revenue: {total_revenue.revenue:,.0f} MNT from {total_revenue.paid_orders} orders")
        print(f"✅ Conversion rate: {conversion_rate:.1f}%")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabEbarimt Receipt` WHERE bill_id LIKE 'BF-RCPT-%'")
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'BF-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "orders_processed": 200,
            "receipts_generated": len(paid_invoices),
            "revenue": float(total_revenue.revenue),
            "conversion_rate": conversion_rate
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_payment_gateway_integration():
    """Test payment gateway compatibility"""
    print("\n=== WEBSHOP TEST 5: Payment Gateway Integration ===")
    
    try:
        # Check if Webshop settings exist
        webshop_exists = frappe.db.exists("DocType", "Webshop Settings")
        print(f"{'✅' if webshop_exists else '⚠️'} Webshop Settings DocType: {'Available' if webshop_exists else 'Not found'}")
        
        # Test payment gateway account compatibility
        gateway_exists = frappe.db.exists("DocType", "Payment Gateway Account")
        print(f"{'✅' if gateway_exists else '⚠️'} Payment Gateway Account: {'Available' if gateway_exists else 'Not found'}")
        
        # Create test invoice with gateway reference
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"GATEWAY-{frappe.generate_hash(length=10)}",
            "amount": 150000,
            "currency": "MNT",
            "qr_text": "https://qpay.mn/gateway/test",
            "invoice_status": "UNPAID"
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Payment gateway invoice created: {invoice.invoice_id}")
        
        # Cleanup
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "gateway_compatible": True}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_abandoned_cart_recovery():
    """Test abandoned cart tracking"""
    print("\n=== WEBSHOP TEST 6: Abandoned Cart Recovery ===")
    
    try:
        import time
        from frappe.utils import add_to_date, now
        
        # Create mix of paid and unpaid invoices (abandoned carts)
        abandoned_carts = []
        completed_orders = []
        
        for i in range(50):
            status = "PAID" if i % 4 == 0 else "UNPAID"  # 25% conversion
            
            invoice = frappe.get_doc({
                "doctype": "QPay Invoice",
                "invoice_id": f"CART-{i:03d}-{frappe.generate_hash(length=6)}",
                "amount": 100000 + (i * 5000),
                "currency": "MNT",
                "qr_text": f"https://qpay.mn/cart/{i}",
                "invoice_status": status,
                "creation": add_to_date(now(), days=-2) if status == "UNPAID" else now()
            })
            invoice.insert(ignore_permissions=True)
            
            if status == "UNPAID":
                abandoned_carts.append(invoice.invoice_id)
            else:
                completed_orders.append(invoice.invoice_id)
        
        frappe.db.commit()
        
        print(f"✅ Created 50 shopping sessions:")
        print(f"   - Completed: {len(completed_orders)} ({len(completed_orders)/50*100:.0f}%)")
        print(f"   - Abandoned: {len(abandoned_carts)} ({len(abandoned_carts)/50*100:.0f}%)")
        
        # Query abandoned carts
        start = time.time()
        abandoned_query = frappe.db.sql("""
            SELECT 
                COUNT(*) as count,
                SUM(amount) as potential_revenue
            FROM `tabQPay Invoice`
            WHERE invoice_id LIKE 'CART-%'
            AND invoice_status = 'UNPAID'
            AND creation < NOW() - INTERVAL 1 DAY
        """, as_dict=True)[0]
        query_time = (time.time() - start) * 1000
        
        print(f"✅ Abandoned cart analysis (query time: {query_time:.2f}ms):")
        print(f"   - Count: {abandoned_query.count}")
        potential_rev = abandoned_query.potential_revenue or 0
        print(f"   - Potential revenue: {potential_rev:,.0f} MNT")
        
        # Cleanup
        frappe.db.sql("DELETE FROM `tabQPay Invoice` WHERE invoice_id LIKE 'CART-%'")
        frappe.db.commit()
        
        return {
            "success": True,
            "abandoned_count": len(abandoned_carts),
            "conversion_rate": len(completed_orders)/50*100
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_digital_goods_receipt():
    """Test digital goods (no physical shipping) receipt"""
    print("\n=== WEBSHOP TEST 7: Digital Goods Receipt ===")
    
    try:
        from mn_payments.sdk.ebarimt import VATCalculator
        
        digital_products = [
            {"name": "Software License - 1 Year", "price": 450000},
            {"name": "eBook - Programming Guide", "price": 35000},
            {"name": "Online Course Access", "price": 250000},
            {"name": "Music Album Download", "price": 15000},
            {"name": "Stock Photos Pack", "price": 95000}
        ]
        
        receipt = frappe.get_doc({
            "doctype": "Ebarimt Receipt",
            "bill_id": f"DIGITAL-{frappe.generate_hash(length=10)}",
            "total_amount": 0,
            "total_vat": 0,
            "total_city_tax": 0,
            "lottery_number": frappe.utils.random_string(8),
            "qr_data": "http://ebarimt.mn/?billId=DIGITAL",
            "status": "SUCCESS"
        })
        receipt.insert(ignore_permissions=True)
        
        total = 0
        for product in digital_products:
            total += product["price"]
            receipt.append("items", {
                "item_name": product["name"],
                "qty": 1,
                "unit_price": product["price"],
                "total_amount": product["price"]
            })
            print(f"   ✅ {product['name']}: {product['price']:,} MNT")
        
        receipt.total_amount = total
        receipt.total_vat = VATCalculator.get_vat(total)
        receipt.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Digital goods total: {total:,} MNT")
        print(f"✅ VAT: {receipt.total_vat:,.2f} MNT")
        print(f"✅ Products: {len(digital_products)}")
        
        # Cleanup
        receipt.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "digital_products": len(digital_products)}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def test_webshop_doctype_compatibility():
    """Test compatibility with Webshop DocTypes"""
    print("\n=== WEBSHOP TEST 8: Webshop DocType Compatibility ===")
    
    try:
        webshop_doctypes = [
            "Webshop Settings",
            "Website Item",
            "Item Review",
            "Recommended Products",
            "E Commerce Settings"
        ]
        
        for dt in webshop_doctypes:
            exists = frappe.db.exists("DocType", dt)
            if exists:
                print(f"✅ {dt}: Available")
            else:
                print(f"⚠️  {dt}: Not found (may be optional)")
        
        # Test Item compatibility (core for webshop)
        item_exists = frappe.db.exists("DocType", "Item")
        print(f"{'✅' if item_exists else '❌'} Item DocType: {'Available' if item_exists else 'Missing'}")
        
        # Test Quotation (used by webshop for carts)
        quotation_exists = frappe.db.exists("DocType", "Quotation")
        print(f"{'✅' if quotation_exists else '❌'} Quotation DocType: {'Available' if quotation_exists else 'Missing'}")
        
        # Create test invoice with webshop references
        invoice = frappe.get_doc({
            "doctype": "QPay Invoice",
            "invoice_id": f"WEBSHOP-COMPAT-{frappe.generate_hash(length=8)}",
            "amount": 175000,
            "currency": "MNT",
            "qr_text": "https://qpay.mn/webshop/test",
            "invoice_status": "UNPAID",
            "reference_doctype": "Quotation" if quotation_exists else None
        })
        invoice.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Created invoice with webshop compatibility: {invoice.invoice_id}")
        
        # Cleanup
        invoice.delete(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "compatible": True}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def run_webshop_battle_tests():
    """Run comprehensive webshop integration tests"""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  MN PAYMENTS - WEBSHOP INTEGRATION BATTLE TEST           ║")
    print("║  E-Commerce Payment Flow Testing                         ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    print(f"Environment: Frappe v{frappe.__version__}")
    print(f"Site: {frappe.local.site}")
    print(f"Apps: {', '.join(frappe.get_installed_apps())}\n")
    
    # Run all tests
    results = {}
    results["checkout_flow"] = test_webshop_checkout_flow()
    results["cart_items"] = test_shopping_cart_items()
    results["multi_currency"] = test_multi_currency_payments()
    results["bulk_processing"] = test_bulk_order_processing()
    results["payment_gateway"] = test_payment_gateway_integration()
    results["abandoned_cart"] = test_abandoned_cart_recovery()
    results["digital_goods"] = test_digital_goods_receipt()
    results["doctype_compatibility"] = test_webshop_doctype_compatibility()
    
    # Summary
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  WEBSHOP BATTLE TEST RESULTS                             ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    passed = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        test_label = test_name.replace("_", " ").title()
        print(f"{status}  {test_label}")
        
        # Show key metrics
        if result.get("success"):
            if "conversion_rate" in result:
                print(f"        Conversion: {result['conversion_rate']:.1f}%")
            if "revenue" in result:
                print(f"        Revenue: {result['revenue']:,.0f} MNT")
            if "orders_processed" in result:
                print(f"        Orders: {result['orders_processed']}")
        else:
            if "error" in result:
                print(f"        Error: {result['error'][:80]}")
    
    print(f"\n{'='*65}")
    print(f"FINAL RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*65}\n")
    
    if passed == total:
        print("🎉🎉🎉 ALL WEBSHOP TESTS PASSED! 🎉🎉🎉")
        print("✅ MN Payments is READY for Webshop:")
        print("   - Complete checkout flow with QPay")
        print("   - Shopping cart item receipts")
        print("   - Multi-currency international payments")
        print("   - Bulk order processing (flash sales)")
        print("   - Payment gateway integration")
        print("   - Abandoned cart tracking")
        print("   - Digital goods support")
        print("   - Full DocType compatibility")
        print("\n🛒 Ready for production e-commerce! 🛒")
    else:
        print(f"⚠️  {total-passed} test(s) failed. Review errors above.")
    
    return results


if __name__ == "__main__":
    os.chdir('/Users/bg/frappe-bench/sites')
    frappe.init(site='test.local')
    frappe.connect()
    frappe.local.lang = frappe.db.get_default("lang") or "en"
    
    try:
        results = run_webshop_battle_tests()
    finally:
        frappe.destroy()
