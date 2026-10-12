"""管理端：看板 / 用户管理 / 股票池管理 / 全局成交 / 大赛设置。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BacktestRun, Order, Position, Setting, Stock, Strategy, User
from ..security import hash_password, require_admin
from ..services import realtime_quotes

router = APIRouter(prefix="/api/admin", tags=["管理端"], dependencies=[Depends(require_admin)])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    user_count = db.query(func.count(User.id)).filter(User.role == "user").scalar() or 0
    stock_count = db.query(func.count(Stock.id)).filter(Stock.is_active.is_(True)).scalar() or 0
    order_count = db.query(func.count(Order.id)).scalar() or 0
    turnover = db.query(func.coalesce(func.sum(Order.amount), 0)).scalar() or 0
    strategy_count = db.query(func.count(Strategy.id)).scalar() or 0
    backtest_count = db.query(func.count(BacktestRun.id)).scalar() or 0

    positions = db.query(Position).all()
    quotes = realtime_quotes(db, [p.stock_id for p in positions]) if positions else {}
    holdings_value = sum(
        quotes.get(p.stock_id, {}).get("price", 0) * p.qty for p in positions
    )
    total_equity = (
        db.query(func.coalesce(func.sum(User.cash), 0)).filter(User.role == "user").scalar() or 0
    ) + holdings_value

    hot = (
        db.query(Order.stock_id, func.count(Order.id).label("cnt"), func.sum(Order.amount))
        .group_by(Order.stock_id)
        .order_by(func.count(Order.id).desc())
        .limit(8)
        .all()
    )
    hot_list = []
    for sid, cnt, amount in hot:
        stock = db.get(Stock, sid)
        hot_list.append({"code": stock.symbol, "name": stock.name, "count": cnt,
                         "amount": round(amount or 0, 0)})

    latest = db.query(Order).order_by(Order.id.desc()).limit(8).all()
    settings = {r.key: r.value for r in db.query(Setting).all()}
    return {
        "cards": {
            "user_count": user_count, "stock_count": stock_count,
            "order_count": order_count, "turnover": round(turnover, 0),
            "strategy_count": strategy_count, "backtest_count": backtest_count,
            "total_equity": round(total_equity, 0),
        },
        "hot_stocks": hot_list,
        "latest_orders": [
            {"id": o.id, "user": o.user.nickname, "code": o.stock.symbol, "name": o.stock.name,
             "side": o.side, "price": o.price, "qty": o.qty, "amount": o.amount,
             "time": o.created_at.isoformat(timespec="seconds")}
            for o in latest
        ],
        "settings": settings,
    }


@router.get("/users")
def list_users(page: int = 1, size: int = 10, keyword: str = "", db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == "user")
    if keyword:
        query = query.filter(User.username.contains(keyword) | User.nickname.contains(keyword)
                             | User.school.contains(keyword))
    total = query.count()
    items = query.order_by(User.id).offset((page - 1) * size).limit(size).all()
    quotes = realtime_quotes(db, [p.stock_id for p in db.query(Position).all()])
    out = []
    for u in items:
        pos_value = sum(
            quotes.get(p.stock_id, {}).get("price", 0) * p.qty
            for p in db.query(Position).filter(Position.user_id == u.id).all()
        )
        out.append({
            "id": u.id, "username": u.username, "nickname": u.nickname, "school": u.school,
            "cash": round(u.cash, 2), "total": round(u.cash + pos_value, 2),
            "order_count": db.query(func.count(Order.id)).filter(Order.user_id == u.id).scalar() or 0,
            "is_active": u.is_active, "created_at": u.created_at.isoformat(timespec="seconds"),
        })
    return {"total": total, "items": out}


@router.put("/users/{user_id}")
def update_user(user_id: int, body: dict, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None or u.role != "user":
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.get("password"):
        if len(body["password"]) < 6:
            raise HTTPException(status_code=400, detail="密码至少 6 位")
        u.password_hash = hash_password(body["password"])
    if "is_active" in body:
        u.is_active = bool(body["is_active"])
    if "nickname" in body and body["nickname"]:
        u.nickname = body["nickname"]
    db.commit()
    return {"detail": "ok"}


@router.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).order_by(Stock.market, Stock.symbol).all()
    quotes = realtime_quotes(db, [s.id for s in stocks])
    return [
        {
            "id": s.id, "symbol": s.symbol, "name": s.name, "market": s.market, "sector": s.sector,
            "description": s.description, "is_active": s.is_active,
            "price": quotes.get(s.id, {}).get("price", 0),
            "change_pct": quotes.get(s.id, {}).get("change_pct", 0),
        }
        for s in stocks
    ]


@router.put("/stocks/{stock_id}")
def update_stock(stock_id: int, body: dict, db: Session = Depends(get_db)):
    s = db.get(Stock, stock_id)
    if s is None:
        raise HTTPException(status_code=404, detail="股票不存在")
    if "is_active" in body:
        s.is_active = bool(body["is_active"])
    if "description" in body:
        s.description = str(body["description"])[:255]
    db.commit()
    return {"detail": "ok"}


@router.get("/orders")
def list_orders(page: int = 1, size: int = 12, side: str = "", keyword: str = "",
                db: Session = Depends(get_db)):
    query = db.query(Order)
    if side:
        query = query.filter(Order.side == side)
    if keyword:
        like = f"%{keyword}%"
        query = query.join(User, Order.user_id == User.id).filter(
            User.nickname.like(like) | User.username.like(like)
        )
    total = query.count()
    items = query.order_by(Order.id.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {"id": o.id, "user": o.user.nickname, "code": o.stock.symbol, "name": o.stock.name,
             "market": o.stock.market, "side": o.side, "price": o.price, "qty": o.qty,
             "amount": o.amount, "fee": o.fee,
             "time": o.created_at.isoformat(timespec="seconds")}
            for o in items
        ],
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {r.key: r.value for r in db.query(Setting).all()}


@router.put("/settings")
def update_settings(body: dict, db: Session = Depends(get_db)):
    allowed = {"comp_name", "comp_season", "comp_start", "comp_end"}
    for k, v in body.items():
        if k in allowed:
            row = db.get(Setting, k)
            if row is None:
                db.add(Setting(key=k, value=str(v)))
            else:
                row.value = str(v)
    db.commit()
    return {"detail": "ok"}
