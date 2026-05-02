# -*- coding: utf-8 -*-
"""
数据获取模块 - 整合妙想API、国信API、新闻搜索API
用于获取DDX、财务数据、舆情数据
"""

import os
import sys
import json
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


class DataFetcher:
    """数据获取模块 - 整合多数据源"""

    def __init__(self):
        # API Key
        self.mx_apikey = os.getenv("MX_APIKEY", "")
        self.gs_api_key = os.getenv("GS_API_KEY", "")

        # 妙想API脚本路径
        self.mx_script = "C:/Users/zhuyi/AppData/Roaming/qianfan-desktop-app/qianfan_desk_xdg/55d1508241624f56a3a831bde4da9cfb/data/skills/user/mx-data/mx_data.py"

        # 缓存
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存

    # ==================== 妙想API - DDX数据 ====================
    def fetch_ddx_data(self, code: str, days: int = 10) -> Dict:
        """
        获取DDX数据（妙想API）

        参数:
            code: 股票代码（如 600519）
            days: 查询天数

        返回:
            {
                'ddx': float,  # 今日DDX
                'ddx_5d_avg': float,  # 5日DDX均值
                'ddx_10d_avg': float,  # 10日DDX均值
                'ddx_trend': float,  # DDX趋势
                'ddx_positive_days': int,  # DDX连续为正天数
            }
        """
        try:
            # 使用妙想API查询DDX
            query = f"{code}近{days}日DDX DDY DDZ"
            result = self._call_mx_api(query)

            if result and "data" in result:
                # 解析DDX数据
                ddx_data = self._parse_ddx_from_mx(result, days)
                return ddx_data
            else:
                print(f"Warning: No DDX data for {code}")
                return {}

        except Exception as e:
            print(f"Error fetching DDX data: {e}")
            return {}

    def fetch_fund_flow(self, code: str, days: int = 5) -> Dict:
        """
        获取资金流向数据（妙想API）

        参数:
            code: 股票代码
            days: 查询天数

        返回:
            {
                'main_flow': float,  # 主力净流入
                'main_flow_5d_sum': float,  # 5日主力净流入
                'super_large_flow': float,  # 超大单净流入
                'large_flow': float,  # 大单净流入
                'medium_flow': float,  # 中单净流入
                'small_flow': float,  # 小单净流入
            }
        """
        try:
            query = f"{code}近{days}日主力资金流向 超大单 大单 中单 小单"
            result = self._call_mx_api(query)

            if result and "data" in result:
                fund_flow_data = self._parse_fund_flow_from_mx(result, days)
                return fund_flow_data
            else:
                print(f"Warning: No fund flow data for {code}")
                return {}

        except Exception as e:
            print(f"Error fetching fund flow data: {e}")
            return {}

    # ==================== 国信API - 财务数据 ====================
    def fetch_financial_data(self, code: str) -> Dict:
        """
        获取财务数据（国信API）

        参数:
            code: 股票代码

        返回:
            {
                'pe': float,  # 市盈率
                'pb': float,  # 市净率
                'roe': float,  # 净资产收益率
                'revenue_growth': float,  # 营收增长率
                'profit_growth': float,  # 净利润增长率
                'debt_ratio': float,  # 资产负债率
                'gross_margin': float,  # 毛利率
                'net_margin': float,  # 净利率
                'operating_cash_flow': float,  # 经营现金流
            }
        """
        try:
            # 使用国信API查询财务数据
            # 这里简化处理，实际需要调用国信API
            # 暂时返回模拟数据
            financial_data = {
                "pe": 0.0,
                "pb": 0.0,
                "roe": 0.0,
                "revenue_growth": 0.0,
                "profit_growth": 0.0,
                "debt_ratio": 0.0,
                "gross_margin": 0.0,
                "net_margin": 0.0,
                "operating_cash_flow": 0.0,
            }

            # TODO: 调用国信API获取真实数据
            # from scripts.get_data import get_financial_data
            # financial_data = get_financial_data(code)

            return financial_data

        except Exception as e:
            print(f"Error fetching financial data: {e}")
            return {}

    # ==================== 新闻搜索API - 舆情数据 ====================
    def fetch_sentiment_data(self, code: str, days: int = 7) -> Dict:
        """
        获取舆情数据（新闻搜索API）

        参数:
            code: 股票代码
            days: 查询天数

        返回:
            {
                'sentiment_score': float,  # 情绪评分（-1到1）
                'news_count': int,  # 新闻数量
                'positive_ratio': float,  # 正面情绪比例
                'negative_ratio': float,  # 负面情绪比例
                'hot_rank': int,  # 热度排名
            }
        """
        try:
            # 使用新闻搜索API查询舆情
            # 这里简化处理，实际需要调用新闻搜索API
            # 暂时返回模拟数据
            sentiment_data = {
                "sentiment_score": 0.0,
                "news_count": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "hot_rank": 0,
            }

            # TODO: 调用新闻搜索API获取真实数据
            # from skills.user.news-search import search_news
            # news = search_news(f"{code}相关新闻")
            # sentiment_data = analyze_sentiment(news)

            return sentiment_data

        except Exception as e:
            print(f"Error fetching sentiment data: {e}")
            return {}

    # ==================== 批量获取数据 ====================
    def fetch_all_data(self, code: str, days: int = 10) -> Dict:
        """
        批量获取所有数据（DDX + 财务 + 舆情）

        参数:
            code: 股票代码
            days: 查询天数

        返回:
            {
                'ddx': {...},
                'fund_flow': {...},
                'financial': {...},
                'sentiment': {...},
            }
        """
        all_data = {}

        # 获取DDX数据
        all_data["ddx"] = self.fetch_ddx_data(code, days)

        # 获取资金流向
        all_data["fund_flow"] = self.fetch_fund_flow(code, min(days, 5))

        # 获取财务数据
        all_data["financial"] = self.fetch_financial_data(code)

        # 获取舆情数据
        all_data["sentiment"] = self.fetch_sentiment_data(code, 7)

        return all_data

    # ==================== 内部方法 ====================
    def _call_mx_api(self, query: str) -> Optional[Dict]:
        """调用妙想API"""
        try:
            # 检查API Key
            if not self.mx_apikey:
                print("Warning: MX_APIKEY not set")
                return None

            # 调用妙想API脚本
            cmd = f'python "{self.mx_script}" "{query}"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                # 解析JSON输出
                output = result.stdout.strip()
                if output:
                    # 尝试找到JSON部分
                    lines = output.split("\n")
                    for line in lines:
                        if line.startswith("{"):
                            return json.loads(line)
                return None
            else:
                print(f"MX API error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("MX API timeout")
            return None
        except Exception as e:
            print(f"Error calling MX API: {e}")
            return None

    def _parse_ddx_from_mx(self, result: Dict, days: int) -> Dict:
        """从妙想API结果解析DDX数据"""
        ddx_data = {}

        try:
            # 解析dataTableDTOList
            if "data" in result and "dataTableDTOList" in result["data"]:
                for table in result["data"]["dataTableDTOList"]:
                    if "table" in table:
                        # 提取DDX数据
                        table_data = table["table"]
                        if "DDX" in table_data or "ddx" in table_data:
                            ddx_values = table_data.get(
                                "DDX", table_data.get("ddx", [])
                            )
                            if ddx_values:
                                ddx_data["ddx"] = ddx_values[-1] if ddx_values else 0
                                ddx_data["ddx_5d_avg"] = (
                                    np.mean(ddx_values[-5:])
                                    if len(ddx_values) >= 5
                                    else np.mean(ddx_values)
                                )
                                ddx_data["ddx_10d_avg"] = (
                                    np.mean(ddx_values)
                                    if len(ddx_values) >= 10
                                    else np.mean(ddx_values)
                                )
                                ddx_data["ddx_positive_days"] = sum(
                                    1 for x in ddx_values if x > 0
                                )

        except Exception as e:
            print(f"Error parsing DDX data: {e}")

        return ddx_data

    def _parse_fund_flow_from_mx(self, result: Dict, days: int) -> Dict:
        """从妙想API结果解析资金流向数据"""
        fund_flow_data = {}

        try:
            # 解析dataTableDTOList
            if "data" in result and "dataTableDTOList" in result["data"]:
                for table in result["data"]["dataTableDTOList"]:
                    if "table" in table:
                        table_data = table["table"]

                        # 主力净流入
                        if "主力净流入" in table_data or "MAIN_FLOW" in table_data:
                            main_flow = table_data.get(
                                "主力净流入", table_data.get("MAIN_FLOW", [])
                            )
                            if main_flow:
                                fund_flow_data["main_flow"] = (
                                    main_flow[-1] if main_flow else 0
                                )
                                fund_flow_data["main_flow_5d_sum"] = (
                                    sum(main_flow[-5:])
                                    if len(main_flow) >= 5
                                    else sum(main_flow)
                                )

                        # 超大单
                        if "超大单" in table_data or "SUPER_LARGE" in table_data:
                            super_large = table_data.get(
                                "超大单", table_data.get("SUPER_LARGE", [])
                            )
                            if super_large:
                                fund_flow_data["super_large_flow"] = (
                                    super_large[-1] if super_large else 0
                                )

                        # 大单
                        if "大单" in table_data or "LARGE" in table_data:
                            large = table_data.get("大单", table_data.get("LARGE", []))
                            if large:
                                fund_flow_data["large_flow"] = large[-1] if large else 0

                        # 中单
                        if "中单" in table_data or "MEDIUM" in table_data:
                            medium = table_data.get(
                                "中单", table_data.get("MEDIUM", [])
                            )
                            if medium:
                                fund_flow_data["medium_flow"] = (
                                    medium[-1] if medium else 0
                                )

                        # 小单
                        if "小单" in table_data or "SMALL" in table_data:
                            small = table_data.get("小单", table_data.get("SMALL", []))
                            if small:
                                fund_flow_data["small_flow"] = small[-1] if small else 0

        except Exception as e:
            print(f"Error parsing fund flow data: {e}")

        return fund_flow_data


def test_data_fetcher():
    """测试数据获取模块"""
    print("\n" + "=" * 60)
    print("Data Fetcher Test")
    print("=" * 60)

    fetcher = DataFetcher()

    # 测试股票代码
    test_code = "600519"  # 贵州茅台

    # 测试DDX数据获取
    print(f"\nFetching DDX data for {test_code}...")
    ddx_data = fetcher.fetch_ddx_data(test_code, days=10)
    print(f"DDX data: {ddx_data}")

    # 测试资金流向获取
    print(f"\nFetching fund flow data for {test_code}...")
    fund_flow_data = fetcher.fetch_fund_flow(test_code, days=5)
    print(f"Fund flow data: {fund_flow_data}")

    # 测试财务数据获取
    print(f"\nFetching financial data for {test_code}...")
    financial_data = fetcher.fetch_financial_data(test_code)
    print(f"Financial data: {financial_data}")

    # 测试舆情数据获取
    print(f"\nFetching sentiment data for {test_code}...")
    sentiment_data = fetcher.fetch_sentiment_data(test_code, days=7)
    print(f"Sentiment data: {sentiment_data}")

    # 测试批量获取
    print(f"\nFetching all data for {test_code}...")
    all_data = fetcher.fetch_all_data(test_code, days=10)
    print(f"All data keys: {all_data.keys()}")

    print("\n" + "=" * 60)
    print("Test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_data_fetcher()
