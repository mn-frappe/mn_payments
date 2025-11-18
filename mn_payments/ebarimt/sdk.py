"""
Compatibility layer for old import paths
"""

# Import from new SDK location
from mn_payments.sdk.ebarimt import *  # noqa
from mn_payments.sdk.ebarimt import __all__

# Re-export everything
__all__ = __all__
