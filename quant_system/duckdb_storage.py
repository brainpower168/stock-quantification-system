#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB数据存储模块
参考FactorWeave-Quant系统的DuckDB应用

核心功能：
1. 高性能数据存储（列式存储）
2. 亚秒级查询
3. 历史数据管理
4. 数据缓存机制
"""

import os
import duckdb
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class DataConfig:
    """数据配置"""

    db_path: str = "data/quant_data.duckdb"
    cache_size: int = 10000  # 缓存大小
    data_retention_days: int = 365  # 数据保留天数


class DuckDBStorage:
    """DuckDB数据存储"""

    def __init__(self, config: Optional[DataConfig] = None):
        """初始化"""
        self.config = config or DataConfig()

        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.config.db_path), exist_ok=True)

        # 连接数据库
        self.conn = duckdb.connect(self.config.db_path)

        # 初始化表
        self._init_tables()

        # 内存缓存
        self._cache: Dict[str, pd.DataFrame] = {}

    def _init_tables(self):
        """初始化数据表"""
        # 股票行情表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_quotes (
                stock_code VARCHAR,
                trade_date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount DOUBLE,
                turnover_rate DOUBLE,
                PRIMARY KEY (stock_code, trade_date)
            )
        """)

        # DDX数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ddx_data (
                stock_code VARCHAR,
                trade_date DATE,
                ddx DOUBLE,
                ddy DOUBLE,
                ddz DOUBLE,
                main_inflow DOUBLE,
                main_outflow DOUBLE,
                retail_inflow DOUBLE,
                retail_outflow DOUBLE,
                PRIMARY KEY (stock_code, trade_date)
            )
        """)

        # 财务数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_data (
                stock_code VARCHAR,
                report_date DATE,
                revenue DOUBLE,
                net_profit DOUBLE,
                roe DOUBLE,
                pe DOUBLE,
                pb DOUBLE,
                debt_ratio DOUBLE,
                PRIMARY KEY (stock_code, report_date)
            )
        """)

        # 热点事件表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS hot_events (
                event_id VARCHAR,
                event_date DATE,
                event_time TIMESTAMP,
                title VARCHAR,
                content VARCHAR,
                industry VARCHAR,
                impact_depth VARCHAR,
                score INTEGER,
                source VARCHAR,
                PRIMARY KEY (event_id)
            )
        """)

        # 交易记录表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                trade_id VARCHAR,
                stock_code VARCHAR,
                trade_date DATE,
                trade_type VARCHAR,
                price DOUBLE,
                quantity INTEGER,
                amount DOUBLE,
                profit_loss DOUBLE,
                strategy VARCHAR,
                notes VARCHAR,
                PRIMARY KEY (trade_id)
            )
        """)

        # 创建索引
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quotes_code ON stock_quotes(stock_code)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quotes_date ON stock_quotes(trade_date)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ddx_code ON ddx_data(stock_code)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_date ON hot_events(event_date)"
        )

    def save_stock_quotes(self, data: pd.DataFrame, if_exists: str = "append") -> int:
        """
        保存股票行情数据

        Args:
            data: DataFrame，需包含 stock_code, trade_date, open, high, low, close, volume
            if_exists: append（追加）或 replace（替换）

        Returns:
            插入的行数
        """
        if data.empty:
            return 0

        # 确保列名正确
        required_cols = [
            "stock_code",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 转换日期格式
        data["trade_date"] = pd.to_datetime(data["trade_date"]).dt.date

        # 插入数据
        if if_exists == "replace":
            # 删除已存在的数据
            codes = data["stock_code"].unique()
            dates = data["trade_date"].unique()
            self.conn.execute(f"""
                DELETE FROM stock_quotes
                WHERE stock_code IN ({",".join([f"'{c}'" for c in codes])})
                AND trade_date IN ({",".join([f"'{d}'" for d in dates])})
            """)

        # 插入新数据
        self.conn.execute("INSERT INTO stock_quotes SELECT * FROM data")

        # 清除缓存
        self._cache.clear()

        return len(data)

    def get_stock_quotes(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        查询股票行情数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存

        Returns:
            行情数据DataFrame
        """
        # 检查缓存
        cache_key = f"{stock_code}_{start_date}_{end_date}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # 构建查询
        sql = f"SELECT * FROM stock_quotes WHERE stock_code = '{stock_code}'"

        if start_date:
            sql += f" AND trade_date >= '{start_date}'"
        if end_date:
            sql += f" AND trade_date <= '{end_date}'"

        sql += " ORDER BY trade_date"

        # 执行查询
        result = self.conn.execute(sql).fetchdf()

        # 缓存结果
        if use_cache and len(result) < self.config.cache_size:
            self._cache[cache_key] = result.copy()

        return result

    def save_ddx_data(self, data: pd.DataFrame) -> int:
        """保存DDX数据"""
        if data.empty:
            return 0

        data["trade_date"] = pd.to_datetime(data["trade_date"]).dt.date
        self.conn.execute("INSERT INTO ddx_data SELECT * FROM data")

        return len(data)

    def get_ddx_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """查询DDX数据"""
        sql = f"""
            SELECT * FROM ddx_data
            WHERE stock_code = '{stock_code}'
            AND trade_date >= CURRENT_DATE - INTERVAL {days} DAY
            ORDER BY trade_date DESC
        """

        return self.conn.execute(sql).fetchdf()

    def save_hot_events(self, events: List[Dict]) -> int:
        """保存热点事件"""
        if not events:
            return 0

        # 转换为DataFrame
        df = pd.DataFrame(events)

        # 确保必需列存在
        if "event_id" not in df.columns:
            df["event_id"] = [
                f"evt_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                for i in range(len(df))
            ]

        # 插入数据
        self.conn.execute("INSERT INTO hot_events SELECT * FROM df")

        return len(df)

    def get_hot_events(
        self,
        date: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """查询热点事件"""
        sql = "SELECT * FROM hot_events WHERE 1=1"

        if date:
            sql += f" AND event_date = '{date}'"
        if industry:
            sql += f" AND industry = '{industry}'"

        sql += f" ORDER BY event_time DESC LIMIT {limit}"

        return self.conn.execute(sql).fetchdf()

    def save_trade_record(self, trade: Dict) -> str:
        """保存交易记录"""
        trade_id = trade.get(
            "trade_id", f"trade_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        )

        self.conn.execute(f"""
            INSERT INTO trade_records VALUES (
                '{trade_id}',
                '{trade.get("stock_code", "")}',
                '{trade.get("trade_date", datetime.now().date())}',
                '{trade.get("trade_type", "BUY")}',
                {trade.get("price", 0)},
                {trade.get("quantity", 0)},
                {trade.get("amount", 0)},
                {trade.get("profit_loss", 0)},
                '{trade.get("strategy", "")}',
                '{trade.get("notes", "")}'
            )
        """)

        return trade_id

    def get_trade_records(
        self,
        stock_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """查询交易记录"""
        sql = "SELECT * FROM trade_records WHERE 1=1"

        if stock_code:
            sql += f" AND stock_code = '{stock_code}'"
        if start_date:
            sql += f" AND trade_date >= '{start_date}'"
        if end_date:
            sql += f" AND trade_date <= '{end_date}'"

        sql += " ORDER BY trade_date DESC"

        return self.conn.execute(sql).fetchdf()

    def get_statistics(self) -> Dict:
        """获取数据统计"""
        stats = {}

        # 各表数据量
        tables = [
            "stock_quotes",
            "ddx_data",
            "financial_data",
            "hot_events",
            "trade_records",
        ]
        for table in tables:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = count

        # 数据库大小
        db_size = (
            os.path.getsize(self.config.db_path)
            if os.path.exists(self.config.db_path)
            else 0
        )
        stats["db_size_mb"] = db_size / (1024 * 1024)

        # 缓存状态
        stats["cache_count"] = len(self._cache)

        return stats

    def cleanup_old_data(self, days: Optional[int] = None):
        """清理旧数据"""
        retention_days = days or self.config.data_retention_days
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).date()

        # 清理行情数据
        self.conn.execute(
            f"DELETE FROM stock_quotes WHERE trade_date < '{cutoff_date}'"
        )

        # 清理DDX数据
        self.conn.execute(f"DELETE FROM ddx_data WHERE trade_date < '{cutoff_date}'")

        # 清理热点事件
        self.conn.execute(f"DELETE FROM hot_events WHERE event_date < '{cutoff_date}'")

        # 清除缓存
        self._cache.clear()

    def vacuum(self):
        """压缩数据库"""
        self.conn.execute("VACUUM")

    def close(self):
        """关闭连接"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """测试DuckDB存储"""
    print("=" * 70)
    print("测试DuckDB数据存储")
    print("=" * 70)

    # 创建存储实例
    storage = DuckDBStorage(DataConfig(db_path="data/test_quant.duckdb"))

    # 测试1: 保存行情数据
    print("\n【测试1: 保存行情数据】")
    quotes_data = pd.DataFrame(
        [
            {
                "stock_code": "600519",
                "trade_date": "2026-05-01",
                "open": 95,
                "high": 98,
                "low": 94,
                "close": 97,
                "volume": 1000000,
                "amount": 97000000,
                "turnover_rate": 1.5,
            },
            {
                "stock_code": "600519",
                "trade_date": "2026-05-02",
                "open": 97,
                "high": 99,
                "low": 96,
                "close": 98,
                "volume": 1200000,
                "amount": 117600000,
                "turnover_rate": 1.8,
            },
            {
                "stock_code": "600519",
                "trade_date": "2026-05-03",
                "open": 98,
                "high": 100,
                "low": 97,
                "close": 99,
                "volume": 1100000,
                "amount": 108900000,
                "turnover_rate": 1.6,
            },
        ]
    )
    count = storage.save_stock_quotes(quotes_data)
    print(f"  插入 {count} 条行情数据")

    # 测试2: 查询行情数据
    print("\n【测试2: 查询行情数据】")
    result = storage.get_stock_quotes("600519")
    print(f"  查询到 {len(result)} 条数据")
    print(result)

    # 测试3: 保存DDX数据
    print("\n【测试3: 保存DDX数据】")
    ddx_data = pd.DataFrame(
        [
            {
                "stock_code": "600519",
                "trade_date": "2026-05-01",
                "ddx": 1.5,
                "ddy": 1.2,
                "ddz": 1.8,
                "main_inflow": 5000000,
                "main_outflow": 3000000,
                "retail_inflow": 2000000,
                "retail_outflow": 4000000,
            },
            {
                "stock_code": "600519",
                "trade_date": "2026-05-02",
                "ddx": 2.1,
                "ddy": 1.8,
                "ddz": 2.5,
                "main_inflow": 8000000,
                "main_outflow": 2000000,
                "retail_inflow": 3000000,
                "retail_outflow": 6000000,
            },
        ]
    )
    count = storage.save_ddx_data(ddx_data)
    print(f"  插入 {count} 条DDX数据")

    # 测试4: 查询DDX数据
    print("\n【测试4: 查询DDX数据】")
    result = storage.get_ddx_data("600519", days=30)
    print(f"  查询到 {len(result)} 条数据")
    print(result)

    # 测试5: 保存交易记录
    print("\n【测试5: 保存交易记录】")
    trade_id = storage.save_trade_record(
        {
            "stock_code": "600519",
            "trade_date": "2026-05-03",
            "trade_type": "BUY",
            "price": 97.5,
            "quantity": 1000,
            "amount": 97500,
            "strategy": "突破信号策略",
            "notes": "DDX刚转正，主力流入",
        }
    )
    print(f"  交易记录ID: {trade_id}")

    # 测试6: 查询交易记录
    print("\n【测试6: 查询交易记录】")
    result = storage.get_trade_records()
    print(f"  查询到 {len(result)} 条记录")
    print(result)

    # 测试7: 数据统计
    print("\n【测试7: 数据统计】")
    stats = storage.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 关闭连接
    storage.close()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
