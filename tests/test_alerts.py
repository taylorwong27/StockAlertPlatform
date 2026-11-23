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


def test_notification_sent_but_history_save_failed():
    from unittest.mock import patch
    import alerts

    with patch.object(
        alerts,
        "load_alert_history",
        return_value={"alerts": []}
    ), patch.object(
        alerts,
        "send_alert",
        return_value={"success": True, "error": None}
    ), patch.object(
        alerts,
        "save_alert_history",
        side_effect=OSError("Disk full")
    ):
        result = alerts.process_price_alert(
            ticker="AAPL",
            price=155,
            threshold=150,
            direction="above",
            channel="telegram"
        )

    assert result["success"] is True
    assert result["history_saved"] is False
    assert "could not be saved" in result["error"]


if __name__ == "__main__":
    unittest.main()