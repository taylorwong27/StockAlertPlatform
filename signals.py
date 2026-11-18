"""SMA5 / SMA20 crossover signals for the Stock Alert Platform (Part C).

Input contract (from Part A, stock_data.get_price_history):
    DataFrame with columns:
        Date  : date-like, ascending, no duplicates
        Close : positive float

Output contract (agreed in the group work plan):
    generate_signal(price_df) -> dict with keys:
        signal, as_of, sma5, sma20, reason
"""

import pandas as pd

SMA_SHORT = 5
SMA_LONG = 20


def _validate_price_df(price_df):
    """Raise ValueError if price_df does not match Part A's output contract."""
    if not isinstance(price_df, pd.DataFrame):
        raise ValueError("price_df must be a pandas DataFrame")

    missing = {"Date", "Close"} - set(price_df.columns)
    if missing:
        raise ValueError(f"price_df is missing columns: {sorted(missing)}")

    if price_df.empty:
        raise ValueError("price_df is empty")

    dates = pd.to_datetime(price_df["Date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("price_df contains invalid dates")

    close = pd.to_numeric(price_df["Close"], errors="coerce")
    if close.isna().any():
        raise ValueError("price_df contains missing or non-numeric Close values")
    if (close <= 0).any():
        raise ValueError("price_df contains non-positive Close values")

    if dates.duplicated().any():
        raise ValueError("price_df contains duplicate dates")
    if not dates.is_monotonic_increasing:
        raise ValueError("price_df must be sorted by Date ascending")

    return price_df.assign(Date=dates, Close=close).reset_index(drop=True)


def add_moving_averages(price_df):
    """Return a copy of price_df with SMA5 and SMA20 columns added."""
    data = _validate_price_df(price_df).copy()
    data["SMA5"] = data["Close"].rolling(window=SMA_SHORT, min_periods=SMA_SHORT).mean()
    data["SMA20"] = data["Close"].rolling(window=SMA_LONG, min_periods=SMA_LONG).mean()
    return data


def _crossover_signal(prev_sma5, prev_sma20, sma5, sma20):
    """Apply the group's crossover rule to two consecutive SMA pairs."""
    if any(pd.isna(v) for v in (prev_sma5, prev_sma20, sma5, sma20)):
        return "HOLD"

    if prev_sma5 <= prev_sma20 and sma5 > sma20:
        return "BUY"

    if prev_sma5 >= prev_sma20 and sma5 < sma20:
        return "SELL"

    return "HOLD"


def generate_signal(price_df):
    """Generate BUY / HOLD / SELL from the latest SMA5/SMA20 crossover."""
    data = add_moving_averages(price_df)

    if len(data) <= SMA_LONG:
        raise ValueError(
            f"Insufficient data to determine crossover: need at least {SMA_LONG + 1} trading days "
            f"(got {len(data)}), because comparing crossovers requires both previous and current moving averages."
        )

    latest = data.iloc[-1]
    previous = data.iloc[-2]

    signal = _crossover_signal(
        previous["SMA5"], previous["SMA20"], latest["SMA5"], latest["SMA20"]
    )

    if signal == "BUY":
        reason = (
            f"SMA5 crossed above SMA20: previous SMA5 {previous['SMA5']:.2f} "
            f"<= SMA20 {previous['SMA20']:.2f}, latest SMA5 {latest['SMA5']:.2f} "
            f"> SMA20 {latest['SMA20']:.2f}."
        )
    elif signal == "SELL":
        reason = (
            f"SMA5 crossed below SMA20: previous SMA5 {previous['SMA5']:.2f} "
            f">= SMA20 {previous['SMA20']:.2f}, latest SMA5 {latest['SMA5']:.2f} "
            f"< SMA20 {latest['SMA20']:.2f}."
        )
    else:
        reason = (
            f"No new crossover: previous SMA5 {previous['SMA5']:.2f} vs SMA20 "
            f"{previous['SMA20']:.2f}; latest SMA5 {latest['SMA5']:.2f} vs SMA20 "
            f"{latest['SMA20']:.2f}. Rule-based observation only; not investment advice."
        )

    return {
        "signal": signal,
        "as_of": str(pd.Timestamp(latest["Date"]).date()),
        "sma5": float(latest["SMA5"]),
        "sma20": float(latest["SMA20"]),
        "reason": reason,
    }