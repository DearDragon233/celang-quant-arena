from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """统一账号：admin 管理员 / user 参赛选手。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False, default="")
    role = Column(String(20), nullable=False, default="user")  # admin / user
    school = Column(String(50), nullable=False, default="")  # 学校（大赛用）
    cash = Column(Float, nullable=False, default=1_000_000.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship("Order", back_populates="user")
    positions = relationship("Position", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")


class Stock(Base):
    """股票池：真实行情标的（A股 / 美股）。"""

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(12), unique=True, index=True, nullable=False)  # 600519 / AAPL
    name = Column(String(30), nullable=False)
    market = Column(String(8), nullable=False, default="CN")  # CN / US
    sector = Column(String(30), nullable=False, default="")
    em_secid = Column(String(16), nullable=False, default="")  # 东方财富 secid
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=False, default="")


class DailyBar(Base):
    """日线行情缓存（来自真实数据源）。"""

    __tablename__ = "daily_bars"
    __table_args__ = (Index("ix_bar_stock_date", "stock_id", "date"),)

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(String(10), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    amount = Column(Float, nullable=False, default=0.0)

    stock = relationship("Stock")


class Contest(Base):
    """模拟盘比赛：由管理员发布，选手报名后获得独立资金账户。"""

    __tablename__ = "contests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), nullable=False)
    description = Column(String(255), nullable=False, default="")
    initial_cash = Column(Float, nullable=False, default=1_000_000.0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="published")  # draft / published
    created_at = Column(DateTime, default=datetime.now)


class ContestEntry(Base):
    """比赛报名记录 = 比赛账户（独立于年度场资金）。"""

    __tablename__ = "contest_entries"
    __table_args__ = (UniqueConstraint("contest_id", "user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cash = Column(Float, nullable=False, default=1_000_000.0)
    created_at = Column(DateTime, default=datetime.now)

    contest = relationship("Contest")
    user = relationship("User")


class Position(Base):
    """持仓。contest_id 为空表示年度常驻账户。"""

    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "stock_id", "contest_id"),)

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, nullable=False, default=0)  # 0=年度场, >0=比赛
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    qty = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="positions")
    stock = relationship("Stock")


class Order(Base):
    """成交记录（模拟盘即时成交，价格为实时价）。contest_id 0=年度场。"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, nullable=False, default=0, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    side = Column(String(10), nullable=False)  # buy / sell
    price = Column(Float, nullable=False)
    qty = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="orders")
    stock = relationship("Stock")


class Strategy(Base):
    """用户自配的量化策略。"""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    params = Column(Text, nullable=False, default="{}")
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    initial_cash = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="strategies")
    stock = relationship("Stock")


class BacktestRun(Base):
    """回测运行结果。"""

    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    strategy_name = Column(String(50), nullable=False, default="")
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    params = Column(Text, nullable=False, default="{}")
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    initial_cash = Column(Float, nullable=False)
    metrics = Column(Text, nullable=False, default="{}")
    equity = Column(Text, nullable=False, default="[]")
    trades = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.now)

    stock = relationship("Stock")


class Setting(Base):
    """大赛设置（键值对）。"""

    __tablename__ = "settings"

    key = Column(String(30), primary_key=True)
    value = Column(String(200), nullable=False, default="")


class NpcTrader(Base):
    """NPC 交易者：不同职业与风格，基于真实行情自动对战。"""

    __tablename__ = "npc_traders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), nullable=False)
    title = Column(String(30), nullable=False, default="")  # 职业
    avatar = Column(String(10), nullable=False, default="🎭")
    style_tag = Column(String(20), nullable=False, default="")  # 风格标签
    bio = Column(String(200), nullable=False, default="")
    kind = Column(String(20), nullable=False)  # 引用 engine 策略 / npc_custom
    params = Column(Text, nullable=False, default="{}")
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    cash = Column(Float, nullable=False, default=1_000_000.0)
    initial_cash = Column(Float, nullable=False, default=1_000_000.0)
    position_ratio = Column(Float, nullable=False, default=1.0)  # 单次全仓比例
    curve = Column(Text, nullable=False, default="[]")  # 净值曲线 JSON
    last_replay_date = Column(String(10), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.now)

    stock = relationship("Stock")


class NpcOrder(Base):
    """NPC 成交记录。"""

    __tablename__ = "npc_orders"

    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(Integer, ForeignKey("npc_traders.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    side = Column(String(10), nullable=False)
    price = Column(Float, nullable=False)
    qty = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0.0)
    reason = Column(String(200), nullable=False, default="")
    trade_date = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    stock = relationship("Stock")
