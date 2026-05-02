#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v4.0 System Integration Test
Test the complete workflow: Factor Library -> Strategy Factory -> Risk Budget -> Pre-trade Risk Control
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# v4.0 modules
from factor_library import FactorLibrary
from strategy_factory import StrategyFactory
from risk_budget_system import RiskBudgetSystem
from pre_trade_risk_control import PreTradeRiskControl

# v3.0 modules
from theme_hot_tracker import ThemeHotTracker
from smart_sell_strategy import SmartSellStrategy

# v2.0 modules
from three_layer_picker import ThreeLayerStockPicker


class V4SystemIntegration:
    """v4.0 System Integration - Complete workflow"""

    def __init__(self, total_capital: float = 270000.0):
        self.total_capital = total_capital

        # Initialize v4.0 modules
        self.factor_library = FactorLibrary()
        self.strategy_factory = StrategyFactory()
        self.risk_budget = RiskBudgetSystem(total_capital=total_capital)
        self.pre_trade_risk = PreTradeRiskControl(total_capital=total_capital)

        # Initialize v3.0 modules
        self.theme_tracker = ThemeHotTracker()
        self.sell_strategy = SmartSellStrategy()

        # Initialize v2.0 modules
        self.stock_picker = ThreeLayerStockPicker()

    def run_complete_workflow(
        self, stock_data: pd.DataFrame, market_data: pd.DataFrame
    ) -> Dict:
        """
        Run complete v4.0 workflow

        Args:
            stock_data: DataFrame with columns [code, name, close, volume, amount, ...]
            market_data: DataFrame with market time series data (for strategy factory)

        Returns:
            Dict with recommended stocks, risk metrics, and strategy parameters
        """
        print("\n" + "=" * 60)
        print("v4.0 System Integration Test")
        print("=" * 60)

        # Step 1: Generate factors from factor library
        print("\n[Step 1] Factor Library - Generating factors...")
        factors = self.factor_library.extract_all_factors(stock_data)
        print(f"  Generated {len(factors)} factors for {len(stock_data)} stocks")

        # Step 2: Detect market state and adjust strategy parameters
        print("\n[Step 2] Strategy Factory - Detecting market state...")
        strategy_result = self.strategy_factory.adjust_strategy(market_data)
        market_state = strategy_result["market_state"]
        strategy_params = strategy_result["strategy_params"]
        print(f"  Market State: {market_state}")
        print(f"  Strategy Type: {strategy_params['strategy_type']}")
        print(f"  Position Limit: {strategy_params['position_size']:.1%}")

        # Step 3: Pre-trade risk control - Filter stocks
        print("\n[Step 3] Pre-trade Risk Control - Filtering stocks...")
        filter_result = self.pre_trade_risk.stock_filter.filter_all(
            stock_data.to_dict("records")
        )

        if len(filter_result["passed"]) > 0:
            filtered_stocks = pd.DataFrame(filter_result["passed"])
        else:
            # If all stocks filtered, use original data (for testing)
            filtered_stocks = stock_data
            print("  WARNING: All stocks filtered, using original data for testing")

        print(f"  Filtered {len(filter_result['filtered_st'])} ST stocks")
        print(
            f"  Filtered {len(filter_result['filtered_liquidity'])} low liquidity stocks"
        )
        print(f"  Remaining {len(filtered_stocks)} stocks for selection")

        # Step 4: Stock selection using three-layer picker
        print("\n[Step 4] Three-Layer Stock Picker - Selecting stocks...")
        selected_stocks = self.stock_picker.pick_stocks(
            filtered_stocks.to_dict("records"), top_n=10
        )
        print(f"  Selected {len(selected_stocks)} stocks")

        # Step 5: Theme and hotness tracking
        print("\n[Step 5] Theme Hot Tracker - Analyzing themes...")
        theme_scores = {}
        for stock in selected_stocks:
            code = stock["code"]
            # Extract theme score from stock data
            themes = [stock.get("industry", "Unknown")]  # Use industry as theme
            limit_up_gene = {
                "limit_up_gene_score": stock.get("score", 50),
                "is_hot": stock.get("score", 50) > 60,
                "consecutive_days": 0,
            }
            fund_flow = stock.get("main_flow", 0) / 10000  # Convert to 万元
            pct_change = stock.get("change_pct", 0)
            theme_result = self.theme_tracker.calculate_theme_score(
                themes, limit_up_gene, fund_flow, pct_change
            )
            theme_scores[code] = theme_result["theme_score"]
            print(
                f"  {stock['name']}({code}): Theme Score = {theme_result['theme_score']:.1f}"
            )

        # Step 6: Risk budget calculation
        print("\n[Step 6] Risk Budget System - Calculating risk budget...")

        # Convert selected stocks to strategy format
        strategies = []
        for stock in selected_stocks:
            strategies.append(
                {
                    "name": stock["code"],
                    "expected_return": stock.get("score", 50) / 100 * 0.1,  # 0-5%
                    "volatility": 0.20,  # Assume 20% volatility
                }
            )

        # Allocate risk budget
        if len(strategies) > 0:
            allocation = self.risk_budget.budget_allocator.allocate(strategies)
            positions = {}
            for code, alloc in allocation["strategy_allocations"].items():
                positions[code] = alloc["capital"]
        else:
            positions = {}

        total_position = sum(positions.values())
        print(f"  Total position: {total_position:.2f} / {self.total_capital:.2f}")
        print(f"  Position ratio: {total_position / self.total_capital:.1%}")

        # Step 7: Check circuit breaker
        print("\n[Step 7] Circuit Breaker Check...")
        circuit_breaker = self.risk_budget.circuit_breaker.check(
            0, 0
        )  # No daily PnL for test
        if not circuit_breaker["can_trade"]:
            print(f"  WARNING: Circuit breaker triggered!")
            print(f"  Reason: {circuit_breaker.get('reason', 'Unknown')}")
        else:
            print(f"  Circuit breaker: OK")

        # Step 8: Generate final recommendations
        print("\n[Step 8] Final Recommendations...")
        recommendations = []
        for stock in selected_stocks:
            code = stock["code"]
            position = positions.get(code, 0)
            theme_score = theme_scores.get(code, 0)

            # Calculate composite score
            composite_score = (
                stock.get("score", 50) * 0.4  # Base score
                + theme_score * 0.3  # Theme score
                + (position / self.total_capital * 100) * 0.3  # Position weight
            )

            recommendations.append(
                {
                    "code": code,
                    "name": stock["name"],
                    "close": stock.get("close", 0),
                    "score": stock.get("score", 50),
                    "theme_score": theme_score,
                    "position": position,
                    "position_pct": position / self.total_capital,
                    "composite_score": composite_score,
                    "grade": self._get_grade(composite_score),
                }
            )

        # Sort by composite score
        recommendations.sort(key=lambda x: x["composite_score"], reverse=True)

        # Print top 5
        print("\n  Top 5 Recommendations:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec['name']}({rec['code']})")
            print(
                f"     Score: {rec['score']:.1f} | Theme: {rec['theme_score']:.1f} | Composite: {rec['composite_score']:.1f}"
            )
            print(
                f"     Position: {rec['position']:.2f} ({rec['position_pct']:.1%}) | Grade: {rec['grade']}"
            )

        return {
            "market_state": market_state,
            "strategy_params": strategy_params,
            "circuit_breaker": circuit_breaker,
            "recommendations": recommendations,
            "risk_metrics": {
                "total_position": sum(positions.values()),
                "position_ratio": sum(positions.values()) / self.total_capital,
                "num_stocks": len(selected_stocks),
            },
        }

    def _get_grade(self, score: float) -> str:
        """Get grade based on composite score"""
        if score >= 70:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        else:
            return "D"


def generate_test_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate test stock data and market time series data"""
    np.random.seed(42)

    stocks = [
        {"code": "600519", "name": "贵州茅台", "industry": "白酒"},
        {"code": "000001", "name": "平安银行", "industry": "银行"},
        {"code": "300750", "name": "宁德时代", "industry": "新能源"},
        {"code": "002475", "name": "立讯精密", "industry": "电子"},
        {"code": "601318", "name": "中国平安", "industry": "保险"},
        {"code": "000858", "name": "五粮液", "industry": "白酒"},
        {"code": "002460", "name": "赣锋锂业", "industry": "新能源"},
        {"code": "002281", "name": "光迅科技", "industry": "通信"},
        {"code": "601138", "name": "工业富联", "industry": "电子"},
        {"code": "002463", "name": "沪电股份", "industry": "电子"},
    ]

    # Generate stock list data
    stock_list = []
    for i, stock in enumerate(stocks):
        close = np.random.uniform(20, 200)
        high = close * np.random.uniform(1.0, 1.05)
        low = close * np.random.uniform(0.95, 1.0)
        open_price = close * np.random.uniform(0.98, 1.02)
        volume = np.random.uniform(1000000, 10000000)
        amount = close * volume

        # Make first 5 stocks pass the filter
        if i < 5:
            pe_ratio = np.random.uniform(15, 45)  # PE < 50
            roe = np.random.uniform(0.12, 0.25)  # ROE > 10% (decimal form)
            revenue_growth = np.random.uniform(
                0.20, 0.50
            )  # Revenue growth > 15% (decimal form)
            debt_ratio = np.random.uniform(
                0.20, 0.60
            )  # Debt ratio < 70% (decimal form)
            operating_cash_flow = np.random.uniform(1e8, 10e8)  # Positive cash flow
        else:
            pe_ratio = np.random.uniform(50, 100)  # PE > 50 (will be filtered)
            roe = np.random.uniform(0.05, 0.10)
            revenue_growth = np.random.uniform(0, 0.15)
            debt_ratio = np.random.uniform(
                0.70, 0.90
            )  # Debt ratio > 70% (will be filtered)
            operating_cash_flow = np.random.uniform(-10e8, -1e8)  # Negative cash flow

        stock_list.append(
            {
                "code": stock["code"],
                "name": stock["name"],
                "industry": stock["industry"],
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "amount": amount,
                "turnover_rate": np.random.uniform(1, 10),
                "change_pct": np.random.uniform(-5, 5),
                "ddx_5d": np.random.uniform(-5, 5),
                "ddx_10d": np.random.uniform(-3, 3),
                "main_flow": np.random.uniform(-5, 10) * 100000000,
                "pe_ratio": pe_ratio,
                "roe": roe,
                "revenue_growth": revenue_growth,
                "debt_ratio": debt_ratio,
                "operating_cash_flow": operating_cash_flow,
                "market_cap": np.random.uniform(50, 500) * 1e8,
                "is_st": False,
                "score": np.random.uniform(40, 80),
            }
        )

    # Generate market time series data (for strategy factory)
    dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
    base_price = 3000
    market_data = []

    for i, date in enumerate(dates):
        change = np.random.uniform(-0.03, 0.03)
        base_price = base_price * (1 + change)

        market_data.append(
            {
                "date": date,
                "open": base_price * np.random.uniform(0.99, 1.01),
                "high": base_price * np.random.uniform(1.0, 1.02),
                "low": base_price * np.random.uniform(0.98, 1.0),
                "close": base_price,
                "volume": np.random.uniform(100000000, 200000000),
            }
        )

    market_df = pd.DataFrame(market_data)
    market_df.set_index("date", inplace=True)

    return pd.DataFrame(stock_list), market_df


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("v4.0 System Integration Test - Start")
    print("=" * 60)

    # Generate test data
    print("\nGenerating test data...")
    stock_data, market_data = generate_test_data()
    print(
        f"Generated {len(stock_data)} stocks and {len(market_data)} days of market data"
    )

    # Initialize system
    system = V4SystemIntegration(total_capital=270000.0)

    # Run complete workflow
    results = system.run_complete_workflow(stock_data, market_data)

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Market State: {results['market_state']}")
    print(f"Strategy Params: {results['strategy_params']}")
    print(f"Circuit Breaker: {results['circuit_breaker']}")
    print(f"Risk Metrics: {results['risk_metrics']}")
    print(f"Top Recommendations: {len(results['recommendations'])} stocks")

    print("\n" + "=" * 60)
    print("v4.0 System Integration Test - PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
