import frappe


def scrub_individuals():
	"""Remove sensitive data from individual payment transactions for privacy compliance."""
	records = frappe.get_all(
		"Payment Transaction",
		filters={"payer_type": "Individual"},
		pluck="name",
		limit=200,
	)
	for name in records:
		# Clear sensitive fields for privacy
		frappe.db.set_value("Payment Transaction", name, {
			"payer_email": None,
			"entity_name": None,
			"entity_registration": None
		})
