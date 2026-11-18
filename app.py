import streamlit as st

from stock_data import get_price_history
from stock_news import get_stock_news
from signals import generate_signal, add_moving_averages
from backtest import backtest_ma_cross
from alerts import process_price_alert


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
try:
    price_history = get_price_history(ticker, period="6mo")

    if price_history.empty:
        st.error("No stock data available.")
        st.stop()

    current_price = float(price_history["Close"].iloc[-1])
    latest_date = price_history["Date"].iloc[-1]

except Exception as error:
    st.error(f"Unable to retrieve stock data: {error}")
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

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Number of Signals",
        result["num_signals"]
    )

    col2.metric(
        "Strategy Return",
        f"{result['strategy_return']:.2f}%"
    )

    col3.metric(
        "Buy & Hold Return",
        f"{result['buy_hold_return']:.2f}%"
    )

    st.caption(result["assumptions"])

except ValueError as error:
    st.info(str(error))

except Exception as error:
    st.warning(f"Unable to run backtesting: {error}")


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

    result = process_price_alert(
    ticker,
    current_price,
    threshold,
    direction,
    channel,
    signal=current_signal
)