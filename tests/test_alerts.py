import unittest
import tempfile
import os

import alerts


class TestPriceAlert(unittest.TestCase):

    def test_price_above_threshold(self):
        self.assertTrue(
            alerts.check_price_alert(160, 150, "above")
        )

    def test_price_below_threshold(self):
        self.assertTrue(
            alerts.check_price_alert(140, 150, "below")
        )

    def test_price_not_above_threshold(self):
        self.assertFalse(
            alerts.check_price_alert(140, 150, "above")
        )

    def test_price_not_below_threshold(self):
        self.assertFalse(
            alerts.check_price_alert(160, 150, "below")
        )

    def test_invalid_direction(self):
        self.assertFalse(
            alerts.check_price_alert(160, 150, "invalid")
        )


class TestAlertHistory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.original_history_file = alerts.HISTORY_FILE

        alerts.HISTORY_FILE = os.path.join(
            self.temp_dir.name,
            "alert_history.json"
        )

    def tearDown(self):
        alerts.HISTORY_FILE = self.original_history_file
        self.temp_dir.cleanup()

    def test_save_and_load_history(self):

        history = {
            "alerts": [
                {
                    "ticker": "AAPL",
                    "condition": "above",
                    "threshold": 150
                }
            ]
        }

        alerts.save_alert_history(history)

        loaded_history = alerts.load_alert_history()

        self.assertEqual(loaded_history, history)

    def test_duplicate_alert_prevention(self):

        original_send_alert = alerts.send_alert

        def fake_send_alert(message, channel):
            return {"success": True, "error": None}

        alerts.send_alert = fake_send_alert

        try:
            first_result = alerts.process_price_alert(
                "AAPL", 160, 150, "above", "telegram"
            )

            second_result = alerts.process_price_alert(
                "AAPL", 160, 150, "above", "telegram"
            )

            self.assertTrue(first_result["success"])

            self.assertFalse(second_result["success"])

            self.assertEqual(
                second_result["error"],
                "Duplicate alert already sent"
            )

        finally:
            alerts.send_alert = original_send_alert


if __name__ == "__main__":
    unittest.main()