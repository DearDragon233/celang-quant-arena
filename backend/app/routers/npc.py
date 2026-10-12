"""NPC 竞技场接口：赛博斗蛐蛐。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import NpcOrder, NpcTrader, Position, User
from ..npc import refresh_all
from ..security import get_current_user
from ..services import realtime_quotes

router = APIRouter(prefix="/api/npc", tags=["NPC竞技场"], dependencies=[Depends(get_current_user)])


@router.get("/arena")
def arena(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    refresh_all(db)
    traders = db.query(NpcTrader).all()
    stock_ids = [t.stock_id for t in traders]
    quotes = realtime_quotes(db, stock_ids) if stock_ids else {}

    rows = []
    for t in traders:
        q = quotes.get(t.stock_id, {})
        price = q.get("price", 0)
        # 从订单重放当前持仓
        orders = (
            db.query(NpcOrder)
            .filter(NpcOrder.trader_id == t.id)
            .order_by(NpcOrder.id)
            .all()
        )
        qty = sum(o.qty if o.side == "buy" else -o.qty for o in orders)
        market_value = price * qty
        total = t.cash + market_value
        curve = json.loads(t.curve or "[]")
        last_order = orders[-1] if orders else None
        rows.append({
            "id": t.id, "name": t.name, "title": t.title, "avatar": t.avatar,
            "style_tag": t.style_tag, "bio": t.bio,
            "stock": f"{t.stock.name} {t.stock.symbol}",
            "market": t.stock.market,
            "cash": round(t.cash, 2), "market_value": round(market_value, 2),
            "total": round(total, 2),
            "return_pct": round((total / t.initial_cash - 1) * 100, 2),
            "order_count": len(orders),
            "holding": qty,
            "last_action": ({
                "side": last_order.side, "date": last_order.trade_date,
                "reason": last_order.reason,
                "text": f"{'买入' if last_order.side == 'buy' else '卖出'} {last_order.qty} 股 @ {last_order.price}",
            } if last_order else None),
            "curve": curve[-60:],
        })
    rows.sort(key=lambda x: x["return_pct"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    # 人类选手成绩对比
    humans = db.query(User).filter(User.role == "user", User.is_active.is_(True)).all()
    pos_quotes = realtime_quotes(db, [p.stock_id for p in db.query(Position).all()]) if db.query(Position).count() else {}
    my_total = None
    for u in humans:
        if u.id == user.id:
            mv = sum(
                pos_quotes.get(p.stock_id, {}).get("price", 0) * p.qty
                for p in db.query(Position).filter(Position.user_id == u.id).all()
            )
            my_total = u.cash + mv
    best_npc = rows[0] if rows else None
    return {
        "npcs": rows,
        "me": ({
            "nickname": user.nickname,
            "total": round(my_total, 2),
            "return_pct": round((my_total / 1_000_000 - 1) * 100, 2),
            "beats_best_npc": bool(best_npc and my_total / 1_000_000 - 1 > best_npc["return_pct"] / 100),
        } if my_total is not None else None),
    }


@router.get("/{trader_id}")
def detail(trader_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    t = db.get(NpcTrader, trader_id)
    if t is None:
        raise HTTPException(status_code=404, detail="NPC 不存在")
    orders = (
        db.query(NpcOrder)
        .filter(NpcOrder.trader_id == trader_id)
        .order_by(NpcOrder.id.desc())
        .limit(50)
        .all()
    )
    qty = {}
    for o in db.query(NpcOrder).filter(NpcOrder.trader_id == trader_id).order_by(NpcOrder.id).all():
        qty[o.stock_id] = qty.get(o.stock_id, 0) + (o.qty if o.side == "buy" else -o.qty)
    holdings = {sid: q for sid, q in qty.items() if q > 0}
    return {
        "trader": {"id": t.id, "name": t.name, "title": t.title, "avatar": t.avatar,
                   "style_tag": t.style_tag, "bio": t.bio, "stock_name": t.stock.name},
        "orders": [
            {"id": o.id, "side": o.side, "price": o.price, "qty": o.qty,
             "amount": o.amount, "fee": o.fee, "reason": o.reason, "date": o.trade_date}
            for o in orders
        ],
        "holdings": [
            {"stock_id": sid, "qty": q, "name": db_stock_name(db, sid)} for sid, q in holdings.items()
        ],
        "curve": json.loads(t.curve or "[]"),
    }


def db_stock_name(db, stock_id):
    from ..models import Stock
    s = db.get(Stock, stock_id)
    return s.name if s else ""
