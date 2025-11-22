import frappe
from frappe import _
from frappe.model.document import Document


class EbarimtSettings(Document):
    def validate(self):
        # basic validation
        if not self.posapi_endpoint:
            self.posapi_endpoint = "http://localhost:7080"

    def get_client_config(self):
        """Return config dict for SDK client initialization."""
        return {
            "endpoint": (self.posapi_endpoint or "http://localhost:7080").rstrip("/"),
            "pos_no": self.pos_no,
            "merchant_tin": self.merchant_tin,
            "save_to_db": bool(self.auto_save_to_db),
            "send_email": bool(self.auto_send_email),
            "merchant_registration_no": self.merchant_registration_no,
        }


@frappe.whitelist()
def get_ebarimt_settings():
    """Convenience method to return a single Ebarimt Settings doc"""
    if not frappe.db.exists("Ebarimt Settings", "Ebarimt Settings"):
        frappe.throw(_("eBarimt Settings not configured"))
    return frappe.get_doc("Ebarimt Settings", "Ebarimt Settings")
