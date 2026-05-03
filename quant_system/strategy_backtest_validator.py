# -*- coding: utf-8 -*-
"""
策略回测验证系统
- 回测7种实战策略
- 计算胜率、收益率、最大回撤、夏普比率
- 生成策略对比报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import json
from pathlib import Path

warnings.filterwarnings("ignore")

# 导入回测引擎
# 注意：JIT加速引擎不兼容pandas，使用简单回测
HAS_JIT = False


class StrategyBacktestValidator:
    """策略回测验证器"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.results = {}

    def run_all_strategies(
        self, data: pd.DataFrame, strategies: List[str] = None
    ) -> Dict:
        """
        运行所有策略回测

        参数:
            data: OHLCV数据，需包含 open, high, low, close, volume
            strategies: 策略列表，默认运行全部

        返回:
            各策略回测结果
        """
        if strategies is None:
            strategies = [
                "ma_cross",  # MA金叉策略
                "bollinger_band",  # 布林带策略
                "rsi_reversal",  # RSI反转策略
                "tail_market",  # 尾盘30分钟策略
                "strategy_2560",  # 2560战法
                "overnight_holding",  # 一夜持股法
                "breakout_signal",  # 突破信号策略
            ]

        for strategy_name in strategies:
            print(f"\n回测策略: {strategy_name}")
            print("-" * 60)

            try:
                result = self._backtest_strategy(data, strategy_name)
                self.results[strategy_name] = result

                print(f"总收益率: {result['total_return']:.2%}")
                print(f"年化收益: {result['annual_return']:.2%}")
                print(f"最大回撤: {result['max_drawdown']:.2%}")
                print(f"夏普比率: {result['sharpe_ratio']:.2f}")
                print(f"胜率: {result['win_rate']:.2%}")
                print(f"交易次数: {result['trade_count']}")

            except Exception as e:
                print(f"策略 {strategy_name} 回测失败: {e}")
                self.results[strategy_name] = {"error": str(e)}

        return self.results

    def _backtest_strategy(self, data: pd.DataFrame, strategy_name: str) -> Dict:
        """回测单个策略"""

        # 根据策略名称选择策略函数
        strategy_func = self._get_strategy_func(strategy_name)

        # 运行回测
        if HAS_JIT:
            engine = HighPerformanceBacktestEngine()
            result = engine.run_backtest(data, strategy_func, self.initial_capital)
        else:
            result = self._simple_backtest(data, strategy_func)

        return result

    def _get_strategy_func(self, strategy_name: str):
        """获取策略函数"""

        strategies = {
            "ma_cross": self._ma_cross_strategy,
            "bollinger_band": self._bollinger_band_strategy,
            "rsi_reversal": self._rsi_reversal_strategy,
            "tail_market": self._tail_market_strategy,
            "strategy_2560": self._strategy_2560,
            "overnight_holding": self._overnight_holding_strategy,
            "breakout_signal": self._breakout_signal_strategy,
        }

        if strategy_name not in strategies:
            raise ValueError(f"未知策略: {strategy_name}")

        return strategies[strategy_name]

    # ==================== 策略实现 ====================

    def _ma_cross_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        MA金叉策略
        - 买入：MA5上穿MA20
        - 卖出：MA5下穿MA20
        """
        signals = pd.Series(0, index=data.index)

        # 计算均线
        ma5 = data["close"].rolling(5).mean()
        ma20 = data["close"].rolling(20).mean()

        # 金叉信号
        golden_cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
        death_cross = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))

        signals[golden_cross] = 1  # 买入
        signals[death_cross] = -1  # 卖出

        return signals

    def _bollinger_band_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        布林带策略（均值回归）
        - 买入：价格跌破下轨
        - 卖出：价格突破上轨
        """
        signals = pd.Series(0, index=data.index)

        # 计算布林带
        ma20 = data["close"].rolling(20).mean()
        std20 = data["close"].rolling(20).std()

        upper_band = ma20 + 2 * std20
        lower_band = ma20 - 2 * std20

        # 信号
        buy_signal = data["close"] < lower_band
        sell_signal = data["close"] > upper_band

        signals[buy_signal] = 1
        signals[sell_signal] = -1

        return signals

    def _rsi_reversal_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        RSI反转策略
        - 买入：RSI < 30（超卖）
        - 卖出：RSI > 70（超买）
        """
        signals = pd.Series(0, index=data.index)

        # 计算RSI
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # 信号
        buy_signal = rsi < 30
        sell_signal = rsi > 70

        signals[buy_signal] = 1
        signals[sell_signal] = -1

        return signals

    def _tail_market_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        尾盘30分钟策略
        - 买入：涨幅3%-5% + 量比>1 + 换手率5%-10%
        - 卖出：次日开盘卖出
        """
        signals = pd.Series(0, index=data.index)

        # 计算涨幅
        change_pct = data["close"].pct_change() * 100

        # 计算量比（当日成交量 / 5日平均成交量）
        avg_volume = data["volume"].rolling(5).mean()
        volume_ratio = data["volume"] / avg_volume

        # 计算换手率（简化，用成交量占比代替）
        turnover_rate = data["volume"] / data["volume"].rolling(20).mean()

        # 买入条件
        buy_condition = (
            (change_pct >= 3)
            & (change_pct <= 5)  # 涨幅3%-5%
            & (volume_ratio > 1)  # 量比>1
            & (turnover_rate >= 0.5)
            & (turnover_rate <= 2)  # 换手率适中
        )

        signals[buy_condition] = 1

        # 次日卖出（简化处理：持有1天后卖出）
        sell_indices = signals[signals == 1].index + timedelta(days=1)
        for idx in sell_indices:
            if idx in signals.index:
                signals[idx] = -1

        return signals

    def _strategy_2560(self, data: pd.DataFrame) -> pd.Series:
        """
        2560战法
        - 买入：股价回踩25日均线 + 5日均量线在60日均量线之上
        - 卖出：跌破25日均线3%
        """
        signals = pd.Series(0, index=data.index)

        # 计算25日均线
        ma25 = data["close"].rolling(25).mean()

        # 计算均量线
        ma5_vol = data["volume"].rolling(5).mean()
        ma60_vol = data["volume"].rolling(60).mean()

        # 回踩25日均线
        touch_ma25 = abs(data["close"] - ma25) / ma25 < 0.02  # 距离25日均线2%以内

        # 5日均量线在60日均量线之上
        volume_condition = ma5_vol > ma60_vol

        # 买入信号
        buy_signal = touch_ma25 & volume_condition

        # 卖出信号：跌破25日均线3%
        sell_signal = data["close"] < ma25 * 0.97

        signals[buy_signal] = 1
        signals[sell_signal] = -1

        return signals

    def _overnight_holding_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        一夜持股法
        - 买入：尾盘买入（涨幅3%-5% + 量比>1）
        - 卖出：次日开盘卖出
        """
        signals = pd.Series(0, index=data.index)

        # 计算涨幅
        change_pct = data["close"].pct_change() * 100

        # 计算量比
        avg_volume = data["volume"].rolling(5).mean()
        volume_ratio = data["volume"] / avg_volume

        # 买入条件（简化版）
        buy_condition = (
            (change_pct >= 2)
            & (change_pct <= 5)  # 涨幅2%-5%
            & (volume_ratio > 1)  # 量比>1
        )

        signals[buy_condition] = 1

        # 次日卖出
        sell_indices = signals[signals == 1].index + timedelta(days=1)
        for idx in sell_indices:
            if idx in signals.index:
                signals[idx] = -1

        return signals

    def _breakout_signal_strategy(self, data: pd.DataFrame) -> pd.Series:
        """
        突破信号策略
        - 买入：突破20日高点
        - 卖出：跌破10日低点
        """
        signals = pd.Series(0, index=data.index)

        # 计算20日高点
        high_20 = data["high"].rolling(20).max()

        # 计算10日低点
        low_10 = data["low"].rolling(10).min()

        # 突破信号
        breakout = data["close"] > high_20.shift(1)
        breakdown = data["close"] < low_10.shift(1)

        signals[breakout] = 1
        signals[breakdown] = -1

        return signals

    # ==================== 简单回测引擎 ====================

    def _simple_backtest(self, data: pd.DataFrame, strategy_func) -> Dict:
        """简单回测（无JIT加速）"""

        # 生成信号
        signals = strategy_func(data)

        # 计算收益率
        returns = data["close"].pct_change()

        # 模拟交易
        position = 0
        cash = self.initial_capital
        shares = 0
        trades = []
        equity_curve = []

        for i, (date, signal) in enumerate(signals.items()):
            price = data.loc[date, "close"]

            # 买入
            if signal == 1 and position == 0:
                shares = cash // price
                if shares > 0:
                    cash -= shares * price
                    position = 1
                    trades.append(
                        {"date": date, "type": "buy", "price": price, "shares": shares}
                    )

            # 卖出
            elif signal == -1 and position == 1:
                cash += shares * price
                position = 0
                trades.append(
                    {"date": date, "type": "sell", "price": price, "shares": shares}
                )
                shares = 0

            # 记录权益
            equity = cash + shares * price
            equity_curve.append({"date": date, "equity": equity})

        # 最后如果还持仓，按收盘价清仓
        if position == 1:
            last_price = data["close"].iloc[-1]
            cash += shares * last_price
            shares = 0
            position = 0

        # 计算指标
        final_value = cash
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # 年化收益
        days = (data.index[-1] - data.index[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0

        # 最大回撤
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_df["peak"] = equity_df["equity"].cummax()
            equity_df["drawdown"] = (
                equity_df["equity"] - equity_df["peak"]
            ) / equity_df["peak"]
            max_drawdown = equity_df["drawdown"].min()
        else:
            max_drawdown = 0

        # 夏普比率
        if len(returns) > 0:
            excess_returns = returns - 0.03 / 252  # 无风险利率3%
            sharpe_ratio = (
                np.sqrt(252) * excess_returns.mean() / excess_returns.std()
                if excess_returns.std() > 0
                else 0
            )
        else:
            sharpe_ratio = 0

        # 胜率
        winning_trades = 0
        total_trades = len(trades) // 2

        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy_trade = trades[i]
                sell_trade = trades[i + 1]
                if sell_trade["price"] > buy_trade["price"]:
                    winning_trades += 1

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "trade_count": len(trades),
            "final_value": final_value,
            "trades": trades,
            "equity_curve": equity_curve,
        }

    # ==================== 报告生成 ====================

    def generate_report(self, output_path: str = None) -> str:
        """生成策略对比报告"""

        if not self.results:
            return "没有回测结果"

        report = []
        report.append("# 策略回测验证报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"初始资金: {self.initial_capital:,.0f}元")
        report.append("\n---\n")

        # 策略对比表
        report.append("## 策略对比\n")
        report.append(
            "| 策略 | 总收益率 | 年化收益 | 最大回撤 | 夏普比率 | 胜率 | 交易次数 |"
        )
        report.append(
            "|------|----------|----------|----------|----------|------|----------|"
        )

        # 按收益率排序
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (
                x[1].get("total_return", -999) if "error" not in x[1] else -999
            ),
            reverse=True,
        )

        for strategy_name, result in sorted_results:
            if "error" in result:
                report.append(
                    f"| {strategy_name} | 错误: {result['error'][:20]} | - | - | - | - | - |"
                )
            else:
                report.append(
                    f"| {strategy_name} | "
                    f"{result['total_return']:.2%} | "
                    f"{result['annual_return']:.2%} | "
                    f"{result['max_drawdown']:.2%} | "
                    f"{result['sharpe_ratio']:.2f} | "
                    f"{result['win_rate']:.2%} | "
                    f"{result['trade_count']} |"
                )

        # 最优策略
        report.append("\n## 最优策略\n")

        best_strategy = sorted_results[0][0]
        best_result = sorted_results[0][1]

        if "error" not in best_result:
            report.append(f"**{best_strategy}** 表现最佳：")
            report.append(f"- 总收益率: {best_result['total_return']:.2%}")
            report.append(f"- 年化收益: {best_result['annual_return']:.2%}")
            report.append(f"- 最大回撤: {best_result['max_drawdown']:.2%}")
            report.append(f"- 夏普比率: {best_result['sharpe_ratio']:.2f}")
            report.append(f"- 胜率: {best_result['win_rate']:.2%}")

        # 策略分析
        report.append("\n## 策略分析\n")

        # 按风险调整收益排序
        report.append("### 按夏普比率排序\n")
        sorted_by_sharpe = sorted(
            [(k, v) for k, v in self.results.items() if "error" not in v],
            key=lambda x: x[1]["sharpe_ratio"],
            reverse=True,
        )

        for i, (strategy_name, result) in enumerate(sorted_by_sharpe, 1):
            report.append(
                f"{i}. **{strategy_name}**: 夏普比率 {result['sharpe_ratio']:.2f}"
            )

        # 建议
        report.append("\n## 实战建议\n")

        if best_result["sharpe_ratio"] > 1:
            report.append(
                f"- **推荐使用 {best_strategy}**：夏普比率 > 1，风险调整后收益优秀"
            )
        elif best_result["sharpe_ratio"] > 0.5:
            report.append(f"- **可考虑 {best_strategy}**：夏普比率 > 0.5，表现尚可")
        else:
            report.append(
                f"- **谨慎使用**：所有策略夏普比率较低，需要优化参数或组合使用"
            )

        if best_result["max_drawdown"] < -0.2:
            report.append(
                f"- ⚠️ 最大回撤 {best_result['max_drawdown']:.2%} 较大，建议设置止损"
            )

        report_text = "\n".join(report)

        # 保存报告
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"\n报告已保存到: {output_path}")

        return report_text


def test_with_mock_data():
    """使用模拟数据测试"""
    print("\n" + "=" * 60)
    print("策略回测验证系统测试")
    print("=" * 60)

    # 生成模拟数据（1年）
    np.random.seed(42)
    dates = pd.date_range(start="2025-05-01", end="2026-05-01", freq="D")

    # 模拟股价（随机游走 + 趋势）
    n = len(dates)
    returns = np.random.randn(n) * 0.02 + 0.0005  # 日均收益0.05%
    prices = 100 * (1 + returns).cumprod()

    data = pd.DataFrame(
        {
            "open": prices * (1 + np.random.randn(n) * 0.01),
            "high": prices * (1 + np.abs(np.random.randn(n) * 0.02)),
            "low": prices * (1 - np.abs(np.random.randn(n) * 0.02)),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, n),
        },
        index=dates,
    )

    print(
        f"\n数据范围: {dates[0].strftime('%Y-%m-%d')} 至 {dates[-1].strftime('%Y-%m-%d')}"
    )
    print(f"数据条数: {len(data)}")
    print(f"价格范围: {data['close'].min():.2f} - {data['close'].max():.2f}")

    # 运行回测
    validator = StrategyBacktestValidator(initial_capital=100000)
    results = validator.run_all_strategies(data)

    # 生成报告
    report = validator.generate_report()
    print("\n" + report)

    return validator


if __name__ == "__main__":
    test_with_mock_data()
