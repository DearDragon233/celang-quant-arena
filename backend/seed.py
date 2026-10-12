"""数据库初始化：从真实数据源拉取股票池行情，写入演示用户与成交。"""
import json
import random
from datetime import datetime

from app.database import SessionLocal, engine
from app.datasource import fetch_kline
from app.models import Base, DailyBar, Order, Position, Setting, Stock, Strategy, User
from app.security import hash_password

BEG = "20250101"  # 日K起始

# (symbol, name, market, secid, sector, 简介)
STOCK_POOL = [
    ("600519", "贵州茅台", "CN", "1.600519", "白酒食品", "高端白酒龙头"),
    ("000001", "平安银行", "CN", "0.000001", "银行金融", "零售银行标杆"),
    ("300750", "宁德时代", "CN", "0.300750", "新能源", "动力电池全球龙头"),
    ("002594", "比亚迪", "CN", "0.002594", "新能源汽车", "新能源汽车整车龙头"),
    ("600036", "招商银行", "CN", "1.600036", "银行金融", "零售银行之王"),
    ("000858", "五粮液", "CN", "0.000858", "白酒食品", "浓香型白酒龙头"),
    ("601318", "中国平安", "CN", "1.601318", "保险金融", "综合金融集团"),
    ("000333", "美的集团", "CN", "0.000333", "家电", "白电全产业链龙头"),
    ("600900", "长江电力", "CN", "1.600900", "公用事业", "全球最大水电公司"),
    ("601899", "紫金矿业", "CN", "1.601899", "有色金属", "铜金矿业巨头"),
    ("002415", "海康威视", "CN", "0.002415", "电子安防", "智能安防龙头"),
    ("300059", "东方财富", "CN", "0.300059", "互联网金融", "互联网券商平台"),
    ("603259", "药明康德", "CN", "1.603259", "医药生物", "医药研发外包龙头"),
    ("600276", "恒瑞医药", "CN", "1.600276", "医药生物", "创新药龙头"),
    ("601012", "隆基绿能", "CN", "1.601012", "光伏", "单晶硅片龙头"),
    ("002714", "牧原股份", "CN", "0.002714", "农林牧渔", "生猪养殖一体化"),
    ("AAPL", "苹果", "US", "105.AAPL", "消费电子", "Apple Inc. 全球市值龙头"),
    ("MSFT", "微软", "US", "105.MSFT", "软件云服务", "Microsoft 云与AI巨头"),
    ("NVDA", "英伟达", "US", "105.NVDA", "半导体", "AI 算力芯片霸主"),
    ("TSLA", "特斯拉", "US", "105.TSLA", "新能源汽车", "Tesla 电动车先锋"),
    ("AMZN", "亚马逊", "US", "105.AMZN", "互联网零售", "Amazon 电商与云计算"),
    ("GOOG", "谷歌", "US", "105.GOOG", "互联网", "Alphabet 搜索与AI"),
    ("META", "Meta", "US", "105.META", "社交网络", "Facebook 母公司"),
    ("BABA", "阿里巴巴", "US", "106.BABA", "互联网零售", "电商与云计算巨头（美股）"),
]

DEMO_USERS = [
    ("trader01", "赵启明", "中国农业大学"),
    ("trader02", "钱思颖", "中国农业大学"),
    ("trader03", "孙浩然", "清华大学"),
    ("trader04", "李文博", "北京大学"),
    ("trader05", "周雨桐", "复旦大学"),
]

DEFAULT_SETTINGS = {
    "comp_name": "全国大学生模拟炒股大赛",
    "comp_season": "2026 秋季赛",
    "comp_start": "2026-10-01",
    "comp_end": "2026-12-31",
}


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = random.Random(42)
    try:
        if db.query(User).count() > 0:
            print("数据库已有数据，跳过初始化。")
            return

        admin = User(username="admin", password_hash=hash_password("admin123"),
                     nickname="大赛组委会", role="admin", cash=0, school="组委会")
        db.add(admin)
        users = []
        for username, nickname, school in DEMO_USERS:
            u = User(username=username, password_hash=hash_password("123456"),
                     nickname=nickname, role="user", cash=1_000_000, school=school)
            db.add(u)
            users.append(u)

        for k, v in DEFAULT_SETTINGS.items():
            db.add(Setting(key=k, value=v))
        db.flush()

        stocks = []
        failed = []
        for symbol, name, market, secid, sector, desc in STOCK_POOL:
            s = Stock(symbol=symbol, name=name, market=market, sector=sector,
                      em_secid=secid, description=desc)
            db.add(s)
            stocks.append(s)
        db.flush()

        # 拉取真实日线
        bars_by_stock = {}
        for s in stocks:
            try:
                bars = fetch_kline(s.em_secid, beg=BEG)
            except Exception as e:
                failed.append(f"{s.symbol}: {e}")
                continue
            for b in bars:
                db.add(DailyBar(stock_id=s.id, **b))
            bars_by_stock[s.id] = bars
        db.flush()

        # 用真实行情重放演示成交（近 45 个交易日随机买卖）
        active = [s for s in stocks if s.id in bars_by_stock]
        for u in users:
            picks = rng.sample(active, k=4)
            for s in picks:
                bars = bars_by_stock[s.id][-45:]
                qty = 0
                avg_cost = 0.0
                buys = 0
                for b in bars:
                    if rng.random() < 0.12 and buys < 3:
                        q = rng.choice([100, 200, 300])
                        amount = q * b["close"]
                        fee = max(amount * 0.0003, 5)
                        u.cash -= amount + fee
                        avg_cost = (avg_cost * qty + amount) / (qty + q)
                        qty += q
                        buys += 1
                        db.add(Order(user_id=u.id, stock_id=s.id, side="buy",
                                     price=b["close"], qty=q, amount=round(amount, 2),
                                     fee=round(fee, 2),
                                     created_at=datetime.fromisoformat(b["date"] + "T14:55:00")))
                    elif qty > 0 and rng.random() < 0.06:
                        q = qty // 2
                        amount = q * b["close"]
                        fee = max(amount * 0.0008, 5)
                        u.cash += amount - fee
                        qty -= q
                        db.add(Order(user_id=u.id, stock_id=s.id, side="sell",
                                     price=b["close"], qty=q, amount=round(amount, 2),
                                     fee=round(fee, 2),
                                     created_at=datetime.fromisoformat(b["date"] + "T14:55:00")))
                if qty > 0:
                    db.add(Position(user_id=u.id, stock_id=s.id, qty=qty, avg_cost=round(avg_cost, 3)))

        # 示例策略：基于真实行情的区间
        if active:
            s0 = active[4]
            bars0 = bars_by_stock[s0.id]
            db.add(Strategy(
                user_id=users[0].id, name="海龟突破示例（茅台）", stock_id=s0.id, kind="turtle",
                params=json.dumps({"entry": 20, "exit": 10}),
                start_date=bars0[60]["date"], end_date=bars0[-1]["date"], initial_cash=100000,
            ))

        db.commit()
        print(f"初始化完成：真实行情 {len(active)}/{len(STOCK_POOL)} 只"
              + (f"；失败: {failed}" if failed else ""))
        print("  管理员 admin / admin123")
        print("  参赛选手 trader01 ~ trader05 / 123456")
    finally:
        db.close()


if __name__ == "__main__":
    run()
