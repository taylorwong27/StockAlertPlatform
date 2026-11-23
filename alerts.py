import os
import requests
import json
import tempfile
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load information from .env
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(message):
    """Send a message through Telegram Bot."""

    if not BOT_TOKEN or not CHAT_ID:
        return {
            "success": False,
            "error": "Missing Bot Token or Chat ID"
        }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if result.get("ok"):
            return {
                "success": True,
                "error": None
            }

        return {
            "success": False,
            "error": result.get("description", "Unknown error")
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def send_discord_message(message):
    """Send a message through Discord Webhook."""

    if not DISCORD_WEBHOOK_URL:
        return {
            "success": False,
            "error": "Missing Discord Webhook URL"
        }

    data = {
        "content": message
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=data,
            timeout=10
        )

        if response.status_code in [200, 204]:
            return {
                "success": True,
                "error": None
            }

        return {
            "success": False,
            "error": response.text
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }
    
def send_alert(message, channel):
    """Send an alert through the selected channel."""

    if channel == "telegram":
        return send_telegram_message(message)

    elif channel == "discord":
        return send_discord_message(message)

    else:
        return {
            "success": False,
            "error": "Invalid notification channel"
        }
    
def check_price_alert(price, threshold, direction):
    if direction == "above":
        return price >= threshold

    elif direction == "below":
        return price <= threshold

    else:
        return False

HISTORY_FILE = "alert_history.json"


def load_alert_history():
    """Load alert history without silently discarding damaged records."""

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            history = json.load(file)

    except FileNotFoundError:
        return {"alerts": []}

    except json.JSONDecodeError as error:
        raise ValueError(
            "Alert history JSON is corrupted. "
            "Please repair or restore the file before sending alerts."
        ) from error

    except OSError as error:
        raise OSError(
            "Unable to read alert history. "
            "Please check file permissions."
        ) from error

    if not isinstance(history, dict):
        raise ValueError("Alert history must be a JSON object.")

    if not isinstance(history.get("alerts"), list):
        raise ValueError("Alert history must contain an alerts list.")

    for alert in history["alerts"]:
        if not isinstance(alert, dict):
            raise ValueError("Alert history contains an invalid alert record.")

        if "alert_id" in alert and not isinstance(alert["alert_id"], str):
            raise ValueError("Alert history contains an invalid alert ID.")
    return history

def save_alert_history(history):
    """Save alert history using an atomic file replacement."""

    directory = os.path.dirname(
        os.path.abspath(HISTORY_FILE)
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".alert_history_",
            suffix=".tmp",
            delete=False
        ) as temp_file:
            temp_path = temp_file.name
            json.dump(history, temp_file, indent=4)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, HISTORY_FILE)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def process_price_alert(
    ticker,
    price,
    threshold,
    direction,
    channel,
    signal="N/A",
    latest_date=None
):
    """Check price condition and prevent duplicate notifications."""

    # Check whether the price condition is met
    if not check_price_alert(price, threshold, direction):
        return {
            "success": False,
            "error": "Price condition not met"
        }

    # Load previous alert records
    history = load_alert_history()

    # Create a unique alert ID
    alert_id = f"{ticker.upper()}_{direction}_{float(threshold):.2f}_{channel.lower()}"
    # Check whether this alert has already been sent
    for alert in history["alerts"]:
        if alert.get("alert_id") == alert_id:
            return {
                "success": False,
                "error": "Duplicate alert already sent"
            }
    # Create notification message
    triggered_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    price_date = str(latest_date) if latest_date is not None else "Not available"
    
    message = f"""

    STOCK PRICE ALERT

    Stock: {ticker.upper()}

    Current Price: ${price:.2f}

    Target Price: ${threshold:.2f}

    Condition: {direction.upper()}

    Trading Signal: {signal}

    Price Date: {price_date}

    Triggered At: {triggered_at}

    """

    # Send notification
    result = send_alert(message, channel)

    # Save record only if notification was successful
    if result["success"]:
        history["alerts"].append({
            "alert_id": alert_id,
            "ticker": ticker.upper(),
            "condition": direction,
            "threshold": threshold,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "price_date": price_date
        })

        try:
            save_alert_history(history)
        except OSError:
            return {
                "success": True,
                "error": (
                    "Notification sent, but alert history could not be saved. "
                    "A duplicate notification may be sent next time."
                ),
                "history_saved": False
            }
    return result
        
if __name__ == "__main__":

    message = "TEST: Stock Alert Platform notification is working!"
    
# Test duplicate prevention
    print("\nDuplicate alert tests:")

    first = process_price_alert(
        "AAPL", 155, 150, "above", "telegram"
    )
    print("First attempt:", first)

    second = process_price_alert(
        "AAPL", 155, 150, "above", "telegram"
    )
    print("Second attempt:", second)

# Test alert history
    history = load_alert_history()
    print("Alert history:", history)

    save_alert_history(history)
    print("Alert history saved successfully!")
