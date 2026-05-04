#!/usr/bin/env python3
"""
策略参数优化器
- 网格搜索最优参数
- 支持多种策略参数优化
- 生成优化报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import warnings

warnings.filterwarnings("ignore")


@dataclass
class OptimizationResult:
    """优化结果"""

    strategy_name: str
    best_params: Dict
    best_return: float
    best_win_rate: float
    best_drawdown: float
    all_results: List[Dict]


class StrategyParamOptimizer:
    """策略参数优化器"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital

    def optimize_ma_cross(
        self,
        data: pd.DataFrame,
        short_range: Tuple[int, int] = (3, 10),
        long_range: Tuple[int, int] = (15, 30),
        step: int = 1,
    ) -> OptimizationResult:
        """
        优化MA金叉策略参数

        参数:
            data: OHLCV数据
            short_range: 短期均线范围 (min, max)
            long_range: 长期均线范围 (min, max)
            step: 步长

        返回:
            优化结果
        """
        results = []
        best_return = -float("inf")
        best_params = None
        best_result = None

        for short in range(short_range[0], short_range[1] + 1, step):
            for long in range(long_range[0], long_range[1] + 1, step):
                if short >= long:
                    continue

                # 回测
                result = self._backtest_ma_cross(data, short, long)

                results.append(
                    {
                        "short_ma": short,
                        "long_ma": long,
                        "total_return": result["total_return"],
                        "win_rate": result["win_rate"],
                        "max_drawdown": result["max_drawdown"],
                    }
                )

                if result["total_return"] > best_return:
                    best_return = result["total_return"]
                    best_params = {"short_ma": short, "long_ma": long}
                    best_result = result

        return OptimizationResult(
            strategy_name="ma_cross",
            best_params=best_params,
            best_return=best_return,
            best_win_rate=best_result["win_rate"] if best_result else 0,
            best_drawdown=best_result["max_drawdown"] if best_result else 0,
            all_results=results,
        )

    def optimize_rsi_reversal(
        self,
        data: pd.DataFrame,
        period_range: Tuple[int, int] = (7, 21),
        oversold_range: Tuple[int, int] = (20, 35),
        overbought_range: Tuple[int, int] = (65, 80),
        step: int = 1,
    ) -> OptimizationResult:
        """
        优化RSI反转策略参数

        参数:
            data: OHLCV数据
            period_range: RSI周期范围
            oversold_range: 超卖阈值范围
            overbought_range: 超买阈值范围

        返回:
            优化结果
        """
        results = []
        best_return = -float("inf")
        best_params = None
        best_result = None

        for period in range(period_range[0], period_range[1] + 1, step):
            for oversold in range(oversold_range[0], oversold_range[1] + 1, step):
                for overbought in range(
                    overbought_range[0], overbought_range[1] + 1, step
                ):
                    if oversold >= overbought:
                        continue

                    # 回测
                    result = self._backtest_rsi(data, period, oversold, overbought)

                    results.append(
                        {
                            "period": period,
                            "oversold": oversold,
                            "overbought": overbought,
                            "total_return": result["total_return"],
                            "win_rate": result["win_rate"],
                            "max_drawdown": result["max_drawdown"],
                        }
                    )

                    if result["total_return"] > best_return:
                        best_return = result["total_return"]
                        best_params = {
                            "period": period,
                            "oversold": oversold,
                            "overbought": overbought,
                        }
                        best_result = result

        return OptimizationResult(
            strategy_name="rsi_reversal",
            best_params=best_params,
            best_return=best_return,
            best_win_rate=best_result["win_rate"] if best_result else 0,
            best_drawdown=best_result["max_drawdown"] if best_result else 0,
            all_results=results,
        )

    def optimize_strategy_2560(
        self,
        data: pd.DataFrame,
        ma_range: Tuple[int, int] = (20, 30),
        vol_short_range: Tuple[int, int] = (3, 7),
        vol_long_range: Tuple[int, int] = (50, 70),
        touch_range: Tuple[float, float] = (0.01, 0.03),
    ) -> OptimizationResult:
        """
        优化2560战法参数

        参数:
            data: OHLCV数据
            ma_range: 均线周期范围
            vol_short_range: 短期均量线范围
            vol_long_range: 长期均量线范围
            touch_range: 回踩距离范围

        返回:
            优化结果
        """
        results = []
        best_return = -float("inf")
        best_params = None
        best_result = None

        for ma_period in range(ma_range[0], ma_range[1] + 1, 1):
            for vol_short in range(vol_short_range[0], vol_short_range[1] + 1, 1):
                for vol_long in range(vol_long_range[0], vol_long_range[1] + 1, 5):
                    if vol_short >= vol_long:
                        continue

                    for touch_dist in np.arange(
                        touch_range[0], touch_range[1] + 0.005, 0.005
                    ):
                        # 回测
                        result = self._backtest_2560(
                            data, ma_period, vol_short, vol_long, touch_dist
                        )

                        results.append(
                            {
                                "ma_period": ma_period,
                                "vol_short": vol_short,
                                "vol_long": vol_long,
                                "touch_distance": round(touch_dist, 3),
                                "total_return": result["total_return"],
                                "win_rate": result["win_rate"],
                                "max_drawdown": result["max_drawdown"],
                            }
                        )

                        if result["total_return"] > best_return:
                            best_return = result["total_return"]
                            best_params = {
                                "ma_period": ma_period,
                                "vol_short": vol_short,
                                "vol_long": vol_long,
                                "touch_distance": round(touch_dist, 3),
                            }
                            best_result = result

        return OptimizationResult(
            strategy_name="strategy_2560",
            best_params=best_params,
            best_return=best_return,
            best_win_rate=best_result["win_rate"] if best_result else 0,
            best_drawdown=best_result["max_drawdown"] if best_result else 0,
            all_results=results,
        )

    def optimize_breakout(
        self,
        data: pd.DataFrame,
        high_range: Tuple[int, int] = (10, 30),
        low_range: Tuple[int, int] = (5, 15),
    ) -> OptimizationResult:
        """
        优化突破信号策略参数

        参数:
            data: OHLCV数据
            high_range: 高点周期范围
            low_range: 低点周期范围

        返回:
            优化结果
        """
        results = []
        best_return = -float("inf")
        best_params = None
        best_result = None

        for high_period in range(high_range[0], high_range[1] + 1, 2):
            for low_period in range(low_range[0], low_range[1] + 1, 1):
                # 回测
                result = self._backtest_breakout(data, high_period, low_period)

                results.append(
                    {
                        "high_period": high_period,
                        "low_period": low_period,
                        "total_return": result["total_return"],
                        "win_rate": result["win_rate"],
                        "max_drawdown": result["max_drawdown"],
                    }
                )

                if result["total_return"] > best_return:
                    best_return = result["total_return"]
                    best_params = {
                        "high_period": high_period,
                        "low_period": low_period,
                    }
                    best_result = result

        return OptimizationResult(
            strategy_name="breakout_signal",
            best_params=best_params,
            best_return=best_return,
            best_win_rate=best_result["win_rate"] if best_result else 0,
            best_drawdown=best_result["max_drawdown"] if best_result else 0,
            all_results=results,
        )

    # ==================== 回测函数 ====================

    def _backtest_ma_cross(self, data: pd.DataFrame, short: int, long: int) -> Dict:
        """回测MA金叉策略"""
        signals = pd.Series(0, index=data.index)

        ma_short = data["close"].rolling(short).mean()
        ma_long = data["close"].rolling(long).mean()

        golden_cross = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        death_cross = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))

        signals[golden_cross] = 1
        signals[death_cross] = -1

        return self._simple_backtest(data, signals)

    def _backtest_rsi(
        self, data: pd.DataFrame, period: int, oversold: int, overbought: int
    ) -> Dict:
        """回测RSI反转策略"""
        signals = pd.Series(0, index=data.index)

        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        buy_signal = rsi < oversold
        sell_signal = rsi > overbought

        signals[buy_signal] = 1
        signals[sell_signal] = -1

        return self._simple_backtest(data, signals)

    def _backtest_2560(
        self,
        data: pd.DataFrame,
        ma_period: int,
        vol_short: int,
        vol_long: int,
        touch_dist: float,
    ) -> Dict:
        """回测2560战法"""
        signals = pd.Series(0, index=data.index)

        ma = data["close"].rolling(ma_period).mean()
        ma_vol_short = data["volume"].rolling(vol_short).mean()
        ma_vol_long = data["volume"].rolling(vol_long).mean()

        touch_ma = abs(data["close"] - ma) / ma < touch_dist
        volume_condition = ma_vol_short > ma_vol_long

        buy_signal = touch_ma & volume_condition
        sell_signal = data["close"] < ma * 0.97

        signals[buy_signal] = 1
        signals[sell_signal] = -1

        return self._simple_backtest(data, signals)

    def _backtest_breakout(
        self, data: pd.DataFrame, high_period: int, low_period: int
    ) -> Dict:
        """回测突破信号策略"""
        signals = pd.Series(0, index=data.index)

        high_n = data["high"].rolling(high_period).max()
        low_n = data["low"].rolling(low_period).min()

        breakout = data["close"] > high_n.shift(1)
        breakdown = data["close"] < low_n.shift(1)

        signals[breakout] = 1
        signals[breakdown] = -1

        return self._simple_backtest(data, signals)

    def _simple_backtest(self, data: pd.DataFrame, signals: pd.Series) -> Dict:
        """简单回测引擎"""
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = [capital]

        for i in range(len(data)):
            signal = signals.iloc[i]
            price = data["close"].iloc[i]

            if signal == 1 and position == 0:
                # 买入
                shares = int(capital * 0.95 / price)
                if shares > 0:
                    position = shares
                    capital -= shares * price
                    trades.append({"type": "buy", "price": price, "shares": shares})

            elif signal == -1 and position > 0:
                # 卖出
                capital += position * price
                trades.append({"type": "sell", "price": price, "shares": position})
                position = 0

            # 记录权益
            equity = capital + position * price
            equity_curve.append(equity)

        # 最后如果还持仓，平仓
        if position > 0:
            last_price = data["close"].iloc[-1]
            capital += position * last_price
            position = 0

        # 计算指标
        equity_curve = pd.Series(equity_curve)
        total_return = (capital - self.initial_capital) / self.initial_capital

        # 计算最大回撤
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = drawdown.min()

        # 计算胜率
        win_trades = 0
        total_trades = 0
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy_trade = trades[i]
                sell_trade = trades[i + 1]
                if sell_trade["price"] > buy_trade["price"]:
                    win_trades += 1
                total_trades += 1

        win_rate = win_trades / total_trades if total_trades > 0 else 0

        return {
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "trade_count": total_trades,
        }

    def generate_report(self, results: List[OptimizationResult]) -> str:
        """生成优化报告"""
        lines = []
        lines.append("# 策略参数优化报告\n")
        lines.append(f"**优化时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        for result in results:
            lines.append(f"\n## {result.strategy_name}\n")
            lines.append(f"**最优参数**: {result.best_params}\n")
            lines.append(f"**最优收益**: {result.best_return:.2%}\n")
            lines.append(f"**最优胜率**: {result.best_win_rate:.2%}\n")
            lines.append(f"**最大回撤**: {result.best_drawdown:.2%}\n")

            # Top 5参数组合
            sorted_results = sorted(
                result.all_results, key=lambda x: x["total_return"], reverse=True
            )[:5]

            lines.append("\n### Top 5参数组合\n")
            lines.append("| 排名 | 参数 | 收益率 | 胜率 | 最大回撤 |\n")
            lines.append("|------|------|--------|------|----------|\n")

            for i, res in enumerate(sorted_results, 1):
                params_str = str(res).replace("{", "").replace("}", "")[:50]
                lines.append(
                    f"| {i} | {params_str} | "
                    f"{res['total_return']:.2%} | "
                    f"{res['win_rate']:.2%} | "
                    f"{res['max_drawdown']:.2%} |\n"
                )

        return "".join(lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="策略参数优化器")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--strategy", type=str, help="策略名称")
    parser.add_argument("--output", type=str, default="markdown", help="输出格式")
    parser.add_argument("--save", type=str, help="保存报告到文件")

    args = parser.parse_args()

    # 示例：生成模拟数据测试
    print("策略参数优化器已创建")
    print("使用方法:")
    print(
        "  python quant_system/strategy_param_optimizer.py --stock 600519 --strategy ma_cross"
    )


if __name__ == "__main__":
    main()
