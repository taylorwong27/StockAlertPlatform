from unittest.mock import patch
import alerts


def test_alert_includes_price_date_and_utc_timestamp():
    with patch.object(alerts, "load_alert_history", return_value={"alerts": []}), \
         patch.object(alerts, "send_alert", return_value={"success": True, "error": None}) as send, \
         patch.object(alerts, "save_alert_history") as save:
        result = alerts.process_price_alert("AAPL", 155, 150, "above", "telegram", latest_date="2026-11-20")
    assert result["success"] is True
    assert "Price Date: 2026-11-20" in send.call_args.args[0]
    assert "UTC" in send.call_args.args[0]
    assert save.call_args.args[0]["alerts"][0]["price_date"] == "2026-11-20"


def test_corrupt_history_blocks_sending():
    with patch.object(alerts, "load_alert_history", side_effect=ValueError("corrupted")), \
         patch.object(alerts, "send_alert") as send:
        try:
            alerts.process_price_alert("AAPL", 155, 150, "above", "telegram")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected history error")
    send.assert_not_called()


def test_channels_have_independent_deduplication():
    history = {"alerts": []}
    def fake_save(updated):
        history["alerts"] = list(updated["alerts"])
    with patch.object(alerts, "load_alert_history", side_effect=lambda: {"alerts": list(history["alerts"])}), \
         patch.object(alerts, "send_alert", return_value={"success": True, "error": None}) as send, \
         patch.object(alerts, "save_alert_history", side_effect=fake_save):
        telegram = alerts.process_price_alert("AAPL", 155, 150, "above", "telegram")
        discord = alerts.process_price_alert("AAPL", 155, 150, "above", "discord")
        duplicate = alerts.process_price_alert("AAPL", 155, 150, "above", "telegram")
    assert telegram["success"] and discord["success"]
    assert duplicate["error"] == "Duplicate alert already sent"
    assert send.call_count == 2

def test_save_failure_reports_delivery_without_claiming_history_saved():
    with patch.object(alerts, "load_alert_history", return_value={"alerts": []}), \
         patch.object(alerts, "send_alert", return_value={"success": True, "error": None}), \
         patch.object(alerts, "save_alert_history", side_effect=OSError("disk full")):
        result = alerts.process_price_alert("AAPL", 155, 150, "above", "telegram")
    assert result["success"] is True
    assert result["history_saved"] is False
    assert "duplicate" in result["error"].lower()
