# -*- coding: utf-8 -*-
"""
量化交易系统 - 回测模块 v2.0
升级：交易成本 + 绩效评估 + 风险调整后收益
作者：DuMate AI
日期：2026-05-01
功能：历史数据回测 + 绩效评估 + Alpha/Beta计算
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import warnings

warnings.filterwarnings("ignore")


# ==================== 配置区 ====================
CONFIG = {
    "backtest_params": {
        "initial_capital": 1000000,  # 初始资金
        "commission_rate": 0.0003,  # 佣金费率（万三）
        "stamp_duty_rate": 0.001,  # 印花税（千一，卖出）
        "transfer_fee_rate": 0.00005,  # 过户费（万分之0.5）
        "min_commission": 5,  # 最低佣金 5 元
        "max_drawdown_limit": 0.15,  # 最大回撤限制 15%
        "risk_free_rate": 0.03,  # 无风险利率 3%
    }
}


# ==================== 交易成本计算器 ====================
class TransactionCostCalculator:
    """交易成本计算器"""

    def __init__(self, params=None):
        self.params = params or CONFIG["backtest_params"]

    def calculate_buy_cost(self, amount):
        """
        计算买入成本
        :param amount: 买入金额
        :return: 总成本（含佣金、过户费）
        """
        # 佣金
        commission = max(
            amount * self.params["commission_rate"], self.params["min_commission"]
        )

        # 过户费
        transfer_fee = amount * self.params["transfer_fee_rate"]

        # 总成本
        total_cost = amount + commission + transfer_fee

        return {
            "amount": amount,
            "commission": commission,
            "transfer_fee": transfer_fee,
            "total_cost": total_cost,
        }

    def calculate_sell_cost(self, amount):
        """
        计算卖出成本
        :param amount: 卖出金额
        :return: 总成本（含佣金、印花税、过户费）
        """
        # 佣金
        commission = max(
            amount * self.params["commission_rate"], self.params["min_commission"]
        )

        # 印花税（仅卖出）
        stamp_duty = amount * self.params["stamp_duty_rate"]

        # 过户费
        transfer_fee = amount * self.params["transfer_fee_rate"]

        # 总成本
        total_cost = commission + stamp_duty + transfer_fee

        return {
            "amount": amount,
            "commission": commission,
            "stamp_duty": stamp_duty,
            "transfer_fee": transfer_fee,
            "total_cost": total_cost,
        }

    def calculate_round_trip_cost(self, buy_amount, sell_amount):
        """
        计算往返交易成本
        :param buy_amount: 买入金额
        :param sell_amount: 卖出金额
        :return: 总成本
        """
        buy_cost = self.calculate_buy_cost(buy_amount)
        sell_cost = self.calculate_sell_cost(sell_amount)

        return {
            "buy_cost": buy_cost,
            "sell_cost": sell_cost,
            "total_cost": buy_cost["total_cost"] + sell_cost["total_cost"],
            "cost_ratio": (buy_cost["total_cost"] + sell_cost["total_cost"])
            / buy_amount,
        }


# ==================== 回测引擎 ====================
class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.positions = {}  # 持仓记录
        self.trades = []  # 交易记录
        self.portfolio_history = []  # 组合价值历史
        self.benchmark_history = []  # 基准对比
        self.cost_calculator = TransactionCostCalculator()

    def run_backtest(self, stock_list, start_date, end_date, capital=None):
        """
        执行回测
        :param stock_list: 股票列表 [{'code','name'}, ...]
        :param start_date: 开始日期 '2024-01-01'
        :param end_date: 结束日期 '2024-12-31'
        :param capital: 初始资金
        :return: 回测结果字典
        """
        if capital is None:
            capital = self.initial_capital

        print(f"[Backtest Engine v2.0]")
        print(f"   Stocks: {len(stock_list)}")
        print(f"   Period: {start_date} ~ {end_date}")
        print(f"   Initial Capital: {capital:,.0f}")
        print()

        # 初始化持仓
        for stock in stock_list:
            self.positions[stock["code"]] = {
                "name": stock["name"],
                "cost_price": 0,
                "shares": 0,
                "market_value": 0,
                "profit_pct": 0,
                "buy_count": 0,
                "sell_count": 0,
                "total_cost": 0,
            }

        # 生成交易日列表
        trade_days = self._generate_trade_days(start_date, end_date)
        print(f"   Trading Days: {len(trade_days)}")
        print()

        # 模拟每日行情
        daily_returns = self._simulate_daily_returns(len(trade_days), stock_list)

        # 执行策略
        portfolio_value = capital
        cash = capital
        total_transaction_cost = 0

        for day_idx, date in enumerate(trade_days):
            # 简单策略：第一天买入所有股票，最后一天卖出
            if day_idx == 0:
                # 买入
                position_per_stock = capital * 0.8 / len(stock_list)  # 80%仓位
                for stock in stock_list:
                    code = stock["code"]
                    price = np.random.uniform(10, 200)  # 模拟价格

                    # 计算买入成本
                    buy_result = self.cost_calculator.calculate_buy_cost(
                        position_per_stock
                    )
                    shares = int(position_per_stock / price)

                    # 更新持仓
                    self.positions[code]["cost_price"] = price
                    self.positions[code]["shares"] = shares
                    self.positions[code]["market_value"] = shares * price
                    self.positions[code]["buy_count"] = 1
                    self.positions[code]["total_cost"] = buy_result["total_cost"]

                    cash -= buy_result["total_cost"]
                    total_transaction_cost += buy_result["total_cost"]

                    # 记录交易
                    self.trades.append(
                        {
                            "date": date,
                            "code": code,
                            "action": "BUY",
                            "price": price,
                            "shares": shares,
                            "amount": position_per_stock,
                            "cost": buy_result["total_cost"],
                        }
                    )

            # 计算当日持仓市值
            daily_pnl = 0
            for code, pos in self.positions.items():
                if pos["shares"] > 0:
                    daily_return = daily_returns[day_idx].get(code, 0)
                    pos_change = pos["shares"] * pos["cost_price"] * daily_return
                    daily_pnl += pos_change
                    pos["market_value"] += pos_change

            # 更新总资产
            portfolio_value = cash + sum(
                [pos["market_value"] for pos in self.positions.values()]
            )

            # 记录组合价值
            self.portfolio_history.append(
                {
                    "date": date,
                    "value": portfolio_value,
                    "cash": cash,
                    "market_value": portfolio_value - cash,
                    "daily_pnl": daily_pnl,
                    "daily_return": daily_pnl / max(portfolio_value, 1),
                }
            )

            # 最后一天卖出
            if day_idx == len(trade_days) - 1:
                for code, pos in self.positions.items():
                    if pos["shares"] > 0:
                        price = pos["cost_price"] * (1 + np.random.uniform(-0.2, 0.3))
                        sell_amount = pos["shares"] * price

                        # 计算卖出成本
                        sell_result = self.cost_calculator.calculate_sell_cost(
                            sell_amount
                        )

                        cash += sell_amount - sell_result["total_cost"]
                        total_transaction_cost += sell_result["total_cost"]

                        # 记录交易
                        self.trades.append(
                            {
                                "date": date,
                                "code": code,
                                "action": "SELL",
                                "price": price,
                                "shares": pos["shares"],
                                "amount": sell_amount,
                                "cost": sell_result["total_cost"],
                                "profit": sell_amount
                                - pos["shares"] * pos["cost_price"],
                            }
                        )

        # 计算最终结果
        final_value = cash
        total_return = (final_value - capital) / capital

        return {
            "success": True,
            "initial_capital": capital,
            "final_value": final_value,
            "total_return": total_return,
            "holding_days": len(trade_days),
            "annualized_return": self._calculate_annual_return(
                total_return, len(trade_days)
            ),
            "sharpe_ratio": self._calculate_sharpe(),
            "max_drawdown": self._calculate_max_drawdown(),
            "win_rate": self._calculate_win_rate(),
            "trade_count": len(self.trades),
            "total_transaction_cost": total_transaction_cost,
            "transaction_cost_ratio": total_transaction_cost / capital,
        }

    def _generate_trade_days(self, start_date, end_date):
        """生成交易日列表"""
        dates = []
        current = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        while current <= end:
            if current.weekday() < 5:
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return dates

    def _simulate_daily_returns(self, days, stock_list):
        """模拟每日收益率"""
        np.random.seed(42)

        daily_volatility = 0.25 / np.sqrt(252)
        returns = []

        for i in range(days):
            day_returns = {}
            for stock in stock_list:
                ret = np.random.normal(0.0003, daily_volatility)
                day_returns[stock["code"]] = ret
            returns.append(day_returns)

        return returns

    def _calculate_annual_return(self, total_return, holding_days):
        """计算年化收益率"""
        years = holding_days / 365.25
        if years <= 0:
            return 0
        annual_return = (1 + total_return) ** (1 / years) - 1
        return annual_return

    def _calculate_sharpe(self):
        """计算夏普比率"""
        if not self.portfolio_history:
            return 0

        returns = [h["daily_return"] for h in self.portfolio_history]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        risk_free_rate = CONFIG["backtest_params"]["risk_free_rate"] / 252
        sharpe_ratio = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
        return sharpe_ratio

    def _calculate_max_drawdown(self):
        """计算最大回撤"""
        if not self.portfolio_history:
            return 0

        values = [h["value"] for h in self.portfolio_history]
        max_value = values[0]
        max_drawdown = 0

        for value in values:
            if value > max_value:
                max_value = value
            drawdown = (value - max_value) / max_value
            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def _calculate_win_rate(self):
        """计算胜率"""
        if not self.trades:
            return 0

        profits = [t.get("profit", 0) for t in self.trades if t["action"] == "SELL"]
        if not profits:
            return 0

        wins = sum(1 for p in profits if p > 0)
        return wins / len(profits)


# ==================== 绩效评估器 ====================
class PerformanceEvaluator:
    """绩效评估器"""

    @staticmethod
    def calculate_alpha_beta(portfolio_returns, benchmark_returns):
        """
        计算Alpha和Beta
        :param portfolio_returns: 组合收益率序列
        :param benchmark_returns: 基准收益率序列
        :return: Alpha, Beta
        """
        if len(portfolio_returns) != len(benchmark_returns):
            return 0, 1

        # 计算协方差矩阵
        cov_matrix = np.cov(portfolio_returns, benchmark_returns)
        cov = cov_matrix[0, 1]
        var_benchmark = np.var(benchmark_returns)

        # Beta = Cov(Rp, Rm) / Var(Rm)
        beta = cov / var_benchmark if var_benchmark > 0 else 1

        # Alpha = Rp - [Rf + Beta * (Rm - Rf)]
        risk_free_rate = CONFIG["backtest_params"]["risk_free_rate"] / 252
        mean_portfolio = np.mean(portfolio_returns)
        mean_benchmark = np.mean(benchmark_returns)

        alpha = mean_portfolio - (
            risk_free_rate + beta * (mean_benchmark - risk_free_rate)
        )

        # 年化Alpha
        alpha_annual = alpha * 252

        return alpha_annual, beta

    @staticmethod
    def calculate_information_ratio(excess_returns):
        """
        计算信息比率
        :param excess_returns: 超额收益序列
        :return: 信息比率
        """
        if not excess_returns:
            return 0

        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)

        if std_excess == 0:
            return 0

        # 年化信息比率
        ir = mean_excess / std_excess * np.sqrt(252)
        return ir

    @staticmethod
    def calculate_sortino_ratio(returns, target_return=0):
        """
        计算索提诺比率
        :param returns: 收益率序列
        :param target_return: 目标收益率
        :return: 索提诺比率
        """
        if not returns:
            return 0

        mean_return = np.mean(returns)

        # 计算下行标准差
        downside_returns = [r for r in returns if r < target_return]
        if not downside_returns:
            return float("inf")

        downside_std = np.std(downside_returns)

        if downside_std == 0:
            return 0

        risk_free_rate = CONFIG["backtest_params"]["risk_free_rate"] / 252
        sortino = (mean_return - risk_free_rate) / downside_std * np.sqrt(252)

        return sortino

    @staticmethod
    def evaluate_risk_adjusted_return(metrics):
        """
        综合评估风险调整后收益
        :param metrics: 指标字典
        :return: 评估结果字典
        """
        scores = {}

        # 夏普比率评分（越高越好）
        sharpe = metrics.get("sharpe_ratio", 0)
        scores["Sharpe Ratio"] = min(10, max(0, sharpe * 3))

        # 最大回撤评分（越小越好）
        max_dd = abs(metrics.get("max_drawdown", 0.3))
        scores["Max Drawdown"] = max(0, min(10, (0.3 - max_dd) / 0.3 * 10))

        # 胜率评分
        win_rate = metrics.get("win_rate", 0)
        scores["Win Rate"] = min(10, win_rate * 10)

        # 年化收益评分
        annual_return = metrics.get("annualized_return", 0)
        scores["Annual Return"] = min(10, max(0, annual_return * 20))

        # 交易成本评分（越低越好）
        cost_ratio = metrics.get("transaction_cost_ratio", 0.02)
        scores["Transaction Cost"] = max(0, min(10, (0.03 - cost_ratio) / 0.03 * 10))

        # 综合评分
        total_score = sum(scores.values()) / len(scores)

        # 评级
        if total_score >= 8:
            grade = "A+"
        elif total_score >= 7:
            grade = "A"
        elif total_score >= 6:
            grade = "B+"
        elif total_score >= 5:
            grade = "B"
        elif total_score >= 4:
            grade = "C+"
        else:
            grade = "C"

        return {
            "total_score": total_score,
            "grade": grade,
            "scores": scores,
            "recommendation": PerformanceEvaluator._get_recommendation(total_score),
        }

    @staticmethod
    def _get_recommendation(score):
        """根据评分给出建议"""
        if score >= 8:
            return "Excellent strategy, consider increasing allocation"
        elif score >= 7:
            return "Good strategy, maintain current allocation"
        elif score >= 6:
            return "Average strategy, optimize parameters"
        elif score >= 5:
            return "Below average, consider adjustments"
        else:
            return "Poor performance, redesign strategy"


# ==================== 主程序 ====================
def main():
    """主函数 - 回测演示"""
    print("=" * 70)
    print("[Backtest Engine v2.0]")
    print("=" * 70)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 创建回测引擎
    engine = BacktestEngine(initial_capital=1000000)

    # 测试股票列表
    stock_list = [
        {"code": "600519", "name": "Moutai"},
        {"code": "000001", "name": "Ping An Bank"},
        {"code": "300750", "name": "CATL"},
        {"code": "601318", "name": "Ping An"},
        {"code": "000858", "name": "Wuliangye"},
    ]

    # 回测参数
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    # 执行回测
    print("[Running backtest...]")
    results = engine.run_backtest(stock_list, start_date, end_date)

    # 绩效评估
    print("\n[Performance Evaluation...]")
    evaluation = PerformanceEvaluator.evaluate_risk_adjusted_return(results)

    # 显示结果
    print("\n" + "=" * 70)
    print("[BACKTEST RESULTS]")
    print("=" * 70)
    print(f"\nInitial Capital: {results['initial_capital']:,.0f}")
    print(f"Final Value: {results['final_value']:,.0f}")
    print(f"Total Return: {results['total_return'] * 100:.2f}%")
    print(f"Annualized Return: {results['annualized_return'] * 100:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {results['max_drawdown'] * 100:.2f}%")
    print(f"Win Rate: {results['win_rate'] * 100:.1f}%")
    print(f"Holding Days: {results['holding_days']}")
    print(f"Trade Count: {results['trade_count']}")
    print(f"Total Transaction Cost: {results['total_transaction_cost']:,.0f}")
    print(f"Transaction Cost Ratio: {results['transaction_cost_ratio'] * 100:.2f}%")

    # 绩效评估结果
    print("\n" + "=" * 70)
    print("[PERFORMANCE EVALUATION]")
    print("=" * 70)
    print(f"\nTotal Score: {evaluation['total_score']:.1f}/10")
    print(f"Grade: {evaluation['grade']}")
    print(f"\nDetailed Scores:")
    for key, value in evaluation["scores"].items():
        print(f"   {key}: {value:.1f}/10")
    print(f"\nRecommendation: {evaluation['recommendation']}")

    print("\n" + "=" * 70)
    print("[OK] Backtest completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
