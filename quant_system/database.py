# -*- coding: utf-8 -*-
"""
数据库支持模块 - Database Support
SQLite/PostgreSQL 数据存储
"""

import sqlite3
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from .logger import get_logger
from .exceptions import QuantException

logger = get_logger("database")


class DatabaseManager:
    """数据库管理器"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        db_type: str = "sqlite",
        db_path: str = "data/quant_system.db",
        database_url: Optional[str] = None,
    ):
        """
        Args:
            db_type: 数据库类型 ('sqlite', 'postgresql')
            db_path: SQLite 数据库路径
            database_url: PostgreSQL 连接字符串
        """
        if DatabaseManager._initialized:
            return

        self.db_type = db_type
        self.db_path = Path(db_path)
        self.database_url = database_url

        if db_type == "sqlite":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()
        elif db_type == "postgresql":
            if not database_url:
                raise QuantException(
                    "PostgreSQL 需要 database_url 参数", config_key="DATABASE_URL"
                )
            self._init_postgresql()
        else:
            raise QuantException(f"不支持的数据库类型：{db_type}", config_key="DB_TYPE")

        DatabaseManager._initialized = True
        logger.info(f"数据库初始化完成：{db_type}")

    def _init_sqlite(self) -> None:
        """初始化 SQLite 数据库"""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"SQLite 数据库：{self.db_path}")

    def _init_postgresql(self) -> None:
        """初始化 PostgreSQL 数据库"""
        try:
            import psycopg2
            from psycopg2 import pool

            self.connection_pool = pool.SimpleConnectionPool(1, 20, self.database_url)
            self._create_tables()
            logger.info("PostgreSQL 连接池初始化完成")
        except ImportError:
            raise QuantException(
                "PostgreSQL 需要安装 psycopg2-binary", code="MISSING_DEP"
            )

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        if self.db_type == "sqlite":
            conn = self.conn
            try:
                yield conn
            finally:
                pass
        elif self.db_type == "postgresql":
            conn = self.connection_pool.getconn()
            try:
                yield conn
            finally:
                self.connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(self):
        """获取数据库游标"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()

            try:
                yield cursor
                if self.db_type == "postgresql":
                    conn.commit()
            except Exception as e:
                if self.db_type == "postgresql":
                    conn.rollback()
                raise e
            finally:
                cursor.close()

    def _create_tables(self):
        """创建数据表"""
        with self.get_cursor() as cursor:
            # 交易日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    price REAL,
                    shares INTEGER,
                    amount REAL,
                    reason TEXT,
                    profit_loss REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 持仓记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT,
                    shares INTEGER,
                    cost_price REAL,
                    current_price REAL,
                    market_value REAL,
                    profit_loss REAL,
                    profit_loss_pct REAL,
                    entry_date TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 推荐记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    score REAL,
                    reason TEXT,
                    source TEXT,
                    next_day_return REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 市场情绪表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_sentiment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    sentiment_score REAL,
                    fear_greed_index REAL,
                    limit_up_count INTEGER,
                    limit_down_count INTEGER,
                    north_flow REAL,
                    volume_ratio REAL,
                    turnover_ratio REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 因子数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    factor_name TEXT NOT NULL,
                    factor_value REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, code, factor_name)
                )
            """)

            # AI 决策记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    model_name TEXT,
                    vote TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    consensus TEXT,
                    final_decision TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_code ON trade_logs(code)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_timestamp ON trade_logs(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_rec_code ON recommendations(code)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_factor_date ON factor_data(date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_factor_code ON factor_data(code)"
            )

            logger.info("数据库表创建完成")

    # ============ 交易日志操作 ============
    def add_trade_log(
        self,
        action: str,
        code: str,
        price: float,
        shares: int,
        reason: str = "",
        profit_loss: float = 0,
    ) -> int:
        """添加交易日志"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO trade_logs (action, code, price, shares, reason, profit_loss)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (action, code, price, shares, reason, profit_loss),
            )

            return cursor.lastrowid

    def get_trade_logs(
        self, code: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """获取交易日志"""
        with self.get_cursor() as cursor:
            if code:
                cursor.execute(
                    """
                    SELECT * FROM trade_logs 
                    WHERE code = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """,
                    (code, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM trade_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

            return [dict(row) for row in cursor.fetchall()]

    # ============ 持仓操作 ============
    def update_position(
        self, code: str, name: str, shares: int, cost_price: float, current_price: float
    ) -> None:
        """更新持仓"""
        market_value = shares * current_price
        profit_loss = (current_price - cost_price) * shares
        profit_loss_pct = (current_price - cost_price) / cost_price * 100

        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO positions 
                (code, name, shares, cost_price, current_price, market_value, profit_loss, profit_loss_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    code,
                    name,
                    shares,
                    cost_price,
                    current_price,
                    market_value,
                    profit_loss,
                    profit_loss_pct,
                ),
            )

    def get_positions(self) -> List[Dict]:
        """获取所有持仓"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM positions ORDER BY code")
            return [dict(row) for row in cursor.fetchall()]

    def delete_position(self, code: str) -> None:
        """删除持仓"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM positions WHERE code = ?", (code,))

    # ============ 推荐记录操作 ============
    def add_recommendation(
        self, code: str, name: str, score: float, reason: str, source: str = ""
    ) -> int:
        """添加推荐记录"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO recommendations (code, name, score, reason, source)
                VALUES (?, ?, ?, ?, ?)
            """,
                (code, name, score, reason, source),
            )
            return cursor.lastrowid

    def update_recommendation_return(self, rec_id: int, next_day_return: float) -> None:
        """更新推荐次日收益"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE recommendations 
                SET next_day_return = ? 
                WHERE id = ?
            """,
                (next_day_return, rec_id),
            )

    # ============ 市场情绪操作 ============
    def save_market_sentiment(self, date: str, sentiment_data: Dict) -> int:
        """保存市场情绪数据"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO market_sentiment 
                (date, sentiment_score, fear_greed_index, limit_up_count, 
                 limit_down_count, north_flow, volume_ratio, turnover_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    date,
                    sentiment_data.get("sentiment_score", 0),
                    sentiment_data.get("fear_greed_index", 0),
                    sentiment_data.get("limit_up_count", 0),
                    sentiment_data.get("limit_down_count", 0),
                    sentiment_data.get("north_flow", 0),
                    sentiment_data.get("volume_ratio", 0),
                    sentiment_data.get("turnover_ratio", 0),
                ),
            )
            return cursor.lastrowid

    def get_market_sentiment(self, date: str) -> Optional[Dict]:
        """获取市场情绪数据"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM market_sentiment 
                WHERE date = ?
            """,
                (date,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ============ 统计查询 ============
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        with self.get_cursor() as cursor:
            stats = {}

            # 交易统计
            cursor.execute("""
                SELECT COUNT(*) as count, SUM(profit_loss) as total_pnl
                FROM trade_logs
            """)
            row = cursor.fetchone()
            stats["trades"] = {
                "count": row["count"],
                "total_pnl": row["total_pnl"] or 0,
            }

            # 持仓统计
            cursor.execute("""
                SELECT COUNT(*) as count, SUM(market_value) as total_value
                FROM positions
            """)
            row = cursor.fetchone()
            stats["positions"] = {
                "count": row["count"],
                "total_value": row["total_value"] or 0,
            }

            # 推荐统计
            cursor.execute("""
                SELECT COUNT(*) as count, AVG(next_day_return) as avg_return
                FROM recommendations
                WHERE next_day_return IS NOT NULL
            """)
            row = cursor.fetchone()
            stats["recommendations"] = {
                "count": row["count"],
                "avg_return": row["avg_return"] or 0,
            }

            return stats

    def close(self) -> None:
        """关闭数据库连接"""
        if self.db_type == "sqlite":
            self.conn.close()
            logger.info("SQLite 连接已关闭")
        elif self.db_type == "postgresql":
            self.connection_pool.closeall()
            logger.info("PostgreSQL 连接池已关闭")


# 全局数据库实例
_db_manager: Optional[DatabaseManager] = None


def init_database(
    db_type: str = "sqlite",
    db_path: str = "data/quant_system.db",
    database_url: Optional[str] = None,
) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(db_type, db_path, database_url)
    return _db_manager


def get_database() -> DatabaseManager:
    """获取数据库实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
