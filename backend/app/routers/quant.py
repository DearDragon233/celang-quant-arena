"""量化模块：策略配置 CRUD 与回测运行（基于真实日K缓存）。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..datasource import fetch_kline
from ..engine import run_backtest
from ..models import BacktestRun, DailyBar, Stock, Strategy, User
from ..security import get_current_user

KINDS = {
    "dual_ma": {"name": "双均线交叉", "source": "Backtrader 社区经典", "params": ["fast", "slow"],
                "defaults": {"fast": 5, "slow": 20}},
    "macd": {"name": "MACD 趋势", "source": "Gerald Appel 经典趋势指标", "params": ["fast", "slow", "signal"],
             "defaults": {"fast": 12, "slow": 26, "signal": 9}},
    "rsi": {"name": "RSI 均值回复", "source": "J. Welles Wilder《技术交易系统新概念》", "params": ["period", "oversold", "overbought"],
            "defaults": {"period": 14, "oversold": 30, "overbought": 70}},
    "boll": {"name": "布林带均值回复", "source": "John Bollinger 布林带体系", "params": ["period", "k"],
             "defaults": {"period": 20, "k": 2}},
    "turtle": {"name": "海龟突破", "source": "海龟交易法则 / ABU 量化 AbuFactorBuyBreak", "params": ["entry", "exit"],
               "defaults": {"entry": 20, "exit": 10}},
    "momentum": {"name": "动量趋势", "source": "Qlib Alpha158 动量因子思路", "params": ["lookback"],
                 "defaults": {"lookback": 20}},
}

router = APIRouter(prefix="/api/quant", tags=["量化回测"], dependencies=[Depends(get_current_user)])


def require_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "user":
        raise HTTPException(status_code=403, detail="量化模块仅对参赛选手账户开放")
    return user


class StrategySave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    stock_id: int
    kind: str
    params: dict = {}
    start_date: str
    end_date: str
    initial_cash: float = Field(gt=0)


@router.get("/meta")
def meta(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stocks = db.query(Stock).filter(Stock.is_active.is_(True)).order_by(Stock.market, Stock.symbol).all()
    date_range = {}
    for sid, d in db.query(DailyBar.stock_id, DailyBar.date).order_by(DailyBar.stock_id, DailyBar.date).all():
        lo, hi = date_range.get(sid, (d, d))
        date_range[sid] = (min(lo, d), max(hi, d))
    return {
        "kinds": [
            {"key": k, "name": v["name"], "source": v["source"],
             "params": v["params"], "defaults": v["defaults"]}
            for k, v in KINDS.items()
        ],
        "stocks": [
            {"id": s.id, "symbol": s.symbol, "code": s.symbol, "name": s.name, "market": s.market,
             "start": date_range.get(s.id, ("", ""))[0], "end": date_range.get(s.id, ("", ""))[1]}
            for s in stocks
        ],
    }


@router.get("/strategies")
def my_strategies(db: Session = Depends(get_db), user: User = Depends(require_user)):
    rows = db.query(Strategy).filter(Strategy.user_id == user.id).order_by(Strategy.id.desc()).all()
    return [
        {"id": s.id, "name": s.name, "stock_id": s.stock_id, "code": s.stock.symbol,
         "stock_name": s.stock.name, "kind": s.kind, "kind_name": KINDS.get(s.kind, {}).get("name", s.kind),
         "params": json.loads(s.params), "start_date": s.start_date, "end_date": s.end_date,
         "initial_cash": s.initial_cash, "created_at": s.created_at.isoformat(timespec="seconds")}
        for s in rows
    ]


@router.post("/strategies")
def save_strategy(body: StrategySave, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="未知策略类型")
    if body.start_date >= body.end_date:
        raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")
    stock = db.get(Stock, body.stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="股票不存在")
    s = Strategy(user_id=user.id, name=body.name, stock_id=body.stock_id, kind=body.kind,
                 params=json.dumps(body.params), start_date=body.start_date,
                 end_date=body.end_date, initial_cash=body.initial_cash)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id}


@router.delete("/strategies/{sid}")
def delete_strategy(sid: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    s = db.get(Strategy, sid)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(s)
    db.commit()
    return {"detail": "ok"}


def _bars_in_range(db: Session, stock: Stock, start: str, end: str):
    """从缓存取日K；缓存为空或明显过期时从数据源补拉。"""
    rows = (
        db.query(DailyBar)
        .filter(DailyBar.stock_id == stock.id, DailyBar.date >= start, DailyBar.date <= end)
        .order_by(DailyBar.date)
        .all()
    )
    if len(rows) < 30:
        try:
            fresh = fetch_kline(stock.em_secid, beg=start.replace("-", ""), end=end.replace("-", ""))
            known = {b.date for b in rows}
            for b in fresh:
                if b["date"] not in known:
                    db.add(DailyBar(stock_id=stock.id, **b))
            db.commit()
            rows = (
                db.query(DailyBar)
                .filter(DailyBar.stock_id == stock.id, DailyBar.date >= start, DailyBar.date <= end)
                .order_by(DailyBar.date)
                .all()
            )
        except Exception:
            pass
    if len(rows) < 30:
        raise HTTPException(status_code=400, detail=f"区间内行情数据不足（{len(rows)} 条，至少需要 30 条）")
    return [{"date": b.date, "open": b.open, "high": b.high, "low": b.low,
             "close": b.close, "volume": b.volume} for b in rows]


@router.post("/backtest")
def backtest(body: StrategySave, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="未知策略类型")
    stock = db.get(Stock, body.stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="股票不存在")
    bars = _bars_in_range(db, stock, body.start_date, body.end_date)
    metrics, equity, trades = run_backtest(body.kind, bars, body.params, body.initial_cash)
    return {"metrics": metrics, "equity": equity, "trades": trades, "bars": bars}


@router.post("/backtest/save")
def backtest_save(body: StrategySave, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="未知策略类型")
    stock = db.get(Stock, body.stock_id)
    if stock is None:
        raise HTTPException(status_code=404, detail="股票不存在")
    bars = _bars_in_range(db, stock, body.start_date, body.end_date)
    metrics, equity, trades = run_backtest(body.kind, bars, body.params, body.initial_cash)
    run = BacktestRun(
        user_id=user.id, strategy_id=None, strategy_name=body.name, stock_id=stock.id,
        kind=body.kind, params=json.dumps(body.params), start_date=body.start_date,
        end_date=body.end_date, initial_cash=body.initial_cash,
        metrics=json.dumps(metrics), equity=json.dumps(equity), trades=json.dumps(trades),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "metrics": metrics}


@router.get("/runs")
def my_runs(db: Session = Depends(get_db), user: User = Depends(require_user)):
    rows = db.query(BacktestRun).filter(BacktestRun.user_id == user.id).order_by(BacktestRun.id.desc()).limit(30).all()
    return [
        {"id": r.id, "strategy_name": r.strategy_name, "code": r.stock.symbol, "stock_name": r.stock.name,
         "kind": r.kind, "kind_name": KINDS.get(r.kind, {}).get("name", r.kind),
         "start_date": r.start_date, "end_date": r.end_date, "initial_cash": r.initial_cash,
         "metrics": json.loads(r.metrics), "created_at": r.created_at.isoformat(timespec="seconds")}
        for r in rows
    ]


@router.get("/runs/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    r = db.get(BacktestRun, run_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="回测记录不存在")
    return {
        "id": r.id, "strategy_name": r.strategy_name, "code": r.stock.symbol, "stock_name": r.stock.name,
        "kind": r.kind, "params": json.loads(r.params),
        "start_date": r.start_date, "end_date": r.end_date, "initial_cash": r.initial_cash,
        "metrics": json.loads(r.metrics), "equity": json.loads(r.equity), "trades": json.loads(r.trades),
        "created_at": r.created_at.isoformat(timespec="seconds"),
    }
