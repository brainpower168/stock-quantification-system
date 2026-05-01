# -*- coding: utf-8 -*-
"""
题材热点追踪模块
- 板块轮动分析
- 涨停基因识别
- 热点题材评分
- 连板股识别
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class ThemeHotTracker:
    """题材热点追踪器"""

    def __init__(self):
        # 热点题材关键词
        self.hot_keywords = {
            "AI": [
                "人工智能",
                "AI",
                "ChatGPT",
                "大模型",
                "算力",
                "GPU",
                "光刻机",
                "国产替代",
            ],
            "新能源": ["锂电池", "固态电池", "储能", "光伏", "风电", "核电", "充电桩"],
            "半导体": ["芯片", "半导体", "集成电路", "封测", "光刻胶", "EDA"],
            "军工": ["军工", "航空航天", "卫星", "导弹", "无人机"],
            "医药": ["创新药", "生物制药", "疫苗", "医疗器械", "中药"],
            "稀土": ["稀土", "永磁", "钨", "钼", "锑"],
            "气体": ["特种气体", "工业气体", "电子气体", "氧气", "氮气"],
            "机器人": ["机器人", "工业机器人", "人形机器人", "减速器", "伺服电机"],
            "数据要素": ["数据要素", "数据资产", "数据交易", "大数据"],
            "低空经济": ["低空经济", "eVTOL", "飞行汽车", "无人机"],
        }

        # 板块权重（根据市场热度动态调整）
        self.sector_weights = {
            "AI": 1.5,
            "新能源": 1.3,
            "半导体": 1.4,
            "军工": 1.2,
            "医药": 1.0,
            "稀土": 1.3,
            "气体": 1.4,
            "机器人": 1.5,
            "数据要素": 1.4,
            "低空经济": 1.6,
        }

    def analyze_limit_up_gene(self, stock_data: pd.DataFrame, days: int = 20) -> Dict:
        """
        分析涨停基因

        参数:
            stock_data: 股票历史数据，需包含 close, high, low, volume
            days: 分析天数

        返回:
            {
                'limit_up_count': 涨停次数,
                'limit_up_gene_score': 涨停基因评分 (0-100),
                'last_limit_up_date': 最近涨停日期,
                'consecutive_days': 连续涨停天数,
                'is_hot': 是否热点股
            }
        """
        if len(stock_data) < days:
            days = len(stock_data)

        recent_data = stock_data.tail(days).copy()

        # 计算涨停（涨幅>=9.9%）
        recent_data["pct_change"] = recent_data["close"].pct_change() * 100
        limit_ups = recent_data[recent_data["pct_change"] >= 9.9]

        limit_up_count = len(limit_ups)

        # 涨停基因评分
        # 评分 = 涨停次数 * 10 + 连续涨停 * 20
        if limit_up_count > 0:
            # 计算连续涨停
            consecutive_days = self._count_consecutive_limit_ups(recent_data)
            gene_score = min(100, limit_up_count * 10 + consecutive_days * 20)
            last_limit_up_date = (
                limit_ups.index[-1].strftime("%Y-%m-%d") if len(limit_ups) > 0 else None
            )
        else:
            consecutive_days = 0
            gene_score = 0
            last_limit_up_date = None

        # 是否热点股（最近3天有涨停）
        is_hot = False
        if limit_up_count > 0:
            last_date = limit_ups.index[-1]
            days_ago = (recent_data.index[-1] - last_date).days
            is_hot = days_ago <= 3

        return {
            "limit_up_count": limit_up_count,
            "limit_up_gene_score": gene_score,
            "last_limit_up_date": last_limit_up_date,
            "consecutive_days": consecutive_days,
            "is_hot": is_hot,
        }

    def _count_consecutive_limit_ups(self, data: pd.DataFrame) -> int:
        """计算连续涨停天数"""
        max_consecutive = 0
        current_consecutive = 0

        for pct in data["pct_change"]:
            if pct >= 9.9:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def detect_theme(self, stock_name: str, stock_intro: str = "") -> List[str]:
        """
        检测股票所属题材

        参数:
            stock_name: 股票名称
            stock_intro: 股票简介

        返回:
            题材列表
        """
        text = stock_name + stock_intro
        themes = []

        for theme, keywords in self.hot_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    themes.append(theme)
                    break

        return themes

    def calculate_theme_score(
        self,
        themes: List[str],
        limit_up_gene: Dict,
        fund_flow: float,
        pct_change: float,
    ) -> Dict:
        """
        计算题材热度评分

        参数:
            themes: 题材列表
            limit_up_gene: 涨停基因数据
            fund_flow: 主力资金流向（万元）
            pct_change: 当日涨幅（%）

        返回:
            {
                'theme_score': 题材评分 (0-100),
                'hot_level': 热度等级 (高/中/低),
                'theme_tags': 题材标签,
                'recommend_action': 推荐操作
            }
        """
        score = 0

        # 1. 题材权重（最高30分）
        theme_score = 0
        for theme in themes:
            weight = self.sector_weights.get(theme, 1.0)
            theme_score += 10 * weight
        score += min(30, theme_score)

        # 2. 涨停基因（最高30分）
        score += min(30, limit_up_gene["limit_up_gene_score"] * 0.3)

        # 3. 资金流向（最高20分）
        if fund_flow > 10000:  # 流入>1亿
            score += 20
        elif fund_flow > 5000:  # 流入>5000万
            score += 15
        elif fund_flow > 1000:  # 流入>1000万
            score += 10
        elif fund_flow > 0:
            score += 5

        # 4. 涨幅（最高20分）
        if 0 < pct_change < 3:
            score += 20  # 最佳买点
        elif 3 <= pct_change < 5:
            score += 15  # 可以追
        elif 5 <= pct_change < 7:
            score += 10  # 风险较高
        elif pct_change >= 7:
            score += 5  # 追高风险大

        # 热度等级
        if score >= 70:
            hot_level = "高"
            recommend_action = "强烈关注，敢于上车"
        elif score >= 50:
            hot_level = "中"
            recommend_action = "可以关注，设好止损"
        else:
            hot_level = "低"
            recommend_action = "观望为主"

        # 题材标签
        theme_tags = themes.copy()
        if limit_up_gene["is_hot"]:
            theme_tags.append("热点股")
        if limit_up_gene["consecutive_days"] >= 2:
            theme_tags.append(f"{limit_up_gene['consecutive_days']}连板")

        return {
            "theme_score": round(score, 1),
            "hot_level": hot_level,
            "theme_tags": theme_tags,
            "recommend_action": recommend_action,
        }

    def analyze_sector_rotation(
        self, sector_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        分析板块轮动

        参数:
            sector_data: {板块名: 板块指数数据}

        返回:
            板块轮动评分表
        """
        results = []

        for sector_name, data in sector_data.items():
            if len(data) < 20:
                continue

            # 计算5日、10日、20日涨幅
            close = data["close"]
            pct_5d = (
                (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
            )
            pct_10d = (
                (close.iloc[-1] / close.iloc[-10] - 1) * 100 if len(close) >= 10 else 0
            )
            pct_20d = (
                (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0
            )

            # 计算成交量变化
            volume = data["volume"]
            vol_ratio = (
                volume.iloc[-1] / volume.iloc[-5:].mean() if len(volume) >= 5 else 1
            )

            # 板块评分
            score = 0
            score += pct_5d * 2  # 5日涨幅权重高
            score += pct_10d
            score += pct_20d * 0.5
            score += (vol_ratio - 1) * 20  # 量能放大加分

            # 题材权重加成
            theme_weight = self.sector_weights.get(sector_name, 1.0)
            score *= theme_weight

            results.append(
                {
                    "sector": sector_name,
                    "pct_5d": round(pct_5d, 2),
                    "pct_10d": round(pct_10d, 2),
                    "pct_20d": round(pct_20d, 2),
                    "vol_ratio": round(vol_ratio, 2),
                    "rotation_score": round(score, 2),
                    "trend": "up"
                    if pct_5d > 0 and pct_10d > 0
                    else "down"
                    if pct_5d < 0 and pct_10d < 0
                    else "sideways",
                }
            )

        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values("rotation_score", ascending=False)

        return df

    def get_hot_stocks(
        self, stocks_data: Dict[str, Dict], top_n: int = 10
    ) -> pd.DataFrame:
        """
        获取热点股票列表

        参数:
            stocks_data: {股票代码: {'name': 名称, 'data': 历史数据, 'fund_flow': 资金流向, 'pct_change': 涨幅}}
            top_n: 返回前N只

        返回:
            热点股票评分表
        """
        results = []

        for code, info in stocks_data.items():
            # 涨停基因
            limit_up_gene = self.analyze_limit_up_gene(info["data"])

            # 题材识别
            themes = self.detect_theme(info["name"])

            # 题材评分
            theme_result = self.calculate_theme_score(
                themes,
                limit_up_gene,
                info.get("fund_flow", 0),
                info.get("pct_change", 0),
            )

            results.append(
                {
                    "code": code,
                    "name": info["name"],
                    "themes": ", ".join(themes) if themes else "无",
                    "limit_up_count": limit_up_gene["limit_up_count"],
                    "limit_up_gene_score": limit_up_gene["limit_up_gene_score"],
                    "is_hot": limit_up_gene["is_hot"],
                    "theme_score": theme_result["theme_score"],
                    "hot_level": theme_result["hot_level"],
                    "theme_tags": ", ".join(theme_result["theme_tags"]),
                    "recommend_action": theme_result["recommend_action"],
                    "fund_flow": info.get("fund_flow", 0),
                    "pct_change": info.get("pct_change", 0),
                }
            )

        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values("theme_score", ascending=False).head(top_n)

        return df

    def should_buy_by_theme(
        self,
        themes: List[str],
        limit_up_gene: Dict,
        fund_flow: float,
        pct_change: float,
    ) -> Tuple[bool, str]:
        """
        根据题材判断是否应该买入

        返回:
            (是否买入, 原因说明)
        """
        # 1. 连板股不看DDX，直接看题材和资金
        if limit_up_gene["consecutive_days"] >= 2:
            if fund_flow > 0 and pct_change < 5:
                return (
                    True,
                    f"{limit_up_gene['consecutive_days']}连板股，题材炒作，敢于上车",
                )
            elif fund_flow > 0 and pct_change >= 5:
                return (
                    True,
                    f"{limit_up_gene['consecutive_days']}连板股，但涨幅已高，小仓位试错",
                )

        # 2. 热点股（最近3天有涨停）
        if limit_up_gene["is_hot"]:
            if fund_flow > 5000 and pct_change < 5:
                return True, "热点股，资金流入，可以关注"
            elif fund_flow > 0:
                return True, "热点股，资金流入，但涨幅偏高，谨慎"

        # 3. 有题材热点
        if len(themes) > 0:
            theme_score = sum([self.sector_weights.get(t, 1.0) for t in themes])
            if theme_score >= 2.5 and fund_flow > 3000 and pct_change < 5:
                return True, f"题材热点({', '.join(themes)})，资金流入，可以关注"

        # 4. 涨停基因强
        if limit_up_gene["limit_up_gene_score"] >= 30:
            if fund_flow > 0 and pct_change < 5:
                return True, "涨停基因强，资金流入，可以关注"

        return False, "题材热度不足，按常规策略判断"


class ThemeStrategy:
    """题材炒作策略"""

    def __init__(self):
        self.tracker = ThemeHotTracker()

    def analyze_stock(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        fund_flow: float,
        pct_change: float,
    ) -> Dict:
        """
        分析单只股票的题材热度

        返回:
            完整分析结果
        """
        # 涨停基因
        limit_up_gene = self.tracker.analyze_limit_up_gene(data)

        # 题材识别
        themes = self.tracker.detect_theme(name)

        # 题材评分
        theme_result = self.tracker.calculate_theme_score(
            themes, limit_up_gene, fund_flow, pct_change
        )

        # 是否买入
        should_buy, reason = self.tracker.should_buy_by_theme(
            themes, limit_up_gene, fund_flow, pct_change
        )

        return {
            "code": code,
            "name": name,
            "themes": themes,
            "limit_up_gene": limit_up_gene,
            "theme_score": theme_result["theme_score"],
            "hot_level": theme_result["hot_level"],
            "theme_tags": theme_result["theme_tags"],
            "should_buy": should_buy,
            "reason": reason,
            "fund_flow": fund_flow,
            "pct_change": pct_change,
        }

    def screen_hot_stocks(
        self, stocks_data: Dict[str, Dict], min_score: float = 50
    ) -> pd.DataFrame:
        """
        筛选热点股票

        参数:
            stocks_data: {股票代码: {'name': 名称, 'data': 历史数据, 'fund_flow': 资金流向, 'pct_change': 涨幅}}
            min_score: 最低题材评分

        返回:
            热点股票列表
        """
        results = []

        for code, info in stocks_data.items():
            analysis = self.analyze_stock(
                code,
                info["name"],
                info["data"],
                info.get("fund_flow", 0),
                info.get("pct_change", 0),
            )

            if analysis["theme_score"] >= min_score:
                results.append(
                    {
                        "code": code,
                        "name": info["name"],
                        "themes": ", ".join(analysis["themes"])
                        if analysis["themes"]
                        else "无",
                        "theme_score": analysis["theme_score"],
                        "hot_level": analysis["hot_level"],
                        "limit_up_count": analysis["limit_up_gene"]["limit_up_count"],
                        "is_hot": analysis["limit_up_gene"]["is_hot"],
                        "should_buy": analysis["should_buy"],
                        "reason": analysis["reason"],
                        "fund_flow": info.get("fund_flow", 0),
                        "pct_change": info.get("pct_change", 0),
                    }
                )

        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values("theme_score", ascending=False)

        return df


# 测试代码
if __name__ == "__main__":
    import random

    print("=" * 60)
    print("题材热点追踪模块测试")
    print("=" * 60)

    tracker = ThemeHotTracker()
    strategy = ThemeStrategy()

    # 模拟测试数据
    np.random.seed(42)
    dates = pd.date_range("2026-04-01", "2026-04-30")

    # 测试涨停基因分析
    print("\n1. 涨停基因分析测试")
    print("-" * 60)

    # 模拟有涨停的数据
    data = pd.DataFrame(
        {
            "close": 100 + np.random.randn(30).cumsum() * 2,
            "high": 102 + np.random.randn(30).cumsum() * 2,
            "low": 98 + np.random.randn(30).cumsum() * 2,
            "volume": np.random.randint(1000, 5000, 30),
        },
        index=dates,
    )

    # 人为加入涨停
    data.iloc[-3, data.columns.get_loc("close")] = data.iloc[-4]["close"] * 1.10
    data.iloc[-5, data.columns.get_loc("close")] = data.iloc[-6]["close"] * 1.10

    limit_up_result = tracker.analyze_limit_up_gene(data)
    print(f"涨停次数: {limit_up_result['limit_up_count']}")
    print(f"涨停基因评分: {limit_up_result['limit_up_gene_score']}")
    print(f"最近涨停日期: {limit_up_result['last_limit_up_date']}")
    print(f"连续涨停天数: {limit_up_result['consecutive_days']}")
    print(f"是否热点股: {limit_up_result['is_hot']}")

    # 测试题材识别
    print("\n2. 题材识别测试")
    print("-" * 60)

    test_stocks = [
        ("光迅科技", "光模块,光通信,AI算力"),
        ("赣锋锂业", "锂电池,新能源,储能"),
        ("华特气体", "特种气体,电子气体,半导体"),
        ("北方华创", "半导体设备,芯片,集成电路"),
    ]

    for name, intro in test_stocks:
        themes = tracker.detect_theme(name, intro)
        print(f"{name}: {', '.join(themes) if themes else '无'}")

    # 测试题材评分
    print("\n3. 题材热度评分测试")
    print("-" * 60)

    score_result = tracker.calculate_theme_score(
        themes=["AI", "半导体"],
        limit_up_gene=limit_up_result,
        fund_flow=8000,  # 流入8000万
        pct_change=3.5,
    )

    print(f"题材评分: {score_result['theme_score']}")
    print(f"热度等级: {score_result['hot_level']}")
    print(f"题材标签: {score_result['theme_tags']}")
    print(f"推荐操作: {score_result['recommend_action']}")

    # 测试是否买入
    print("\n4. 题材买入判断测试")
    print("-" * 60)

    should_buy, reason = tracker.should_buy_by_theme(
        themes=["AI", "半导体"],
        limit_up_gene=limit_up_result,
        fund_flow=8000,
        pct_change=3.5,
    )

    print(f"是否买入: {should_buy}")
    print(f"原因: {reason}")

    # 测试热点股票筛选
    print("\n5. 热点股票筛选测试")
    print("-" * 60)

    stocks_data = {}
    test_codes = ["002281", "002460", "300750", "002371"]
    test_names = ["光迅科技", "赣锋锂业", "宁德时代", "北方华创"]

    for code, name in zip(test_codes, test_names):
        stocks_data[code] = {
            "name": name,
            "data": data,
            "fund_flow": random.randint(3000, 15000),
            "pct_change": random.uniform(1, 6),
        }

    hot_stocks = strategy.screen_hot_stocks(stocks_data, min_score=40)
    print(
        hot_stocks[
            [
                "code",
                "name",
                "themes",
                "theme_score",
                "hot_level",
                "should_buy",
                "reason",
            ]
        ]
    )

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
