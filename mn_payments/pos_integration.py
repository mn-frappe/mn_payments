from __future__ import annotations

import frappe
from frappe import _


def on_pos_invoice_submit(doc, method=None):
	"""Hook called when POS Invoice is submitted - send receipt to Ebarimt if enabled."""
	
	try:
		settings = frappe.get_single("Ebarimt Settings")
		if not settings.get("auto_submit_on_pos") or not settings.get("posapi_enabled"):
			return
		
		# Import here to avoid circular dependency
		from mn_payments.utils.ebarimt import save_receipt
		
		# Build receipt payload from POS Invoice
		receipt_data = _build_receipt_from_pos_invoice(doc, settings)
		
		# Submit to Ebarimt
		response = save_receipt(receipt_data)
		
		# Store response in custom field or log
		if response:
			frappe.msgprint(
				_("Receipt submitted to Ebarimt successfully"),
				alert=True,
				indicator="green"
			)
			
	except Exception as exc:
		frappe.log_error(
			frappe.get_traceback(),
			title=f"Ebarimt submission failed for {doc.name}"
		)
		frappe.msgprint(
			_("Failed to submit receipt to Ebarimt: {0}").format(str(exc)),
			alert=True,
			indicator="orange"
		)


def _build_receipt_from_pos_invoice(doc, settings):
	"""Build Ebarimt receipt payload from POS Invoice."""
	
	is_pharmacy = settings.get("is_pharmacy", 0)
	
	# Build items list
	items = []
	total_city_tax = 0
	
	for item in doc.items:
		# Calculate city tax (1% of amount for applicable items)
		city_tax = _calculate_city_tax(item, doc)
		total_city_tax += city_tax
		
		# Calculate VAT
		vat_amount = _calculate_vat(item, doc)
		
		# Build item according to PosAPI.yaml schema
		item_data = {
			"name": item.item_name or item.item_code,
			"barCode": item.get("barcode") or "",
			"barCodeType": item.get("barcode_type") or "UNDEFINED",
			"classificationCode": item.get("classification_code") or "",
			"taxProductCode": item.get("tax_product_code") or None,
			"measureUnit": item.uom or "ш",
			"qty": item.qty,
			"unitPrice": item.rate,
			"totalVAT": vat_amount,
			"totalCityTax": city_tax,
			"totalAmount": item.amount,
		}
		
		# Pharmacy-specific data (lotNo for serial number)
		if is_pharmacy and item.get("serial_no"):
			item_data["data"] = {
				"lotNo": item.get("serial_no")
			}
		
		items.append(item_data)
	
	# Calculate total VAT
	total_vat = sum(_calculate_vat(item, doc) for item in doc.items)
	
	# Get customer information
	customer_info = _get_customer_info(doc.customer)
	
	# Determine receipt type based on customer type
	# B2B_RECEIPT: Business to Business (uses customerTin)
	# B2C_RECEIPT: Business to Consumer (uses consumerNo)
	receipt_type = "B2B_RECEIPT" if customer_info.get("type") == "company" else "B2C_RECEIPT"
	
	# Build main receipt payload according to PosAPI.yaml schema
	receipt = {
		"totalAmount": doc.grand_total,
		"totalVAT": total_vat,
		"totalCityTax": total_city_tax,
		"districtCode": doc.get("district_code") or "",
		"merchantTin": doc.get("tax_id") or "",  # Seller's tax ID
		"branchNo": doc.get("pos_profile") or "001",
		"posNo": doc.get("pos_terminal") or "001",
		"type": receipt_type,
		"billIdSuffix": doc.name[-8:] if len(doc.name) > 8 else doc.name,
		"inactiveId": doc.get("return_against") or None,
		"reportMonth": None,
	}
	
	# Add customer identification based on type (per PosAPI.yaml schema)
	if customer_info.get("type") == "company":
		# B2B: Company customer - use customerTin
		receipt["customerTin"] = customer_info.get("regno") or ""
		receipt["consumerNo"] = ""
	else:
		# B2C: Individual customer - use consumerNo
		receipt["customerTin"] = None
		receipt["consumerNo"] = customer_info.get("regno") or ""
	
	# Build sub-receipt (receipts array per PosAPI.yaml schema)
	sub_receipt = {
		"totalAmount": doc.grand_total,
		"totalVAT": total_vat,
		"totalCityTax": total_city_tax,
		"taxType": "VAT_ABLE",  # Default, should be determined by items
		"merchantTin": doc.get("tax_id") or "",
		"customerTin": None,
		"bankAccountNo": "",
		"iBan": "",
		"invoiceId": None,
		"items": items,
	}
	
	receipt["receipts"] = [sub_receipt]
	
	# Add payments (per PosAPI.yaml schema)
	payments = []
	for payment in doc.payments:
		payment_data = {
			"code": _get_payment_code(payment.mode_of_payment),
			"status": "PAID",
			"paidAmount": payment.amount,
			"data": None,  # Required by schema, can be null for non-card payments
		}
		payments.append(payment_data)
	receipt["payments"] = payments
	
	return receipt


def _calculate_city_tax(item, doc):
	"""Calculate city tax (1% of taxable amount) for applicable items.
	
	City tax applies to:
	- Alcohol products
	- Tobacco products
	- Fuel/petroleum products
	- Other items marked as city_tax_applicable
	"""
	
	# Check if item has city tax flag in custom field
	if item.get("city_tax_applicable"):
		return round(item.amount * 0.01, 2)
	
	# Check item group for automatic city tax
	if item.item_group:
		item_group_name = item.item_group.lower()
		city_tax_groups = ["alcohol", "tobacco", "fuel", "petroleum", "gas"]
		
		for tax_group in city_tax_groups:
			if tax_group in item_group_name:
				return round(item.amount * 0.01, 2)
	
	# Check if custom field exists on Item master
	try:
		item_doc = frappe.get_cached_doc("Item", item.item_code)
		if item_doc.get("city_tax_applicable"):
			return round(item.amount * 0.01, 2)
	except Exception:
		pass
	
	return 0


def _calculate_vat(item, doc):
	"""Calculate VAT amount from item taxes or default 10%.
	
	Returns the VAT amount from:
	1. Item's tax template if available
	2. POS Invoice's taxes_and_charges
	3. Default 10% if item is VAT applicable
	"""
	
	# Try to get VAT from item's tax detail
	vat_amount = 0
	
	# Check if there's a custom field for vat_amount
	if item.get("vat_amount"):
		return item.get("vat_amount")
	
	# Check doc-level taxes for VAT
	if hasattr(doc, "taxes") and doc.taxes:
		for tax in doc.taxes:
			tax_desc = (tax.description or "").lower()
			if "vat" in tax_desc or "ндс" in tax_desc or tax.account_head and "vat" in tax.account_head.lower():
				# Allocate tax proportionally to this item
				if doc.net_total and doc.net_total > 0:
					item_ratio = item.amount / doc.net_total
					vat_amount = round(tax.tax_amount * item_ratio, 2)
					return vat_amount
	
	# Default: 10% VAT if not explicitly zero-rated
	if not item.get("is_vat_exempt") and not item.get("is_zero_rated"):
		# Calculate VAT from net amount (amount / 1.1 * 0.1)
		net_amount = item.amount / 1.1
		vat_amount = round(net_amount * 0.1, 2)
	
	return vat_amount


def _get_payment_code(mode_of_payment):
	"""Map ERPNext payment mode to Ebarimt payment codes per PosAPI.yaml schema.
	
	Valid codes:
	- CASH: Cash payment
	- PAYMENT_CARD: Card payment
	"""
	
	# Map card-related payments to PAYMENT_CARD
	card_modes = ["Card", "Credit Card", "Debit Card", "Bank Card"]
	
	if mode_of_payment in card_modes:
		return "PAYMENT_CARD"
	
	# Everything else defaults to CASH (including QPay, Social Pay, Bank Transfer)
	return "CASH"


def _get_customer_info(customer_name):
	"""Get customer registration number and type information.
	
	Returns:
		dict: {
			"regno": Tax registration number or citizen ID,
			"name": Company name (for legal entities only),
			"type": "company" or "individual"
		}
	"""
	
	if not customer_name:
		return {"regno": "", "name": "", "type": "individual"}
	
	try:
		customer = frappe.get_cached_doc("Customer", customer_name)
		
		# Check if customer is a company/legal entity
		customer_type = customer.customer_type or "Individual"
		
		result = {
			"regno": "",
			"name": "",
			"type": "company" if customer_type == "Company" else "individual"
		}
		
		# Get registration number from custom field or tax_id
		regno = (
			customer.get("tax_id") 
			or customer.get("registration_number")
			or customer.get("regno")
			or customer.get("company_registration_number")
			or ""
		)
		
		result["regno"] = regno
		
		# For companies, include the company name
		if result["type"] == "company":
			result["name"] = customer.customer_name or customer_name
		
		return result
		
	except Exception as exc:
		frappe.log_error(
			frappe.get_traceback(),
			title=f"Failed to fetch customer info for {customer_name}"
		)
		return {"regno": "", "name": "", "type": "individual"}
