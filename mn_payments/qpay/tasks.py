import frappe
from frappe.utils import now_datetime

from mn_payments.qpay.client import QPayGateway


def check_pending():
	pending = frappe.get_all(
		"Payment Transaction",
		filters={"status": "Pending", "qpay_invoice_id": ["is", "set"]},
		pluck="name",
	)
	if not pending:
		return
	gw = QPayGateway()
	for name in pending:
		try:
			tx = frappe.get_doc("Payment Transaction", name)
			resp = gw.check_payment(tx.qpay_invoice_id)
			invoice_status = (resp.get("invoice_status") or resp.get("status") or "").upper()
			if invoice_status == "PAID":
				tx.status = "Paid"
			elif invoice_status in {"EXPIRED", "CANCELLED"}:
				tx.status = "Cancelled"
			tx.callback_payload = frappe.as_json(resp)
			tx.save(ignore_permissions=True)
		except Exception as exc:
			frappe.log_error(message=str(exc), title=f"QPay poll failed {name} @ {now_datetime()}")
