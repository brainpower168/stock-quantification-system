#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业对冲策略模块
参考AQT系统的行业对冲功能

核心功能：
1. 智能行业配对（正相关/负相关）
2. 风险对冲建议
3. 对冲比例计算
4. 对冲效果评估
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


class HedgeType(Enum):
    """对冲类型"""

    SAME_INDUSTRY = "同行业对冲"  # 同行业内多空对冲
    CROSS_INDUSTRY = "跨行业对冲"  # 不同行业对冲
    INDEX_HEDGE = "指数对冲"  # 用指数期货对冲
    ETF_HEDGE = "ETF对冲"  # 用行业ETF对冲


class CorrelationType(Enum):
    """相关性类型"""

    POSITIVE = "正相关"  # 同涨同跌
    NEGATIVE = "负相关"  # 涨跌相反
    WEAK = "弱相关"  # 相关性弱


@dataclass
class IndustryPair:
    """行业配对"""

    industry_a: str
    industry_b: str
    correlation: float  # 相关系数 -1 到 1
    correlation_type: CorrelationType
    hedge_ratio: float  # 对冲比例
    hedge_effectiveness: float  # 对冲效果评分 0-100


@dataclass
class HedgeRecommendation:
    """对冲建议"""

    stock_code: str
    stock_name: str
    industry: str
    position_value: float  # 持仓金额
    hedge_type: HedgeType
    hedge_target: str  # 对冲标的（股票代码/指数代码/ETF代码）
    hedge_target_name: str
    hedge_ratio: float  # 对冲比例
    hedge_amount: float  # 对冲金额
    expected_risk_reduction: float  # 预期风险降低比例
    confidence: float  # 置信度 0-1


class IndustryHedgeStrategy:
    """行业对冲策略"""

    # 行业相关性矩阵（示例数据，实际应从历史数据计算）
    INDUSTRY_CORRELATION = {
        ("白酒", "食品饮料"): 0.85,
        ("白酒", "医药"): 0.45,
        ("白酒", "银行"): 0.25,
        ("白酒", "房地产"): -0.15,
        ("白酒", "黄金"): -0.25,
        ("新能源", "电力设备"): 0.80,
        ("新能源", "有色金属"): 0.65,
        ("新能源", "煤炭"): -0.35,
        ("新能源", "石油"): -0.40,
        ("半导体", "电子"): 0.75,
        ("半导体", "计算机"): 0.60,
        ("半导体", "通信"): 0.55,
        ("银行", "保险"): 0.70,
        ("银行", "房地产"): 0.55,
        ("银行", "券商"): 0.65,
        ("军工", "航空航天"): 0.80,
        ("军工", "船舶"): 0.75,
        ("医药", "生物制品"): 0.85,
        ("医药", "医疗器械"): 0.70,
        ("黄金", "有色金属"): 0.60,
        ("黄金", "石油"): 0.35,
    }

    # 行业ETF映射
    INDUSTRY_ETF = {
        "白酒": "512690.SH",  # 酒ETF
        "食品饮料": "515170.SH",  # 食品ETF
        "医药": "512010.SH",  # 医药ETF
        "新能源": "516160.SH",  # 新能源ETF
        "半导体": "512480.SH",  # 半导体ETF
        "银行": "512800.SH",  # 银行ETF
        "券商": "512000.SH",  # 券商ETF
        "军工": "512660.SH",  # 军工ETF
        "黄金": "518880.SH",  # 黄金ETF
        "有色金属": "512400.SH",  # 有色ETF
    }

    # 指数期货映射
    INDEX_FUTURES = {
        "沪深300": "IF",
        "中证500": "IC",
        "上证50": "IH",
        "中证1000": "IM",
    }

    def __init__(self):
        """初始化"""
        self.correlation_matrix = self._build_correlation_matrix()

    def _build_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """构建行业相关性矩阵"""
        matrix = {}
        for (a, b), corr in self.INDUSTRY_CORRELATION.items():
            if a not in matrix:
                matrix[a] = {}
            if b not in matrix:
                matrix[b] = {}
            matrix[a][b] = corr
            matrix[b][a] = corr
        return matrix

    def get_correlation(self, industry_a: str, industry_b: str) -> float:
        """获取两个行业的相关系数"""
        if industry_a == industry_b:
            return 1.0

        # 查找直接相关性
        if industry_a in self.correlation_matrix:
            if industry_b in self.correlation_matrix[industry_a]:
                return self.correlation_matrix[industry_a][industry_b]

        # 默认弱相关
        return 0.3

    def get_correlation_type(self, correlation: float) -> CorrelationType:
        """判断相关性类型"""
        if correlation > 0.5:
            return CorrelationType.POSITIVE
        elif correlation < -0.3:
            return CorrelationType.NEGATIVE
        else:
            return CorrelationType.WEAK

    def find_hedge_pairs(self, industry: str, top_n: int = 5) -> List[IndustryPair]:
        """找到最佳对冲配对"""
        pairs = []

        # 遍历所有行业
        for other_industry in self.correlation_matrix.keys():
            if other_industry == industry:
                continue

            correlation = self.get_correlation(industry, other_industry)
            correlation_type = self.get_correlation_type(correlation)

            # 计算对冲比例（负相关用正比例，正相关用反比例）
            if correlation < 0:
                hedge_ratio = abs(correlation)  # 负相关，同向对冲
            else:
                hedge_ratio = 1 - correlation  # 正相关，反向对冲

            # 计算对冲效果评分
            # 负相关对冲效果最好，正相关需要反向操作
            if correlation < -0.3:
                effectiveness = 80 + abs(correlation) * 20
            elif correlation < 0.3:
                effectiveness = 60
            else:
                effectiveness = 40 + (1 - correlation) * 30

            pair = IndustryPair(
                industry_a=industry,
                industry_b=other_industry,
                correlation=correlation,
                correlation_type=correlation_type,
                hedge_ratio=hedge_ratio,
                hedge_effectiveness=effectiveness,
            )
            pairs.append(pair)

        # 按对冲效果排序
        pairs.sort(key=lambda x: x.hedge_effectiveness, reverse=True)

        return pairs[:top_n]

    def generate_hedge_recommendations(
        self, positions: List[Dict], max_hedge_ratio: float = 0.5
    ) -> List[HedgeRecommendation]:
        """
        生成对冲建议

        Args:
            positions: 持仓列表，每个元素包含 stock_code, stock_name, industry, position_value
            max_hedge_ratio: 最大对冲比例（默认50%）

        Returns:
            对冲建议列表
        """
        recommendations = []

        for pos in positions:
            stock_code = pos.get("stock_code", "")
            stock_name = pos.get("stock_name", "")
            industry = pos.get("industry", "")
            position_value = pos.get("position_value", 0)

            if not industry or position_value <= 0:
                continue

            # 找到最佳对冲配对
            hedge_pairs = self.find_hedge_pairs(industry, top_n=3)

            if not hedge_pairs:
                continue

            # 选择最佳对冲方案
            best_pair = hedge_pairs[0]

            # 确定对冲类型
            if best_pair.correlation < -0.3:
                # 负相关，用同向对冲（买入对冲标的）
                hedge_type = HedgeType.CROSS_INDUSTRY
                hedge_target = self.INDUSTRY_ETF.get(best_pair.industry_b, "")
                hedge_target_name = f"{best_pair.industry_b}ETF"
            elif best_pair.correlation > 0.5:
                # 正相关，用反向对冲（卖出对冲标的或做空）
                hedge_type = HedgeType.ETF_HEDGE
                hedge_target = self.INDUSTRY_ETF.get(industry, "")
                hedge_target_name = f"{industry}ETF（反向）"
            else:
                # 弱相关，用指数对冲
                hedge_type = HedgeType.INDEX_HEDGE
                hedge_target = "IF"  # 沪深300期货
                hedge_target_name = "沪深300期货"

            # 计算对冲金额
            hedge_ratio = min(best_pair.hedge_ratio, max_hedge_ratio)
            hedge_amount = position_value * hedge_ratio

            # 预期风险降低
            risk_reduction = best_pair.hedge_effectiveness / 100 * hedge_ratio

            recommendation = HedgeRecommendation(
                stock_code=stock_code,
                stock_name=stock_name,
                industry=industry,
                position_value=position_value,
                hedge_type=hedge_type,
                hedge_target=hedge_target,
                hedge_target_name=hedge_target_name,
                hedge_ratio=hedge_ratio,
                hedge_amount=hedge_amount,
                expected_risk_reduction=risk_reduction,
                confidence=min(best_pair.hedge_effectiveness / 100, 0.9),
            )
            recommendations.append(recommendation)

        return recommendations

    def calculate_portfolio_risk(self, positions: List[Dict]) -> Dict:
        """
        计算组合风险

        Args:
            positions: 持仓列表

        Returns:
            组合风险分析
        """
        if not positions:
            return {"total_risk": 0, "industry_concentration": {}}

        # 计算行业集中度
        industry_values = {}
        total_value = 0

        for pos in positions:
            industry = pos.get("industry", "未知")
            value = pos.get("position_value", 0)
            industry_values[industry] = industry_values.get(industry, 0) + value
            total_value += value

        # 行业集中度
        industry_concentration = {
            ind: val / total_value if total_value > 0 else 0
            for ind, val in industry_values.items()
        }

        # 计算组合风险（基于行业集中度和相关性）
        # 集中度越高，风险越高
        concentration_risk = sum(
            (ratio**2) for ratio in industry_concentration.values()
        )

        # 相关性风险
        correlation_risk = 0
        industries = list(industry_concentration.keys())
        for i, ind_a in enumerate(industries):
            for ind_b in industries[i + 1 :]:
                corr = self.get_correlation(ind_a, ind_b)
                weight_a = industry_concentration[ind_a]
                weight_b = industry_concentration[ind_b]
                correlation_risk += 2 * weight_a * weight_b * corr

        # 总风险（0-1）
        total_risk = (concentration_risk + correlation_risk) / 2

        return {
            "total_risk": total_risk,
            "concentration_risk": concentration_risk,
            "correlation_risk": correlation_risk,
            "industry_concentration": industry_concentration,
            "risk_level": "高"
            if total_risk > 0.6
            else "中"
            if total_risk > 0.3
            else "低",
        }

    def generate_report(self, positions: List[Dict]) -> str:
        """生成对冲建议报告"""
        # 计算组合风险
        risk_analysis = self.calculate_portfolio_risk(positions)

        # 生成对冲建议
        recommendations = self.generate_hedge_recommendations(positions)

        # 构建报告
        lines = []
        lines.append("=" * 70)
        lines.append("行业对冲策略报告")
        lines.append("=" * 70)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 组合风险分析
        lines.append("【组合风险分析】")
        lines.append(f"  总风险评分: {risk_analysis['total_risk']:.2%}")
        lines.append(f"  风险等级: {risk_analysis['risk_level']}")
        lines.append(f"  集中度风险: {risk_analysis['concentration_risk']:.2%}")
        lines.append(f"  相关性风险: {risk_analysis['correlation_risk']:.2%}")
        lines.append("")

        # 行业集中度
        lines.append("【行业集中度】")
        for ind, ratio in sorted(
            risk_analysis["industry_concentration"].items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            lines.append(f"  {ind}: {ratio:.1%}")
        lines.append("")

        # 对冲建议
        if recommendations:
            lines.append("【对冲建议】")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"\n{i}. {rec.stock_name} ({rec.stock_code})")
                lines.append(f"   行业: {rec.industry}")
                lines.append(f"   持仓金额: {rec.position_value:,.0f}元")
                lines.append(f"   对冲方式: {rec.hedge_type.value}")
                lines.append(
                    f"   对冲标的: {rec.hedge_target_name} ({rec.hedge_target})"
                )
                lines.append(f"   对冲比例: {rec.hedge_ratio:.1%}")
                lines.append(f"   对冲金额: {rec.hedge_amount:,.0f}元")
                lines.append(f"   预期风险降低: {rec.expected_risk_reduction:.1%}")
                lines.append(f"   置信度: {rec.confidence:.0%}")
        else:
            lines.append("【对冲建议】")
            lines.append("  当前持仓无需对冲或数据不足")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """测试行业对冲策略"""
    print("=" * 70)
    print("测试行业对冲策略")
    print("=" * 70)

    # 创建策略实例
    strategy = IndustryHedgeStrategy()

    # 测试1: 查找对冲配对
    print("\n【测试1: 查找白酒行业对冲配对】")
    pairs = strategy.find_hedge_pairs("白酒", top_n=5)
    for pair in pairs:
        print(
            f"  {pair.industry_b}: 相关系数={pair.correlation:.2f}, "
            f"对冲比例={pair.hedge_ratio:.1%}, 效果={pair.hedge_effectiveness:.0f}分"
        )

    # 测试2: 生成对冲建议
    print("\n【测试2: 生成对冲建议】")
    positions = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "industry": "白酒",
            "position_value": 100000,
        },
        {
            "stock_code": "000858",
            "stock_name": "五粮液",
            "industry": "白酒",
            "position_value": 80000,
        },
        {
            "stock_code": "300750",
            "stock_name": "宁德时代",
            "industry": "新能源",
            "position_value": 120000,
        },
        {
            "stock_code": "002475",
            "stock_name": "立讯精密",
            "industry": "电子",
            "position_value": 60000,
        },
    ]

    recommendations = strategy.generate_hedge_recommendations(positions)
    for rec in recommendations:
        print(f"\n  {rec.stock_name}:")
        print(f"    对冲标的: {rec.hedge_target_name}")
        print(f"    对冲金额: {rec.hedge_amount:,.0f}元")
        print(f"    预期风险降低: {rec.expected_risk_reduction:.1%}")

    # 测试3: 生成完整报告
    print("\n【测试3: 生成完整报告】")
    report = strategy.generate_report(positions)
    print(report)


if __name__ == "__main__":
    main()
