"""
QPay Python SDK
Python implementation of qpay-go SDK for Mongolian payment gateway

Supports QPay API v1, v2, and Quick merchant onboarding
"""

__all__ = [
    "QPayClient",
    "QPayVersion",
    "QPayConfig",
    "QPayInvoice",
    "QPayInvoiceDetails",
    "QPayAuthToken",
]

import requests
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json


class QPayVersion(Enum):
    """QPay API versions"""
    V1 = "v1"
    V2 = "v2"
    QUICK = "quick"


@dataclass
class QPayConfig:
    """QPay configuration"""
    endpoint: str
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    callback_url: str = ""
    invoice_code: str = ""
    merchant_id: str = ""
    terminal_id: str = ""


@dataclass
class QPayInvoice:
    """QPay Invoice"""
    invoice_id: str
    qr_text: str
    qr_image: str
    qpay_short_url: str
    urls: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class QPayInvoiceDetails:
    """Detailed invoice information"""
    invoice_id: str
    invoice_status: str
    total_amount: int
    invoice_description: str
    sender_invoice_no: str
    transactions: List[Dict[str, Any]] = field(default_factory=list)


class QPayAuthToken:
    """OAuth2 token management"""
    
    def __init__(self, token_data: Dict[str, Any]):
        self.access_token = token_data.get("access_token", "")
        self.refresh_token = token_data.get("refresh_token", "")
        self.expires_in = token_data.get("expires_in", 0)
        self.refresh_expires_in = token_data.get("refresh_expires_in", 0)
        self.token_type = token_data.get("token_type", "Bearer")
        
        # Calculate expiry times
        now = datetime.now()
        self.expires_at = now + timedelta(seconds=self.expires_in)
        self.refresh_expires_at = now + timedelta(seconds=self.refresh_expires_in)
    
    def is_valid(self) -> bool:
        """Check if token is still valid (with 5 min buffer)"""
        return datetime.now() < (self.expires_at - timedelta(minutes=5))
    
    def can_refresh(self) -> bool:
        """Check if refresh token is still valid"""
        return datetime.now() < self.refresh_expires_at


class QPayClient:
    """
    QPay Python Client (API v2)
    
    Example usage:
        client = QPayClient(QPayConfig(
            endpoint="https://merchant.qpay.mn/v2",
            username="your_username",
            password="your_password",
            callback_url="https://yoursite.com/callback",
            invoice_code="YOUR_CODE",
            merchant_id="YOUR_MERCHANT_ID"
        ))
        
        # Create invoice
        invoice = client.create_invoice(
            sender_code="ORDER001",
            receiver_code="CUSTOMER001",
            description="Product Purchase",
            amount=10000
        )
        
        # Check payment
        payment = client.check_payment(invoice.invoice_id)
    """
    
    def __init__(self, config: QPayConfig):
        self.config = config
        self.session = requests.Session()
        self.token: Optional[QPayAuthToken] = None
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QPayPythonSDK/1.0'
        })
    
    def _authenticate(self) -> QPayAuthToken:
        """Authenticate with QPay OAuth2"""
        # Check if we have a valid token
        if self.token and self.token.is_valid():
            return self.token
        
        # Try to refresh if possible
        if self.token and self.token.can_refresh():
            return self._refresh_token()
        
        # Get new token
        url = f"{self.config.endpoint}/auth/token"
        
        payload = {
            "username": self.config.username,
            "password": self.config.password
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        self.token = QPayAuthToken(token_data)
        
        return self.token
    
    def _refresh_token(self) -> QPayAuthToken:
        """Refresh access token"""
        if not self.token:
            return self._authenticate()
        
        url = f"{self.config.endpoint}/auth/refresh"
        
        payload = {
            "refresh_token": self.token.refresh_token
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        self.token = QPayAuthToken(token_data)
        
        return self.token
    
    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to QPay API"""
        # Ensure we have valid token
        token = self._authenticate()
        
        # Build URL
        url = f"{self.config.endpoint}{path}"
        
        # Set authorization header
        headers = {
            'Authorization': f'{token.token_type} {token.access_token}'
        }
        
        # Make request
        response = self.session.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=headers,
            timeout=30
        )
        
        # Handle errors
        if response.status_code != 200:
            error_data = response.text
            raise ValueError(f"QPay API Error ({response.status_code}): {error_data}")
        
        return response.json()
    
    def create_invoice(
        self,
        sender_code: str,
        description: str,
        amount: int,
        receiver_code: str = "",
        sender_branch_code: str = "",
        callback_params: Optional[Dict[str, str]] = None
    ) -> QPayInvoice:
        """
        Create QPay invoice
        
        Args:
            sender_code: Unique order/invoice number from merchant
            description: Payment description
            amount: Amount in MNT
            receiver_code: Customer identifier (optional)
            sender_branch_code: Branch code (optional)
            callback_params: Additional params for callback URL
        
        Returns:
            QPayInvoice with QR code and deep links
        """
        # Build callback URL with params
        callback_url = self.config.callback_url
        if callback_params:
            params_str = "&".join([f"{k}={v}" for k, v in callback_params.items()])
            callback_url = f"{callback_url}?{params_str}"
        
        payload = {
            "invoice_code": self.config.invoice_code,
            "sender_invoice_no": sender_code,
            "sender_branch_code": sender_branch_code or "",
            "invoice_receiver_code": receiver_code,
            "invoice_description": description,
            "amount": amount,
            "callback_url": callback_url
        }
        
        response = self._request("POST", "/invoice", data=payload)
        
        return QPayInvoice(
            invoice_id=response.get("invoice_id", ""),
            qr_text=response.get("qr_text", ""),
            qr_image=response.get("qr_image", ""),
            qpay_short_url=response.get("qPay_shortUrl", ""),
            urls=response.get("urls", [])
        )
    
    def get_invoice(self, invoice_id: str) -> QPayInvoiceDetails:
        """Get invoice details"""
        response = self._request("GET", f"/invoice/{invoice_id}")
        
        return QPayInvoiceDetails(
            invoice_id=response.get("invoice_id", ""),
            invoice_status=response.get("invoice_status", ""),
            total_amount=response.get("total_amount", 0),
            invoice_description=response.get("invoice_description", ""),
            sender_invoice_no=response.get("sender_invoice_no", ""),
            transactions=response.get("transactions", [])
        )
    
    def cancel_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Cancel invoice"""
        return self._request("DELETE", f"/invoice/{invoice_id}")
    
    def check_payment(
        self,
        invoice_id: str,
        page_number: int = 1,
        page_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Check payment status for invoice
        
        Args:
            invoice_id: Invoice ID to check
            page_number: Page number for pagination
            page_limit: Results per page (max 100)
        
        Returns:
            Payment check response with transaction details
        """
        payload = {
            "object_type": "INVOICE",
            "object_id": invoice_id,
            "offset": {
                "page_number": page_number,
                "page_limit": min(page_limit, 100)
            }
        }
        
        return self._request("POST", "/payment/check", data=payload)
    
    def get_payment(self, invoice_id: str) -> Dict[str, Any]:
        """Get payment details"""
        return self._request("GET", f"/payment/get/{invoice_id}")
    
    def cancel_payment(self, invoice_id: str, payment_uuid: str) -> Dict[str, Any]:
        """
        Cancel a payment
        
        Args:
            invoice_id: Invoice ID
            payment_uuid: Payment UUID to cancel
        
        Returns:
            Cancellation response
        """
        payload = {
            "callback_url": f"{self.config.callback_url}/{payment_uuid}",
            "note": f"Cancel payment - {invoice_id}"
        }
        
        return self._request("DELETE", f"/payment/cancel/{invoice_id}", data=payload)
    
    def refund_payment(self, invoice_id: str, payment_uuid: str) -> Dict[str, Any]:
        """
        Refund a payment
        
        Args:
            invoice_id: Invoice ID
            payment_uuid: Payment UUID to refund
        
        Returns:
            Refund response
        """
        payload = {
            "callback_url": f"{self.config.callback_url}/{payment_uuid}",
            "note": f"Refund payment - {invoice_id}"
        }
        
        return self._request("DELETE", f"/payment/refund/{invoice_id}", data=payload)


class QPayClientV1:
    """
    QPay Python Client (API v1) - Legacy support
    
    Example usage:
        client = QPayClientV1(QPayConfig(
            endpoint="https://merchant.qpay.mn/v1",
            client_id="your_client_id",
            client_secret="your_client_secret",
            merchant_id="YOUR_MERCHANT_ID",
            template_id="YOUR_TEMPLATE_ID"
        ))
    """
    
    def __init__(self, config: QPayConfig):
        self.config = config
        self.session = requests.Session()
        self.token: Optional[QPayAuthToken] = None
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QPayPythonSDK/1.0'
        })
    
    def _authenticate(self) -> QPayAuthToken:
        """Authenticate with QPay v1 OAuth2"""
        if self.token and self.token.is_valid():
            return self.token
        
        url = f"{self.config.endpoint}/auth/token"
        
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client",
            "refresh_token": ""
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        self.token = QPayAuthToken(token_data)
        
        return self.token
    
    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request"""
        token = self._authenticate()
        
        url = f"{self.config.endpoint}{path}"
        
        headers = {
            'Authorization': f'{token.token_type} {token.access_token}'
        }
        
        response = self.session.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise ValueError(f"QPay API Error ({response.status_code}): {response.text}")
        
        return response.json()
    
    def create_invoice(
        self,
        bill_no: str,
        description: str,
        amount: float,
        receiver: Optional[Dict[str, Any]] = None
    ) -> QPayInvoice:
        """Create invoice using v1 API"""
        payload = {
            "template_id": self.config.terminal_id,
            "merchant_id": self.config.merchant_id,
            "branch_id": "",
            "pos_id": "",
            "bill_no": bill_no,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": description,
            "amount": amount,
            "receiver": receiver or {}
        }
        
        response = self._request("POST", "/bill/create", data=payload)
        
        return QPayInvoice(
            invoice_id=str(response.get("payment_id", "")),
            qr_text=response.get("qPay_QRcode", ""),
            qr_image=response.get("qPay_QRimage", ""),
            qpay_short_url=response.get("qPay_url", ""),
            urls=response.get("qPay_deeplink", [])
        )
    
    def check_payment(self, payment_id: str) -> Dict[str, Any]:
        """Check payment status"""
        return self._request("GET", f"/payment/check/{payment_id}")


class QPayQuickClient:
    """
    QPay Quick Merchant Onboarding Client
    
    Used for registering new merchants with QPay
    
    Example usage:
        client = QPayQuickClient(QPayConfig(
            endpoint="https://merchant.qpay.mn/quick",
            username="your_username",
            password="your_password",
            terminal_id="YOUR_TERMINAL_ID"
        ))
        
        # Register company merchant
        merchant = client.create_company(
            owner_reg_no="УБ12345678",
            register_no="1234567",
            name="My Business LLC",
            mcc_code="5411"
        )
    """
    
    def __init__(self, config: QPayConfig):
        self.config = config
        self.session = requests.Session()
        self.token: Optional[QPayAuthToken] = None
        
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _authenticate(self) -> QPayAuthToken:
        """Authenticate with QPay Quick"""
        if self.token and self.token.is_valid():
            return self.token
        
        url = f"{self.config.endpoint}/auth/token"
        
        payload = {
            "username": self.config.username,
            "password": self.config.password
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        self.token = QPayAuthToken(token_data)
        
        return self.token
    
    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request"""
        token = self._authenticate()
        
        url = f"{self.config.endpoint}{path}"
        
        headers = {
            'Authorization': f'{token.token_type} {token.access_token}'
        }
        
        response = self.session.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise ValueError(f"QPay Quick API Error: {response.text}")
        
        return response.json()
    
    def create_company(
        self,
        owner_reg_no: str,
        owner_first_name: str,
        owner_last_name: str,
        register_no: str,
        name: str,
        mcc_code: str,
        city: str,
        district: str,
        address: str,
        phone: str,
        email: str,
        location_lat: str = "",
        location_lng: str = ""
    ) -> Dict[str, Any]:
        """Register company merchant"""
        payload = {
            "owner_register_no": owner_reg_no,
            "owner_first_name": owner_first_name,
            "owner_last_name": owner_last_name,
            "register_nubmer": register_no,
            "name": name,
            "mcc_code": mcc_code,
            "city": city,
            "district": district,
            "address": address,
            "phone": phone,
            "email": email,
            "location_lat": location_lat,
            "location_lng": location_lng
        }
        
        return self._request("POST", "/merchant/company", data=payload)
    
    def create_person(
        self,
        register_no: str,
        first_name: str,
        last_name: str,
        mcc_code: str,
        city: str,
        district: str,
        address: str,
        phone: str,
        email: str
    ) -> Dict[str, Any]:
        """Register person merchant"""
        payload = {
            "register_number": register_no,
            "first_name": first_name,
            "last_name": last_name,
            "mcc_code": mcc_code,
            "city": city,
            "district": district,
            "address": address,
            "phone": phone,
            "email": email
        }
        
        return self._request("POST", "/merchant/person", data=payload)
    
    def get_merchant(self, merchant_id: str) -> Dict[str, Any]:
        """Get merchant details"""
        return self._request("GET", f"/merchant/{merchant_id}")
    
    def list_merchants(self, page_number: int = 1, page_limit: int = 10) -> Dict[str, Any]:
        """List all merchants"""
        payload = {
            "offset": {
                "page_number": page_number,
                "page_limit": page_limit
            }
        }
        
        return self._request("POST", "/merchant/list", data=payload)
