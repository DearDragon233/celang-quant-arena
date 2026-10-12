"""大赛：排行榜 + 赛程信息。"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Position, Setting, Stock, User
from ..security import get_current_user
from ..services import realtime_quotes

router = APIRouter(prefix="/api/competition", tags=["大赛"], dependencies=[Depends(get_current_user)])

_lb_cache = {"ts": 0.0, "data": None}


def get_settings(db: Session) -> dict:
    rows = db.query(Setting).all()
    s = {r.key: r.value for r in rows}
    s.setdefault("comp_name", "全国大学生模拟炒股大赛")
    s.setdefault("comp_season", "")
    s.setdefault("comp_start", "")
    s.setdefault("comp_end", "")
    return s


@router.get("/info")
def info(db: Session = Depends(get_db)):
    return get_settings(db)


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import time
    if _lb_cache["data"] and time.time() - _lb_cache["ts"] < 10:
        data = _lb_cache["data"]
        me = next((r for r in data["list"] if r["user_id"] == user.id), None)
        return {**data, "me": me}
    return _leaderboard_impl(db, user)


def _leaderboard_impl(db: Session, user: User):
    users = db.query(User).filter(User.role == "user", User.is_active.is_(True)).all()
    positions = db.query(Position).filter(Position.qty > 0).all()
    quotes = realtime_quotes(db, list({p.stock_id for p in positions})) if positions else {}
    rows = []
    for u in users:
        total = u.cash + sum(
            quotes.get(p.stock_id, {}).get("price", 0) * p.qty
            for p in positions
            if p.user_id == u.id
        )
        rows.append({
            "user_id": u.id, "nickname": u.nickname, "school": u.school,
            "username": u.username,
            "total": round(total, 2),
            "return_pct": round((total / 1_000_000 - 1) * 100, 2),
            "position_count": sum(1 for p in positions if p.user_id == u.id),
            "order_count": db.query(Order).filter(Order.user_id == u.id).count(),
        })
    rows.sort(key=lambda x: x["return_pct"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    me = next((r for r in rows if r["user_id"] == user.id), None)
    import time
    data = {"list": rows, "settings": get_settings(db), "updated_at": datetime.now().isoformat(timespec="seconds")}
    _lb_cache["ts"] = time.time()
    _lb_cache["data"] = data
    return {**data, "me": me}
