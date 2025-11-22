import unittest

from mn_payments.qpay.client import append_query_params


class TestQPayClientUtils(unittest.TestCase):
    def test_append_query_params_new(self):
        url = "https://example.com/callback"
        params = {"txn": "TX123"}
        merged = append_query_params(url, params)
        self.assertIn("txn=TX123", merged)

    def test_append_query_params_existing(self):
        url = "https://example.com/callback?a=1"
        params = {"txn": "TX123"}
        merged = append_query_params(url, params)
        self.assertIn("a=1", merged)
        self.assertIn("txn=TX123", merged)


if __name__ == "__main__":
    unittest.main()
