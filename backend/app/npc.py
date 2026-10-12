"""NPC 交易者引擎：不同职业风格的机器人基于真实行情自动对战。"""
import json
import random

from sqlalchemy.orm import Session

from .engine import macd, ma, rsi
from .models import DailyBar, NpcOrder, NpcTrader

FEE_RATE = 0.0003
MIN_FEE = 5.0
STAMP_TAX = 0.0005
INITIAL_CASH = 1_000_000.0


def _bars(db, stock_id, limit=260):
    rows = (
        db.query(DailyBar)
        .filter(DailyBar.stock_id == stock_id)
        .order_by(DailyBar.date.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {"date": b.date, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in rows
    ]


def _reason(kind, params, bars, i, side):
    """按策略生成人性化操作理由。"""
    closes = [b["close"] for b in bars[: i + 1]]
    if kind == "dual_ma":
        f, s = ma(closes, int(params.get("fast", 5))), ma(closes, int(params.get("slow", 20)))
        return (f"MA{params.get('fast',5)} 上穿 MA{params.get('slow',20)} 形成金叉" if side == "buy"
                else f"MA{params.get('fast',5)} 跌破 MA{params.get('slow',20)}，趋势走坏离场")
    if kind == "macd":
        return "DIF 金叉 DEA，多头信号确立" if side == "buy" else "DIF 死叉 DEA，兑现离场"
    if kind == "rsi":
        r = rsi(closes, int(params.get("period", 14)))[-1] or 50
        return f"RSI 回落至 {r:.1f}，超卖低吸" if side == "buy" else f"RSI 升至 {r:.1f}，超买兑现"
    if kind == "boll":
        return "股价触及布林下轨，均值回复买入" if side == "buy" else "价格触及布林上轨，获利了结"
    if kind == "turtle":
        return f"突破前 {params.get('entry',20)} 日高点，趋势启动" if side == "buy" else f"跌破前 {params.get('exit',10)} 日低点，止损离场"
    if kind == "momentum":
        lb = int(params.get("lookback", 5))
        mom = (closes[-1] / closes[-1 - lb] - 1) * 100
        return f"{lb}日动量 +{mom:.1f}%，强势跟进" if side == "buy" else f"{lb}日动量转弱，快进快出"
    if kind == "dca":
        return "每周定投计划执行，无视涨跌" if side == "buy" else "定投止盈"
    return "信号触发"


def _weekly_dca_signals(bars, params):
    """佛系定投：每 5 个交易日买入一次，跌破 60 日低点清仓避险。"""
    n = len(bars)
    interval = int(params.get("interval", 5))
    pos = [0] * n
    events = []  # (i, side)
    holding = 0
    for i in range(60, n):
        lows = [b["low"] for b in bars[i - 60:i]]
        if holding and bars[i]["close"] < min(lows) * 1.02:
            holding = 0
            events.append((i, "sell"))
        elif not holding and i % interval == 0:
            holding = 1
            events.append((i, "buy"))
        pos[i] = holding
    return pos, events


def replay_trader(db, trader: NpcTrader):
    """按真实行情从头重放某 NPC 的交易，写入订单与净值曲线。幂等。"""
    db.query(NpcOrder).filter(NpcOrder.trader_id == trader.id).delete()
    bars = _bars(db, trader.stock_id)
    if len(bars) < 80:
        db.commit()
        return

    params = json.loads(trader.params or "{}")
    cash = trader.initial_cash
    shares = 0
    lot = 1 if trader.stock.market == "US" else 100
    ratio = trader.position_ratio
    curve, orders = [], []
    entry_price = 0.0
    rng = random.Random(trader.id * 7)

    def close_of(i):
        return bars[i]["close"]

    events = []
    signals = None
    if trader.kind == "dca":
        signals, events = _weekly_dca_signals(bars, params)
    else:
        from .engine import gen_signals
        signals = gen_signals(trader.kind, bars, params)
        for i in range(1, len(bars)):
            if signals[i - 1] == 0 and signals[i] == 1:
                events.append((i, "buy"))
            elif signals[i - 1] == 1 and signals[i] == 0:
                events.append((i, "sell"))

    for i in range(1, len(bars)):
        b_prev, b_next = bars[i], bars[i + 1] if i + 1 < len(bars) else None
        want, have = signals[i], (1 if shares > 0 else 0)
        if b_next is None:
            break
        for ev_i, ev_side in [(j, s) for j, s in events if j == i]:
            px = b_next["open"]
            if ev_side == "buy" and have == 0:
                budget = cash * ratio
                qty = int(budget / (px * (1 + FEE_RATE)) // lot) * lot
                if qty > 0:
                    fee = max(qty * px * FEE_RATE, MIN_FEE)
                    cash -= qty * px + fee
                    shares += qty
                    entry_price = px
                    orders.append(NpcOrder(
                        trader_id=trader.id, stock_id=trader.stock_id, side="buy",
                        price=px, qty=qty, amount=round(qty * px, 2), fee=round(fee, 2),
                        reason=_reason(trader.kind, params, bars, i, "buy")[:200],
                        trade_date=b_next["date"],
                    ))
            elif ev_side == "sell" and have == 1:
                fee = max(shares * px * (FEE_RATE + (STAMP_TAX if trader.stock.market == "CN" else 0)), MIN_FEE)
                cash += shares * px - fee
                orders.append(NpcOrder(
                    trader_id=trader.id, stock_id=trader.stock_id, side="sell",
                    price=px, qty=shares, amount=round(shares * px, 2), fee=round(fee, 2),
                    reason=_reason(trader.kind, params, bars, i, "sell")[:200],
                    trade_date=b_next["date"],
                ))
                shares = 0
        # 每日净值
        mv = shares * close_of(i)
        curve.append({"date": b_prev["date"], "value": round(cash + mv, 2)})

    # 末点用最新收盘
    if bars:
        mv = shares * bars[-1]["close"]
        curve.append({"date": bars[-1]["date"], "value": round(cash + mv, 2)})

    trader.cash = round(cash, 2)
    trader.curve = json.dumps(curve)
    trader.last_replay_date = bars[-1]["date"]
    db.add_all(orders)
    db.commit()


NPC_POOL = [
    ("陈悟道", "退休老股民", "🧓", "稳健价值派", "boll", {"period": 20, "k": 2}, 0.35,
     "炒股三十年，只买看得懂的股，涨多了就卖，跌多了就接。"),
    ("王满仓", "私募基金经理", "🐺", "趋势重仓派", "dual_ma", {"fast": 5, "slow": 20}, 0.9,
     "管着七位数的产品，信奉趋势为王，均线就是军令。"),
    ("赵快刀", "游资打板敢死队", "🔪", "短线情绪派", "momentum", {"lookback": 5}, 1.0,
     "三年一倍全靠快，只做最强风口，割肉从不眨眼。"),
    ("林亦南", "量化研究员", "🤖", "多因子派", "macd", {"fast": 12, "slow": 26, "signal": 9}, 0.7,
     "博士毕业，把 MACD 写进了自己的因子库，只信回测。"),
    ("苏持仓", "华尔街归国交易员", "🗽", "美股动量派", "momentum", {"lookback": 20}, 0.8,
     "在纽约做过两年 TBH，回国有美元仓位就打美股动量。"),
    ("郑佛系", "大三学生", "🧘", "佛系定投派", "dca", {"interval": 5}, 0.3,
     "生活费每月省两千定投，涨了开心，跌了当攒股。"),
    ("孙突破", "海龟派传人", "🐢", "系统突破派", "turtle", {"entry": 20, "exit": 10}, 0.85,
     "把海龟法则贴在显示器边上：突破就追，破位就砍。"),
    ("钱知微", "技术分析博主", "📡", "超卖博弈派", "rsi", {"period": 14, "oversold": 32, "overbought": 70}, 0.6,
     "百万粉丝的技术博主，口头禅是超卖必有反弹。"),
]


def ensure_npcs(db):
    if db.query(NpcTrader).count() > 0:
        return
    from .models import Stock
    stocks = {s.symbol: s for s in db.query(Stock).all()}
    plan = ["600519", "601318", "300750", "000001", "AAPL", "600036", "000858", "600276"]
    for i, (name, title, avatar, style, kind, params, ratio, bio) in enumerate(NPC_POOL):
        s = stocks.get(plan[i % len(plan)])
        if s is None:
            continue
        db.add(NpcTrader(
            name=name, title=title, avatar=avatar, style_tag=style, bio=bio,
            kind=kind, params=json.dumps(params), stock_id=s.id,
            position_ratio=ratio,
        ))
    db.commit()


def refresh_all(db):
    """有新行情日期时重放对应 NPC（幂等，代价低）。"""
    ensure_npcs(db)
    traders = db.query(NpcTrader).all()
    from sqlalchemy import func
    max_dates = dict(
        db.query(DailyBar.stock_id, func.max(DailyBar.date)).group_by(DailyBar.stock_id).all()
    )
    changed = False
    for t in traders:
        latest = max_dates.get(t.stock_id)
        if latest and t.last_replay_date != latest:
            replay_trader(db, t)
            changed = True
    return changed
