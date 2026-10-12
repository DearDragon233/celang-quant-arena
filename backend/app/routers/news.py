"""财经快讯：东方财富 7x24 + 新浪财经滚动，双源合并去重。"""
import json
import time
import urllib.request
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/api/news", tags=["财经快讯"], dependencies=[Depends(get_current_user)])

_cache = {"ts": 0, "items": []}
CACHE_TTL = 300  # 5 分钟缓存


def _get(url, headers=None):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def fetch_eastmoney():
    """东财 7x24 财经快讯。"""
    url = ("https://np-listapi.eastmoney.com/comm/web/getNewsByColumns?"
           "client=web&biz=web_724&column=350&order=1&needInteractData=0"
           "&page_index=1&page_size=50&req_trace=1"
           "&fields=code,showTime,title,summary,mediaName,url")
    data = _get(url, headers={"Referer": "https://kuaixun.eastmoney.com/"})
    items = []
    for it in (data.get("data") or {}).get("list") or []:
        items.append({
            "time": it.get("showTime", ""),
            "title": (it.get("title") or "").strip(),
            "summary": (it.get("summary") or "").strip(),
            "source": it.get("mediaName") or "东方财富",
            "url": it.get("url") or it.get("uniqueUrl") or "",
        })
    return items


def fetch_sina():
    """新浪财经滚动新闻。"""
    url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=50&page=1"
    data = _get(url, headers={"Referer": "https://finance.sina.com.cn/"})
    items = []
    for it in (data.get("result") or {}).get("data") or []:
        ctime = int(it.get("ctime", 0))
        items.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime)),
            "title": (it.get("title") or "").strip(),
            "summary": "",
            "source": "新浪财经",
            "url": it.get("url", ""),
        })
    return items


BULL_WORDS = {"利好": 3, "上涨": 2, "大涨": 3, "增长": 2, "创新高": 3, "降准": 3, "降息": 3,
              "回购": 2, "增持": 2, "超预期": 3, "回暖": 2, "盈利": 1, "突破": 1, "中标": 2,
              "涨价": 2, "振兴": 2, "政策支持": 3, "新高": 2, "走红": 1, "加快": 1}
BEAR_WORDS = {"利空": 3, "下跌": 2, "大跌": 3, "减持": 3, "退市": 3, "亏损": 3, "警告": 2,
              "制裁": 3, "风险": 1, "下滑": 2, "暴跌": 3, "处罚": 2, "立案": 3, "黑客": 2,
              "断裂": 2, "解禁": 2, "遇冷": 2, "放缓": 2, "翻盘无望": 2}


def analyze(text: str):
    """关键词规则情绪分析：返回 (倾向, 分值, 命中词)。"""
    bull = [(w, v) for w, v in BULL_WORDS.items() if w in text]
    bear = [(w, v) for w, v in BEAR_WORDS.items() if w in text]
    score = sum(v for _, v in bull) - sum(v for _, v in bear)
    if score >= 2:
        label = "利好"
    elif score <= -2:
        label = "利空"
    else:
        label = "中性"
    hits = [w for w, _ in bull] + [w for w, _ in bear]
    return label, score, hits


@router.get("/sentiment")
def sentiment_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """市场情绪温度：昨日收盘以来利好/利空统计。"""
    data = await_news()
    stat = {"利好": 0, "利空": 0, "中性": 0}
    for it in data:
        stat[it["sentiment"]] += 1
    net = stat["利好"] - stat["利空"]
    temp = "偏暖" if net >= 3 else ("偏冷" if net <= -3 else "平稳")
    return {"stat": stat, "net": net, "temperature": temp, "total": len(data)}


def await_news():
    return news_items()


def news_items():
    now = time.time()
    if now - _cache["ts"] > CACHE_TTL:
        _news_reload()
    return _cache["items"]


def _news_reload():
    merged = {}
    for fetcher in (fetch_eastmoney, fetch_sina):
        try:
            for it in fetcher():
                if not it["title"]:
                    continue
                label, score, hits = analyze(it["title"] + " " + it["summary"])
                it["sentiment"] = label
                it["sentiment_score"] = score
                it["sentiment_hits"] = hits
                key = it["title"][:30]
                if key not in merged:
                    merged[key] = it
        except Exception:
            continue
    _cache["items"] = sorted(merged.values(), key=lambda x: x["time"], reverse=True)
    _cache["ts"] = time.time()


@router.get("/list")
def news_list(limit: int = 60, since_close: int = 1, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    items = news_items()

    # 「昨日收盘以来」过滤：昨日 15:00（A股收盘）之后
    if since_close:
        cutoff = (datetime.now() - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        items = [i for i in items if i["time"] >= cutoff_str]

    stat = {"利好": 0, "利空": 0, "中性": 0}
    for it in items:
        stat[it["sentiment"]] += 1
    net = stat["利好"] - stat["利空"]
    return {
        "total": len(items),
        "cutoff": ((datetime.now() - timedelta(days=1)).replace(hour=15, minute=0, second=0)
                   .strftime("%Y-%m-%d %H:%M")),
        "sentiment": {
            "stat": stat, "net": net,
            "temperature": "偏暖" if net >= 3 else ("偏冷" if net <= -3 else "平稳"),
        },
        "items": items[: max(min(limit, 100), 10)],
    }
