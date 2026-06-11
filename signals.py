from __future__ import annotations

import numpy as np
import pandas as pd


def _scalar(value) -> float:
    try:
        return float(value.item())
    except AttributeError:
        return float(value)


def rsi(close: pd.Series, period: int = 14) -> float | None:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    value = 100 - (100 / (1 + rs))
    last = value.dropna()
    return _scalar(last.iloc[-1]) if not last.empty else None


def macd(close: pd.Series) -> tuple[float | None, float | None]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    if line.dropna().empty or signal.dropna().empty:
        return None, None
    return _scalar(line.iloc[-1]), _scalar(signal.iloc[-1])


def bollinger(close: pd.Series) -> tuple[float | None, float | None]:
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    if upper.dropna().empty or lower.dropna().empty:
        return None, None
    return _scalar(upper.iloc[-1]), _scalar(lower.iloc[-1])
