"""
Compatibility layer for old import paths
"""

# Import from new SDK location
from mn_payments.sdk.qpay import *  # noqa
from mn_payments.sdk.qpay import __all__

# Re-export everything
__all__ = __all__
