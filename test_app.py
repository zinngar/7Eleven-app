import unittest
from unittest.mock import patch, Mock
import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.app.testing = True
        self.app = app.app.test_client()

    @patch('functions.get_fuel_prices')
    def test_index(self, mock_get_fuel_prices):
        mock_get_fuel_prices.return_value = []
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    @patch('httpx.post')
    @patch('httpx.get')
    @patch('functions.getStores')
    @patch('functions.lockedPrices')
    def test_login(self, mock_locked_prices, mock_get_stores, mock_get, mock_post):
        mock_post.return_value.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
        }
        mock_get.return_value.json.return_value = {
            "id": "test_user",
            "first_name": "Test",
            "card_balance": 10.0,
        }
        mock_get_stores.return_value = b'[]'
        def mock_lp_side_effect():
            from flask import session
            session['fuelLockStatus'] = 0
            return ("", 0, "", "", "", "", "")
        mock_locked_prices.side_effect = mock_lp_side_effect
        response = self.app.post('/login', data={
            "email": "test@example.com",
            "password": "password",
            "device_id": "test_device_id",
        })
        self.assertEqual(response.status_code, 302)

    @patch('httpx.post')
    @patch('httpx.get')
    @patch('functions.get_fuel_prices')
    @patch('functions.getStores')
    @patch('functions.lockedPrices')
    def test_lockin(self, mock_locked_prices, mock_get_stores, mock_get_fuel_prices, mock_get, mock_post):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['access_token'] = 'test_access_token'
                sess['accountID'] = 'test_account_id'

        mock_get_fuel_prices.return_value = [
            {
                "fuel_type": "57",
                "price": 123.4,
                "postcode": "1234",
                "latitude": 1.234,
                "longitude": 1.234,
            }
        ]

        mock_post.side_effect = [
            Mock(content='{"CheapestFuelTypeStores": [{"FuelPrices": [{"Ean": "57", "Price": 123.4}]}]}'),
            Mock(content='{"Status": "0", "TotalLitres": 10.0}')
        ]
        mock_locked_prices.return_value = ("", 0, "", "", "", "", "")

        response = self.app.post('/lockin', data={
            "fueltype": "57",
            "submit": "automatic",
        })
        self.assertEqual(response.status_code, 302)

if __name__ == '__main__':
    unittest.main()
