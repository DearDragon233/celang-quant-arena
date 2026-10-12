"""技术指标库与回测引擎（策略来源标注见 KINDS）。"""
import math


# ---------------- 技术指标 ----------------

def ma(values, n):
    out = [None] * len(values)
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(values, n):
    out = []
    k = 2 / (n + 1)
    e = values[0]
    for v in values:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def macd(values, fast=12, slow=26, signal=9):
    ef, es = ema(values, fast), ema(values, slow)
    dif = [a - b for a, b in zip(ef, es)]
    dea = ema(dif, signal)
    hist = [(a - b) * 2 for a, b in zip(dif, dea)]
    return dif, dea, hist


def rsi(values, n=14):
    out = [None] * len(values)
    gains = losses = 0.0
    ag = al = 0.0
    for i in range(1, len(values)):
        chg = values[i] - values[i - 1]
        g, l = max(chg, 0), max(-chg, 0)
        if i <= n:
            gains += g
            losses += l
            if i == n:
                ag, al = gains / n, losses / n
                out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        else:
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + l) / n
            out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def boll(values, n=20, k=2):
    mid = ma(values, n)
    upper, lower = [None] * len(values), [None] * len(values)
    for i in range(n - 1, len(values)):
        window = values[i - n + 1:i + 1]
        sd = (sum((x - mid[i]) ** 2 for x in window) / n) ** 0.5
        upper[i] = mid[i] + k * sd
        lower[i] = mid[i] - k * sd
    return mid, upper, lower


def atr(bars, n=14):
    out = [None] * len(bars)
    vals = []
    for i, b in enumerate(bars):
        prev_close = bars[i - 1]["close"] if i > 0 else b["open"]
        tr = max(b["high"] - b["low"], abs(b["high"] - prev_close), abs(b["low"] - prev_close))
        vals.append(tr)
        if i >= n - 1:
            out[i] = sum(vals[i - n + 1:i + 1]) / n
    return out


# ---------------- 策略信号 ----------------

def gen_signals(kind, bars, params):
    """生成目标持仓信号序列：1 持有 / 0 空仓（第 i 日收盘确认，次日开盘执行）。"""
    closes = [b["close"] for b in bars]
    n = len(bars)
    pos = [0] * n

    if kind == "dual_ma":
        fast = ma(closes, int(params.get("fast", 5)))
        slow = ma(closes, int(params.get("slow", 20)))
        holding = 0
        for i in range(n):
            if fast[i] is not None and slow[i] is not None:
                holding = 1 if fast[i] > slow[i] else 0
            pos[i] = holding
    elif kind == "macd":
        dif, dea, _ = macd(closes, int(params.get("fast", 12)),
                           int(params.get("slow", 26)), int(params.get("signal", 9)))
        holding = 0
        for i in range(1, n):
            if dif[i - 1] <= dea[i - 1] and dif[i] > dea[i]:
                holding = 1
            elif dif[i - 1] >= dea[i - 1] and dif[i] < dea[i]:
                holding = 0
            pos[i] = holding
    elif kind == "rsi":
        period = int(params.get("period", 14))
        low_th = float(params.get("oversold", 30))
        high_th = float(params.get("overbought", 70))
        r = rsi(closes, period)
        holding = 0
        for i in range(n):
            if r[i] is not None:
                if r[i] < low_th:
                    holding = 1
                elif r[i] > high_th:
                    holding = 0
            pos[i] = holding
    elif kind == "boll":
        period = int(params.get("period", 20))
        k = float(params.get("k", 2))
        _, upper, lower = boll(closes, period, k)
        holding = 0
        for i in range(n):
            if upper[i] is not None:
                if closes[i] <= lower[i]:
                    holding = 1
                elif closes[i] >= upper[i]:
                    holding = 0
            pos[i] = holding
    elif kind == "turtle":
        # 海龟交易法则：突破前 N1 日高点入场，跌破前 N2 日低点离场
        entry_n = int(params.get("entry", 20))
        exit_n = int(params.get("exit", 10))
        holding = 0
        for i in range(entry_n, n):
            if holding == 0:
                hh = max(b["high"] for b in bars[i - entry_n:i])
                if closes[i] > hh:
                    holding = 1
            else:
                ll = min(b["low"] for b in bars[i - exit_n:i])
                if closes[i] < ll:
                    holding = 0
            pos[i] = holding
    elif kind == "momentum":
        # 动量趋势：20 日动量为正且站上 MA20 持有，反之离场（Qlib Alpha158 动量因子思路）
        lookback = int(params.get("lookback", 20))
        holding = 0
        for i in range(lookback, n):
            mom = closes[i] / closes[i - lookback] - 1
            ma20 = sum(closes[i - 19:i + 1]) / 20
            holding = 1 if (mom > 0 and closes[i] > ma20) else 0
            pos[i] = holding
    else:
        raise ValueError(f"未知策略类型: {kind}")
    return pos


def run_backtest(kind, bars, params, initial_cash=100000.0, fee_rate=0.0003, min_fee=5.0):
    """收盘确认信号、次日开盘成交的回测。返回 metrics / equity / trades。"""
    closes = [b["close"] for b in bars]
    pos_signal = gen_signals(kind, bars, params)
    cash = initial_cash
    shares = 0
    equity, trades = [], []
    trade_log = []
    entry = None

    for i in range(len(bars) - 1):
        b_next = bars[i + 1]
        want, have = pos_signal[i], (1 if shares > 0 else 0)
        if want == 1 and have == 0:
            px = b_next["open"]
            qty = int(cash / (px * (1 + fee_rate)) // 100) * 100
            if qty > 0:
                fee = max(qty * px * fee_rate, min_fee)
                cash -= qty * px + fee
                shares += qty
                entry = {"date": b_next["date"], "price": px, "qty": qty, "side": "buy", "cash": round(cash, 2)}
                trades.append(entry)
        elif want == 0 and have == 1:
            px = b_next["open"]
            fee = max(shares * px * (fee_rate + 0.0005), min_fee)
            cash += shares * px - fee
            if entry:
                trade_log.append({
                    "entry_date": entry["date"], "entry_price": entry["price"],
                    "exit_date": b_next["date"], "exit_price": px,
                    "ret": round(px / entry["price"] - 1, 4),
                })
            entry = None
            shares = 0
            trades.append({"date": b_next["date"], "price": px, "qty": 0, "side": "sell", "cash": round(cash, 2)})
        market_value = shares * b_next["close"]
        equity.append({"date": b_next["date"], "value": round(cash + market_value, 2),
                       "benchmark": round(initial_cash * b_next["close"] / closes[0], 2)})

    if not equity:
        empty = {"total_return": 0, "annual_return": 0, "max_drawdown": 0, "sharpe": 0,
                 "benchmark_return": 0, "trade_count": 0, "win_rate": 0,
                 "final_value": initial_cash, "avg_hold_ret": 0}
        return empty, [], []

    total_ret = equity[-1]["value"] / initial_cash - 1
    bench_ret = equity[-1]["benchmark"] / initial_cash - 1
    peak, max_dd = equity[0]["value"], 0.0
    for p in equity:
        peak = max(peak, p["value"])
        max_dd = max(max_dd, 1 - p["value"] / peak)
    years = max(len(equity) / 244, 1 / 244)
    annual = (1 + total_ret) ** (1 / years) - 1 if total_ret > -1 else -1
    rets = [equity[i]["value"] / equity[i - 1]["value"] - 1 for i in range(1, len(equity)) if equity[i - 1]["value"] > 0]
    mean = sum(rets) / len(rets) if rets else 0
    sd = (sum((x - mean) ** 2 for x in rets) / len(rets)) ** 0.5 if rets else 0
    sharpe = round((mean * 244 - 0.03) / (sd * math.sqrt(244)), 2) if sd > 0 else 0
    wins = [t for t in trade_log if t["ret"] > 0]

    metrics = {
        "total_return": round(total_ret * 100, 2),
        "annual_return": round(annual * 100, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "sharpe": sharpe,
        "benchmark_return": round(bench_ret * 100, 2),
        "trade_count": len(trade_log),
        "win_rate": round(len(wins) / len(trade_log) * 100, 1) if trade_log else 0,
        "final_value": equity[-1]["value"],
        "avg_hold_ret": round(sum(t["ret"] for t in trade_log) / len(trade_log) * 100, 2) if trade_log else 0,
    }
    return metrics, equity, trades
