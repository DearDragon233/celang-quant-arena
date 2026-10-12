"""比赛：管理员发布与管理，选手报名、比赛窗口与比赛排行。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Contest, ContestEntry, Position, Stock, User
from ..security import get_current_user, require_admin
from ..services import realtime_quotes

router = APIRouter(prefix="/api/contests", tags=["模拟盘比赛"])


def contest_status(c: Contest, now: datetime) -> str:
    if c.status != "published":
        return "未发布"
    if now < c.start_date:
        return "未开始"
    if now > c.end_date:
        return "已结束"
    return "进行中"


def _contest_out(c: Contest, entry_count: int = 0):
    return {
        "id": c.id, "name": c.name, "description": c.description,
        "initial_cash": c.initial_cash,
        "start_date": c.start_date.isoformat(timespec="seconds"),
        "end_date": c.end_date.isoformat(timespec="seconds"),
        "status_text": contest_status(c, datetime.now()),
        "published": c.status == "published",
        "entry_count": entry_count,
    }


class ContestSave(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: str = ""
    initial_cash: float = Field(gt=0)
    start_date: datetime
    end_date: datetime
    status: str = "published"


# ---------------- 管理端 ----------------
admin_router = APIRouter(prefix="/api/admin/contests", tags=["比赛管理"], dependencies=[Depends(require_admin)])


@admin_router.get("")
def admin_list(db: Session = Depends(get_db)):
    rows = db.query(Contest).order_by(Contest.id.desc()).all()
    counts = dict(db.query(ContestEntry.contest_id, func.count(ContestEntry.id)).group_by(ContestEntry.contest_id).all())
    return [_contest_out(c, counts.get(c.id, 0)) for c in rows]


@admin_router.post("")
def admin_create(body: ContestSave, db: Session = Depends(get_db)):
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    if body.status not in ("draft", "published"):
        raise HTTPException(status_code=400, detail="状态无效")
    c = Contest(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id}


@admin_router.put("/{contest_id}")
def admin_update(contest_id: int, body: ContestSave, db: Session = Depends(get_db)):
    c = db.get(Contest, contest_id)
    if c is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    data = body.model_dump()
    data.pop("initial_cash", None)  # 已报名账户资金不随设置变动
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    return {"detail": "ok"}


@admin_router.delete("/{contest_id}")
def admin_delete(contest_id: int, db: Session = Depends(get_db)):
    c = db.get(Contest, contest_id)
    if c is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if db.query(ContestEntry).filter(ContestEntry.contest_id == contest_id).count() > 0:
        raise HTTPException(status_code=400, detail="已有选手报名，只能下架（改为未发布）不能删除")
    db.delete(c)
    db.commit()
    return {"detail": "ok"}


# ---------------- 选手端 ----------------
@router.get("/window")
def window(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """比赛窗口：已发布的比赛 + 我的报名/成绩状态。"""
    rows = (
        db.query(Contest)
        .filter(Contest.status == "published")
        .order_by(Contest.start_date.desc())
        .all()
    )
    now = datetime.now()
    my_entries = {
        e.contest_id: e for e in
        db.query(ContestEntry).filter(ContestEntry.user_id == user.id).all()
    }
    out = []
    for c in rows:
        entry = my_entries.get(c.id)
        st = contest_status(c, now)
        total = None
        if entry:
            quotes = realtime_quotes(db, [p.stock_id for p in db.query(Position).filter(
                Position.user_id == user.id, Position.contest_id == c.id).all()])
            mv = sum(quotes.get(p.stock_id, {}).get("price", 0) * p.qty for p in db.query(Position).filter(
                Position.user_id == user.id, Position.contest_id == c.id).all())
            total = round(entry.cash + mv, 2)
        out.append({
            **_contest_out(c, db.query(ContestEntry).filter(ContestEntry.contest_id == c.id).count()),
            "joined": entry is not None,
            "ongoing": st == "进行中",
            "my_total": total,
            "my_return_pct": round((total / c.initial_cash - 1) * 100, 2) if total is not None else None,
        })
    return {"contests": out}


@router.post("/{contest_id}/join")
def join(contest_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Contest, contest_id)
    if c is None or c.status != "published":
        raise HTTPException(status_code=404, detail="比赛不存在或未发布")
    if db.query(ContestEntry).filter(ContestEntry.contest_id == contest_id, ContestEntry.user_id == user.id).first():
        raise HTTPException(status_code=400, detail="已报名该比赛")
    db.add(ContestEntry(contest_id=contest_id, user_id=user.id, cash=c.initial_cash))
    db.commit()
    return {"detail": "ok", "message": f"报名成功，已获得 {c.initial_cash:,.0f} 元比赛资金"}


@router.get("/{contest_id}/leaderboard")
def contest_leaderboard(contest_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    c = db.get(Contest, contest_id)
    if c is None or c.status != "published":
        raise HTTPException(status_code=404, detail="比赛不存在或未发布")
    entries = db.query(ContestEntry).filter(ContestEntry.contest_id == contest_id).all()
    quotes = realtime_quotes(db, [p.stock_id for p in db.query(Position).filter(
        Position.contest_id == contest_id).all()])
    rows = []
    for e in entries:
        u = db.get(User, e.user_id)
        mv = sum(
            quotes.get(p.stock_id, {}).get("price", 0) * p.qty
            for p in db.query(Position).filter(
                Position.user_id == e.user_id, Position.contest_id == contest_id).all()
        )
        total = e.cash + mv
        rows.append({
            "user_id": e.user_id, "nickname": u.nickname, "school": u.school,
            "total": round(total, 2),
            "return_pct": round((total / c.initial_cash - 1) * 100, 2),
        })
    rows.sort(key=lambda x: x["return_pct"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    me = next((r for r in rows if r["user_id"] == user.id), None)
    return {"contest": _contest_out(c, len(rows)), "list": rows, "me": me}
