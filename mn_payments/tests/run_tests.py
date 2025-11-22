#!/usr/bin/env python3
"""
Test runner for MN Payments app.

Run with: bench run-tests --app mn_payments
Or directly: python mn_payments/tests/run_tests.py
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    # In Frappe environment, use frappe's test runner
    try:
        import frappe
        from frappe.commands.testing import run_tests
        run_tests(app="mn_payments")
    except ImportError:
        print("Frappe not available. Install dependencies and run with pytest:")
        print("pip install -r requirements-dev.txt")
        print("pytest")
        sys.exit(1)