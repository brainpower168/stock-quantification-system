# -*- coding: utf-8 -*-
"""
量化交易系统 - 三层过滤法选股引擎 v2.0
升级：系统化筛选流程，每层输出评分和原因
作者：DuMate AI
日期：2026-05-01
功能：基本面硬指标 + 技术面资金面 + 风险控制
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import warnings

warnings.filterwarnings("ignore")

# 导入特征工程模块
from feature_engineer import FeatureEngineer, DataGenerator


# ==================== 配置区 ====================
CONFIG = {
    "risk_params": {
        "stop_loss": -0.05,  # 止损 -5%
        "take_profit_1": 0.10,  # 止盈 +10%
        "take_profit_2": 0.15,  # 止盈 +15%
        "max_position_per_stock": 0.20,  # 单票最大仓位 20%
        "max_industry_position": 0.30,  # 单行业最大仓位 30%
        "max_total_position": 0.80,  # 总仓位最大 80%
        "max_drawdown": 0.15,  # 最大回撤 15%
    },
    "fundamental_thresholds": {
        "pe_max": 50,  # PE < 50
        "roe_min": 0.10,  # ROE > 10%
        "revenue_growth_min": 0.15,  # 营收增速 > 15%
        "debt_ratio_max": 0.70,  # 负债率 < 70%
    },
    "technical_thresholds": {
        "macd_trend": "bullish",  # MACD金叉
        "ma_position": "above",  # 股价在均线上方
        "volume_ratio_min": 1.5,  # 成交量放大 > 50%
        "rsi_range": (30, 70),  # RSI在30-70之间
    },
    "fund_thresholds": {
        "main_inflow_days": 3,  # 主力资金连续3日净流入
        "daily_inflow_min": 50000000,  # 日均流入 > 5000万
    },
}


# ==================== 第一层：基本面硬指标筛选 ====================
class FundamentalFilter:
    """基本面硬指标筛选器"""

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or CONFIG["fundamental_thresholds"]

    def filter(self, stock_data):
        """
        应用基本面筛选
        :param stock_data: 股票数据字典
        :return: 筛选结果字典
        """
        scores = {}
        reasons = []
        passed = True

        # PE评分（越低越好）
        pe = stock_data.get("pe_ratio", 100)
        if pe > self.thresholds["pe_max"]:
            passed = False
            reasons.append(f"PE={pe:.1f} > {self.thresholds['pe_max']}")
        pe_score = max(0, min(100, (50 - pe) / 50 * 100))
        scores["PE_SCORE"] = pe_score

        # ROE评分（越高越好）
        roe = stock_data.get("roe", 0)
        if roe < self.thresholds["roe_min"]:
            passed = False
            reasons.append(
                f"ROE={roe * 100:.1f}% < {self.thresholds['roe_min'] * 100}%"
            )
        roe_score = min(100, roe / 0.15 * 100)
        scores["ROE_SCORE"] = roe_score

        # 营收增速评分
        revenue_growth = stock_data.get("revenue_growth", 0)
        if revenue_growth < self.thresholds["revenue_growth_min"]:
            passed = False
            reasons.append(
                f"Revenue Growth={revenue_growth * 100:.1f}% < {self.thresholds['revenue_growth_min'] * 100}%"
            )
        rev_score = min(100, revenue_growth / 0.25 * 100)
        scores["REV_GROWTH_SCORE"] = rev_score

        # 负债率评分（越低越好）
        debt_ratio = stock_data.get("debt_ratio", 1)
        if debt_ratio > self.thresholds["debt_ratio_max"]:
            passed = False
            reasons.append(
                f"Debt Ratio={debt_ratio * 100:.1f}% > {self.thresholds['debt_ratio_max'] * 100}%"
            )
        debt_score = max(0, min(100, (0.70 - debt_ratio) / 0.70 * 100))
        scores["DEBT_SCORE"] = debt_score

        # 现金流评分
        cash_flow = stock_data.get("operating_cash_flow", 0)
        cash_score = 100 if cash_flow > 0 else 0
        scores["CASH_FLOW_SCORE"] = cash_score
        if cash_flow <= 0:
            reasons.append(f"Operating Cash Flow <= 0")

        # 计算综合得分
        total_score = sum(scores.values()) / len(scores)

        return {
            "passed": passed,
            "total_score": total_score,
            "scores": scores,
            "reasons": reasons,
            "summary": f"Fundamental Score: {total_score:.1f}/100",
        }


# ==================== 第二层：技术面 + 资金面筛选 ====================
class TechnicalAndFundFilter:
    """技术面 + 资金面筛选器"""

    def __init__(self, tech_thresholds=None, fund_thresholds=None):
        self.tech_thresholds = tech_thresholds or CONFIG["technical_thresholds"]
        self.fund_thresholds = fund_thresholds or CONFIG["fund_thresholds"]

    def filter(self, stock_data, fund_data=None):
        """
        应用技术面 + 资金面筛选
        :param stock_data: 股票数据字典
        :param fund_data: 资金流向数据字典
        :return: 筛选结果字典
        """
        scores = {}
        reasons = []
        passed = True

        # ========== 技术面评分 ==========

        # MACD趋势评分
        macd_trend = stock_data.get("macd_trend", "neutral")
        macd_hist = stock_data.get("macd_hist", 0)
        if macd_hist > 0:
            macd_trend = "bullish"
        elif macd_hist < 0:
            macd_trend = "bearish"

        macd_scores = {"bullish": 100, "neutral": 50, "bearish": 0}
        scores["MACD_SCORE"] = macd_scores.get(macd_trend, 50)
        if macd_trend != "bullish":
            reasons.append(f"MACD trend: {macd_trend}")

        # 均线位置评分
        price = stock_data.get("price", 100)
        ma_20 = stock_data.get("ma_20", price)
        ma_position = "above" if price > ma_20 else "below"

        ma_scores = {"above": 100, "on": 70, "below": 0}
        scores["MA_POSITION_SCORE"] = ma_scores.get(ma_position, 50)
        if ma_position == "below":
            reasons.append(f"Price below MA20")

        # 成交量评分
        volume_ratio = stock_data.get("volume_ratio", 1)
        vol_score = min(100, volume_ratio / 1.5 * 100)
        scores["VOLUME_SCORE"] = vol_score
        if volume_ratio < self.tech_thresholds["volume_ratio_min"]:
            reasons.append(
                f"Volume Ratio={volume_ratio:.2f} < {self.tech_thresholds['volume_ratio_min']}"
            )

        # RSI评分
        rsi_6 = stock_data.get("rsi_6", 50)
        rsi_range = self.tech_thresholds["rsi_range"]
        if rsi_range[0] <= rsi_6 <= rsi_range[1]:
            rsi_score = 100 - abs(rsi_6 - 50)  # 越接近50越好
        else:
            rsi_score = max(0, 50 - abs(rsi_6 - 50))
            if rsi_6 < rsi_range[0]:
                reasons.append(f"RSI={rsi_6:.1f} < {rsi_range[0]} (oversold)")
            else:
                reasons.append(f"RSI={rsi_6:.1f} > {rsi_range[1]} (overbought)")
        scores["RSI_SCORE"] = rsi_score

        # ========== 资金面评分 ==========

        if fund_data:
            # 主力资金流入
            main_inflow = fund_data.get("main_net_inflow", 0)
            inflow_days = fund_data.get("main_inflow_days", 0)

            fund_score = min(100, abs(main_inflow) / 50000000 * 100)
            scores["FUND_SCORE"] = fund_score

            if main_inflow < self.fund_thresholds["daily_inflow_min"]:
                passed = False
                reasons.append(
                    f"Main Inflow={main_inflow / 1e8:.2f}亿 < {self.fund_thresholds['daily_inflow_min'] / 1e8:.2f}亿"
                )

            if inflow_days < self.fund_thresholds["main_inflow_days"]:
                reasons.append(
                    f"Main Inflow Days={inflow_days} < {self.fund_thresholds['main_inflow_days']}"
                )
        else:
            scores["FUND_SCORE"] = 50
            reasons.append("No fund flow data")

        # 计算综合得分
        total_score = sum(scores.values()) / len(scores)

        return {
            "passed": passed,
            "total_score": total_score,
            "scores": scores,
            "reasons": reasons,
            "summary": f"Technical+Fund Score: {total_score:.1f}/100",
        }


# ==================== 第三层：风险控制检查 ====================
class RiskControl:
    """风险控制系统"""

    def __init__(self, params=None):
        self.params = params or CONFIG["risk_params"]
        self.position_history = []

    def check_position(self, current_position, new_trade):
        """
        检查仓位是否超限
        :param current_position: 当前仓位比例
        :param new_trade: 新交易字典 {'symbol', 'size', 'entry_price'}
        :return: 检查结果字典
        """
        checks = {}
        warnings_list = []

        # 检查单票仓位限制
        single_stock_limit = new_trade["size"] <= self.params["max_position_per_stock"]
        checks["single_stock_limit"] = single_stock_limit
        if not single_stock_limit:
            warnings_list.append(
                f"Single stock position {new_trade['size'] * 100:.1f}% > {self.params['max_position_per_stock'] * 100}%"
            )

        # 检查总仓位限制
        total_after = current_position + new_trade["size"]
        total_limit = total_after <= self.params["max_total_position"]
        checks["total_limit"] = total_limit
        if not total_limit:
            warnings_list.append(
                f"Total position {total_after * 100:.1f}% > {self.params['max_total_position'] * 100}%"
            )

        # 计算止损止盈价
        stop_loss_price = new_trade["entry_price"] * (1 + self.params["stop_loss"])
        take_profit_1 = new_trade["entry_price"] * (1 + self.params["take_profit_1"])
        take_profit_2 = new_trade["entry_price"] * (1 + self.params["take_profit_2"])

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "warnings": warnings_list,
            "stop_loss_price": stop_loss_price,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "recommendation": self._get_recommendation(checks),
        }

    def calculate_position_size(
        self, capital, risk_per_trade=0.02, entry_price=None, stop_loss_price=None
    ):
        """
        计算建议仓位大小
        :param capital: 总资金
        :param risk_per_trade: 单笔交易风险比例（默认2%）
        :param entry_price: 入场价
        :param stop_loss_price: 止损价
        :return: 建议仓位比例
        """
        # 简单仓位计算：固定比例
        base_position = self.params["max_position_per_stock"] * 0.5  # 默认10%仓位

        # 如果有止损价，根据风险计算仓位
        if entry_price and stop_loss_price:
            risk_amount = capital * risk_per_trade
            loss_per_share = entry_price - stop_loss_price
            if loss_per_share > 0:
                shares = risk_amount / loss_per_share
                position_value = shares * entry_price
                position_ratio = min(
                    position_value / capital, self.params["max_position_per_stock"]
                )
                return position_ratio

        return base_position

    def _get_recommendation(self, checks):
        """根据检查结果给出建议"""
        recommendations = []

        if not checks.get("single_stock_limit", True):
            recommendations.append("Reduce position size")

        if not checks.get("total_limit", True):
            recommendations.append("Reduce total exposure")

        if not recommendations:
            recommendations.append("Position size OK")

        return recommendations[0] if recommendations else "OK"


# ==================== 三层过滤法选股引擎 ====================
class ThreeLayerStockPicker:
    """三层过滤法选股引擎"""

    def __init__(self):
        self.fundamental_filter = FundamentalFilter()
        self.technical_filter = TechnicalAndFundFilter()
        self.risk_control = RiskControl()
        self.feature_engineer = FeatureEngineer()

    def pick_stocks(self, stock_list, capital=1000000, top_n=5):
        """
        执行三层过滤选股
        :param stock_list: 股票列表 [{'code', 'name', 'sector', ...}, ...]
        :param capital: 总资金
        :param top_n: 返回前N只股票
        :return: 推荐股票列表
        """
        print("=" * 70)
        print("[Three-Layer Stock Picker v2.0]")
        print("=" * 70)
        print(f"Total candidates: {len(stock_list)}")
        print()

        results = []

        for stock in stock_list:
            code = stock["code"]
            name = stock.get("name", code)

            print(f"[Analyzing] {name} ({code})...")

            # 第一层：基本面筛选
            fundamental_result = self.fundamental_filter.filter(stock)
            print(
                f"   Layer 1 (Fundamental): {'PASS' if fundamental_result['passed'] else 'FAIL'} - {fundamental_result['summary']}"
            )

            if not fundamental_result["passed"]:
                print(f"      Reasons: {', '.join(fundamental_result['reasons'][:2])}")
                continue

            # 第二层：技术面+资金面筛选
            fund_data = stock.get("fund_data", None)
            technical_result = self.technical_filter.filter(stock, fund_data)
            print(
                f"   Layer 2 (Technical+Fund): {'PASS' if technical_result['passed'] else 'FAIL'} - {technical_result['summary']}"
            )

            if not technical_result["passed"]:
                print(f"      Reasons: {', '.join(technical_result['reasons'][:2])}")
                continue

            # 第三层：风险控制检查
            entry_price = stock.get("price", 100)
            position_size = self.risk_control.calculate_position_size(capital)

            risk_result = self.risk_control.check_position(
                0, {"symbol": code, "size": position_size, "entry_price": entry_price}
            )
            print(
                f"   Layer 3 (Risk Control): {'PASS' if risk_result['passed'] else 'FAIL'} - {risk_result['recommendation']}"
            )

            if not risk_result["passed"]:
                print(f"      Warnings: {', '.join(risk_result['warnings'][:2])}")
                continue

            # 计算综合得分
            total_score = (
                fundamental_result["total_score"] + technical_result["total_score"]
            ) / 2

            # 提取ML特征
            feature_vector, feature_dict = self.feature_engineer.extract_features(stock)

            results.append(
                {
                    "code": code,
                    "name": name,
                    "sector": stock.get("sector", "Unknown"),
                    "price": entry_price,
                    "fundamental_score": fundamental_result["total_score"],
                    "technical_score": technical_result["total_score"],
                    "total_score": total_score,
                    "position_size": position_size,
                    "stop_loss": risk_result["stop_loss_price"],
                    "take_profit_1": risk_result["take_profit_1"],
                    "take_profit_2": risk_result["take_profit_2"],
                    "feature_vector": feature_vector,
                    "reasons": {
                        "fundamental": fundamental_result["reasons"],
                        "technical": technical_result["reasons"],
                    },
                }
            )

            print(f"   [OK] Total Score: {total_score:.1f}/100")
            print()

        # 按得分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # 返回前N只
        return results[:top_n]

    def generate_trading_plan(self, picks, capital=1000000):
        """
        生成交易计划
        :param picks: 选中的股票列表
        :param capital: 总资金
        :return: 交易计划字典
        """
        plan = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_capital": capital,
            "positions": [],
            "summary": {},
        }

        for pick in picks:
            position_value = capital * pick["position_size"]

            plan["positions"].append(
                {
                    "code": pick["code"],
                    "name": pick["name"],
                    "sector": pick["sector"],
                    "price": pick["price"],
                    "position_size": pick["position_size"],
                    "position_value": position_value,
                    "stop_loss": pick["stop_loss"],
                    "take_profit_1": pick["take_profit_1"],
                    "take_profit_2": pick["take_profit_2"],
                    "fundamental_score": pick["fundamental_score"],
                    "technical_score": pick["technical_score"],
                    "total_score": pick["total_score"],
                }
            )

        # 计算总结
        total_allocation = sum([p["position_size"] for p in plan["positions"]])
        plan["summary"] = {
            "total_allocation": total_allocation,
            "number_of_positions": len(plan["positions"]),
            "average_score": np.mean([p["total_score"] for p in plan["positions"]])
            if plan["positions"]
            else 0,
            "risk_level": "MODERATE" if total_allocation > 0.5 else "CONSERVATIVE",
        }

        return plan


# ==================== 主程序 ====================
def main():
    """主函数 - 三层过滤法演示"""
    print("=" * 70)
    print("[Three-Layer Stock Picker v2.0]")
    print("=" * 70)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 初始化选股引擎
    picker = ThreeLayerStockPicker()

    # 生成测试数据
    print("[Generating test data...]")
    dg = DataGenerator()

    test_stocks = []
    stock_names = {
        "600519": "Moutai",
        "000001": "Ping An Bank",
        "300750": "CATL",
        "601318": "Ping An",
        "000858": "Wuliangye",
        "601888": "China Tourism",
        "002475": "Luxshare",
        "002460": "Ganfeng Lithium",
        "601138": "Foxconn",
        "300059": "East Money",
    }

    for code, name in stock_names.items():
        stock_data = dg.generate_stock_data(code, random_state=hash(code) % 2**32)
        stock_data["code"] = code
        stock_data["name"] = name
        stock_data["sector"] = ["Tech", "Finance", "Energy", "Consumer"][hash(code) % 4]

        # 添加三层过滤所需的额外字段
        stock_data["revenue_growth"] = np.random.uniform(0.10, 0.30)
        stock_data["operating_cash_flow"] = np.random.uniform(1e7, 1e9)

        # 添加资金流向数据
        stock_data["fund_data"] = {
            "main_net_inflow": np.random.uniform(-1e8, 2e8),
            "main_inflow_days": np.random.randint(0, 5),
        }

        test_stocks.append(stock_data)

    print(f"   Generated {len(test_stocks)} stocks")
    print()

    # 执行选股
    picks = picker.pick_stocks(test_stocks, capital=1000000, top_n=5)

    # 显示结果
    print("\n" + "=" * 70)
    print("[TOP 5 PICKS]")
    print("=" * 70)

    for i, pick in enumerate(picks, 1):
        print(f"\n{i}. {pick['name']} ({pick['code']})")
        print(f"   Sector: {pick['sector']}")
        print(f"   Price: {pick['price']:.2f}")
        print(f"   Fundamental Score: {pick['fundamental_score']:.1f}/100")
        print(f"   Technical Score: {pick['technical_score']:.1f}/100")
        print(f"   Total Score: {pick['total_score']:.1f}/100")
        print(f"   Position Size: {pick['position_size'] * 100:.1f}%")
        print(f"   Stop Loss: {pick['stop_loss']:.2f} (-5%)")
        print(f"   Take Profit 1: {pick['take_profit_1']:.2f} (+10%)")
        print(f"   Take Profit 2: {pick['take_profit_2']:.2f} (+15%)")

    # 生成交易计划
    print("\n" + "=" * 70)
    print("[TRADING PLAN]")
    print("=" * 70)

    plan = picker.generate_trading_plan(picks, capital=1000000)

    print(f"\nTotal Capital: {plan['total_capital']:,.0f}")
    print(f"Total Allocation: {plan['summary']['total_allocation'] * 100:.1f}%")
    print(f"Number of Positions: {plan['summary']['number_of_positions']}")
    print(f"Average Score: {plan['summary']['average_score']:.1f}/100")
    print(f"Risk Level: {plan['summary']['risk_level']}")

    print("\n" + "=" * 70)
    print("[OK] Three-Layer Stock Picker test completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
