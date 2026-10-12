"""分析模块：场内分析 / 持仓分析 / 收益分析。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..datasource import fetch_kline, fetch_quotes
from ..database import get_db
from ..models import Contest, ContestEntry, DailyBar, Order, Position, Stock, User
from ..routers.advisor import _facts, _verdict
from ..security import get_current_user
from ..services import realtime_quotes

router = APIRouter(prefix="/api/analysis", tags=["数据分析"], dependencies=[Depends(get_current_user)])

INDEXES = [
    ("1.000001", "上证指数"),
    ("0.399001", "深证成指"),
    ("0.399006", "创业板指"),
    ("1.000300", "沪深300"),
]


def require_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "user":
        raise HTTPException(status_code=403, detail="仅参赛选手可用")
    return user


def _resolve(db: Session, user: User, contest_id: int):
    if contest_id:
        entry = (
            db.query(ContestEntry)
            .filter(ContestEntry.contest_id == contest_id, ContestEntry.user_id == user.id)
            .first()
        )
        if entry is None:
            raise HTTPException(status_code=403, detail="尚未报名该比赛")
        contest = db.get(Contest, contest_id)
        return entry.cash, contest.initial_cash if contest else 1_000_000
    return user.cash, 1_000_000.0


# ---------------- 场内分析 ----------------

@router.get("/market")
def market_pulse(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    idx_secids = [s for s, _ in INDEXES]
    try:
        idx_quotes = fetch_quotes(idx_secids)
    except Exception:
        idx_quotes = {}
    indexes = []
    for secid, name in INDEXES:
        q = idx_quotes.get(secid)
        if q and q.get("price"):
            indexes.append({"symbol": secid.split(".")[1], "name": name, "price": q["price"],
                            "change_pct": q["change_pct"]})

    stocks = db.query(Stock).filter(Stock.is_active.is_(True)).all()
    quotes = realtime_quotes(db, [s.id for s in stocks])
    rows = []
    up = down = flat = 0
    for s in stocks:
        q = quotes.get(s.id)
        if not q:
            continue
        chg = q.get("change_pct", 0)
        if chg > 0:
            up += 1
        elif chg < 0:
            down += 1
        else:
            flat += 1
        rows.append({"id": s.id, "code": s.symbol, "name": q.get("name") or s.name,
                     "market": s.market, "price": q["price"], "change_pct": chg})

    gainers = sorted(rows, key=lambda x: x["change_pct"], reverse=True)[:5]
    losers = sorted(rows, key=lambda x: x["change_pct"])[:5]

    # 距 60 日高点（强势榜）：需日K，取前 24 只的缓存即可
    strength = []
    for s in stocks:
        bar = (
            db.query(DailyBar)
            .filter(DailyBar.stock_id == s.id)
            .order_by(DailyBar.date.desc())
            .first()
        )
        if bar is None:
            continue
        highs = (
            db.query(DailyBar.high)
            .filter(DailyBar.stock_id == s.id)
            .order_by(DailyBar.date.desc())
            .limit(60)
            .all()
        )
        high60 = max(h[0] for h in highs)
        q = quotes.get(s.id)
        if q:
            strength.append({
                "code": s.symbol, "name": s.name, "price": q["price"],
                "off_high": round((q["price"] / high60 - 1) * 100, 2),
            })
    strength.sort(key=lambda x: x["off_high"], reverse=True)

    return {
        "indexes": indexes,
        "breadth": {"up": up, "down": down, "flat": flat, "total": up + down + flat},
        "gainers": gainers,
        "losers": losers,
        "strength_top": strength[:8],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------- 持仓分析 ----------------

@router.get("/portfolio")
def portfolio(contest_id: int = 0, db: Session = Depends(get_db),
              user: User = Depends(require_user)):
    cash, initial_cash = _resolve(db, user, contest_id)
    positions = db.query(Position).filter(
        Position.user_id == user.id, Position.contest_id == contest_id
    ).all()
    quotes = realtime_quotes(db, [p.stock_id for p in positions]) if positions else {}

    items = []
    total_mv = 0.0
    day_pnl = 0.0
    for p in positions:
        q = quotes.get(p.stock_id, {})
        price = q.get("price", p.avg_cost)
        prev = q.get("prev_close", price)
        mv = price * p.qty
        total_mv += mv
        day_pnl += (price - prev) * p.qty
        # 决策树信号
        rows = (
            db.query(DailyBar)
            .filter(DailyBar.stock_id == p.stock_id)
            .order_by(DailyBar.date.desc())
            .limit(120)
            .all()
        )
        verdict, score = "数据不足", 50
        if len(rows) >= 70:
            rows.reverse()
            bars = [{"date": b.date, "open": b.open, "high": b.high,
                     "low": b.low, "close": b.close, "volume": b.volume} for b in rows]
            f = _facts(bars)
            verdict, score, _ = _verdict(f)
        items.append({
            "stock_id": p.stock_id, "code": p.stock.symbol, "name": p.stock.name,
            "market": p.stock.market, "qty": p.qty, "avg_cost": p.avg_cost,
            "price": price, "market_value": round(mv, 2),
            "pnl": round((price - p.avg_cost) * p.qty, 2),
            "pnl_pct": round((price / p.avg_cost - 1) * 100, 2) if p.avg_cost else 0,
            "today_chg": round((price / prev - 1) * 100, 2) if prev else 0,
            "day_pnl": round((price - prev) * p.qty, 2),
            "verdict": verdict, "score": score,
        })
    total = cash + total_mv
    for it in items:
        it["weight"] = round(it["market_value"] / total * 100, 1) if total else 0
    items.sort(key=lambda x: x["market_value"], reverse=True)
    total_pnl = total - initial_cash
    return {
        "account": {"contest_id": contest_id, "cash": round(cash, 2),
                    "market_value": round(total_mv, 2), "total": round(total, 2)},
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round((total / initial_cash - 1) * 100, 2),
            "day_pnl": round(day_pnl, 2),
            "position_count": len(items),
            "top1_weight": items[0]["weight"] if items else 0,
        },
        "positions": items,
    }


# ---------------- 收益分析 ----------------

@router.get("/pnl")
def pnl(contest_id: int = 0, db: Session = Depends(get_db), user: User = Depends(require_user)):
    cash, initial_cash = _resolve(db, user, contest_id)
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id, Order.contest_id == contest_id)
        .order_by(Order.created_at)
        .all()
    )
    if not orders:
        return {"curve": [], "daily": [], "months": [], "stats": {}}

    price_series = {}
    for o in orders:
        if o.stock_id not in price_series:
            price_series[o.stock_id] = (
                db.query(DailyBar.date, DailyBar.close)
                .filter(DailyBar.stock_id == o.stock_id)
                .order_by(DailyBar.date)
                .all()
            )
    timeline = sorted(
        {o.created_at.date().isoformat() for o in orders}
        | {d for series in price_series.values() for d, _ in series}
    )

    from collections import defaultdict
    cash_now, holdings = initial_cash, defaultdict(int)
    pointers = defaultdict(int)
    last_price = defaultdict(float)
    curve = []
    oi = 0
    for d in timeline:
        while oi < len(orders) and orders[oi].created_at.date().isoformat() <= d:
            o = orders[oi]
            if o.side == "buy":
                cash_now -= o.amount + o.fee
                holdings[o.stock_id] += o.qty
            else:
                cash_now += o.amount - o.fee
                holdings[o.stock_id] -= o.qty
            oi += 1
        for sid, series in price_series.items():
            while pointers[sid] < len(series) and series[pointers[sid]][0] <= d:
                last_price[sid] = series[pointers[sid]][1]
                pointers[sid] += 1
        mv = sum(q * last_price[sid] for sid, q in holdings.items() if q > 0)
        curve.append({"date": d, "value": round(cash_now + mv, 2)})

    # 日收益与回撤
    daily, peak, max_dd = [], curve[0]["value"], 0.0
    dd_series = []
    for i, p in enumerate(curve):
        peak = max(peak, p["value"])
        dd = round((p["value"] / peak - 1) * 100, 2)
        max_dd = min(max_dd, dd)
        dd_series.append({"date": p["date"], "dd": dd})
        if i > 0:
            prev = curve[i - 1]["value"]
            if prev > 0:
                daily.append({"date": p["date"],
                              "ret": round((p["value"] / prev - 1) * 100, 2)})
    win_days = len([d for d in daily if d["ret"] > 0])
    best = max(daily, key=lambda d: d["ret"]) if daily else None
    worst = min(daily, key=lambda d: d["ret"]) if daily else None

    # 月度收益
    months = {}
    for p in curve:
        key = p["date"][:7]
        months[key] = p["value"]
    month_rows = []
    keys = sorted(months.keys())
    prev_v = initial_cash
    for k in keys:
        v = months[k]
        month_rows.append({"month": k, "value": v, "ret": round((v / prev_v - 1) * 100, 2)})
        prev_v = v

    # 基准：沪深300 归一化
    try:
        idx_bars = fetch_kline("1.000300", beg=curve[0]["date"].replace("-", ""))
        idx_map = {b["date"]: b["close"] for b in idx_bars}
        base = idx_map.get(curve[0]["date"]) or next(iter(idx_map.values()), None)
        benchmark = [
            {"date": p["date"], "value": round(idx_map[d] / base * initial_cash, 2)}
            for p in curve
            if (d := p["date"]) in idx_map and base
        ]
    except Exception:
        benchmark = []

    total_ret = round((curve[-1]["value"] / initial_cash - 1) * 100, 2)
    return {
        "curve": curve,
        "benchmark": benchmark,
        "drawdown": dd_series,
        "daily": daily,
        "months": month_rows,
        "stats": {
            "total_return": total_ret,
            "max_drawdown": max_dd,
            "win_days_pct": round(win_days / len(daily) * 100, 1) if daily else 0,
            "best_day": best,
            "worst_day": worst,
            "track_days": len(curve),
        },
    }
