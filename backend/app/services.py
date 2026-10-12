"""公共辅助：实时价格与行情快照。"""
from .datasource import fetch_quotes
from .models import DailyBar, Stock


def _stock_rows(db, stock_ids=None):
    query = db.query(Stock)
    if stock_ids:
        query = query.filter(Stock.id.in_(stock_ids))
    return query.all()


def realtime_quotes(db, stock_ids=None):
    """批量获取实时价：{stock_id: {price, change_pct, ...}}。数据源异常时回退日线收盘。"""
    stocks = _stock_rows(db, stock_ids)
    out = {}
    secid_map = {s.em_secid: s for s in stocks if s.em_secid}
    try:
        quotes = fetch_quotes(list(secid_map.keys()))
    except Exception:
        quotes = {}
    for secid, q in quotes.items():
        s = secid_map.get(secid)
        if s:
            out[s.id] = q
    # 数据源失败或缺失的标的回退到日线收盘
    missing = [s for s in stocks if s.id not in out]
    for s in missing:
        bar = (
            db.query(DailyBar)
            .filter(DailyBar.stock_id == s.id)
            .order_by(DailyBar.date.desc())
            .first()
        )
        if bar:
            prev = (
                db.query(DailyBar)
                .filter(DailyBar.stock_id == s.id, DailyBar.date < bar.date)
                .order_by(DailyBar.date.desc())
                .first()
            )
            out[s.id] = {
                "name": s.name, "price": bar.close,
                "change_pct": round((bar.close / prev.close - 1) * 100, 2) if prev else 0,
                "open": bar.open, "high": bar.high, "low": bar.low,
                "prev_close": prev.close if prev else bar.close,
            }
    return out


def realtime_price(db, stock_id: int) -> float:
    q = realtime_quotes(db, [stock_id]).get(stock_id)
    return q["price"] if q else 0.0


# 兼容旧调用名
def stock_snapshot(db, stock_id: int):
    q = realtime_quotes(db, [stock_id]).get(stock_id)
    return q
