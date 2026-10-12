"""真实行情数据源：东方财富（主）+ 腾讯行情（备），带重试与内存 TTL 缓存。"""
import json
import threading
import time
import urllib.request

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://quote.eastmoney.com/",
    "Connection": "close",
}

_quote_cache = {}
QUOTE_TTL = 8
_kline_mem = {}


def _get(url, timeout=8, retries=3, decode="utf-8"):
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return (raw.decode(decode, "ignore") if decode != "utf-8" else raw.decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    raise last_err


def _get_json(url, timeout=8, retries=3):
    return json.loads(_get(url, timeout=timeout, retries=retries))


# ---------------- 实时行情 ----------------

def _tencent_symbol(secid):
    market, code = secid.split(".", 1)
    if market in ("0", "1"):
        return ("sh" if market == "1" else "sz") + code
    return "us" + code


def _quotes_from_tencent(secids):
    symbols = [_tencent_symbol(s) for s in secids]
    raw = _get("https://qt.gtimg.cn/q=" + ",".join(symbols), retries=2, decode="gbk")
    out = {}
    by_symbol = dict(zip(symbols, secids))
    for token in raw.split(";"):
        token = token.strip()
        if "=" not in token or '"' not in token:
            continue
        sym, payload = token.split("=", 1)
        sym = sym.replace("v_", "").strip()
        secid = by_symbol.get(sym)
        if not secid:
            continue
        f = payload.strip('"').split("~")
        if len(f) < 6:
            continue
        def _num(i, default=0.0):
            try:
                return float(f[i])
            except (IndexError, ValueError):
                return default
        price, prev = _num(3), _num(4)
        out[secid] = {
            "name": f[1],
            "price": price,
            "change_pct": round((price / prev - 1) * 100, 2) if prev else _num(32),
            "high": _num(33),
            "low": _num(34),
            "prev_close": prev,
        }
    return out


def _refresh_quotes_bg(key, secids):
    """后台刷新行情缓存（stale-while-revalidate）。"""
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/ulist.np/get?secids="
            + ",".join(secids)
            + "&fields=f2,f3,f12,f13,f14,f15,f16,f17,f18&fltt=2"
        )
        data = _get_json(url)
        out = {}
        for item in (data.get("data") or {}).get("diff") or []:
            def _num(v, default=0.0):
                return v if isinstance(v, (int, float)) else default
            secid = f"{item.get('f13')}.{item.get('f12')}"
            out[secid] = {
                "name": item.get("f14", ""),
                "price": _num(item.get("f2")),
                "change_pct": _num(item.get("f3")),
                "open": _num(item.get("f17")),
                "high": _num(item.get("f15")),
                "low": _num(item.get("f16")),
                "prev_close": _num(item.get("f18")),
            }
        _quote_cache[key] = (time.time(), out)
    except Exception:
        pass


def fetch_quotes(secids):
    """批量实时行情（stale-while-revalidate：过期先返回旧值并后台刷新）。"""
    if not secids:
        return {}
    key = ("q", tuple(sorted(secids)))
    now = time.time()
    cached = _quote_cache.get(key)
    if cached:
        age = now - cached[0]
        if age < QUOTE_TTL:
            return cached[1]
        if age < 300:  # 有 5 分钟内的旧值：立即返回，后台刷新
            threading.Thread(target=_refresh_quotes_bg, args=(key, list(secids)), daemon=True).start()
            return cached[1]

    try:
        url = (
            "https://push2.eastmoney.com/api/qt/ulist.np/get?secids="
            + ",".join(secids)
            + "&fields=f2,f3,f12,f13,f14,f15,f16,f17,f18&fltt=2"
        )
        data = _get_json(url)
        out = {}
        for item in (data.get("data") or {}).get("diff") or []:
            def _num(v, default=0.0):
                return v if isinstance(v, (int, float)) else default
            secid = f"{item.get('f13')}.{item.get('f12')}"
            out[secid] = {
                "name": item.get("f14", ""),
                "price": _num(item.get("f2")),
                "change_pct": _num(item.get("f3")),
                "open": _num(item.get("f17")),
                "high": _num(item.get("f15")),
                "low": _num(item.get("f16")),
                "prev_close": _num(item.get("f18")),
            }
    except Exception:
        out = _quotes_from_tencent(secids)

    _quote_cache[key] = (now, out)
    return out


# ---------------- 日K ----------------

def _tencent_kline(tencent_symbol, beg, end, count=640):
    """腾讯日K备源：param=sh600519,day,2025-01-01,2026-12-31,640,qfq"""
    sym = tencent_symbol
    url = (
        f"https://ifzq.gtimg.cn/appstock/app/fqkline/get?"
        f"param={sym},day,{beg},{end},{count},qfq"
    )
    data = _get_json(url, retries=2)
    node = (data.get("data") or {}).get(sym)
    rows = (node.get("qfqday") or node.get("day")) if node else None
    out = []
    for r in rows or []:
        try:
            out.append({
                "date": r[0], "open": float(r[1]), "close": float(r[2]),
                "high": float(r[3]), "low": float(r[4]),
                "volume": float(r[5]), "amount": float(r[5]) * float(r[2]),
            })
        except (ValueError, IndexError):
            continue
    return out


def _tencent_stock_symbol(secid):
    """secid → 腾讯美股代码，自动尝试 .OQ(纳指) / .N(纽交所)。"""
    market, code = secid.split(".", 1)
    if market in ("0", "1"):
        return [("sh" if market == "1" else "sz") + code]
    return [f"us{code}.OQ", f"us{code}.N"]


KLINE_MEM_TTL = 60  # 秒：盘中当日K线需要及时更新


def fetch_kline(secid, beg="20240101", end="20500000", klt=101, fqt=1, force=False):
    """日K（前复权）。主源东方财富，失败时回落腾讯。返回升序日线列表。"""
    now = time.time()
    cached = _kline_mem.get(secid)
    if not force and cached and now - cached[0] < KLINE_MEM_TTL:
        return cached[1]

    rows = []
    try:
        beg_dt = f"{beg[:4]}-{beg[4:6]}-{beg[6:8]}" if len(beg) == 8 else beg
        end_dt = time.strftime("%Y-%m-%d")
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
            f"&klt={klt}&fqt={fqt}&beg={beg}&end={end}"
        )
        data = _get_json(url, retries=2)
        for line in (data.get("data") or {}).get("klines") or []:
            parts = line.split(",")
            rows.append({
                "date": parts[0], "open": float(parts[1]), "close": float(parts[2]),
                "high": float(parts[3]), "low": float(parts[4]),
                "volume": float(parts[5]), "amount": float(parts[6]),
            })
    except Exception:
        rows = []

    if not rows:
        for sym in _tencent_stock_symbol(secid):
            try:
                rows = _tencent_kline(sym, beg_dt, end_dt)
                if rows:
                    break
            except Exception:
                continue

    _kline_mem[secid] = (time.time(), rows)
    return rows


def index_regime():
    """大盘环境：沪深300 + 标普500ETF（EM SPY 优先，腾讯 QQQ 兜底）。"""
    out = {}
    cn_bars = []
    try:
        cn_bars = fetch_kline("1.000300", beg="20250401")
    except Exception:
        pass
    us_bars = []
    try:
        us_bars = fetch_kline("107.SPY", beg="20250401")
    except Exception:
        pass
    if not us_bars:
        try:
            us_bars = _tencent_kline("usQQQ.OQ", "2025-04-01", time.strftime("%Y-%m-%d"))
        except Exception:
            pass

    for key, bars, name in (("CN", cn_bars, "沪深300"), ("US", us_bars, "纳指100ETF(QQQ)")):
        if len(bars) < 60:
            continue
        closes = [b["close"] for b in bars]
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60
        chg20 = (closes[-1] / closes[-21] - 1) * 100
        above = closes[-1] > ma20 and ma20 > ma60
        below = closes[-1] < ma20 and ma20 < ma60
        out[key] = {
            "index_name": name,
            "close": round(closes[-1], 2),
            "chg20": round(chg20, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "regime": "偏多" if above else ("偏空" if below else "震荡"),
        }
    return out
