"""
Ebarimt POS 3.0 Python SDK
Complete Python implementation for Mongolian tax receipt generation

Features:
- VAT and city tax calculations
- Receipt generation with QR codes
- Database persistence (Frappe/MariaDB)
- Email notifications
- Tax authority API integration
"""

__all__ = [
    "EbarimtClient",
    "TaxType",
    "ReceiptType",
    "BarcodeType",
    "PosStatus",
    "ReceiptItem",
    "CreateReceiptRequest",
    "ReceiptResponse",
    "VATCalculator",
    "MerchantInfo",
]

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import json
from datetime import datetime
import qrcode
from io import BytesIO
import base64


class TaxType(Enum):
    """Tax types for products/services"""
    VAT_ABLE = "VAT_ABLE"  # НӨАТ тооцох бүтээгдэхүүн, үйлчилгээ
    VAT_FREE = "VAT_FREE"  # НӨАТ-аас чөлөөлөгдөх бүтээгдэхүүн, үйлчилгээ
    VAT_ZERO = "VAT_ZERO"  # НӨАТ-н 0 хувь тооцох бүтээгдэхүүн, үйлчилгээ
    NOT_VAT = "NOT_VAT"    # Монгол улсын хилийн гадна борлуулсан бүтээгдэхүүн үйлчилгээ


class ReceiptType(Enum):
    """Receipt types"""
    B2C_RECEIPT = "B2C_RECEIPT"  # Business to Consumer
    B2B_RECEIPT = "B2B_RECEIPT"  # Business to Business
    B2C_INVOICE = "B2C_INVOICE"  # Consumer invoice
    B2B_INVOICE = "B2B_INVOICE"  # Business invoice


class BarcodeType(Enum):
    """Barcode types"""
    UNDEFINED = "UNDEFINED"
    GS1 = "GS1"
    ISBN = "ISBN"


class PosStatus(Enum):
    """POS response status"""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PAYMENT = "PAYMENT"


@dataclass
class ReceiptItem:
    """Item in a receipt"""
    name: str
    tax_type: TaxType
    classification_code: str
    qty: float
    total_amount: float
    measure_unit: str
    tax_product_code: str
    is_city_tax: bool = False
    bar_code: str = ""
    bar_code_type: BarcodeType = BarcodeType.UNDEFINED


@dataclass
class CreateReceiptRequest:
    """Request to create tax receipt"""
    items: List[ReceiptItem]
    branch_no: str
    district_code: str
    org_code: Optional[str] = None  # Customer TIN for B2B
    mail_to: Optional[str] = None
    report_month: Optional[str] = None
    

@dataclass
class ReceiptResponse:
    """Response from tax authority"""
    id: str  # Bill ID
    lottery: str
    qr_data: str
    date: str
    total_amount: float
    total_vat: float
    total_city_tax: float
    status: str
    message: str
    type: str
    receipts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MerchantInfo:
    """Merchant information from tax authority"""
    name: str
    vat_payer: bool
    city_payer: bool
    free_project: bool
    found: bool
    vat_payer_registered_date: Optional[str] = None


class VATCalculator:
    """VAT and City Tax calculations - CRITICAL: Must match government formulas"""
    
    VAT_RATE = Decimal("0.10")      # 10% VAT
    CITY_TAX_RATE = Decimal("0.01")  # 1% City tax
    
    @staticmethod
    def _to_decimal(amount: float) -> Decimal:
        """Convert float to Decimal for precise calculations"""
        return Decimal(str(amount))
    
    @staticmethod
    def _round(value: Decimal) -> float:
        """Round to 2 decimal places"""
        rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(rounded)
    
    @classmethod
    def get_vat(cls, total_amount: float) -> float:
        """
        Calculate VAT from total amount (VAT inclusive)
        Formula: amount / 1.10 * 0.10
        """
        amount = cls._to_decimal(total_amount)
        divisor = Decimal("1") + cls.VAT_RATE
        vat = (amount / divisor) * cls.VAT_RATE
        return cls._round(vat)
    
    @classmethod
    def get_vat_with_city_tax(cls, total_amount: float) -> float:
        """
        Calculate VAT from total amount with city tax
        Formula: amount / (1 + 0.10 + 0.01) * 0.10
        """
        amount = cls._to_decimal(total_amount)
        divisor = Decimal("1") + cls.VAT_RATE + cls.CITY_TAX_RATE
        vat = (amount / divisor) * cls.VAT_RATE
        return cls._round(vat)
    
    @classmethod
    def get_city_tax(cls, total_amount: float) -> float:
        """
        Calculate city tax from total amount with VAT
        Formula: amount / (1 + 0.10 + 0.01) * 0.01
        """
        amount = cls._to_decimal(total_amount)
        divisor = Decimal("1") + cls.VAT_RATE + cls.CITY_TAX_RATE
        city_tax = (amount / divisor) * cls.CITY_TAX_RATE
        return cls._round(city_tax)
    
    @classmethod
    def get_city_tax_without_vat(cls, total_amount: float) -> float:
        """
        Calculate city tax from total amount without VAT
        Formula: amount / 1.01 * 0.01
        """
        amount = cls._to_decimal(total_amount)
        divisor = Decimal("1") + cls.CITY_TAX_RATE
        city_tax = (amount / divisor) * cls.CITY_TAX_RATE
        return cls._round(city_tax)
    
    @classmethod
    def number_precision(cls, amount: float) -> float:
        """Round number to 2 decimal precision"""
        return cls._round(cls._to_decimal(amount))


class EbarimtClient:
    """
    Ebarimt POS 3.0 Python Client
    
    IMPORTANT: This client connects to LOCAL PosAPI service (localhost:7080)
    NOT to remote api.ebarimt.mn directly. PosAPI DEB package must be installed.
    
    Example usage:
        # Initialize from Frappe settings
        settings = frappe.get_single('eBarimt Settings')
        client = EbarimtClient(settings=settings)
        
        # Or manual initialization
        client = EbarimtClient(
            endpoint="http://localhost:7080",
            pos_no="POS001",
            merchant_tin="1234567890"
        )
        
        response = client.create_receipt(CreateReceiptRequest(
            items=[
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
            ],
            branch_no="001",
            district_code="UB01"
        ))
    """
    
    def __init__(
        self,
        endpoint: str = None,
        pos_no: str = None,
        merchant_tin: str = None,
        save_to_db: bool = True,
        send_email: bool = True,
        settings=None
    ):
        # Initialize from settings if provided
        if settings:
            self.endpoint = (settings.posapi_endpoint or "http://localhost:7080").rstrip('/')
            self.pos_no = settings.pos_no
            self.merchant_tin = settings.merchant_tin
            self.save_to_db = settings.auto_save_to_db
            self.send_email = settings.auto_send_email
            self.merchant_registration_no = settings.merchant_registration_no
        else:
            # Manual initialization (backward compatibility)
            self.endpoint = (endpoint or "http://localhost:7080").rstrip('/')
            self.pos_no = pos_no
            self.merchant_tin = merchant_tin
            self.save_to_db = save_to_db
            self.send_email = send_email
            self.merchant_registration_no = None
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'EbarimtPythonSDK/1.0'
        })
    
    def _validate_posapi_connection(self):
        """Verify PosAPI service is running"""
        try:
            response = self.session.get(f"{self.endpoint}/info", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            frappe.throw(f"Cannot connect to PosAPI at {self.endpoint}: {str(e)}")
    
    def get_info(self, tin: str) -> MerchantInfo:
        """Get merchant information from tax authority via PosAPI"""
        # PosAPI proxies the request to api.ebarimt.mn
        url = f"{self.endpoint}/api/info/check/getInfo?tin={tin}"
        
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != 200:
            raise ValueError(f"Failed to get merchant info: {data.get('msg')}")
        
        info_data = data.get("data", {})
        
        return MerchantInfo(
            name=info_data.get("name", ""),
            vat_payer=info_data.get("vatPayer", False),
            city_payer=info_data.get("cityPayer", False),
            free_project=info_data.get("freeProject", False),
            found=info_data.get("found", False),
            vat_payer_registered_date=info_data.get("vatpayerRegisteredDate")
        )
    
    def get_tin_info(self, reg_no: str) -> int:
        """Get TIN from registration number"""
        url = f"https://api.ebarimt.mn/api/info/check/getTinInfo?regNo={reg_no}"
        
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != 200:
            raise ValueError(f"Failed to get TIN: {data.get('msg')}")
        
        return data.get("data", 0)
    
    def create_receipt(self, request: CreateReceiptRequest) -> ReceiptResponse:
        """
        Create tax receipt
        
        Main flow:
        1. Get merchant VAT status
        2. Group items by tax type
        3. Send NO_VAT items first (if any)
        4. Send other tax types
        5. Return response with bill ID, lottery, QR code
        """
        # Get merchant info to check VAT payer status
        merchant_info = self.get_info(self.merchant_tin)
        
        # Build receipt items grouped by tax type
        receipts_by_tax = self._build_receipt_items(request.items, merchant_info)
        
        # Determine receipt type
        receipt_type = ReceiptType.B2B_RECEIPT if request.org_code else ReceiptType.B2C_RECEIPT
        
        # Get customer TIN if B2B
        customer_tin = ""
        if request.org_code:
            try:
                customer_tin = str(self.get_tin_info(request.org_code))
            except Exception:
                pass
        
        # Send NO_VAT items first if exists
        if TaxType.NOT_VAT in receipts_by_tax:
            no_vat_request = self._build_request(
                {TaxType.NOT_VAT: receipts_by_tax[TaxType.NOT_VAT]},
                request,
                receipt_type,
                customer_tin
            )
            
            no_vat_response = self._send_receipt(no_vat_request)
            
            if no_vat_response.get("status") != PosStatus.SUCCESS.value:
                raise ValueError(f"NO_VAT receipt failed: {no_vat_response.get('message')}")
            
            # Remove NO_VAT from dict
            del receipts_by_tax[TaxType.NOT_VAT]
        
        # Send other tax types
        if receipts_by_tax:
            main_request = self._build_request(
                receipts_by_tax,
                request,
                receipt_type,
                customer_tin
            )
            
            main_response = self._send_receipt(main_request)
            
            if main_response.get("status") != PosStatus.SUCCESS.value:
                raise ValueError(f"Receipt failed: {main_response.get('message')}")
            
            # Create response object
            receipt_response = ReceiptResponse(
                id=main_response.get("id", ""),
                lottery=main_response.get("lottery", ""),
                qr_data=main_response.get("qrData", ""),
                date=main_response.get("date", ""),
                total_amount=main_response.get("totalAmount", 0),
                total_vat=main_response.get("totalVat", 0),
                total_city_tax=main_response.get("totalCityTax", 0),
                status=main_response.get("status", ""),
                message=main_response.get("message", ""),
                type=receipt_type.value,
                receipts=main_response.get("receipts", [])
            )
            
            # Save to database if configured
            if self.save_to_db:
                self._save_to_db(receipt_response, request)
            
            # Send email if configured
            if self.send_email and request.mail_to:
                self._send_email(receipt_response, request.mail_to)
            
            return receipt_response
        
        raise ValueError("No items to process")
    
    def _build_receipt_items(
        self,
        items: List[ReceiptItem],
        merchant_info: MerchantInfo
    ) -> Dict[TaxType, Dict[str, Any]]:
        """Group items by tax type and calculate totals"""
        receipts_by_tax = {}
        
        for item in items:
            if not item.tax_type or not item.classification_code:
                continue
            
            tax_type = item.tax_type
            
            # Initialize tax type group if not exists
            if tax_type not in receipts_by_tax:
                receipts_by_tax[tax_type] = {
                    "items": [],
                    "total_amount": 0.0,
                    "total_vat": 0.0,
                    "total_city_tax": 0.0
                }
            
            # Calculate VAT
            total_vat = 0.0
            if merchant_info.vat_payer and tax_type == TaxType.VAT_ABLE:
                if item.is_city_tax:
                    total_vat = VATCalculator.get_vat_with_city_tax(item.total_amount)
                else:
                    total_vat = VATCalculator.get_vat(item.total_amount)
            
            # Calculate city tax
            total_city_tax = 0.0
            if item.is_city_tax and tax_type == TaxType.VAT_ABLE:
                total_city_tax = VATCalculator.get_city_tax(item.total_amount)
            
            # Calculate unit price
            unit_price = VATCalculator.number_precision(item.total_amount / item.qty)
            
            # Build receipt item
            receipt_item = {
                "name": item.name,
                "barCode": item.bar_code,
                "barCodeType": item.bar_code_type.value,
                "classificationCode": item.classification_code,
                "taxProductCode": item.tax_product_code,
                "measureUnit": item.measure_unit,
                "qty": item.qty,
                "unitPrice": unit_price,
                "totalAmount": item.total_amount,
                "totalVat": total_vat,
                "totalCityTax": total_city_tax,
            }
            
            receipts_by_tax[tax_type]["items"].append(receipt_item)
            receipts_by_tax[tax_type]["total_amount"] += item.total_amount
            receipts_by_tax[tax_type]["total_vat"] += total_vat
            receipts_by_tax[tax_type]["total_city_tax"] += total_city_tax
        
        return receipts_by_tax
    
    def _build_request(
        self,
        receipts_by_tax: Dict[TaxType, Dict[str, Any]],
        request: CreateReceiptRequest,
        receipt_type: ReceiptType,
        customer_tin: str
    ) -> Dict[str, Any]:
        """Build receipt request for tax authority API"""
        # Build receipts array
        receipts = []
        total_amount = 0.0
        total_vat = 0.0
        total_city_tax = 0.0
        
        for tax_type, receipt_data in receipts_by_tax.items():
            receipts.append({
                "taxType": tax_type.value,
                "items": receipt_data["items"],
                "totalAmount": receipt_data["total_amount"],
                "totalVat": receipt_data["total_vat"],
                "totalCityTax": receipt_data["total_city_tax"]
            })
            
            total_amount += receipt_data["total_amount"]
            total_vat += receipt_data["total_vat"]
            total_city_tax += receipt_data["total_city_tax"]
        
        return {
            "merchantTin": self.merchant_tin,
            "posNo": self.pos_no,
            "branchNo": request.branch_no,
            "districtCode": request.district_code,
            "type": receipt_type.value,
            "customerTin": customer_tin,
            "consumerNo": "",
            "reportMonth": request.report_month,
            "totalAmount": total_amount,
            "totalVat": total_vat,
            "totalCityTax": total_city_tax,
            "receipts": receipts
        }
    
    def _send_receipt(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send receipt to tax authority"""
        url = f"{self.endpoint}/rest/receipt"
        
        response = self.session.post(url, json=request_data, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def _save_to_db(self, response: ReceiptResponse, request: CreateReceiptRequest):
        """
        Save receipt to Frappe database (MariaDB)
        
        ⚠️ CRITICAL LEGAL REQUIREMENT:
        NEVER save lottery_number or qr_data to database!
        These fields are ILLEGAL to store anywhere per Mongolian law.
        """
        if not self.save_to_db:
            return
        
        try:
            # Create Ebarimt Receipt document
            # NOTE: lottery and qr_data are NOT saved (legal requirement)
            receipt_doc = frappe.get_doc({
                "doctype": "Ebarimt Receipt",
                "bill_id": response.id,
                # "lottery_number": response.lottery,  # ❌ ILLEGAL - DO NOT SAVE
                # "qr_data": response.qr_data,          # ❌ ILLEGAL - DO NOT SAVE
                "receipt_date": response.date,
                "total_amount": float(response.total_amount),
                "total_vat": float(response.total_vat),
                "total_city_tax": float(response.total_city_tax),
                "receipt_type": response.type,
                "merchant_tin": self.merchant_tin,
                "pos_no": self.pos_no,
                "branch_no": request.branch_no,
                "district_code": request.district_code,
                "customer_tin": request.org_code or "",
                "status": response.status,
                "message": response.message
            })
            
            # Add receipt items as child table
            for receipt in response.receipts:
                tax_type = receipt.get("taxType", "")
                for item in receipt.get("items", []):
                    receipt_doc.append("items", {
                        "item_name": item.get("name", ""),
                        "classification_code": item.get("classificationCode", ""),
                        "tax_type": tax_type,
                        "qty": float(item.get("qty", 0)),
                        "unit_price": float(item.get("unitPrice", 0)),
                        "total_amount": float(item.get("totalAmount", 0)),
                        "total_vat": float(item.get("totalVat", 0)),
                        "total_city_tax": float(item.get("totalCityTax", 0)),
                        "measure_unit": item.get("measureUnit", ""),
                        "tax_product_code": item.get("taxProductCode", ""),
                        "bar_code": item.get("barCode", ""),
                        "bar_code_type": item.get("barCodeType", "")
                    })
            
            receipt_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Failed to save ebarimt receipt: {str(e)}", "Ebarimt DB Save Error")
    
    def _send_email(self, response: ReceiptResponse, email_to: str):
        """
        Send receipt via email using Frappe
        
        ⚠️ CRITICAL LEGAL REQUIREMENT:
        Lottery and QR data are passed as TEMPORARY VARIABLES only.
        They are sent via email and NEVER saved to database or files.
        Variables are destroyed after email is sent.
        """
        if not self.send_email or not email_to:
            return
        
        try:
            # Generate QR code image IN MEMORY ONLY (not saved to disk)
            qr_image_base64 = self._generate_qr_code_base64(response.qr_data)
            
            # Prepare email content
            # lottery and qr_data are temporary variables (not persisted)
            subject = f"🧾 Tax Receipt - {response.id}"
            
            context = {
                "bill_id": response.id,
                "lottery": response.lottery,  # Temporary - sent via email only
                "date": response.date,
                "total_amount": float(response.total_amount),
                "total_vat": float(response.total_vat),
                "total_city_tax": float(response.total_city_tax),
                "receipt_type": response.type,
                "qr_image_base64": qr_image_base64  # Embedded in email, not saved
            }
            
            message = frappe.render_template(
                "mn_payments/templates/emails/ebarimt_receipt.html",
                context
            )
            
            # Send email immediately
            frappe.sendmail(
                recipients=[email_to],
                subject=subject,
                message=message,
                header=["Tax Receipt", "green"],
                now=True
            )
            
            # Update receipt doc with email delivery status (but NOT lottery/QR)
            receipt = frappe.get_doc("Ebarimt Receipt", response.id)
            receipt.email_sent = 1
            receipt.email_sent_to = email_to
            receipt.email_sent_at = now_datetime()
            receipt.save(ignore_permissions=True)
            
            # Variables lottery and qr_data are destroyed here
            # They exist only in email sent to customer
            
        except Exception as e:
            frappe.log_error(f"Failed to send ebarimt email: {str(e)}", "Ebarimt Email Error")
    
    def _generate_qr_code_base64(self, qr_data: str) -> str:
        """
        Generate QR code image as base64 data URL for inline email display
        
        ⚠️ CRITICAL: QR code is generated IN MEMORY ONLY.
        NOT saved to file system. Used only in email HTML.
        
        Args:
            qr_data: QR code data string
            
        Returns:
            Base64 encoded data URL for embedding in HTML
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 IN MEMORY (not saved to disk)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Return data URL for embedding in HTML email
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            frappe.log_error(f"Failed to generate QR code: {str(e)}", "QR Code Error")
            return ""
    
    def _generate_qr_code_file(self, qr_data: str, bill_id: str):
        """
        Generate QR code and save to Frappe file system
        
        Args:
            qr_data: QR code data string
            bill_id: Bill ID for filename
            
        Returns:
            Frappe File document or None
        """
        if not qr_data:
            return None
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Create Frappe file document
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": f"ebarimt_qr_{bill_id}.png",
                "content": buffer.read(),
                "is_private": 0
            })
            file_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return file_doc
            
        except Exception as e:
            frappe.log_error(f"Failed to save QR code file: {str(e)}", "QR Code File Error")
            return None
    
    def calculate_totals(self, items: List[ReceiptItem]) -> Dict[str, float]:
        """Calculate total VAT, city tax, and amount for items"""
        total_vat = 0.0
        total_city_tax = 0.0
        total_amount = 0.0
        
        for item in items:
            total_amount += item.total_amount
            
            if item.tax_type == TaxType.VAT_ABLE:
                if item.is_city_tax:
                    total_vat += VATCalculator.get_vat_with_city_tax(item.total_amount)
                    total_city_tax += VATCalculator.get_city_tax(item.total_amount)
                else:
                    total_vat += VATCalculator.get_vat(item.total_amount)
            elif item.tax_type != TaxType.NOT_VAT and item.is_city_tax:
                total_city_tax += VATCalculator.get_city_tax_without_vat(item.total_amount)
        
        return {
            "total_amount": VATCalculator.number_precision(total_amount),
            "total_vat": VATCalculator.number_precision(total_vat),
            "total_city_tax": VATCalculator.number_precision(total_city_tax)
        }
