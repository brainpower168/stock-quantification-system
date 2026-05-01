# -*- coding: utf-8 -*-
"""
智能选股系统 v3.0 集成测试
- 三层过滤法
- 题材热点追踪
- 智能卖出策略
- 分级推荐制度
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from three_layer_picker import ThreeLayerStockPicker
from theme_hot_tracker import ThemeStrategy
from smart_sell_strategy import SmartSellStrategy, SellChecklist
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class SmartStockSystemV3:
    """智能选股系统v3.0"""

    def __init__(self):
        self.picker = ThreeLayerStockPicker()
        self.theme_strategy = ThemeStrategy()
        self.sell_strategy = SmartSellStrategy()
        self.sell_checklist = SellChecklist()

    def analyze_stock(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        fund_flow: float,
        ddx_10d: float,
        pct_change: float,
        pe: float = None,
        roe: float = None,
    ) -> Dict:
        """
        综合分析单只股票

        返回:
            {
                'code': 代码,
                'name': 名称,
                'grade': 推荐等级 (A/B/C/D),
                'theme_score': 题材评分,
                'pick_score': 选股评分,
                'total_score': 综合评分,
                'should_buy': 是否买入,
                'buy_reason': 买入原因,
                'risk_level': 风险等级,
                'themes': 题材列表,
                'action': 行动建议
            }
        """
        # 1. 三层过滤 - 转换为列表格式
        stock_item = {
            "code": code,
            "name": name,
            "data": data,
            "fund_flow": fund_flow,
            "ddx_10d": ddx_10d,
            "pct_change": pct_change,
            "pe": pe,
            "roe": roe,
            "price": data["close"].iloc[-1] if len(data) > 0 else 100,
            "sector": "unknown",
        }

        pick_result = self.picker.pick_stocks([stock_item])

        # 2. 题材分析
        theme_result = self.theme_strategy.analyze_stock(
            code, name, data, fund_flow, pct_change
        )

        # 3. 综合评分
        # pick_result是列表，找到对应股票
        pick_score = 0
        if pick_result and len(pick_result) > 0:
            for item in pick_result:
                if item["code"] == code:
                    pick_score = item["total_score"]
                    break

        theme_score = theme_result["theme_score"]

        # 综合评分 = 选股评分 * 0.6 + 题材评分 * 0.4
        total_score = pick_score * 0.6 + theme_score * 0.4

        # 4. 分级推荐
        grade = self._calculate_grade(total_score, pct_change, ddx_10d, fund_flow)

        # 5. 是否买入
        should_buy, buy_reason = self._should_buy(
            grade, theme_result, pick_result, pct_change, ddx_10d, fund_flow
        )

        # 6. 风险等级
        risk_level = self._calculate_risk(pct_change, ddx_10d, fund_flow, theme_result)

        # 7. 行动建议
        action = self._get_action(grade, should_buy, buy_reason, risk_level)

        return {
            "code": code,
            "name": name,
            "grade": grade,
            "theme_score": round(theme_score, 1),
            "pick_score": round(pick_score, 1),
            "total_score": round(total_score, 1),
            "should_buy": should_buy,
            "buy_reason": buy_reason,
            "risk_level": risk_level,
            "themes": ", ".join(theme_result["themes"])
            if theme_result["themes"]
            else "无",
            "limit_up_gene": theme_result["limit_up_gene"]["limit_up_gene_score"],
            "is_hot": theme_result["limit_up_gene"]["is_hot"],
            "action": action,
            "fund_flow": fund_flow,
            "ddx_10d": ddx_10d,
            "pct_change": pct_change,
        }

    def _calculate_grade(
        self, total_score: float, pct_change: float, ddx_10d: float, fund_flow: float
    ) -> str:
        """计算推荐等级"""
        # A级：综合评分>=70 + 涨幅<3% + 10日DDX>0 + 主力流入
        if total_score >= 70 and pct_change < 3 and ddx_10d > 0 and fund_flow > 0:
            return "A"

        # B级：综合评分>=60 + 涨幅<5% + 主力流入
        elif total_score >= 60 and pct_change < 5 and fund_flow > 0:
            return "B"

        # C级：综合评分>=50 + 涨幅<7%
        elif total_score >= 50 and pct_change < 7:
            return "C"

        # D级：其他
        else:
            return "D"

    def _should_buy(
        self,
        grade: str,
        theme_result: Dict,
        pick_result: List,
        pct_change: float,
        ddx_10d: float,
        fund_flow: float,
    ) -> Tuple[bool, str]:
        """判断是否买入"""
        # A级：强烈推荐
        if grade == "A":
            return (
                True,
                f"A级推荐，最佳买点，涨幅{pct_change:.1f}%，主力流入{fund_flow / 10000:.1f}亿",
            )

        # B级：可以关注
        elif grade == "B":
            if theme_result["should_buy"]:
                return True, f"B级推荐，题材热点({theme_result['reason']})"
            else:
                return True, f"B级推荐，涨幅{pct_change:.1f}%偏高，小仓位试错"

        # C级：风险较高
        elif grade == "C":
            if theme_result["limit_up_gene"]["is_hot"]:
                return True, f"C级，但热点股，可以关注，设好止损"
            else:
                return False, f"C级，涨幅{pct_change:.1f}%较高，追高风险大"

        # D级：不推荐
        else:
            if ddx_10d < 0 and fund_flow < 0:
                return False, f"D级，10日DDX={ddx_10d:.1f}，主力流出，不买"
            elif pct_change >= 7:
                return False, f"D级，涨幅{pct_change:.1f}%过高，追高风险极大"
            else:
                return False, f"D级，综合评分不足，不推荐"

    def _calculate_risk(
        self, pct_change: float, ddx_10d: float, fund_flow: float, theme_result: Dict
    ) -> str:
        """计算风险等级"""
        risk_score = 0

        # 涨幅风险
        if pct_change >= 7:
            risk_score += 30
        elif pct_change >= 5:
            risk_score += 20
        elif pct_change >= 3:
            risk_score += 10

        # DDX风险
        if ddx_10d < -2:
            risk_score += 30
        elif ddx_10d < 0:
            risk_score += 15

        # 资金风险
        if fund_flow < -5000:
            risk_score += 30
        elif fund_flow < 0:
            risk_score += 15

        # 题材风险
        if theme_result["limit_up_gene"]["is_hot"] and fund_flow < 0:
            risk_score += 20

        if risk_score >= 50:
            return "high"
        elif risk_score >= 30:
            return "medium"
        else:
            return "low"

    def _get_action(
        self, grade: str, should_buy: bool, buy_reason: str, risk_level: str
    ) -> str:
        """获取行动建议"""
        if grade == "A":
            return f"强烈推荐买入，{buy_reason}"
        elif grade == "B":
            if risk_level == "low":
                return f"可以买入，{buy_reason}"
            else:
                return f"谨慎买入，{buy_reason}，风险{risk_level}"
        elif grade == "C":
            if should_buy:
                return f"小仓位试错，{buy_reason}，严格止损"
            else:
                return f"观望为主，{buy_reason}"
        else:
            return f"不推荐买入，{buy_reason}"

    def analyze_portfolio(self, stocks_data: Dict[str, Dict]) -> pd.DataFrame:
        """
        分析股票组合

        参数:
            stocks_data: {股票代码: {'name': 名称, 'data': 历史数据, 'fund_flow': 资金流向, ...}}

        返回:
            分析结果表
        """
        results = []

        for code, info in stocks_data.items():
            analysis = self.analyze_stock(
                code,
                info["name"],
                info["data"],
                info.get("fund_flow", 0),
                info.get("ddx_10d", 0),
                info.get("pct_change", 0),
                info.get("pe"),
                info.get("roe"),
            )
            results.append(analysis)

        df = pd.DataFrame(results)
        if len(df) > 0:
            # 按综合评分排序
            df = df.sort_values("total_score", ascending=False)
            # 按等级排序
            grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
            df["grade_order"] = df["grade"].map(grade_order)
            df = df.sort_values(["grade_order", "total_score"], ascending=[True, False])
            df = df.drop("grade_order", axis=1)

        return df


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("智能选股系统 v3.0 测试")
    print("=" * 80)

    system = SmartStockSystemV3()

    # 用户自选股
    watchlist = [
        ("601138", "工业富联", 1.2, 15000, 2.5, 25.0, 15.0),
        ("002475", "立讯精密", 2.1, 8000, 1.8, 28.0, 12.0),
        ("002460", "赣锋锂业", 3.5, 12000, 3.2, 35.0, 10.0),
        ("002281", "光迅科技", 4.2, 20000, 4.5, 40.0, 8.0),
        ("002463", "沪电股份", 1.8, 6000, 1.5, 22.0, 14.0),
        ("300750", "宁德时代", 2.5, 15000, 2.8, 45.0, 18.0),
        ("300476", "胜宏科技", 5.2, 5000, 0.8, 30.0, 11.0),
        ("000988", "华工科技", -2.3, -3000, -1.2, 32.0, 9.0),
    ]

    # 构建测试数据
    np.random.seed(42)
    dates = pd.date_range("2026-04-01", "2026-04-30")

    stocks_data = {}
    for code, name, pct, fund, ddx, pe, roe in watchlist:
        # 模拟历史数据
        base_price = 100
        data = pd.DataFrame(
            {
                "close": base_price * (1 + np.random.randn(30).cumsum() * 0.02),
                "high": base_price * (1.02 + np.random.randn(30).cumsum() * 0.02),
                "low": base_price * (0.98 + np.random.randn(30).cumsum() * 0.02),
                "volume": np.random.randint(1000, 5000, 30),
            },
            index=dates,
        )

        stocks_data[code] = {
            "name": name,
            "data": data,
            "fund_flow": fund,
            "ddx_10d": ddx,
            "pct_change": pct,
            "pe": pe,
            "roe": roe,
        }

    # 分析自选股
    print("\n用户自选股分析结果")
    print("=" * 80)

    result_df = system.analyze_portfolio(stocks_data)

    # 显示结果
    display_cols = [
        "code",
        "name",
        "grade",
        "total_score",
        "should_buy",
        "pct_change",
        "fund_flow",
        "ddx_10d",
        "themes",
        "action",
    ]

    print(result_df[display_cols].to_string(index=False))

    # 统计
    print("\n" + "=" * 80)
    print("推荐统计")
    print("=" * 80)

    grade_counts = result_df["grade"].value_counts()
    print(f"A级（强烈推荐）: {grade_counts.get('A', 0)} 只")
    print(f"B级（可以关注）: {grade_counts.get('B', 0)} 只")
    print(f"C级（风险较高）: {grade_counts.get('C', 0)} 只")
    print(f"D级（不推荐）: {grade_counts.get('D', 0)} 只")

    buy_count = result_df["should_buy"].sum()
    print(f"\n建议买入: {buy_count} 只")

    # 显示建议买入的股票
    if buy_count > 0:
        print("\n建议买入股票:")
        buy_stocks = result_df[result_df["should_buy"] == True]
        for _, row in buy_stocks.iterrows():
            print(
                f"  - {row['name']}({row['code']}): {row['grade']}级, {row['buy_reason']}"
            )

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
