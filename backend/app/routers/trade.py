"""模拟盘交易：实时价成交、持仓摊薄成本、账户与资产曲线。"""
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Contest, ContestEntry, DailyBar, Order, Position, Stock, User
from ..security import get_current_user
from ..services import realtime_quotes

FEE_RATE = 0.0003   # 佣金万三
MIN_FEE = 5.0       # 最低佣金
STAMP_TAX = 0.0005  # 卖出印花税（A股；美股仅佣金）
LOT = {"CN": 100, "US": 1}  # A股一手100股，美股按股
INITIAL_CASH = 1_000_000.0

router = APIRouter(prefix="/api/trade", tags=["模拟交易"], dependencies=[Depends(get_current_user)])


def require_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "user":
        raise HTTPException(status_code=403, detail="模拟盘仅对参赛选手账户开放")
    return user


class TradeRequest(BaseModel):
    stock_id: int
    qty: int = Field(gt=0)
    contest_id: int = 0  # 0=年度常驻账户


def resolve_account(db: Session, user: User, contest_id: int):
    """返回 (cash_obj, initial_cash, account_name)。"""
    if contest_id:
        entry = (
            db.query(ContestEntry)
            .filter(ContestEntry.contest_id == contest_id, ContestEntry.user_id == user.id)
            .first()
        )
        if entry is None:
            raise HTTPException(status_code=403, detail="尚未报名该比赛")
        contest = db.get(Contest, contest_id)
        if contest is None or contest.status != "published":
            raise HTTPException(status_code=400, detail="比赛不存在或未发布")
        now = datetime.now()
        if now < contest.start_date or now > contest.end_date:
            raise HTTPException(status_code=400, detail="当前不在比赛交易时间窗口内")
        return entry, contest.initial_cash, contest.name
    return user, INITIAL_CASH, "年度场（常驻）" 


def _quote_price(db: Session, stock: Stock):
    q = realtime_quotes(db, [stock.id]).get(stock.id)
    if not q or not q.get("price"):
        raise HTTPException(status_code=503, detail="实时行情暂不可用，请稍后重试")
    return q


def _positions_payload(db: Session, user: User, contest_id: int = 0,
                       initial_cash: float = INITIAL_CASH, account_name: str = "年度场（常驻）",
                       cash_obj=None):
    positions = db.query(Position).filter(
        Position.user_id == user.id, Position.contest_id == contest_id
    ).all()
    items, market_value = [], 0.0
    quotes = realtime_quotes(db, [p.stock_id for p in positions]) if positions else {}
    for p in positions:
        q = quotes.get(p.stock_id)
        price = q["price"] if q else p.avg_cost
        value = price * p.qty
        market_value += value
        items.append({
            "id": p.id, "stock_id": p.stock_id, "code": p.stock.symbol,
            "name": p.stock.name, "market": p.stock.market,
            "qty": p.qty, "avg_cost": p.avg_cost, "price": price,
            "market_value": round(value, 2),
            "profit": round((price - p.avg_cost) * p.qty, 2),
            "profit_pct": round((price / p.avg_cost - 1) * 100, 2) if p.avg_cost else 0,
        })
    return {
        "account_name": account_name,
        "contest_id": contest_id,
        "cash": round(cash_obj.cash, 2),
        "market_value": round(market_value, 2),
        "total": round(cash_obj.cash + market_value, 2),
        "positions": items,
    }


@router.get("/account")
def account(contest_id: int = 0, db: Session = Depends(get_db), user: User = Depends(require_user)):
    cash_obj, initial_cash, account_name = resolve_account(db, user, contest_id)
    info = _positions_payload(db, user, contest_id, initial_cash, account_name, cash_obj)
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id, Order.contest_id == contest_id)
        .order_by(Order.created_at)
        .all()
    )
    curve = []
    if orders:
        price_series = {}
        for o in orders:
            if o.stock_id not in price_series:
                rows = (
                    db.query(DailyBar.date, DailyBar.close)
                    .filter(DailyBar.stock_id == o.stock_id)
                    .order_by(DailyBar.date)
                    .all()
                )
                price_series[o.stock_id] = rows
        timeline = sorted(
            {o.created_at.date().isoformat() for o in orders}
            | {d for series in price_series.values() for d, _ in series}
        )
        cash_now, holdings = initial_cash, defaultdict(int)
        pointers = defaultdict(int)
        last_price = defaultdict(lambda: 0.0)
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
        # 末尾补一个实时点，保证曲线终点 == 当前总资产
        curve.append({"date": datetime.now().date().isoformat(), "value": info["total"]})
    return {**info, "curve": curve}


def _trade(db: Session, user: User, stock: Stock, qty: int, side: str, contest_id: int = 0):
    cash_obj, _, _ = resolve_account(db, user, contest_id)
    lot = LOT.get(stock.market, 1)
    if qty % lot != 0:
        raise HTTPException(status_code=400, detail=f"{'买入' if side == 'buy' else '卖出'}数量必须为 {lot} 股的整数倍" if lot > 1 else "数量无效")
    q = _quote_price(db, stock)
    price = q["price"]
    amount = price * qty
    if side == "buy":
        fee = max(amount * FEE_RATE, MIN_FEE)
        if amount + fee > cash_obj.cash:
            raise HTTPException(status_code=400, detail=f"可用资金不足，需 {round(amount + fee, 2)} 元")
        cash_obj.cash -= amount + fee
        pos = db.query(Position).filter(
            Position.user_id == user.id, Position.stock_id == stock.id,
            Position.contest_id == contest_id
        ).first()
        if pos is None:
            pos = Position(user_id=user.id, stock_id=stock.id, qty=0, avg_cost=0, contest_id=contest_id)
            db.add(pos)
        pos.avg_cost = round((pos.avg_cost * pos.qty + amount) / (pos.qty + qty), 4)
        pos.qty += qty
    else:
        pos = db.query(Position).filter(
            Position.user_id == user.id, Position.stock_id == stock.id,
            Position.contest_id == contest_id
        ).first()
        if pos is None or pos.qty < qty:
            raise HTTPException(status_code=400, detail="卖出数量超过持仓数量")
        fee = max(amount * (FEE_RATE + (STAMP_TAX if stock.market == "CN" else 0)), MIN_FEE)
        cash_obj.cash += amount - fee
        pos.qty -= qty
        if pos.qty == 0:
            db.delete(pos)
    order = Order(user_id=user.id, stock_id=stock.id, side=side, price=price, qty=qty,
                  amount=round(amount, 2), fee=round(fee, 2), contest_id=contest_id)
    db.add(order)
    db.commit()
    return {"detail": "ok", "price": price, "amount": round(amount, 2), "fee": round(fee, 2),
            "name": stock.name, "market": stock.market}


@router.post("/buy")
def buy(body: TradeRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    stock = db.get(Stock, body.stock_id)
    if stock is None or not stock.is_active:
        raise HTTPException(status_code=404, detail="股票不在交易池中")
    return _trade(db, user, stock, body.qty, "buy", body.contest_id)


@router.post("/sell")
def sell(body: TradeRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    stock = db.get(Stock, body.stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="股票不存在")
    return _trade(db, user, stock, body.qty, "sell", body.contest_id)


@router.get("/orders")
def orders(page: int = 1, size: int = 15, side: str = "", contest_id: int = 0,
           db: Session = Depends(get_db), user: User = Depends(require_user)):
    query = db.query(Order).filter(Order.user_id == user.id, Order.contest_id == contest_id)
    if side:
        query = query.filter(Order.side == side)
    total = query.count()
    items = query.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {"id": o.id, "code": o.stock.symbol, "name": o.stock.name, "market": o.stock.market,
             "side": o.side, "price": o.price, "qty": o.qty, "amount": o.amount, "fee": o.fee,
             "time": o.created_at.isoformat(timespec="seconds")}
            for o in items
        ],
    }
