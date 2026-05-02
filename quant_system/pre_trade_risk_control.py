# -*- coding: utf-8 -*-
"""
事前风控模块 - 幻方量化风控体系
- ST股过滤
- 流动性过滤
- 标的筛选
- 仓位控制
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class StockFilter:
    """股票过滤器 - 事前风控"""

    def __init__(self):
        # 过滤参数
        self.min_market_cap = 20e8  # 最小市值20亿
        self.min_volume = 100000  # 最小成交量10万股
        self.min_turnover_rate = 0.01  # 最小换手率1%
        self.min_price = 2.0  # 最小股价2元
        self.max_price = 300.0  # 最大股价300元

        # ST股票列表（示例）
        self.st_stocks = set()

        # 退市风险股票
        self.delist_risk_stocks = set()

    def filter_st(self, stock_list: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        过滤ST股票

        返回:
            (通过列表, 过滤列表)
        """
        passed = []
        filtered = []

        for stock in stock_list:
            name = stock.get("name", "")
            code = stock.get("code", "")

            # 检查ST标记
            is_st = False
            filter_reason = []

            if "ST" in name or "st" in name:
                is_st = True
                filter_reason.append("ST股票")

            if "*" in name:
                is_st = True
                filter_reason.append("退市风险")

            if code in self.st_stocks:
                is_st = True
                filter_reason.append("ST列表")

            if code in self.delist_risk_stocks:
                is_st = True
                filter_reason.append("退市风险列表")

            if is_st:
                filtered.append({**stock, "filter_reason": ", ".join(filter_reason)})
            else:
                passed.append(stock)

        return passed, filtered

    def filter_liquidity(self, stock_list: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        过滤流动性不足的股票

        返回:
            (通过列表, 过滤列表)
        """
        passed = []
        filtered = []

        for stock in stock_list:
            filter_reason = []
            is_filtered = False

            # 市值过滤
            market_cap = stock.get("market_cap", 0)
            if market_cap < self.min_market_cap:
                is_filtered = True
                filter_reason.append(
                    f"市值{market_cap / 1e8:.1f}亿<{self.min_market_cap / 1e8:.0f}亿"
                )

            # 成交量过滤
            volume = stock.get("volume", 0)
            if volume < self.min_volume:
                is_filtered = True
                filter_reason.append(
                    f"成交量{volume / 1e4:.1f}万<{self.min_volume / 1e4:.0f}万"
                )

            # 换手率过滤
            turnover_rate = stock.get("turnover_rate", 0)
            if turnover_rate < self.min_turnover_rate:
                is_filtered = True
                filter_reason.append(
                    f"换手率{turnover_rate * 100:.2f}%<{self.min_turnover_rate * 100:.0f}%"
                )

            # 股价过滤
            price = stock.get("price", 0)
            if price < self.min_price:
                is_filtered = True
                filter_reason.append(f"股价{price:.2f}<{self.min_price:.0f}元")

            if price > self.max_price:
                is_filtered = True
                filter_reason.append(f"股价{price:.2f}>{self.max_price:.0f}元")

            if is_filtered:
                filtered.append({**stock, "filter_reason": ", ".join(filter_reason)})
            else:
                passed.append(stock)

        return passed, filtered

    def filter_all(self, stock_list: List[Dict]) -> Dict:
        """
        执行所有过滤

        返回:
            {
                'passed': 通过列表,
                'filtered_st': ST过滤列表,
                'filtered_liquidity': 流动性过滤列表,
                'statistics': 统计信息
            }
        """
        # 1. ST过滤
        passed_st, filtered_st = self.filter_st(stock_list)

        # 2. 流动性过滤
        passed_all, filtered_liquidity = self.filter_liquidity(passed_st)

        return {
            "passed": passed_all,
            "filtered_st": filtered_st,
            "filtered_liquidity": filtered_liquidity,
            "statistics": {
                "total": len(stock_list),
                "passed": len(passed_all),
                "filtered_st": len(filtered_st),
                "filtered_liquidity": len(filtered_liquidity),
                "pass_rate": len(passed_all) / len(stock_list)
                if len(stock_list) > 0
                else 0,
            },
        }


class PositionController:
    """仓位控制器"""

    def __init__(self, total_capital: float = 1000000):
        self.total_capital = total_capital

        # 仓位限制
        self.max_single_position = 0.20  # 单股最大20%
        self.max_sector_position = 0.40  # 单行业最大40%
        self.max_total_position = 0.80  # 总仓位最大80%

        # 当前持仓
        self.positions = {}
        self.sector_positions = {}
        self.total_position = 0

    def can_add_position(
        self, code: str, sector: str, amount: float
    ) -> Tuple[bool, str]:
        """
        检查是否可以加仓

        返回:
            (是否可以, 原因)
        """
        position_ratio = amount / self.total_capital

        # 1. 单股限制
        current_single = self.positions.get(code, 0) / self.total_capital
        if current_single + position_ratio > self.max_single_position:
            remaining = self.max_single_position - current_single
            return False, f"单股仓位超限，剩余{remaining * 100:.1f}%"

        # 2. 行业限制
        current_sector = self.sector_positions.get(sector, 0) / self.total_capital
        if current_sector + position_ratio > self.max_sector_position:
            remaining = self.max_sector_position - current_sector
            return False, f"行业仓位超限，剩余{remaining * 100:.1f}%"

        # 3. 总仓位限制
        if self.total_position + position_ratio > self.max_total_position:
            remaining = self.max_total_position - self.total_position
            return False, f"总仓位超限，剩余{remaining * 100:.1f}%"

        return True, "可以加仓"

    def add_position(self, code: str, sector: str, amount: float):
        """添加持仓"""
        self.positions[code] = self.positions.get(code, 0) + amount
        self.sector_positions[sector] = self.sector_positions.get(sector, 0) + amount
        self.total_position += amount / self.total_capital

    def get_position_status(self) -> Dict:
        """获取仓位状态"""
        return {
            "total_position": self.total_position,
            "position_count": len(self.positions),
            "sector_count": len(self.sector_positions),
            "positions": self.positions,
            "sector_positions": self.sector_positions,
            "available_capital": (1 - self.total_position) * self.total_capital,
        }


class PreTradeRiskControl:
    """事前风控系统"""

    def __init__(self, total_capital: float = 1000000):
        self.stock_filter = StockFilter()
        self.position_controller = PositionController(total_capital)
        self.total_capital = total_capital

    def screen_stocks(self, stock_list: List[Dict]) -> Dict:
        """
        筛选股票

        返回:
            {
                'passed_stocks': 通过筛选的股票,
                'filter_result': 过滤结果,
                'recommendations': 推荐列表
            }
        """
        # 执行过滤
        filter_result = self.stock_filter.filter_all(stock_list)

        # 生成推荐
        recommendations = []
        for stock in filter_result["passed"]:
            # 计算推荐仓位
            price = stock.get("price", 10)
            max_position = self.position_controller.max_single_position
            max_shares = int(self.total_capital * max_position / price)

            recommendations.append(
                {
                    **stock,
                    "max_position_value": self.total_capital * max_position,
                    "max_shares": max_shares,
                    "recommended_position": min(
                        max_position, stock.get("suggested_weight", 0.10)
                    ),
                }
            )

        return {
            "passed_stocks": filter_result["passed"],
            "filter_result": filter_result,
            "recommendations": recommendations,
        }

    def check_before_buy(
        self, code: str, sector: str, amount: float, stock_info: Dict
    ) -> Dict:
        """
        买入前检查

        返回:
            {
                'can_buy': 是否可以买入,
                'reasons': 原因列表,
                'warnings': 警告列表,
                'suggestions': 建议列表
            }
        """
        reasons = []
        warnings = []
        suggestions = []
        can_buy = True

        # 1. ST检查
        name = stock_info.get("name", "")
        if "ST" in name or "*" in name:
            can_buy = False
            reasons.append("ST股票，禁止买入")

        # 2. 流动性检查
        market_cap = stock_info.get("market_cap", 0)
        if market_cap < 20e8:
            warnings.append(f"市值较小({market_cap / 1e8:.1f}亿)，流动性风险")

        volume = stock_info.get("volume", 0)
        if volume < 100000:
            warnings.append(f"成交量较低({volume / 1e4:.1f}万)，流动性风险")

        # 3. 仓位检查
        can_add, add_reason = self.position_controller.can_add_position(
            code, sector, amount
        )
        if not can_add:
            can_buy = False
            reasons.append(add_reason)

        # 4. 价格检查
        price = stock_info.get("price", 0)
        if price < 2:
            warnings.append("股价低于2元，风险较高")

        # 5. 涨跌幅检查
        pct_change = stock_info.get("pct_change", 0)
        if pct_change > 9.5:
            can_buy = False
            reasons.append("涨停板，无法买入")
        elif pct_change > 7:
            warnings.append("涨幅较高，追高风险大")
            suggestions.append("建议等回调再买")

        # 6. 生成建议
        if can_buy and len(warnings) == 0:
            suggestions.append("符合买入条件")
        elif can_buy and len(warnings) > 0:
            suggestions.append("可以买入，但需注意风险")

        return {
            "can_buy": can_buy,
            "reasons": reasons,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def generate_trading_plan(
        self, stock_list: List[Dict], risk_level: str = "medium"
    ) -> Dict:
        """
        生成交易计划

        返回:
            {
                'buy_list': 买入列表,
                'filter_summary': 过滤摘要,
                'position_plan': 仓位计划,
                'risk_control': 风控措施
            }
        """
        # 1. 筛选股票
        screen_result = self.screen_stocks(stock_list)

        # 2. 根据风险等级调整仓位
        if risk_level == "low":
            position_ratio = 0.10
        elif risk_level == "medium":
            position_ratio = 0.15
        else:  # high
            position_ratio = 0.20

        # 3. 生成买入列表
        buy_list = []
        for stock in screen_result["recommendations"]:
            position_value = self.total_capital * position_ratio
            price = stock.get("price", 10)
            shares = int(position_value / price / 100) * 100  # 整手

            buy_list.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "price": price,
                    "shares": shares,
                    "position_value": shares * price,
                    "position_ratio": position_ratio,
                    "stop_loss": price * 0.95,  # -5%
                    "take_profit_1": price * 1.10,  # +10%
                    "take_profit_2": price * 1.20,  # +20%
                }
            )

        return {
            "buy_list": buy_list,
            "filter_summary": screen_result["filter_result"]["statistics"],
            "position_plan": {
                "total_capital": self.total_capital,
                "position_per_stock": position_ratio,
                "max_total_position": self.position_controller.max_total_position,
            },
            "risk_control": {
                "stop_loss": -0.05,
                "take_profit_levels": [0.10, 0.20, 0.30],
                "circuit_breaker": "连续3天亏损触发熔断",
            },
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("事前风控模块测试 - 幻方量化风控体系")
    print("=" * 80)

    # 模拟股票列表
    stock_list = [
        {
            "code": "600519",
            "name": "贵州茅台",
            "price": 1800,
            "market_cap": 22000e8,
            "volume": 500000,
            "turnover_rate": 0.02,
        },
        {
            "code": "000001",
            "name": "平安银行",
            "price": 15,
            "market_cap": 3000e8,
            "volume": 1000000,
            "turnover_rate": 0.03,
        },
        {
            "code": "600000",
            "name": "ST某某",
            "price": 3,
            "market_cap": 50e8,
            "volume": 200000,
            "turnover_rate": 0.05,
        },
        {
            "code": "000002",
            "name": "万科A",
            "price": 10,
            "market_cap": 1200e8,
            "volume": 800000,
            "turnover_rate": 0.02,
        },
        {
            "code": "000003",
            "name": "*ST某某",
            "price": 1.5,
            "market_cap": 10e8,
            "volume": 50000,
            "turnover_rate": 0.01,
        },
        {
            "code": "002475",
            "name": "立讯精密",
            "price": 35,
            "market_cap": 600e8,
            "volume": 300000,
            "turnover_rate": 0.025,
        },
    ]

    # 测试股票过滤
    print("\n1. 股票过滤测试")
    print("-" * 80)

    control = PreTradeRiskControl(total_capital=1000000)
    screen_result = control.screen_stocks(stock_list)

    print(f"总股票数: {screen_result['filter_result']['statistics']['total']}")
    print(f"通过筛选: {screen_result['filter_result']['statistics']['passed']}")
    print(f"ST过滤: {screen_result['filter_result']['statistics']['filtered_st']}")
    print(
        f"流动性过滤: {screen_result['filter_result']['statistics']['filtered_liquidity']}"
    )
    print(
        f"通过率: {screen_result['filter_result']['statistics']['pass_rate'] * 100:.1f}%"
    )

    print("\n通过筛选的股票:")
    for stock in screen_result["passed_stocks"]:
        print(
            f"  {stock['name']}({stock['code']}): 价格{stock['price']:.2f}, 市值{stock['market_cap'] / 1e8:.0f}亿"
        )

    print("\n被过滤的股票:")
    for stock in screen_result["filter_result"]["filtered_st"]:
        print(f"  {stock['name']}({stock['code']}): {stock['filter_reason']}")

    # 测试买入前检查
    print("\n2. 买入前检查测试")
    print("-" * 80)

    test_stock = {
        "name": "立讯精密",
        "price": 35,
        "market_cap": 600e8,
        "volume": 300000,
        "pct_change": 2.5,
    }
    check_result = control.check_before_buy("002475", "电子", 100000, test_stock)

    print(f"股票: 立讯精密(002475)")
    print(f"可以买入: {check_result['can_buy']}")
    print(f"原因: {check_result['reasons'] if check_result['reasons'] else '无'}")
    print(f"警告: {check_result['warnings'] if check_result['warnings'] else '无'}")
    print(f"建议: {check_result['suggestions']}")

    # 测试交易计划生成
    print("\n3. 交易计划生成测试")
    print("-" * 80)

    plan = control.generate_trading_plan(stock_list, risk_level="medium")

    print(f"总资金: {plan['position_plan']['total_capital']:.0f}元")
    print(f"单股仓位: {plan['position_plan']['position_per_stock'] * 100:.0f}%")
    print(f"\n买入列表:")
    for stock in plan["buy_list"]:
        print(f"  {stock['name']}({stock['code']}):")
        print(f"    价格: {stock['price']:.2f}元")
        print(f"    股数: {stock['shares']}股")
        print(f"    金额: {stock['position_value']:.0f}元")
        print(f"    止损: {stock['stop_loss']:.2f}元")
        print(f"    止盈1: {stock['take_profit_1']:.2f}元")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
