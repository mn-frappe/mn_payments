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
		
		item_data = {
			"name": item.item_name or item.item_code,
			"barCode": item.get("barcode") or "",
			"classificationCode": item.get("classification_code") or "",
			"qty": item.qty,
			"unitPrice": item.rate,
			"totalAmount": item.amount,
			"cityTax": city_tax,
			"vat": vat_amount,
		}
		
		# Pharmacy-specific fields
		if is_pharmacy:
			item_data.update({
				"barCodeType": item.get("barcode_type") or "GS1",
				"measureUnit": item.uom or "ш",
			})
		
		items.append(item_data)
	
	# Calculate total VAT
	total_vat = sum(_calculate_vat(item, doc) for item in doc.items)
	
	# Build main receipt payload
	receipt = {
		"amount": doc.grand_total,
		"vat": total_vat,
		"cityTax": total_city_tax,
		"districtCode": doc.get("district_code") or "",
		"branchNo": doc.get("pos_profile") or "001",
		"posNo": doc.get("pos_terminal") or "001",
		"billType": "3" if is_pharmacy else "1",  # 3=pharmacy, 1=general
		"customerNo": doc.customer,
		"billIdSuffix": doc.name[-8:] if len(doc.name) > 8 else doc.name,
		"returnBillId": doc.get("return_against") or None,
		"stocks": items,
	}
	
	# Add payments
	payments = []
	for payment in doc.payments:
		payments.append({
			"code": _get_payment_code(payment.mode_of_payment),
			"amount": payment.amount,
		})
	receipt["payments"] = payments
	
	return {"receipts": [receipt]}


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
	"""Map ERPNext payment mode to Ebarimt payment codes."""
	
	mapping = {
		"Cash": "CASH",
		"Card": "CARD",
		"QPay": "QPAY",
		"Social Pay": "SOCIALPAY",
		"Bank Transfer": "TRANSFER",
	}
	
	return mapping.get(mode_of_payment, "CASH")
