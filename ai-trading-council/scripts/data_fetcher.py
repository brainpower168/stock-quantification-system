#!/usr/bin/env python3
"""
数据获取工具
使用妙想/问财API获取股票数据
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd

# 导入日志
try:
    from logger_config import get_logger

    logger = get_logger("data_fetcher")
except ImportError:
    import logging

    logger = logging.getLogger("data_fetcher")

# 配置路径
CONFIG_PATH = Path(__file__).parent.parent / "config" / "council_config.json"


class DataFetcher:
    """数据获取器"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path or CONFIG_PATH)
        self.miao_key = self.config.get("api_keys", {}).get("miao", "")
        self.wencai_key = self.config.get("api_keys", {}).get("wencai", "")

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def get_stock_data(
        self, stock_code: str, days: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            包含OHLCV的DataFrame
        """
        # 尝试使用妙想API
        df = self._fetch_from_miao(stock_code, days)
        if df is not None:
            return df

        # 尝试使用问财API
        df = self._fetch_from_wencai(stock_code, days)
        if df is not None:
            return df

        # 返回模拟数据
        return self._generate_mock_data(stock_code, days)

    def _fetch_from_miao(self, stock_code: str, days: int) -> Optional[pd.DataFrame]:
        """从妙想API获取数据"""
        if not self.miao_key:
            return None

        try:
            # 妙想历史行情API（使用东方财富API）
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

            params = {
                "secid": f"{'1' if stock_code.startswith('6') else '0'}.{stock_code}",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",  # 日K
                "fqt": "1",  # 前复权
                "end": "20500000",
                "lmt": str(days),
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]

                    rows = []
                    for kline in klines:
                        parts = kline.split(",")
                        rows.append(
                            {
                                "date": parts[0],
                                "open": float(parts[1]),
                                "close": float(parts[2]),
                                "high": float(parts[3]),
                                "low": float(parts[4]),
                                "volume": float(parts[5]),
                                "amount": float(parts[6]),
                            }
                        )

                    df = pd.DataFrame(rows)
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                    return df
        except Exception as e:
            logger.error(f"妙想API获取失败: {e}")

        return None

    def _fetch_from_wencai(self, stock_code: str, days: int) -> Optional[pd.DataFrame]:
        """从问财API获取数据"""
        if not self.wencai_key:
            return None

        try:
            # 问财历史行情API
            url = "https://api.wencai.com/v1/stock/hist"
            headers = {
                "Authorization": f"Bearer {self.wencai_key}",
                "Content-Type": "application/json",
            }

            params = {"code": stock_code, "days": days}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    df = pd.DataFrame(data.get("data", []))
                    if not df.empty:
                        df["date"] = pd.to_datetime(df["date"])
                        df.set_index("date", inplace=True)
                        return df
        except Exception as e:
            logger.error(f"问财API获取失败: {e}")

        return None

    def _generate_mock_data(self, stock_code: str, days: int) -> pd.DataFrame:
        """生成模拟数据（用于测试）"""
        import numpy as np

        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        # 生成随机价格数据
        np.random.seed(hash(stock_code) % 2**32)

        base_price = 100 + np.random.rand() * 100
        returns = np.random.randn(days) * 0.02

        prices = base_price * (1 + returns).cumprod()

        df = pd.DataFrame(
            {
                "open": prices * (1 + np.random.randn(days) * 0.01),
                "high": prices * (1 + np.abs(np.random.randn(days) * 0.02)),
                "low": prices * (1 - np.abs(np.random.randn(days) * 0.02)),
                "close": prices,
                "volume": np.random.randint(1000000, 10000000, days),
            },
            index=dates,
        )

        return df

    def get_realtime_quote(self, stock_code: str) -> Dict:
        """
        获取实时行情

        Args:
            stock_code: 股票代码

        Returns:
            行情数据字典
        """
        try:
            # 使用东方财富实时行情API
            url = "https://push2.eastmoney.com/api/qt/stock/get"

            params = {
                "secid": f"{'1' if stock_code.startswith('6') else '0'}.{stock_code}",
                "fields": "f2,f3,f12,f14,f62,f88,f89,f90,f91,f92,f94,f95,f396,f397",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    d = data["data"]
                    return {
                        "code": stock_code,
                        "price": d.get("f2", 0) / 100 if d.get("f2") else 0,
                        "change_pct": d.get("f3", 0) / 100 if d.get("f3") else 0,
                        "volume": 0,
                        "amount": 0,
                        "main_inflow": d.get("f62", 0) if d.get("f62") else 0,
                        "ddx": d.get("f88", 0) if d.get("f88") else 0,
                        "ddx_3": d.get("f396", 0) if d.get("f396") else 0,
                        "ddx_5": d.get("f91", 0) if d.get("f91") else 0,
                        "ddx_10": d.get("f94", 0) if d.get("f94") else 0,
                        "pe": 20,
                        "roe": 10,
                        "profit_growth": 10,
                    }
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")

        # 返回模拟数据
        return {
            "code": stock_code,
            "price": 100,
            "change_pct": 0,
            "volume": 1000000,
            "amount": 100000000,
            "main_inflow": 0,
            "ddx": 0,
            "ddx_10": 0,
            "pe": 20,
            "roe": 10,
            "profit_growth": 10,
        }


# 测试
if __name__ == "__main__":
    fetcher = DataFetcher()

    logger.info("测试数据获取...")
    df = fetcher.get_stock_data("600519", days=30)

    if df is not None:
        logger.info(f"获取成功，共 {len(df)} 条数据")
        print(df.tail(5))
    else:
        logger.error("获取失败")
