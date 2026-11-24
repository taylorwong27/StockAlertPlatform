
import runpy

import pandas as pd
import pytest
import stock_data


AFTER_CLOSE = "2026-11-05T16:05:00-05:00"


def mock_history(monkeypatch, dates, prices):
    index = pd.DatetimeIndex(dates, name="Date", tz="America/New_York")
    history = pd.DataFrame({"Close": prices}, index=index)

    class FakeStock:
        def history(self, **kwargs):
            return history

    monkeypatch.setattr(stock_data.yf, "Ticker", lambda ticker: FakeStock())


# Test 1: Valid stock
def test_valid_stock(monkeypatch):

    mock_history(monkeypatch, ["2026-11-04", "2026-11-03"], [110.0, 100.0])
    data = stock_data.get_price_history("AAPL", now=AFTER_CLOSE)

    assert not data.empty
    assert list(data.columns) == ["Date", "Close"]
    assert data["Close"].tolist() == [100.0, 110.0]


# Test 2: Invalid input
def test_invalid_stock():

    with pytest.raises(ValueError):
        stock_data.get_price_history("")


# Test 3: Empty API data
def test_empty_data(monkeypatch):

    class FakeStock:
        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(
        stock_data.yf,
        "Ticker",
        lambda ticker: FakeStock()
    )

    with pytest.raises(ValueError):
        stock_data.get_price_history("AAPL")


def test_invalid_prices_are_removed(monkeypatch):
    mock_history(
        monkeypatch,
        ["2026-11-02"] * 7 + ["2026-11-03"],
        [0, -1, float("inf"), float("-inf"), float("nan"), "bad", "100.5", 102],
    )

    data = stock_data.get_price_history("AAPL", now=AFTER_CLOSE)

    assert data["Date"].astype(str).tolist() == ["2026-11-02", "2026-11-03"]
    assert data["Close"].tolist() == [100.5, 102.0]


def test_all_prices_invalid(monkeypatch):
    mock_history(monkeypatch, ["2026-11-02", "2026-11-03"], [0, float("inf")])

    with pytest.raises(ValueError, match="No valid prices found"):
        stock_data.get_price_history("AAPL", now=AFTER_CLOSE)


@pytest.mark.parametrize(
    ("now", "expected_date", "expected_price"),
    [
        ("2026-11-06T15:59:00-05:00", "2026-11-05", 100.0),
        ("2026-11-06T16:05:00-05:00", "2026-11-06", 110.0),
        ("2026-11-07T12:00:00-05:00", "2026-11-06", 110.0),
        ("2026-11-27T12:59:00-05:00", "2026-11-25", 100.0),
        ("2026-11-27T13:05:00-05:00", "2026-11-27", 110.0),
        ("2026-07-07T19:59:00Z", "2026-07-06", 100.0),
        ("2026-07-07T20:05:00Z", "2026-07-07", 110.0),
    ],
)
def test_history_and_latest_respect_market_close(
    monkeypatch, now, expected_date, expected_price
):
    mock_history(
        monkeypatch,
        [
            "2026-07-06", "2026-07-07", "2026-11-05", "2026-11-06",
            "2026-11-07", "2026-11-25", "2026-11-26", "2026-11-27",
        ],
        [100, 110, 100, 110, 999, 100, 999, 110],
    )

    history = stock_data.get_price_history("AAPL", now=now)
    latest = stock_data.get_latest_price(" aapl ", now=now)

    assert str(history.iloc[-1]["Date"]) == expected_date
    assert 999 not in history["Close"].tolist()
    assert latest == {
        "ticker": "AAPL",
        "price": expected_price,
        "currency": "USD",
        "as_of": expected_date,
        "source": "Yahoo Finance daily close",
    }


def test_only_unfinished_candle_has_no_completed_prices(monkeypatch):
    mock_history(monkeypatch, ["2026-11-06"], [110])

    with pytest.raises(ValueError, match="No valid prices for completed trading days"):
        stock_data.get_latest_price("AAPL", now="2026-11-06T15:59:00-05:00")


def test_latest_does_not_silently_use_stale_close(monkeypatch):
    mock_history(monkeypatch, ["2026-11-04"], [100])

    with pytest.raises(ValueError, match="No valid closing price for 2026-11-05"):
        stock_data.get_latest_price("AAPL", now=AFTER_CLOSE)


@pytest.mark.parametrize("invalid_tuesday", [False, True])
def test_missing_previous_trading_day(monkeypatch, invalid_tuesday):
    dates = ["2026-11-02", "2026-11-04", "2026-11-05"]
    prices = [100, 110, 121]
    if invalid_tuesday:
        dates.insert(1, "2026-11-03")
        prices.insert(1, 0)
    mock_history(monkeypatch, dates, prices)

    history = stock_data.get_price_history("AAPL", now=AFTER_CLOSE)
    result = stock_data.calculate_daily_change(history)

    assert result["Date"].tolist() == history["Date"].tolist()
    assert result["Close"].tolist() == [100, 110, 121]
    assert result["Daily_Change_Pct"].iloc[:2].isna().all()
    assert result["Daily_Change_Pct"].iloc[2] == pytest.approx(10.0)


@pytest.mark.parametrize(
    "dates",
    [["2026-11-06", "2026-11-09"], ["2026-11-25", "2026-11-27"]],
)
def test_daily_change_skips_weekends_and_market_holidays(dates):
    history = pd.DataFrame({"Date": pd.to_datetime(dates).date, "Close": [100, 110]})

    result = stock_data.calculate_daily_change(history)

    assert result["Daily_Change_Pct"].iloc[1] == pytest.approx(10.0)


def test_all_failed_sets_process_exit_code(monkeypatch, capsys):
    def fail(ticker):
        raise RuntimeError("simulated Yahoo failure")

    monkeypatch.setattr(stock_data.yf, "Ticker", fail)

    with pytest.raises(SystemExit) as outcome:
        runpy.run_module("stock_data", run_name="__main__")

    assert outcome.value.code == 1
    errors = capsys.readouterr().err.splitlines()
    assert errors == [
        f"{ticker}: Failed to download prices: simulated Yahoo failure"
        for ticker in ["AAPL", "MSFT", "NVDA"]
    ]


def test_partial_success_returns_zero_and_creates_only_successful_chart(
    monkeypatch, capsys
):
    mock_history(monkeypatch, ["2026-11-04", "2026-11-05"], [100, 110])
    fake_stock = stock_data.yf.Ticker("AAPL")
    attempted = []
    charts = []

    def get_stock(ticker):
        attempted.append(ticker)
        if ticker == "MSFT":
            return fake_stock
        raise RuntimeError("simulated Yahoo failure")

    monkeypatch.setattr(stock_data.yf, "Ticker", get_stock)
    monkeypatch.setattr(stock_data, "create_chart", lambda data, ticker: charts.append(ticker))

    assert stock_data.main(now=AFTER_CLOSE) == 0
    assert attempted == ["AAPL", "MSFT", "NVDA"]
    assert charts == ["MSFT"]
    output = capsys.readouterr()
    assert "Stock: MSFT" in output.out
    assert "AAPL:" in output.err
    assert "NVDA:" in output.err
    assert "MSFT:" not in output.err
