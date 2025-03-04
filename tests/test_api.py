# tests/test_api.py

import unittest
from src.api import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_detect_endpoint_without_image(self):
        response = self.app.post('/detect')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

if __name__ == "__main__":
    unittest.main()
