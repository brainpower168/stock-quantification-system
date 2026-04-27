#!/usr/bin/env python3
"""
Data Cache - 数据缓存系统

缓存股票数据，减少API调用，提升系统效率。

缓存类型：
1. 实时行情（1分钟过期）
2. DDX数据（每日过期）
3. 财务数据（季度过期）
4. 自选股列表（永久）

使用方式：
    from data_cache import DataCache

    cache = DataCache()

    # 获取数据（自动缓存）
    data = cache.get_stock_data("600519")

    # 手动刷新
    cache.refresh("600519")

    # 清理过期缓存
    cache.cleanup()
"""

import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class CacheType(Enum):
    REALTIME = "realtime"  # 实时行情，1分钟过期
    DDX = "ddx"  # DDX数据，每日过期
    FINANCIAL = "financial"  # 财务数据，季度过期
    WATCHLIST = "watchlist"  # 自选股，永久


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    data: Dict
    cache_type: CacheType
    created_at: datetime
    expires_at: Optional[datetime]

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class DataCache:
    """数据缓存系统"""

    # 缓存过期时间配置
    EXPIRY_CONFIG = {
        CacheType.REALTIME: timedelta(minutes=1),
        CacheType.DDX: timedelta(hours=24),
        CacheType.FINANCIAL: timedelta(days=90),
        CacheType.WATCHLIST: None,  # 永不过期
    }

    def __init__(self, cache_dir: Optional[str] = None, use_sqlite: bool = True):
        """
        初始化缓存系统

        Args:
            cache_dir: 缓存目录，默认为 data/cache
            use_sqlite: 是否使用SQLite存储（推荐）
        """
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir
            else Path(__file__).parent.parent / "data" / "cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.use_sqlite = use_sqlite
        self.db_path = self.cache_dir / "cache.db"

        if use_sqlite:
            self._init_db()

        # 内存缓存
        self.memory_cache: Dict[str, CacheEntry] = {}

        # API配置
        self.iwencai_api_key = os.environ.get("IWENCAI_API_KEY", "")
        self.mx_api_key = os.environ.get("MX_APIKEY", "")

        logger.info(f"缓存系统初始化完成: {self.cache_dir}")

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                cache_type TEXT,
                created_at TEXT,
                expires_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        """)

        conn.commit()
        conn.close()

    def _generate_key(self, stock_code: str, data_type: str = "stock_data") -> str:
        """生成缓存键"""
        return f"{data_type}:{stock_code}"

    def get_stock_data(
        self, stock_code: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        获取股票数据（自动缓存）

        Args:
            stock_code: 股票代码
            force_refresh: 强制刷新

        Returns:
            股票数据字典
        """
        key = self._generate_key(stock_code, "stock_data")

        # 检查缓存
        if not force_refresh:
            cached = self._get(key)
            if cached:
                logger.debug(f"缓存命中: {stock_code}")
                return cached

        # 缓存未命中，从API获取
        logger.debug(f"缓存未命中，获取数据: {stock_code}")
        data = self._fetch_from_api(stock_code)

        if data:
            # 存入缓存
            self._set(key, data, CacheType.REALTIME)

        return data

    def get_ddx_data(
        self, stock_code: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        获取DDX数据（每日缓存）
        """
        key = self._generate_key(stock_code, "ddx_data")

        if not force_refresh:
            cached = self._get(key)
            if cached:
                return cached

        data = self._fetch_ddx_from_api(stock_code)

        if data:
            self._set(key, data, CacheType.DDX)

        return data

    def get_financial_data(
        self, stock_code: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        获取财务数据（季度缓存）
        """
        key = self._generate_key(stock_code, "financial_data")

        if not force_refresh:
            cached = self._get(key)
            if cached:
                return cached

        data = self._fetch_financial_from_api(stock_code)

        if data:
            self._set(key, data, CacheType.FINANCIAL)

        return data

    def get_watchlist(self) -> List[str]:
        """
        获取自选股列表
        """
        key = "watchlist"

        cached = self._get(key)
        if cached:
            return cached.get("stocks", [])

        # 默认自选股
        default_watchlist = [
            "601138",  # 工业富联
            "002475",  # 立讯精密
            "002460",  # 赣锋锂业
            "002281",  # 光迅科技
            "002463",  # 沪电股份
            "300750",  # 宁德时代
            "300476",  # 胜宏科技
            "000988",  # 华工科技
        ]

        self._set(key, {"stocks": default_watchlist}, CacheType.WATCHLIST)

        return default_watchlist

    def set_watchlist(self, stocks: List[str]):
        """
        设置自选股列表
        """
        key = "watchlist"
        self._set(key, {"stocks": stocks}, CacheType.WATCHLIST)
        logger.info(f"自选股已更新: {len(stocks)}只")

    def _get(self, key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        # 先检查内存缓存
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired():
                return entry.data
            else:
                del self.memory_cache[key]

        # 检查SQLite缓存
        if self.use_sqlite:
            return self._get_from_db(key)

        # 检查文件缓存
        return self._get_from_file(key)

    def _set(self, key: str, data: Dict, cache_type: CacheType):
        """存入缓存"""
        now = datetime.now()
        expiry_delta = self.EXPIRY_CONFIG.get(cache_type)
        expires_at = now + expiry_delta if expiry_delta else None

        entry = CacheEntry(
            key=key,
            data=data,
            cache_type=cache_type,
            created_at=now,
            expires_at=expires_at,
        )

        # 存入内存缓存
        self.memory_cache[key] = entry

        # 存入持久化缓存
        if self.use_sqlite:
            self._set_to_db(entry)
        else:
            self._set_to_file(entry)

    def _get_from_db(self, key: str) -> Optional[Dict]:
        """从SQLite获取"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT data, expires_at FROM cache WHERE key = ?", (key,))

            row = cursor.fetchone()
            conn.close()

            if row:
                data_str, expires_at_str = row

                # 检查是否过期
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() > expires_at:
                        return None

                return json.loads(data_str)

        except Exception as e:
            logger.error(f"从数据库获取缓存失败: {e}")

        return None

    def _set_to_db(self, entry: CacheEntry):
        """存入SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO cache (key, data, cache_type, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.key,
                    json.dumps(entry.data, ensure_ascii=False),
                    entry.cache_type.value,
                    entry.created_at.isoformat(),
                    entry.expires_at.isoformat() if entry.expires_at else None,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"存入数据库缓存失败: {e}")

    def _get_from_file(self, key: str) -> Optional[Dict]:
        """从文件获取"""
        file_path = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                entry = json.load(f)

            # 检查过期
            if entry.get("expires_at"):
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if datetime.now() > expires_at:
                    file_path.unlink()
                    return None

            return entry.get("data")

        except Exception as e:
            logger.error(f"从文件获取缓存失败: {e}")

        return None

    def _set_to_file(self, entry: CacheEntry):
        """存入文件"""
        file_path = (
            self.cache_dir / f"{hashlib.md5(entry.key.encode()).hexdigest()}.json"
        )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "key": entry.key,
                        "data": entry.data,
                        "cache_type": entry.cache_type.value,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat()
                        if entry.expires_at
                        else None,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        except Exception as e:
            logger.error(f"存入文件缓存失败: {e}")

    def _fetch_from_api(self, stock_code: str) -> Optional[Dict]:
        """从API获取股票数据"""
        try:
            import urllib.request

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": f"{stock_code}最新价、涨跌幅、主力资金流向、10日DDX、ROE、市盈率、成交量",
                "page": "1",
                "limit": "1",
                "is_cache": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") == 0 and result.get("datas"):
                item = result["datas"][0]
                return {
                    "code": stock_code,
                    "name": item.get("股票简称", stock_code),
                    "price": float(item.get("最新价", 0)),
                    "change_pct": float(str(item.get("涨跌幅", "0")).replace("%", "")),
                    "capital_flow": float(item.get("主力净流入", 0)),
                    "ddx_10d": float(item.get("10日DDX", 0)),
                    "roe": float(str(item.get("ROE", "0")).replace("%", "")),
                    "pe": float(item.get("市盈率", 0)),
                    "volume": float(item.get("成交量", 0)),
                    "data_source": "iwencai",
                    "cached_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"获取 {stock_code} 数据失败: {e}")

        return None

    def _fetch_ddx_from_api(self, stock_code: str) -> Optional[Dict]:
        """从API获取DDX数据"""
        # 复用 _fetch_from_api
        data = self._fetch_from_api(stock_code)
        if data:
            return {
                "code": stock_code,
                "capital_flow": data.get("capital_flow", 0),
                "ddx_10d": data.get("ddx_10d", 0),
                "cached_at": datetime.now().isoformat(),
            }
        return None

    def _fetch_financial_from_api(self, stock_code: str) -> Optional[Dict]:
        """从API获取财务数据"""
        try:
            import urllib.request

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": f"{stock_code}ROE、市盈率、市净率、净利润增长率、营业收入增长率、资产负债率",
                "page": "1",
                "limit": "1",
                "is_cache": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") == 0 and result.get("datas"):
                item = result["datas"][0]
                return {
                    "code": stock_code,
                    "roe": float(str(item.get("ROE", "0")).replace("%", "")),
                    "pe": float(item.get("市盈率", 0)),
                    "pb": float(item.get("市净率", 0)),
                    "profit_growth": float(
                        str(item.get("净利润增长率", "0")).replace("%", "")
                    ),
                    "revenue_growth": float(
                        str(item.get("营业收入增长率", "0")).replace("%", "")
                    ),
                    "debt_ratio": float(
                        str(item.get("资产负债率", "0")).replace("%", "")
                    ),
                    "cached_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"获取 {stock_code} 财务数据失败: {e}")

        return None

    def refresh(self, stock_code: str):
        """刷新指定股票的缓存"""
        self.get_stock_data(stock_code, force_refresh=True)
        self.get_ddx_data(stock_code, force_refresh=True)
        logger.info(f"已刷新: {stock_code}")

    def refresh_all(self):
        """刷新所有自选股"""
        watchlist = self.get_watchlist()
        for stock in watchlist:
            self.refresh(stock)
        logger.info(f"已刷新 {len(watchlist)} 只股票")

    def cleanup(self):
        """清理过期缓存"""
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now().isoformat(),),
            )

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(f"清理了 {deleted} 条过期缓存")

        # 清理内存缓存
        expired_keys = [
            key for key, entry in self.memory_cache.items() if entry.is_expired()
        ]

        for key in expired_keys:
            del self.memory_cache[key]

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 条内存缓存")

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        stats = {"memory_cache_count": len(self.memory_cache), "cache_types": {}}

        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM cache")
            stats["db_cache_count"] = cursor.fetchone()[0]

            cursor.execute("SELECT cache_type, COUNT(*) FROM cache GROUP BY cache_type")
            for row in cursor.fetchall():
                stats["cache_types"][row[0]] = row[1]

            conn.close()

        return stats

    def clear_all(self):
        """清空所有缓存"""
        self.memory_cache.clear()

        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache")
            conn.commit()
            conn.close()

        logger.info("已清空所有缓存")


# 单例实例
_cache_instance = None


def get_cache() -> DataCache:
    """获取缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache()
    return _cache_instance


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Data Cache")
    parser.add_argument("--stats", action="store_true", help="显示缓存统计")
    parser.add_argument("--cleanup", action="store_true", help="清理过期缓存")
    parser.add_argument("--refresh", type=str, help="刷新指定股票")
    parser.add_argument("--refresh-all", action="store_true", help="刷新所有自选股")
    parser.add_argument("--clear", action="store_true", help="清空所有缓存")
    parser.add_argument("--get", type=str, help="获取股票数据")

    args = parser.parse_args()

    cache = DataCache()

    if args.stats:
        stats = cache.get_stats()
        print(f"内存缓存: {stats['memory_cache_count']} 条")
        if "db_cache_count" in stats:
            print(f"数据库缓存: {stats['db_cache_count']} 条")
        for cache_type, count in stats.get("cache_types", {}).items():
            print(f"  {cache_type}: {count} 条")

    elif args.cleanup:
        cache.cleanup()

    elif args.refresh:
        cache.refresh(args.refresh)

    elif args.refresh_all:
        cache.refresh_all()

    elif args.clear:
        cache.clear_all()

    elif args.get:
        data = cache.get_stock_data(args.get)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("未获取到数据")

    else:
        parser.print_help()
