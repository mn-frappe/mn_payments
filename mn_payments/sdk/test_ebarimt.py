"""
Unit tests for Ebarimt Python SDK
Tests VAT calculations to ensure they match Go SDK behavior
"""

import unittest
from decimal import Decimal
from mn_payments.sdk.ebarimt import (
    VATCalculator,
    TaxType,
    ReceiptType,
    BarcodeType,
    EbarimtClient,
    ReceiptItem,
    CreateReceiptRequest,
)


class TestVATCalculator(unittest.TestCase):
    """Test VAT and city tax calculations"""
    
    def test_get_vat(self):
        """Test VAT calculation without city tax"""
        # 10,000 MNT with VAT
        # Formula: 10000 / 1.10 * 0.10 = 909.09
        vat = VATCalculator.get_vat(10000)
        self.assertAlmostEqual(vat, 909.09, places=2)
        
        # 5,000 MNT
        vat = VATCalculator.get_vat(5000)
        self.assertAlmostEqual(vat, 454.55, places=2)
    
    def test_get_vat_with_city_tax(self):
        """Test VAT calculation with city tax"""
        # 10,000 MNT with VAT + City Tax
        # Formula: 10000 / (1 + 0.10 + 0.01) * 0.10 = 900.90
        vat = VATCalculator.get_vat_with_city_tax(10000)
        self.assertAlmostEqual(vat, 900.90, places=2)
        
        # Match Go SDK test case
        vat = VATCalculator.get_vat_with_city_tax(100)
        self.assertAlmostEqual(vat, 9.01, places=2)
    
    def test_get_city_tax(self):
        """Test city tax calculation with VAT"""
        # 10,000 MNT
        # Formula: 10000 / 1.11 * 0.01 = 90.09
        city_tax = VATCalculator.get_city_tax(10000)
        self.assertAlmostEqual(city_tax, 90.09, places=2)
        
        city_tax = VATCalculator.get_city_tax(100)
        self.assertAlmostEqual(city_tax, 0.90, places=2)
    
    def test_get_city_tax_without_vat(self):
        """Test city tax without VAT"""
        # 10,000 MNT
        # Formula: 10000 / 1.01 * 0.01 = 99.01
        city_tax = VATCalculator.get_city_tax_without_vat(10000)
        self.assertAlmostEqual(city_tax, 99.01, places=2)
    
    def test_number_precision(self):
        """Test number rounding"""
        # Test rounding to 2 decimals
        self.assertEqual(VATCalculator.number_precision(0.357142857), 0.36)
        self.assertEqual(VATCalculator.number_precision(10.555), 10.56)
        self.assertEqual(VATCalculator.number_precision(10.554), 10.55)
    
    def test_vat_calculation_matches_go_sdk(self):
        """Test that Python calculations match Go SDK results"""
        # These values should match the Go SDK test cases
        test_cases = [
            (10000, 900.90, 90.09),  # VAT + City Tax
            (5000, 450.45, 45.05),
            (1000, 90.09, 9.01),
        ]
        
        for amount, expected_vat, expected_city_tax in test_cases:
            vat = VATCalculator.get_vat_with_city_tax(amount)
            city_tax = VATCalculator.get_city_tax(amount)
            
            self.assertAlmostEqual(vat, expected_vat, places=2,
                msg=f"VAT mismatch for {amount}: got {vat}, expected {expected_vat}")
            self.assertAlmostEqual(city_tax, expected_city_tax, places=2,
                msg=f"City tax mismatch for {amount}: got {city_tax}, expected {expected_city_tax}")


class TestReceiptCalculations(unittest.TestCase):
    """Test receipt total calculations"""
    
    def setUp(self):
        """Set up test client (no actual API calls)"""
        self.client = EbarimtClient(
            endpoint="https://test.ebarimt.mn",
            pos_no="TEST001",
            merchant_tin="1234567890"
        )
    
    def test_calculate_totals_vat_able_with_city_tax(self):
        """Test total calculations for VAT items with city tax"""
        items = [
            ReceiptItem(
                name="Coffee",
                tax_type=TaxType.VAT_ABLE,
                classification_code="1011010",
                qty=2,
                total_amount=5000,
                measure_unit="cup",
                tax_product_code="101",
                is_city_tax=True
            )
        ]
        
        totals = self.client.calculate_totals(items)
        
        # 5000 MNT with VAT + City Tax
        # VAT: 5000 / 1.11 * 0.10 = 450.45
        # City Tax: 5000 / 1.11 * 0.01 = 45.05
        self.assertAlmostEqual(totals["total_amount"], 5000, places=2)
        self.assertAlmostEqual(totals["total_vat"], 450.45, places=2)
        self.assertAlmostEqual(totals["total_city_tax"], 45.05, places=2)
    
    def test_calculate_totals_vat_able_without_city_tax(self):
        """Test total calculations for VAT items without city tax"""
        items = [
            ReceiptItem(
                name="Product",
                tax_type=TaxType.VAT_ABLE,
                classification_code="2022020",
                qty=1,
                total_amount=10000,
                measure_unit="pcs",
                tax_product_code="202",
                is_city_tax=False
            )
        ]
        
        totals = self.client.calculate_totals(items)
        
        # 10000 MNT with VAT only
        # VAT: 10000 / 1.10 * 0.10 = 909.09
        self.assertAlmostEqual(totals["total_amount"], 10000, places=2)
        self.assertAlmostEqual(totals["total_vat"], 909.09, places=2)
        self.assertAlmostEqual(totals["total_city_tax"], 0, places=2)
    
    def test_calculate_totals_no_vat(self):
        """Test calculations for NO_VAT items"""
        items = [
            ReceiptItem(
                name="Exported Product",
                tax_type=TaxType.NOT_VAT,
                classification_code="3033030",
                qty=1,
                total_amount=10000,
                measure_unit="pcs",
                tax_product_code="303",
                is_city_tax=False
            )
        ]
        
        totals = self.client.calculate_totals(items)
        
        # NO_VAT items have no VAT or city tax
        self.assertAlmostEqual(totals["total_amount"], 10000, places=2)
        self.assertAlmostEqual(totals["total_vat"], 0, places=2)
        self.assertAlmostEqual(totals["total_city_tax"], 0, places=2)
    
    def test_calculate_totals_vat_zero(self):
        """Test calculations for VAT_ZERO items"""
        items = [
            ReceiptItem(
                name="Zero VAT Product",
                tax_type=TaxType.VAT_ZERO,
                classification_code="4044040",
                qty=1,
                total_amount=10000,
                measure_unit="pcs",
                tax_product_code="404",
                is_city_tax=True
            )
        ]
        
        totals = self.client.calculate_totals(items)
        
        # VAT_ZERO items: 0% VAT but may have city tax
        # City tax: 10000 / 1.01 * 0.01 = 99.01
        self.assertAlmostEqual(totals["total_amount"], 10000, places=2)
        self.assertAlmostEqual(totals["total_vat"], 0, places=2)
        self.assertAlmostEqual(totals["total_city_tax"], 99.01, places=2)
    
    def test_calculate_totals_mixed_items(self):
        """Test calculations with mixed tax types"""
        items = [
            ReceiptItem(
                name="VAT Item",
                tax_type=TaxType.VAT_ABLE,
                classification_code="1011010",
                qty=2,
                total_amount=5000,
                measure_unit="pcs",
                tax_product_code="101",
                is_city_tax=True
            ),
            ReceiptItem(
                name="No VAT Item",
                tax_type=TaxType.NOT_VAT,
                classification_code="2022020",
                qty=1,
                total_amount=3000,
                measure_unit="pcs",
                tax_product_code="202",
                is_city_tax=False
            )
        ]
        
        totals = self.client.calculate_totals(items)
        
        # Total amount: 5000 + 3000 = 8000
        # VAT: 450.45 (from first item only)
        # City tax: 45.05 (from first item only)
        self.assertAlmostEqual(totals["total_amount"], 8000, places=2)
        self.assertAlmostEqual(totals["total_vat"], 450.45, places=2)
        self.assertAlmostEqual(totals["total_city_tax"], 45.05, places=2)


class TestReceiptItemGrouping(unittest.TestCase):
    """Test grouping of items by tax type"""
    
    def setUp(self):
        self.client = EbarimtClient(
            endpoint="https://test.ebarimt.mn",
            pos_no="TEST001",
            merchant_tin="1234567890"
        )
    
    def test_items_grouped_by_tax_type(self):
        """Test that items are correctly grouped by tax type"""
        items = [
            ReceiptItem(
                name="VAT Item 1",
                tax_type=TaxType.VAT_ABLE,
                classification_code="101",
                qty=1,
                total_amount=1000,
                measure_unit="pcs",
                tax_product_code="101",
                is_city_tax=True
            ),
            ReceiptItem(
                name="VAT Item 2",
                tax_type=TaxType.VAT_ABLE,
                classification_code="102",
                qty=1,
                total_amount=2000,
                measure_unit="pcs",
                tax_product_code="102",
                is_city_tax=True
            ),
            ReceiptItem(
                name="No VAT Item",
                tax_type=TaxType.NOT_VAT,
                classification_code="201",
                qty=1,
                total_amount=3000,
                measure_unit="pcs",
                tax_product_code="201",
                is_city_tax=False
            )
        ]
        
        # Mock merchant info
        from mn_payments.ebarimt.sdk import MerchantInfo
        merchant_info = MerchantInfo(
            name="Test Merchant",
            vat_payer=True,
            city_payer=True,
            free_project=False,
            found=True
        )
        
        grouped = self.client._build_receipt_items(items, merchant_info)
        
        # Should have 2 groups: VAT_ABLE and NOT_VAT
        self.assertEqual(len(grouped), 2)
        self.assertIn(TaxType.VAT_ABLE, grouped)
        self.assertIn(TaxType.NOT_VAT, grouped)
        
        # VAT_ABLE group should have 2 items
        self.assertEqual(len(grouped[TaxType.VAT_ABLE]["items"]), 2)
        
        # NOT_VAT group should have 1 item
        self.assertEqual(len(grouped[TaxType.NOT_VAT]["items"]), 1)
        
        # Check totals for VAT_ABLE group
        vat_group = grouped[TaxType.VAT_ABLE]
        self.assertAlmostEqual(vat_group["total_amount"], 3000, places=2)


if __name__ == '__main__':
    unittest.main()
