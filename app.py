import streamlit as st

from stock_data import get_price_history, get_latest_price
from stock_news import get_stock_news
from signals import generate_signal, add_moving_averages
from backtest import backtest_ma_cross
from alerts import process_price_alert, send_alert

# Dashboard settings
st.set_page_config(
    page_title="Stock Alert Platform",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Alert Platform")
st.write("Welcome to our Stock Alert Dashboard!")


# Stock Selection
st.subheader("Stock Search")

ticker = st.selectbox(
    "Select a stock:",
    ["AAPL", "MSFT", "NVDA"]
)

st.write("Selected Stock:", ticker)


# Get Stock Data

# Get Stock Data
try:
    # Retrieve historical data for charts and backtesting
    price_history = get_price_history(ticker, period="6mo")

    if price_history.empty:
        st.error("No historical stock data available.")
        st.stop()

    # Validate the latest completed trading-day price
    latest = get_latest_price(ticker)

    current_price = float(latest["price"])
    latest_date = latest["as_of"]

    # Make sure the historical data and latest quote agree
    history_latest_date = str(price_history["Date"].iloc[-1])

    if history_latest_date != str(latest_date):
        st.error(
            "Latest stock price data is incomplete or inconsistent. "
            "Please try again later."
        )
        st.stop()

except (ValueError, RuntimeError):
    st.error(
        "Latest stock price is unavailable or incomplete. "
        "Please try again later."
    )
    st.stop()

except Exception:
    st.error(
        "Unable to retrieve verified stock prices. "
        "Please check your connection and try again."
    )
    st.stop()



# Stock Price
st.subheader("Stock Price")

st.metric(
    label=f"{ticker} Latest Available Closing Price",
    value=f"${current_price:.2f}"
)

st.caption(f"Data date: {latest_date}")


# Stock Price Chart
st.subheader("Stock Price Chart")

try:
    chart_data = add_moving_averages(price_history)
    chart_data = chart_data.set_index("Date")

    st.line_chart(chart_data[["Close", "SMA5", "SMA20"]])

except Exception as error:
    st.warning(f"Unable to display chart: {error}")


# Trading Signal
st.subheader("Trading Signal")
current_signal = "N/A"
try:
    signal = generate_signal(price_history)

    current_signal = signal["signal"]

    st.metric(
        label="Current Signal",
        value=signal["signal"]
    )

    st.write(signal["reason"])
    st.caption(f"Signal date: {signal['as_of']}")

except ValueError as error:
    st.info(str(error))

except Exception as error:
    st.warning(f"Unable to generate trading signal: {error}")


# Stock News
st.subheader("Latest Stock News")

try:
    news_items = get_stock_news(ticker, limit=5)

    if news_items:
        for item in news_items:
            st.markdown(f"[{item['title']}]({item['url']})")
            st.caption(
                f"{item['source']} · {item['published_at']}"
            )
    else:
        st.info("No relevant news available right now.")

except Exception as error:
    st.warning(f"Unable to retrieve news: {error}")


# Backtesting
st.subheader("Strategy Backtesting")

try:
    result = backtest_ma_cross(price_history)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Number of Signals",
        result["num_signals"]
    )

    col2.metric(
        "Number of Trades",
        result.get("num_trades", "N/A")
    )

    col3.metric(
        "Strategy Return",
        f"{result['strategy_return']:.2f}%"
    )

    col4.metric(
        "Buy & Hold Return",
        f"{result['buy_hold_return']:.2f}%"
    )

    st.caption(
        "Signals count SMA crossover signals. "
        "Trades count executed orders."
    )

    unexecuted_signal = result.get("unexecuted_signal")

    if unexecuted_signal:
        st.info(
            f"Unexecuted signal: {unexecuted_signal}"
        )

    st.caption(str(result.get("assumptions", "")))

except ValueError as error:
    st.info(str(error))

except Exception:
    st.warning("Unable to run backtesting. Please check the data.")


# Price Alert
st.subheader("Price Alert")

st.write(
    "Set a target price. The alert checks the latest available "
    "closing price when you click the button."
)

threshold = st.number_input(
    "Set your target price:",
    min_value=0.0,
    value=150.0
)

direction = st.selectbox(
    "Alert condition:",
    ["above", "below"]
)

channel = st.selectbox(
    "Notification channel:",
    ["telegram", "discord"]
)

if st.button("Set Price Alert"):
    try:
        result = process_price_alert(
            ticker,
            current_price,
            threshold,
            direction,
            channel,
            signal=current_signal,
            latest_date=latest_date
        )
        if result.get("success"):
            if result.get("history_saved") is False:
                st.warning(result.get("error", "Notification sent, but history could not be saved."))
            else:
                st.success("Price alert sent successfully!")
        else:
            error = result.get("error", "Unable to send alert.")
            if error == "Price condition not met":
                st.info("Price condition not met; no alert was sent.")
            elif error == "Duplicate alert already sent":
                st.info("Duplicate alert skipped; no new notification was sent.")
            else:
                st.error(
                "Alert sending failed. "
                "Please check your notification configuration and try again."
                )
    except (ValueError, OSError) as error:
        st.error(f"Unable to access alert history: {error}")
    except Exception:
        st.error("Unable to process price alert. Please check the configuration.")

# Independent TEST notification
st.divider()
st.write(
    "Send a TEST notification to verify your Telegram "
    "or Discord connection. This does not create a price alert."
)

if st.button("Send TEST Alert"):
    test_message = (
        f"TEST - Stock Alert Platform\n"
        f"Ticker: {ticker}\n"
        f"Latest available closing price: ${current_price:.2f}\n"
        f"Price date: {latest_date}\n"
        f"Trading signal: {current_signal}\n"
        f"This is a TEST notification only."
    )

    try:
        test_result = send_alert(test_message, channel)

        if test_result.get("success"):
            st.success(
                f"TEST notification sent successfully via {channel}!"
            )
        else:
            st.error(
                "TEST notification failed. "
                "Please check your notification configuration."
            )

    except Exception:
        st.error(
            "Unable to send TEST notification. "
            "Please check your notification configuration."
        )