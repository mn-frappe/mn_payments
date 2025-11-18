# Copyright (c) 2025, Digital Consulting Service LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QPayInvoice(Document):
    """QPay Invoice"""
    
    def validate(self):
        """Validate invoice data"""
        # Validate amount is positive
        if self.amount and self.amount <= 0:
            frappe.throw(f"Invoice amount must be greater than 0. Got: {self.amount}")
    
    def before_insert(self):
        """Generate QR code image before saving"""
        if self.qr_text and not self.qr_image:
            self.generate_qr_image()
    
    def generate_qr_image(self):
        """Generate and attach QR code image"""
        try:
            import qrcode
            from io import BytesIO
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_text)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to file
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Create file document
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": f"qpay_qr_{self.invoice_id}.png",
                "attached_to_doctype": "QPay Invoice",
                "attached_to_name": self.name,
                "content": buffer.read(),
                "is_private": 0
            })
            file_doc.save(ignore_permissions=True)
            
            self.qr_image = file_doc.file_url
            
        except Exception as e:
            frappe.log_error(f"Failed to generate QR image: {str(e)}")
