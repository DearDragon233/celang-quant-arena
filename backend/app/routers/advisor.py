"""策略决策树顾问：基于多指标信号生成 长线/短线/技巧 三分支的决策树与今日雷达。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..datasource import fetch_kline
from ..datasource import fetch_quotes, index_regime
from ..engine import atr, boll, macd, ma, rsi
from ..models import DailyBar, Stock, User
from ..security import get_current_user

router = APIRouter(prefix="/api/advisor", tags=["策略决策树"], dependencies=[Depends(get_current_user)])

_cache = {"ts": 0.0, "data": None}
CACHE_TTL = 300  # 决策树 5 分钟缓存


def _facts(bars):
    """单只股票的技术信号事实。"""
    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]
    ma5, ma10, ma20, ma60 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 60)
    r14 = rsi(closes, 14)
    dif, dea, _ = macd(closes)
    _, b_up, b_low = boll(closes, 20, 2)
    a14 = atr(bars, 14)
    last = closes[-1]
    vol_ratio = vols[-1] / (sum(vols[-21:-1]) / 20) if len(vols) > 21 and sum(vols[-21:-1]) > 0 else 1.0
    high60 = max(b["high"] for b in bars[-60:])
    low60 = min(b["low"] for b in bars[-60:])
    mom20 = (last / closes[-21] - 1) * 100 if len(closes) > 21 else 0

    ma_state = "多头排列" if (ma5[-1] and ma10[-1] and ma20[-1] and ma5[-1] > ma10[-1] > ma20[-1]) else (
        "空头排列" if (ma5[-1] and ma10[-1] and ma20[-1] and ma5[-1] < ma10[-1] < ma20[-1]) else "均线纠缠")
    macd_cross = None
    if len(dif) > 3:
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            macd_cross = "金叉"
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            macd_cross = "死叉"

    return {
        "last": last, "ma5": ma5[-1], "ma10": ma10[-1], "ma20": ma20[-1], "ma60": ma60[-1],
        "ma_state": ma_state, "rsi": round(r14[-1], 1) if r14[-1] else 50,
        "macd_cross": macd_cross, "dif_above": dif[-1] > dea[-1],
        "boll_pos": ("上轨上方" if b_up[-1] and last > b_up[-1] else
                     "下轨附近" if b_low[-1] and last <= b_low[-1] * 1.02 else
                     "中轨上方" if b_up[-1] and last > (b_up[-1] + b_low[-1]) / 2 else "中轨下方"),
        "vol_ratio": round(vol_ratio, 2),
        "mom20": round(mom20, 1),
        "high60": high60, "low60": low60,
        "off_high": round((last / high60 - 1) * 100, 1),
        "atr": a14[-1] if a14[-1] else last * 0.02,
    }


def _verdict(f):
    """综合判定：返回 (评级, 评分0-100, 理由列表)。"""
    score, reasons = 50, []
    if f["ma_state"] == "多头排列":
        score += 18; reasons.append("均线多头排列")
    elif f["ma_state"] == "空头排列":
        score -= 18; reasons.append("均线空头排列")
    if f["dif_above"]:
        score += 10; reasons.append("MACD 在零轴柱之上" )
    else:
        score -= 10; reasons.append("MACD 偏弱")
    if f["macd_cross"] == "金叉":
        score += 8; reasons.append("MACD 刚出现金叉")
    if f["rsi"] < 30:
        score += 12; reasons.append(f"RSI {f['rsi']} 超卖")
    elif f["rsi"] > 70:
        score -= 12; reasons.append(f"RSI {f['rsi']} 超买")
    if f["vol_ratio"] > 1.3:
        score += 6; reasons.append(f"量比 {f['vol_ratio']} 放量")
    if f["mom20"] > 5:
        score += 8; reasons.append(f"20日动量 +{f['mom20']}%")
    elif f["mom20"] < -8:
        score -= 8; reasons.append(f"20日动量 {f['mom20']}%")
    score = max(5, min(95, score))
    if score >= 70:
        verdict = "强势可做多"
    elif score >= 55:
        verdict = "回调低吸"
    elif score >= 40:
        verdict = "持有观察"
    else:
        verdict = "回避减仓"
    return verdict, score, reasons


def _build_tree(regime, picks):
    """由市场环境 + 精选标的分析构建决策树 JSON。"""
    def env_desc(r):
        if not r:
            return "行情数据暂不可用，请谨慎参考"
        return (f"{r['index_name']} 收 {r['close']}，20日涨跌 {r['chg20']:+}%，"
                f"{'站上' if r['close'] > r['ma20'] else '跌破'} MA20（{r['ma20']}），市场环境判定「{r['regime']}」")

    long_branch = {
        "id": "long", "title": "长期操作（趋势跟随，持有 1~6 个月）",
        "desc": "以中期趋势与多头结构为依据，低频操作、重仓波段", "children": [],
    }
    short_branch = {
        "id": "short", "title": "短期操作（信号驱动，持有 3~15 个交易日）",
        "desc": "以技术信号共振为依据，快进快出、严格止损", "children": [],
    }
    skill_branch = {
        "id": "skill", "title": "交易技巧（纪律与工具箱）",
        "desc": "网格、定投与止损纪律，适用于震荡市与持仓管理", "children": [],
    }

    # ---- 长期分支：从强势池取前 3 只 ----
    strong = [a for a in picks if a["score"] >= 60][:3]
    for a in strong:
        stop = round(a["facts"]["last"] - 2 * a["facts"]["atr"], 2)
        long_branch["children"].append({
            "id": f"long-{a['stock_id']}",
            "title": f"{a['name']}（{a['code']}）：分批建仓，趋势持有",
            "badge": a["verdict"], "score": a["score"],
            "leaf": {
                "action": "分批买入", "stock_id": a["stock_id"], "stock": f"{a['name']} {a['code']}",
                "position": "首笔 20% 仓位，回踩 MA10 加 20%",
                "entry": f"{round(a['facts']['last'] * 0.995, 2)} ~ {round(a['facts']['last'] * 1.01, 2)}",
                "stop": f"收盘跌破 {stop}（约 -{round(2 * a['facts']['atr'] / a['facts']['last'] * 100, 1)}%，2倍ATR）无条件离场",
                "target": f"60日高点 {round(a['facts']['high60'], 2)} 上方，跌破 MA20 / MA60 减仓",
                "basis": a["reasons"][:4],
                "confidence": a["score"],
            },
        })
    if not strong:
        long_branch["children"].append({
            "id": "long-none", "title": "当前无满足趋势条件的标的，建议空仓等待",
            "badge": "观望", "score": 50,
            "leaf": {"action": "观望", "basis": ["全部标的多头结构不足", "等待趋势确立再介入"]},
        })

    # ---- 短期分支：金叉/低吸/兑现 三类信号 ----
    for a in picks:
        f = a["facts"]
        if a["score"] >= 65 and (f["macd_cross"] == "金叉" or (f["ma_state"] == "多头排列" and f["vol_ratio"] > 1.2)):
            stop = round(f["last"] * 0.95, 2)
            short_branch["children"].append({
                "id": f"short-buy-{a['stock_id']}",
                "title": f"短线买入信号：{a['name']}（{a['code']}）",
                "badge": "短线买入", "score": a["score"],
                "leaf": {
                    "action": "买入", "stock_id": a["stock_id"], "stock": f"{a['name']} {a['code']}",
                    "position": "轻仓试错，10%~15% 仓位",
                    "entry": f"现价 {f['last']} 附近",
                    "stop": f"止损 {stop}（-5%纪律止损）",
                    "target": f"目标 {round(f['last'] * 1.10, 2)} ~ {round(f['last'] * 1.15, 2)}（+10%~15%），或 RSI>75 兑现",
                    "basis": a["reasons"][:4],
                    "confidence": a["score"],
                },
            })
        if f["rsi"] < 32 and a["score"] >= 45:
            short_branch["children"].append({
                "id": f"short-dip-{a['stock_id']}",
                "title": f"超卖低吸机会：{a['name']}（{a['code']}）",
                "badge": "超卖低吸", "score": a["score"],
                "leaf": {
                    "action": "低吸", "stock_id": a["stock_id"], "stock": f"{a['name']} {a['code']}",
                    "position": "5%~10% 仓位博反弹",
                    "entry": f"现价 {f['last']}，靠近 60日低点 {round(f['low60'], 2)} 更佳",
                    "stop": f"跌破 {round(f['low60'] * 0.98, 2)} 止损",
                    "target": "反弹至 BOLL 中轨即止盈",
                    "basis": [f"RSI {f['rsi']} 超卖", "均值回复博弈，快进快出"],
                    "confidence": a["score"],
                },
            })
        if f["rsi"] > 72 or f["boll_pos"] == "上轨上方":
            short_branch["children"].append({
                "id": f"short-sell-{a['stock_id']}",
                "title": f"短线兑现信号：{a['name']}（{a['code']}）",
                "badge": "逢高兑现", "score": a["score"],
                "leaf": {
                    "action": "减仓/兑现", "stock_id": a["stock_id"], "stock": f"{a['name']} {a['code']}",
                    "position": "持有者减持 1/2 ~ 全部",
                    "entry": "现价区间逢高卖出",
                    "stop": "—",
                    "target": f"RSI {f['rsi']} 超买{'，价格触及布林上轨' if f['boll_pos'] == '上轨上方' else ''}，短期回撤风险大",
                    "basis": [f"RSI {f['rsi']} 超买", f"布林位置：{f['boll_pos']}"],
                    "confidence": a["score"],
                },
            })
    if not short_branch["children"]:
        short_branch["children"].append({
            "id": "short-none", "title": "暂无有效短线信号，宁缺毋滥",
            "badge": "观望", "score": 50,
            "leaf": {"action": "观望", "basis": ["无金叉/超卖/超买信号共振"]},
        })

    # ---- 技巧分支：以波动率最高的 2 只给网格方案 + 通用纪律 ----
    volatile = sorted(picks, key=lambda a: a["facts"]["atr"] / a["facts"]["last"], reverse=True)[:2]
    for a in volatile:
        f = a["facts"]
        step = round(f["atr"] / f["last"] * 100, 1)
        skill_branch["children"].append({
            "id": f"skill-grid-{a['stock_id']}",
            "title": f"网格交易方案：{a['name']}（{a['code']}）",
            "badge": "网格技巧", "score": a["score"],
            "leaf": {
                "action": "网格挂单", "stock_id": a["stock_id"], "stock": f"{a['name']} {a['code']}",
                "position": "网格总仓位 ≤ 30%，每格 5%",
                "entry": f"以 {f['last']} 为中轴，每 {step}% 一格（ATR 自适应间距），跌买涨卖",
                "stop": f"价格跌破 60日低点 {round(f['low60'], 2)} 停止网格",
                "target": "震荡区间内反复赚取波动收益",
                "basis": [f"日 ATR 约 {round(f['atr'], 2)}（{step}%）", "适合震荡市机械化操作"],
                "confidence": a["score"],
            },
        })
    skill_branch["children"].append({
        "id": "skill-rules", "title": "仓位与止损纪律（所有操作通用）",
        "badge": "风控纪律", "score": 60,
        "leaf": {
            "action": "纪律执行",
            "basis": [
                "单票仓位 ≤ 30%，保留至少 20% 现金",
                "短线亏损 -5% 无条件止损，长线收盘破 MA20 减仓",
                "浮盈超过 15% 后将止损上移至成本价（保本单）",
                "大赛期初比排名，稳住回撤比追求暴利更重要",
            ],
        },
    })

    regime_title = regime.get("CN", {}).get("regime", "震荡") if regime else "震荡"
    return {
        "regime": regime or {},
        "root": {
            "id": "root", "title": f"当前市场环境：{regime_title}",
            "desc": env_desc(regime.get("CN") if regime else None),
            "children": [long_branch, short_branch, skill_branch],
        },
    }


@router.get("/tree")
def get_tree(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    import time
    if _cache["data"] and time.time() - _cache["ts"] < CACHE_TTL:
        return _cache["data"]
    stocks = db.query(Stock).filter(Stock.is_active.is_(True)).all()
    # 计算前增量刷新日K：保证信号基于最新行情（含当日未完成bar）
    for s in stocks:
        try:
            last = (
                db.query(DailyBar.date)
                .filter(DailyBar.stock_id == s.id)
                .order_by(DailyBar.date.desc())
                .first()
            )
            if last is None:
                continue
            fresh = fetch_kline(s.em_secid, beg=last.date.replace("-", ""), force=True)
            known = {b.date for b in db.query(DailyBar.date).filter(DailyBar.stock_id == s.id).all()}
            new_rows = [b for b in fresh if b["date"] not in known]
            for b in new_rows:
                db.add(DailyBar(stock_id=s.id, **b))
            if new_rows:
                db.commit()
        except Exception:
            continue
    picks = []
    for s in stocks:
        rows = (
            db.query(DailyBar)
            .filter(DailyBar.stock_id == s.id)
            .order_by(DailyBar.date.desc())
            .limit(120)
            .all()
        )
        rows.reverse()
        if len(rows) < 70:
            continue
        bars = [{"date": b.date, "open": b.open, "high": b.high,
                 "low": b.low, "close": b.close, "volume": b.volume} for b in rows]
        f = _facts(bars)
        verdict, score, reasons = _verdict(f)
        picks.append({
            "stock_id": s.id, "code": s.symbol, "name": s.name, "market": s.market,
            "verdict": verdict, "score": score, "reasons": reasons, "facts": f,
        })
    regime = index_regime()
    tree = _build_tree(regime, picks)

    radar = [
        {
            "stock_id": a["stock_id"], "code": a["code"], "name": a["name"], "market": a["market"],
            "verdict": a["verdict"], "score": a["score"], "reasons": a["reasons"][:3],
            "rsi": a["facts"]["rsi"], "mom20": a["facts"]["mom20"], "ma_state": a["facts"]["ma_state"],
        }
        for a in sorted(picks, key=lambda x: x["score"], reverse=True)
    ]
    result = {**tree, "radar": radar}
    import time
    _cache["ts"] = time.time()
    _cache["data"] = result
    return result
