from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..datasource import fetch_kline
from ..models import DailyBar, Stock, User
from ..security import get_current_user
from ..services import realtime_quotes

router = APIRouter(prefix="/api/market", tags=["行情"], dependencies=[Depends(get_current_user)])


@router.get("/stocks")
def stock_list(db: Session = Depends(get_db)):
    """股票池列表 + 实时行情（A股/美股），按涨跌幅排序。"""
    stocks = db.query(Stock).filter(Stock.is_active.is_(True)).order_by(Stock.market, Stock.symbol).all()
    quotes = realtime_quotes(db, [s.id for s in stocks])
    out = []
    for s in stocks:
        q = quotes.get(s.id)
        if not q:
            continue
        prev_close = q.get("prev_close") or 0
        out.append({
            "id": s.id, "symbol": s.symbol, "code": s.symbol, "name": q.get("name") or s.name,
            "market": s.market, "sector": s.sector,
            "price": q["price"], "change_pct": q["change_pct"],
            "open": q.get("open") or prev_close,
            "high": q.get("high") or prev_close, "low": q.get("low") or prev_close,
            "prev_close": prev_close,
        })
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out


@router.get("/kline/{stock_id}")
def kline(stock_id: int, days: int = 120, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """真实日K：优先读缓存，缓存最新日期落后于数据源时自动刷新。"""
    stock = db.get(Stock, stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="股票不存在")

    cached = (
        db.query(DailyBar)
        .filter(DailyBar.stock_id == stock_id)
        .order_by(DailyBar.date.desc())
        .limit(min(days, 500))
        .all()
    )
    cached.reverse()
    need_refresh = True
    if cached:
        try:
            # force=True 绕过 60 秒内存缓存，保证盘中当日K线及时进入
            remote_tail = fetch_kline(stock.em_secid, beg=cached[-1].date.replace("-", ""), force=True)
            remote_new = [b for b in remote_tail if b["date"] > cached[-1].date]
            if remote_new:
                known = {b.date for b in cached}
                for b in remote_new:
                    if b["date"] not in known:
                        db.add(DailyBar(stock_id=stock_id, **b))
                db.commit()
                cached.extend(remote_new)
            need_refresh = False
        except Exception:
            need_refresh = False
    if need_refresh and not cached:
        try:
            for b in fetch_kline(stock.em_secid):
                db.add(DailyBar(stock_id=stock_id, **b))
            db.commit()
            cached = (
                db.query(DailyBar)
                .filter(DailyBar.stock_id == stock_id)
                .order_by(DailyBar.date.desc())
                .limit(min(days, 500))
                .all()
            )
            cached.reverse()
        except Exception:
            pass

    if not cached:
        raise HTTPException(status_code=503, detail="行情数据暂不可用，请稍后重试")

    return {
        "stock": {"id": stock.id, "symbol": stock.symbol, "name": stock.name,
                  "market": stock.market, "sector": stock.sector, "description": stock.description},
        "bars": [
            {"date": b.date, "open": b.open, "high": b.high, "low": b.low,
             "close": b.close, "volume": b.volume}
            for b in cached
        ],
    }
