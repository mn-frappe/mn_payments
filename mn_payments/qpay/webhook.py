import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def handle(payload: dict | None = None):
	"""Simple webhook handler for payment status updates."""
	if not payload:
		frappe.throw(_("Missing payload"))

	# Extract payment information
	invoice_id = payload.get("invoice_id")
	status = payload.get("status")

	if not invoice_id:
		frappe.throw(_("Missing invoice_id in payload"))

	# Find and update payment transaction
	transactions = frappe.get_all(
		"Payment Transaction",
		filters={"invoice_id": invoice_id},
		limit=1
	)

	if transactions:
		tx = frappe.get_doc("Payment Transaction", transactions[0].name)
		if status == "PAID":
			tx.status = "Completed"
		elif status == "FAILED":
			tx.status = "Failed"
		tx.save()
		frappe.db.commit()

	return {"status": "success"}
