Stock Alert Platform

1. Project Overview

Stock Alert Platform is a stock monitoring dashboard developed using Python and Streamlit.

The platform provides users with stock price information, historical price charts, technical trading signals, financial news, strategy backtesting, and price alert notifications.

Users can select stocks, monitor price movements, set price thresholds, and receive notifications through Telegram or Discord.

2. Features

Stock Search

* Select and monitor supported stocks.
* Currently supports AAPL, MSFT, and NVDA.

Stock Price

* Retrieve the latest available completed trading-day closing price.
* Display the corresponding data date.

Stock Price Chart

* Visualize historical stock prices.
* Display Simple Moving Averages (SMA5 and SMA20).

Trading Signals

* Generate BUY, SELL, or HOLD signals.
* Use SMA5 and SMA20 moving average crossover logic.

Stock News

* Retrieve the latest stock-related news.
* Display news titles, sources, publication times, and links.

Strategy Backtesting

* Evaluate the moving average trading strategy.
* Compare strategy returns with Buy & Hold returns.
* Display the number of trading signals and backtesting assumptions.

Price Alerts

* Set custom target prices.
* Support ABOVE and BELOW price conditions.
* Send notifications through Telegram or Discord.
* Include stock ticker, current price, target price, trading signal, and trigger time and the quoted trading date in notifications.

Duplicate Alert Prevention

* Store triggered alert records in a local JSON file.
* Prevent repeated notifications for the same ticker, condition, threshold, and channel (one-time alerts).

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
├── .env.example
├── .gitignore
├── partC_test.py
│
└── tests/
    ├── test_alerts.py
    ├── test_stock_news.py
    └── test_news_regressions.py

Main Files

File	Description
app.py	Main Streamlit dashboard
alerts.py	Price alert logic and notification functions
stock_data.py	Stock price data retrieval and processing
stock_news.py	Stock news retrieval
signals.py	Moving average calculations and trading signals
backtest.py	Trading strategy backtesting
requirements.txt	Required Python packages
tests/test_alerts.py	Automated tests for the alert system

4. Installation

Step 1: Clone the Repository

git clone https://github.com/taylorwong27/StockAlertPlatform

Navigate into the project folder:

cd StockAlertPlatform

Step 2: Create a Virtual Environment

python -m venv .venv

Activate the environment on macOS or Linux:

source .venv/bin/activate

Step 3: Install Dependencies

python -m pip install -r requirements.txt

5. Environment Configuration

The application uses environment variables to store notification credentials.

Copy `.env.example` to `.env` in the project root directory (for example: `cp .env.example .env`).

Add the following configuration:

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url

Replace the placeholder values with your own Telegram Bot Token, Telegram Chat ID, and Discord Webhook URL.

Important: Never upload the .env file or expose your API tokens and webhook URLs publicly.

6. Running the Application

After installing the dependencies and configuring the .env file, start the Streamlit dashboard:

python -m streamlit run app.py

Streamlit will display a local URL in the terminal. Open that URL in your browser to access the dashboard.

7. Using the Price Alert Feature

1. Open the Stock Alert Platform dashboard.
2. Select a stock.
3. Enter a target price.
4. Choose an alert condition: ABOVE or BELOW.
5. Select a notification channel: Telegram or Discord.
6. Click the Set Price Alert button.
7. If the selected price condition is satisfied, the system sends a notification through the selected channel.

The notification includes:

* Stock ticker
* Current stock price
* Target price
* Alert condition
* Trading signal
* Triggered time (UTC)
* Price date (latest available trading date)

The current implementation checks the latest available closing price when the user clicks the alert button. It does not continuously monitor stock prices in the background.

**Alert re-trigger policy:** Alerts are one-time per ticker, direction, target price, and notification channel. After a successful send, the same alert will not automatically re-arm when the price crosses back over the threshold. Telegram and Discord are tracked separately.

**History recovery:** If a notification is delivered but saving `alert_history.json` fails, the dashboard displays a warning. Do not immediately retry: the recipient may already have received the alert. Check Telegram/Discord and restore write access or disk space before sending another alert. If the history file is corrupted, the dashboard blocks sending until the file is repaired or restored; keep a backup before making changes. This is a documented limitation, not an automatic recovery queue.

8. Running Automated Tests

The project includes automated tests for the price alert system.

Run the following command from the project root directory:

python -m pytest -q

The tests cover:

* Price ABOVE threshold checking
* Price BELOW threshold checking
* Conditions that are not satisfied
* Invalid alert directions
* Alert history saving and loading
* Duplicate alert prevention

The test count may change as the project evolves. Run pytest to see the current number of passing tests.

The `partC_test.py` file in the project root contains additional Student C tests.

9. Disclaimer

This platform is developed for educational purposes only.

Trading signals and backtesting results are based on historical stock price data and technical indicators. Past performance does not guarantee future results.

This platform does not provide financial advice or guarantee investment returns. Users should conduct their own research before making investment decisions.
## Submission checklist

- Do not submit `.env`, `alert_history.json`, `.venv`, `.git`, `__pycache__`, or `.pytest_cache`.
- Include `.env.example` (placeholder credentials only).
- Run `python -m pytest -q` after installing dependencies and verify Telegram/Discord test messages on the demo computer.
