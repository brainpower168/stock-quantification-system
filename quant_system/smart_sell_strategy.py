# -*- coding: utf-8 -*-
"""
智能卖出策略模块
- 分批止盈
- 反弹卖出
- 主力资金判断
- 技术位分析
- 卖出时机判断
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class SmartSellStrategy:
    """智能卖出策略"""

    def __init__(self):
        # 止损止盈参数
        self.stop_loss_pct = -0.05  # 止损线 -5%
        self.take_profit_levels = [0.10, 0.20, 0.30]  # 止盈线 10%, 20%, 30%
        self.take_profit_ratios = [0.33, 0.33, 0.34]  # 分批卖出比例

        # 反弹卖出参数
        self.rebound_target_ma = 5  # 反弹目标：5日均线
        self.rebound_profit_pullback = 0.025  # 利润回撤2.5%清仓

        # 主力资金判断参数
        self.fund_outflow_days = 3  # 连续流出天数
        self.fund_outflow_threshold = -5000  # 流出阈值（万元）

    def analyze_sell_opportunity(
        self, position: Dict, market_data: pd.DataFrame, fund_flow_data: pd.DataFrame
    ) -> Dict:
        """
        分析卖出机会

        参数:
            position: {
                'code': 股票代码,
                'name': 股票名称,
                'entry_price': 买入价,
                'current_price': 当前价,
                'shares': 持仓股数,
                'entry_date': 买入日期
            }
            market_data: 历史行情数据（需包含 close, high, low, volume）
            fund_flow_data: 资金流向数据（需包含 date, main_flow, ddx）

        返回:
            {
                'should_sell': 是否应该卖出,
                'sell_ratio': 卖出比例,
                'sell_reason': 卖出原因,
                'target_price': 目标卖出价,
                'urgency': 紧急程度 (高/中/低),
                'action_plan': 行动计划
            }
        """
        # 计算盈亏
        profit_pct = (position["current_price"] - position["entry_price"]) / position[
            "entry_price"
        ]

        # 分析技术位
        tech_analysis = self._analyze_technical_levels(market_data)

        # 分析资金流向
        fund_analysis = self._analyze_fund_flow(fund_flow_data)

        # 分析卖出时机
        timing_analysis = self._analyze_sell_timing(
            profit_pct, tech_analysis, fund_analysis, market_data
        )

        # 综合判断
        decision = self._make_sell_decision(
            position, profit_pct, tech_analysis, fund_analysis, timing_analysis
        )

        return decision

    def _analyze_technical_levels(self, data: pd.DataFrame) -> Dict:
        """分析技术位"""
        if len(data) < 20:
            return {
                "ma5": None,
                "ma10": None,
                "ma20": None,
                "support": None,
                "resistance": None,
            }

        close = data["close"]

        # 计算均线
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]

        # 计算支撑阻力位
        recent_high = close.tail(20).max()
        recent_low = close.tail(20).min()
        current = close.iloc[-1]

        # 支撑位：最近低点、20日均线
        support = min(recent_low, ma20)

        # 阻力位：最近高点、5日均线
        resistance = max(recent_high, ma5)

        return {
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "current": round(current, 2),
            "trend": "up"
            if current > ma5 > ma10
            else "down"
            if current < ma5 < ma10
            else "sideways",
        }

    def _analyze_fund_flow(self, data: pd.DataFrame) -> Dict:
        """分析资金流向"""
        if len(data) < 5:
            return {"trend": "unknown", "consecutive_outflow": 0, "total_flow_5d": 0}

        # 计算连续流出天数
        consecutive_outflow = 0
        for flow in data["main_flow"].iloc[-5:][::-1]:
            if flow < 0:
                consecutive_outflow += 1
            else:
                break

        # 5日资金流向
        total_flow_5d = data["main_flow"].iloc[-5:].sum()

        # DDX趋势
        ddx_5d = data["ddx"].iloc[-5:].sum() if "ddx" in data.columns else 0
        ddx_10d = (
            data["ddx"].iloc[-10:].sum()
            if len(data) >= 10 and "ddx" in data.columns
            else 0
        )

        # 资金趋势判断
        if total_flow_5d > 10000 and ddx_5d > 0:
            trend = "strong_inflow"
        elif total_flow_5d > 0 and ddx_5d > 0:
            trend = "inflow"
        elif total_flow_5d < -10000 and ddx_5d < 0:
            trend = "strong_outflow"
        elif total_flow_5d < 0 or ddx_5d < 0:
            trend = "outflow"
        else:
            trend = "neutral"

        return {
            "trend": trend,
            "consecutive_outflow": consecutive_outflow,
            "total_flow_5d": round(total_flow_5d, 2),
            "ddx_5d": round(ddx_5d, 2),
            "ddx_10d": round(ddx_10d, 2),
        }

    def _analyze_sell_timing(
        self, profit_pct: float, tech: Dict, fund: Dict, data: pd.DataFrame
    ) -> Dict:
        """分析卖出时机"""
        current = tech["current"]

        # 判断是否急跌
        if len(data) >= 3:
            recent_change = (data["close"].iloc[-1] - data["close"].iloc[-3]) / data[
                "close"
            ].iloc[-3]
            is_crash = recent_change < -0.05  # 3天跌5%以上算急跌
        else:
            is_crash = False

        # 判断是否有反弹机会
        has_rebound_chance = False
        rebound_target = None

        if is_crash and fund["trend"] not in ["strong_outflow"]:
            # 急跌后通常有反弹
            has_rebound_chance = True
            rebound_target = tech["ma5"]  # 反弹目标：5日均线

        # 判断是否在支撑位附近
        near_support = False
        if tech["support"] and current:
            near_support = abs(current - tech["support"]) / tech["support"] < 0.02

        return {
            "is_crash": is_crash,
            "has_rebound_chance": has_rebound_chance,
            "rebound_target": rebound_target,
            "near_support": near_support,
            "profit_pct": round(profit_pct * 100, 2),
        }

    def _make_sell_decision(
        self, position: Dict, profit_pct: float, tech: Dict, fund: Dict, timing: Dict
    ) -> Dict:
        """做出卖出决策"""
        should_sell = False
        sell_ratio = 0.0
        sell_reason = ""
        target_price = position["current_price"]
        urgency = "低"
        action_plan = ""

        # 1. 止损判断（最高优先级）
        if profit_pct <= self.stop_loss_pct:
            # 但要判断是否急跌
            if timing["is_crash"] and timing["has_rebound_chance"]:
                should_sell = True
                sell_ratio = 0.5  # 先卖一半
                sell_reason = f"触发止损线({self.stop_loss_pct * 100}%)，但急跌后有反弹机会，先卖一半"
                target_price = timing["rebound_target"]
                urgency = "中"
                action_plan = f"先卖一半，等反弹到{target_price}再卖另一半"
            else:
                should_sell = True
                sell_ratio = 1.0
                sell_reason = f"触发止损线({self.stop_loss_pct * 100}%)，立即清仓"
                urgency = "高"
                action_plan = "立即全部卖出"

        # 2. 止盈判断
        elif profit_pct >= self.take_profit_levels[2]:  # 30%以上
            should_sell = True
            sell_ratio = 1.0
            sell_reason = f"盈利{profit_pct * 100:.1f}%，达到第三止盈线，全部清仓"
            urgency = "高"
            action_plan = "全部卖出，锁定利润"

        elif profit_pct >= self.take_profit_levels[1]:  # 20%以上
            should_sell = True
            sell_ratio = 0.5
            sell_reason = f"盈利{profit_pct * 100:.1f}%，达到第二止盈线，卖一半"
            urgency = "中"
            action_plan = "卖一半，留一半看能不能继续涨"

        elif profit_pct >= self.take_profit_levels[0]:  # 10%以上
            should_sell = True
            sell_ratio = 0.33
            sell_reason = f"盈利{profit_pct * 100:.1f}%，达到第一止盈线，卖1/3"
            urgency = "低"
            action_plan = "卖1/3，锁定部分利润"

        # 3. 资金流向判断
        elif fund["trend"] == "strong_outflow":
            if profit_pct > 0:
                should_sell = True
                sell_ratio = 0.5
                sell_reason = f"主力资金大幅流出({fund['total_flow_5d'] / 10000:.1f}亿)，盈利{profit_pct * 100:.1f}%，先卖一半"
                urgency = "高"
                action_plan = "主力在出货，反弹就卖"
            else:
                if timing["has_rebound_chance"]:
                    should_sell = True
                    sell_ratio = 0.5
                    sell_reason = (
                        f"主力资金流出，亏损{abs(profit_pct) * 100:.1f}%，等反弹卖一半"
                    )
                    target_price = timing["rebound_target"]
                    urgency = "中"
                    action_plan = f"等反弹到{target_price}再卖"
                else:
                    should_sell = True
                    sell_ratio = 1.0
                    sell_reason = (
                        f"主力资金大幅流出，亏损{abs(profit_pct) * 100:.1f}%，立即清仓"
                    )
                    urgency = "高"
                    action_plan = "主力在出货，立即全部卖出"

        # 4. 连续流出判断
        elif fund["consecutive_outflow"] >= self.fund_outflow_days:
            should_sell = True
            sell_ratio = 0.5
            sell_reason = f"主力资金连续{fund['consecutive_outflow']}天流出，先卖一半"
            urgency = "中"
            action_plan = "观察资金流向，如果继续流出就全卖"

        # 5. 技术位判断
        elif tech["trend"] == "down" and profit_pct < 0:
            if timing["near_support"]:
                should_sell = False
                sell_reason = f"下跌趋势但接近支撑位{tech['support']}，观察支撑是否有效"
                action_plan = "观察支撑位，如果跌破就止损"
            else:
                should_sell = True
                sell_ratio = 0.5
                sell_reason = f"下跌趋势，亏损{abs(profit_pct) * 100:.1f}%，先卖一半"
                urgency = "中"
                action_plan = "下跌趋势，先减仓"

        # 6. 盈利但主力流入
        elif profit_pct > 0 and fund["trend"] in ["inflow", "strong_inflow"]:
            should_sell = False
            sell_reason = f"盈利{profit_pct * 100:.1f}%，主力资金流入，继续持有"
            action_plan = "主力还在买，继续持有"

        # 7. 亏损但主力流入
        elif profit_pct < 0 and fund["trend"] in ["inflow", "strong_inflow"]:
            should_sell = False
            sell_reason = f"亏损{abs(profit_pct) * 100:.1f}%，但主力资金流入，不慌卖"
            action_plan = "主力在吸筹，不急着卖"

        else:
            should_sell = False
            sell_reason = (
                f"盈利{profit_pct * 100:.1f}%，资金趋势{fund['trend']}，继续观察"
            )
            action_plan = "继续观察，不急着操作"

        return {
            "should_sell": should_sell,
            "sell_ratio": sell_ratio,
            "sell_reason": sell_reason,
            "target_price": target_price,
            "urgency": urgency,
            "action_plan": action_plan,
            "profit_pct": round(profit_pct * 100, 2),
            "fund_trend": fund["trend"],
            "tech_trend": tech["trend"],
            "has_rebound_chance": timing["has_rebound_chance"],
        }

    def calculate_rebound_sell_price(
        self, entry_price: float, current_price: float, tech: Dict, fund: Dict
    ) -> Dict:
        """
        计算反弹卖出价格

        返回:
            {
                'target_prices': [目标价位列表],
                'sell_ratios': [对应卖出比例],
                'reasons': [原因说明]
            }
        """
        profit_pct = (current_price - entry_price) / entry_price
        targets = []
        ratios = []
        reasons = []

        # 1. 如果亏损，反弹到成本价附近卖
        if profit_pct < 0:
            if tech["ma5"] and tech["ma5"] > current_price:
                targets.append(tech["ma5"])
                ratios.append(0.5)
                reasons.append(f"反弹到5日均线{tech['ma5']:.2f}，卖一半")

            targets.append(entry_price)
            ratios.append(0.5)
            reasons.append(f"反弹到成本价{entry_price:.2f}，卖剩余部分")

        # 2. 如果盈利，分批止盈
        else:
            if profit_pct < 0.10:
                # 盈利<10%，等涨到10%
                target = entry_price * 1.10
                targets.append(target)
                ratios.append(0.33)
                reasons.append(f"涨到{target:.2f}(+10%)，卖1/3")

            if profit_pct < 0.20:
                target = entry_price * 1.20
                targets.append(target)
                ratios.append(0.33)
                reasons.append(f"涨到{target:.2f}(+20%)，再卖1/3")

            target = entry_price * 1.30
            targets.append(target)
            ratios.append(0.34)
            reasons.append(f"涨到{target:.2f}(+30%)，全部清仓")

        return {"target_prices": targets, "sell_ratios": ratios, "reasons": reasons}

    def should_wait_for_rebound(
        self, current_price: float, entry_price: float, fund: Dict, tech: Dict
    ) -> Tuple[bool, str]:
        """
        判断是否应该等反弹再卖

        返回:
            (是否等反弹, 原因)
        """
        profit_pct = (current_price - entry_price) / entry_price

        # 1. 主力流入，不急着卖
        if fund["trend"] in ["inflow", "strong_inflow"]:
            return True, "主力资金流入，不急着卖，等反弹"

        # 2. 急跌后通常有反弹
        if profit_pct < 0 and abs(profit_pct) > 0.05:
            if fund["trend"] != "strong_outflow":
                return True, "急跌后通常有反弹，等反弹再卖"

        # 3. 接近支撑位
        if (
            tech["support"]
            and abs(current_price - tech["support"]) / tech["support"] < 0.02
        ):
            return True, f"接近支撑位{tech['support']:.2f}，观察支撑是否有效"

        # 4. 主力大幅流出，不等反弹
        if fund["trend"] == "strong_outflow":
            return False, "主力大幅流出，反弹就卖，不要等"

        # 5. 盈利状态，可以等
        if profit_pct > 0:
            return True, "盈利状态，可以等更好的卖点"

        return False, "没有反弹机会，及时止损"


class SellChecklist:
    """卖出检查清单"""

    def __init__(self):
        self.strategy = SmartSellStrategy()

    def check_before_sell(
        self, position: Dict, market_data: pd.DataFrame, fund_flow_data: pd.DataFrame
    ) -> Dict:
        """
        卖出前检查清单

        返回:
            {
                'checklist': [
                    {'item': '检查项', 'result': '结果', 'advice': '建议'}
                ],
                'overall_advice': '总体建议',
                'should_sell': 是否应该卖出
            }
        """
        checks = []
        should_sell_overall = False

        profit_pct = (position["current_price"] - position["entry_price"]) / position[
            "entry_price"
        ]

        # 1. 检查主力资金流向
        fund = self.strategy._analyze_fund_flow(fund_flow_data)
        if fund["trend"] in ["outflow", "strong_outflow"]:
            checks.append(
                {
                    "item": "主力资金流向",
                    "result": f"流出{abs(fund['total_flow_5d']) / 10000:.1f}亿",
                    "advice": "主力流出，反弹是卖的机会",
                }
            )
            if fund["trend"] == "strong_outflow":
                should_sell_overall = True
        else:
            checks.append(
                {
                    "item": "主力资金流向",
                    "result": f"流入{fund['total_flow_5d'] / 10000:.1f}亿",
                    "advice": "主力流入，不急着卖",
                }
            )

        # 2. 检查盈亏幅度
        if profit_pct <= -0.05:
            checks.append(
                {
                    "item": "盈亏幅度",
                    "result": f"亏损{abs(profit_pct) * 100:.1f}%",
                    "advice": "触发止损线，考虑卖出",
                }
            )
            should_sell_overall = True
        elif profit_pct >= 0.10:
            checks.append(
                {
                    "item": "盈亏幅度",
                    "result": f"盈利{profit_pct * 100:.1f}%",
                    "advice": "达到止盈线，考虑分批卖出",
                }
            )
            should_sell_overall = True
        else:
            checks.append(
                {
                    "item": "盈亏幅度",
                    "result": f"{'盈利' if profit_pct > 0 else '亏损'}{abs(profit_pct) * 100:.1f}%",
                    "advice": "未到止损止盈线，继续观察",
                }
            )

        # 3. 检查技术位
        tech = self.strategy._analyze_technical_levels(market_data)
        if tech["trend"] == "down":
            checks.append(
                {
                    "item": "技术趋势",
                    "result": "下跌趋势",
                    "advice": "下跌趋势，谨慎持有",
                }
            )
        else:
            checks.append(
                {
                    "item": "技术趋势",
                    "result": tech["trend"],
                    "advice": "趋势尚可，不急着卖",
                }
            )

        # 4. 检查是否有反弹机会
        timing = self.strategy._analyze_sell_timing(profit_pct, tech, fund, market_data)
        if timing["has_rebound_chance"]:
            checks.append(
                {
                    "item": "反弹机会",
                    "result": f"有反弹机会，目标{timing['rebound_target']:.2f}",
                    "advice": "等反弹再卖",
                }
            )
        else:
            checks.append(
                {
                    "item": "反弹机会",
                    "result": "无明显反弹机会",
                    "advice": "根据资金流向决定",
                }
            )

        # 5. 检查连续流出天数
        if fund["consecutive_outflow"] >= 3:
            checks.append(
                {
                    "item": "资金连续性",
                    "result": f"连续{fund['consecutive_outflow']}天流出",
                    "advice": "资金持续流出，考虑减仓",
                }
            )
            should_sell_overall = True
        else:
            checks.append(
                {"item": "资金连续性", "result": "资金流向稳定", "advice": "继续观察"}
            )

        # 综合建议
        if should_sell_overall:
            overall_advice = "建议卖出，但先分析最佳卖出时机"
        else:
            overall_advice = "暂不卖出，继续观察"

        return {
            "checklist": checks,
            "overall_advice": overall_advice,
            "should_sell": should_sell_overall,
            "profit_pct": round(profit_pct * 100, 2),
            "fund_trend": fund["trend"],
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("智能卖出策略模块测试")
    print("=" * 60)

    strategy = SmartSellStrategy()
    checklist = SellChecklist()

    # 模拟持仓数据
    position = {
        "code": "000988",
        "name": "华工科技",
        "entry_price": 120.50,
        "current_price": 114.00,
        "shares": 1000,
        "entry_date": "2026-04-20",
    }

    # 模拟行情数据
    np.random.seed(42)
    dates = pd.date_range("2026-04-01", "2026-04-30")
    market_data = pd.DataFrame(
        {
            "close": 120 + np.random.randn(30).cumsum() * 2,
            "high": 122 + np.random.randn(30).cumsum() * 2,
            "low": 118 + np.random.randn(30).cumsum() * 2,
            "volume": np.random.randint(1000, 5000, 30),
        },
        index=dates,
    )

    # 模拟资金流向数据
    fund_flow_data = pd.DataFrame(
        {
            "date": dates,
            "main_flow": np.random.randint(-5000, 8000, 30),
            "ddx": np.random.uniform(-2, 3, 30),
        }
    )

    # 测试卖出分析
    print("\n1. 卖出机会分析测试")
    print("-" * 60)

    result = strategy.analyze_sell_opportunity(position, market_data, fund_flow_data)
    print(f"股票: {position['name']}({position['code']})")
    print(f"买入价: {position['entry_price']:.2f}")
    print(f"当前价: {position['current_price']:.2f}")
    print(f"盈亏: {result['profit_pct']:.2f}%")
    print(f"是否卖出: {result['should_sell']}")
    print(f"卖出比例: {result['sell_ratio'] * 100:.0f}%")
    print(f"卖出原因: {result['sell_reason']}")
    print(f"目标价: {result['target_price']:.2f}")
    print(f"紧急程度: {result['urgency']}")
    print(f"行动计划: {result['action_plan']}")

    # 测试反弹卖出价格
    print("\n2. 反弹卖出价格测试")
    print("-" * 60)

    tech = strategy._analyze_technical_levels(market_data)
    fund = strategy._analyze_fund_flow(fund_flow_data)

    rebound_prices = strategy.calculate_rebound_sell_price(
        position["entry_price"], position["current_price"], tech, fund
    )

    print("反弹卖出计划:")
    for price, ratio, reason in zip(
        rebound_prices["target_prices"],
        rebound_prices["sell_ratios"],
        rebound_prices["reasons"],
    ):
        print(f"  - {reason} (卖出{ratio * 100:.0f}%)")

    # 测试是否等反弹
    print("\n3. 是否等反弹测试")
    print("-" * 60)

    should_wait, reason = strategy.should_wait_for_rebound(
        position["current_price"], position["entry_price"], fund, tech
    )
    print(f"是否等反弹: {should_wait}")
    print(f"原因: {reason}")

    # 测试卖出检查清单
    print("\n4. 卖出检查清单测试")
    print("-" * 60)

    check_result = checklist.check_before_sell(position, market_data, fund_flow_data)
    print(f"总体建议: {check_result['overall_advice']}")
    print(f"是否卖出: {check_result['should_sell']}")
    print("\n检查清单:")
    for check in check_result["checklist"]:
        print(f"  - {check['item']}: {check['result']} -> {check['advice']}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
