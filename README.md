Stock Alert Platform

1. Project Overview

Stock Alert Platform is a stock monitoring dashboard developed using Python and Streamlit.

The platform allows users to search selected stocks, view historical stock prices, monitor moving averages, receive trading signals, read stock news, and set price alerts through Telegram and Discord.

2. Features

* Stock Search: Select stocks including AAPL, MSFT, and NVDA.
* Stock Price: Display the latest available closing price.
* Stock Price Chart: Visualize historical closing prices with SMA5 and SMA20.
* Trading Signals: Generate BUY, SELL, or HOLD signals based on moving average crossovers.
* Stock News: Display the latest available stock-related news.
* Strategy Backtesting: Compare the moving average strategy return with the Buy & Hold return.
* Price Alerts: Set ABOVE or BELOW price conditions.
* Notifications: Send price alert messages through Telegram and Discord.
* Duplicate Prevention: Record previously triggered alerts in a local JSON file.

3. Project Structure

StockAlertPlatform/
│
├── app.py
├── alerts.py
├── stock_data.py
├── stock_news.py
├── signals.py
├── backtest.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
└── tests/
    └── test_alerts.py

4. Installation

Clone or download the project repository.

Create and activate a Python virtual environment:

python -m venv .venv
source .venv/bin/activate

Install the required packages:

python -m pip install -r requirements.txt

5. Environment Configuration

Create a .env file in the project root directory.

Add the following settings:

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url

Replace the placeholder values with your own credentials.

Important: Do not upload .env to GitHub or share your API tokens and webhook URLs publicly.

6. Run the Application

Start the Streamlit dashboard:

python -m streamlit run app.py

Open the local URL displayed in the terminal to access the dashboard.

7. Price Alert Usage

1. Select a stock.
2. Enter a target price.
3. Choose ABOVE or BELOW.
4. Select Telegram or Discord.
5. Click Set Price Alert.

The system checks the latest available closing price when the user clicks the button. If the condition is satisfied, a notification is sent through the selected channel.

8. Disclaimer

Trading signals and backtesting results are for educational purposes only. Historical performance does not guarantee future results. This platform does not provide financial advice.