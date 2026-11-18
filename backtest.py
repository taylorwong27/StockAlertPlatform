"""Simple SMA crossover backtest for the Stock Alert Platform (Part C)."""

import pandas as pd
from signals import SMA_LONG, add_moving_averages

DEFAULT_COST_PCT = 0.1

def get_assumptions(cost_pct):
    
    return (
        "Long-only; signals from SMA5/SMA20 crossover on daily closes; "
        "signal is confirmed at close, but trade executes at the NEXT trading day's close; "
        "no leverage, no shorting; "
        f"{cost_pct}% transaction cost applied on each buy and each sell; "
        "Buy-and-Hold benchmark assumes 0% transaction cost; "
        "dividends, taxes, slippage and intraday prices are ignored; "
        "past performance does not guarantee future results."
    )


def _backtest_series(close, sma5, sma20, cost_pct):
    """Return (num_signals, strategy_return, buy_hold_return, trades)."""
    num_signals = 0
    position = 0.0          
    entry_price = None
    equity = 1.0            
    trades = []

    for i in range(len(close)):
        if i == 0:
            continue

        prev5, prev20 = sma5.iloc[i - 1], sma20.iloc[i - 1]
        cur5, cur20 = sma5.iloc[i], sma20.iloc[i]
        if any(pd.isna(v) for v in (prev5, prev20, cur5, cur20)):
            continue

        is_buy = prev5 <= prev20 and cur5 > cur20
        is_sell = prev5 >= prev20 and cur5 < cur20

        # Fix: Look-ahead bias. Signal is confirmed at day i's close, execute at day i+1's close.
        if (is_buy or is_sell) and (i + 1 < len(close)):
            num_signals += 1
            exec_price = float(close.iloc[i + 1])
            exec_date = str(pd.Timestamp(close.index[i + 1]).date())

            if is_buy and position == 0.0:
                position = 1.0
                entry_price = exec_price
                equity *= (1 - cost_pct / 100)
                trades.append({"date": exec_date, "action": "BUY", "price": exec_price})
                
            elif is_sell and position == 1.0:
                gross = exec_price / entry_price
                equity *= gross * (1 - cost_pct / 100)
                position = 0.0
                entry_price = None
                trades.append({"date": exec_date, "action": "SELL", "price": exec_price})

    if position == 1.0 and entry_price is not None:
        equity *= float(close.iloc[-1]) / entry_price

    strategy_return = (equity - 1) * 100
    buy_hold_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100
    return num_signals, strategy_return, buy_hold_return, trades


def backtest_ma_cross(price_df, cost_pct=DEFAULT_COST_PCT):
    """Backtest the SMA5/SMA20 crossover rule against buy-and-hold."""
    data = add_moving_averages(price_df)

    if len(data) < SMA_LONG:
        raise ValueError(
            f"Need at least {SMA_LONG} trading days to backtest; got {len(data)}"
        )

    close = data["Close"].reset_index(drop=True)
    sma5 = data["SMA5"].reset_index(drop=True)
    sma20 = data["SMA20"].reset_index(drop=True)

    date_index = pd.to_datetime(data["Date"]).reset_index(drop=True)
    close.index = date_index
    sma5.index = date_index
    sma20.index = date_index

    num_signals, strategy_return, buy_hold_return, trades = _backtest_series(
        close, sma5, sma20, cost_pct
    )

    return {
        "num_signals": num_signals,
        "strategy_return": round(strategy_return, 4),
        "buy_hold_return": round(buy_hold_return, 4),
        "assumptions": get_assumptions(cost_pct),
        "trades": trades,
    }