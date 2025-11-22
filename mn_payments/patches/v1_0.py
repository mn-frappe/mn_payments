import frappe


def create_default_ebarimt_settings():
    """Create a default eBarimt Settings doc if none exists."""
    if not frappe.db.exists("Ebarimt Settings", "Ebarimt Settings"):
        doc = frappe.get_doc(
            {
                "doctype": "Ebarimt Settings",
                "posapi_endpoint": "http://localhost:7080",
                "pos_no": "POS01",
                "merchant_tin": "",
                "auto_save_to_db": 1,
                "auto_send_email": 0,
            }
        )
        doc.insert(ignore_permissions=True)


# Register for direct patch invocation
def execute():
    create_default_ebarimt_settings()
