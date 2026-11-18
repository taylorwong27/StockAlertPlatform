
import sys

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import pandas_market_calendars as mcal


MARKET_TIMEZONE = "America/New_York"
MARKET_CALENDAR = mcal.get_calendar("NASDAQ")


def _market_time(now):
    if now is None:
        return pd.Timestamp.now(tz=MARKET_TIMEZONE)

    timestamp = pd.Timestamp(now)
    if timestamp.tzinfo is None:
        raise ValueError("now must include a time zone")
    return timestamp.tz_convert(MARKET_TIMEZONE)


def _completed_sessions(start_date, now):
    today = now.date()
    schedule = MARKET_CALENDAR.schedule(
        start_date=min(start_date, today), end_date=today
    )
    return schedule.index[schedule["market_close"] <= now]


def _valid_close(close):
    return close.gt(0) & close.lt(float("inf"))


# 1. Get historical prices
def get_price_history(ticker, period="6mo", *, now=None):

    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Stock code cannot be empty")

    now = _market_time(now)
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(
            period=period, interval="1d", auto_adjust=False, prepost=False
        )
    except Exception as error:
        raise RuntimeError(f"Failed to download prices: {error}") from error

    if data.empty:
        raise ValueError("No stock data found")

    if "Close" not in data.columns:
        raise ValueError("Close price is missing")

    data = data.reset_index()

    if "Datetime" in data.columns:
        data = data.rename(columns={"Datetime": "Date"})

    data = data[["Date", "Close"]].copy()

    dates = pd.to_datetime(data["Date"], errors="coerce")
    if dates.dt.tz is not None:
        dates = dates.dt.tz_convert(MARKET_TIMEZONE)
    data["Date"] = dates.dt.date
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")

    data = data.dropna(subset=["Date", "Close"])
    data = data.loc[_valid_close(data["Close"])]

    if data.empty:
        raise ValueError("No valid prices found")

    completed = _completed_sessions(data["Date"].min(), now)
    data = data.loc[data["Date"].isin(completed.date)]
    if data.empty:
        raise ValueError("No valid prices for completed trading days")

    return data.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)


# 2. Get latest available closing price
def get_latest_price(ticker, *, now=None):

    ticker = ticker.strip().upper()
    now = _market_time(now)
    data = get_price_history(ticker, period="1mo", now=now)
    return _latest_price_from_history(ticker, data, now)


def _latest_price_from_history(ticker, data, now):
    completed = _completed_sessions((now - pd.Timedelta(days=31)).date(), now)
    if completed.empty:
        raise ValueError("No completed trading day found in the past month")

    latest_date = completed[-1].date()
    close = data.loc[data["Date"].eq(latest_date), "Close"]
    if close.empty:
        raise ValueError(f"No valid closing price for {latest_date}")

    return {
        "ticker": ticker,
        "price": float(close.iloc[0]),
        "currency": "USD",
        "as_of": str(latest_date),
        "source": "Yahoo Finance daily close"
    }


# 3. Calculate daily percentage change
def calculate_daily_change(data):

    result = data.copy()
    if result.empty:
        result["Daily_Change_Pct"] = pd.Series(dtype="float64")
        return result

    dates = pd.to_datetime(result["Date"]).dt.normalize()
    sessions = MARKET_CALENDAR.valid_days(
        start_date=dates.min() - pd.Timedelta(days=31), end_date=dates.max(), tz=None
    )
    previous_session = pd.Series(sessions, index=sessions).shift()
    close = pd.to_numeric(result["Close"], errors="coerce")
    close = close.where(_valid_close(close))
    close_by_date = pd.Series(close.array, index=dates)
    previous_close = dates.map(previous_session).map(close_by_date)
    result["Daily_Change_Pct"] = (close / previous_close - 1) * 100

    return result


# 4. Create a stock price chart
def create_chart(data, ticker):

    plt.figure(figsize=(10, 5))
    plt.plot(data["Date"], data["Close"])

    plt.title(f"{ticker} Stock Price")
    plt.xlabel("Date")
    plt.ylabel("Closing Price (USD)")

    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(f"{ticker}_chart.png")
    plt.close()


# 5. Run the program
def main(*, now=None):

    tickers = ["AAPL", "MSFT", "NVDA"]
    now = _market_time(now)
    success_count = 0

    for ticker in tickers:
        try:
            history = get_price_history(ticker, now=now)
            latest = _latest_price_from_history(ticker, history, now)

            print(f"\nStock: {ticker}")
            print("Latest:", latest)

            result = calculate_daily_change(history)
            print(result.tail())

            create_chart(history, ticker)
            success_count += 1

        except (ValueError, RuntimeError) as error:
            print(f"{ticker}: {error}", file=sys.stderr)

    return 0 if success_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
