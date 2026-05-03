#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能回测引擎
- JIT加速（Numba）
- 向量化计算（NumPy）
- 完整绩效分析

参考：FactorWeave-Quant 系统
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time

# 尝试导入Numba（JIT加速）
try:
    from numba import jit, prange

    NUMBA_AVAILABLE = True
    print("Numba JIT加速已启用")
except ImportError:
    NUMBA_AVAILABLE = False
    print("警告: Numba未安装，JIT加速不可用。安装方法: pip install numba")

    # 定义一个空的装饰器
    def jit(*args, **kwargs):
        def decorator(func):
            return func

        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

    prange = range


class SignalType(Enum):
    """信号类型"""

    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class Trade:
    """交易记录"""

    entry_time: int  # 入场时间（索引）
    exit_time: int  # 出场时间（索引）
    entry_price: float  # 入场价格
    exit_price: float  # 出场价格
    position: int  # 仓位（正数做多，负数做空）
    pnl: float = 0.0  # 盈亏
    pnl_pct: float = 0.0  # 盈亏百分比
    hold_days: int = 0  # 持仓天数
    exit_reason: str = ""  # 退出原因


@dataclass
class BacktestResult:
    """回测结果"""

    # 基础数据
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float

    # 收益指标
    total_return: float = 0.0  # 总收益率
    annual_return: float = 0.0  # 年化收益率
    benchmark_return: float = 0.0  # 基准收益率

    # 风险指标
    max_drawdown: float = 0.0  # 最大回撤
    volatility: float = 0.0  # 年化波动率
    sharpe_ratio: float = 0.0  # 夏普比率
    sortino_ratio: float = 0.0  # 索提诺比率
    calmar_ratio: float = 0.0  # 卡玛比率

    # 交易统计
    total_trades: int = 0  # 总交易次数
    win_trades: int = 0  # 盈利次数
    loss_trades: int = 0  # 亏损次数
    win_rate: float = 0.0  # 胜率
    avg_win: float = 0.0  # 平均盈利
    avg_loss: float = 0.0  # 平均亏损
    profit_factor: float = 0.0  # 盈亏比
    avg_hold_days: float = 0.0  # 平均持仓天数

    # 性能指标
    backtest_time: float = 0.0  # 回测耗时（秒）
    data_points: int = 0  # 数据点数
    speed: float = 0.0  # 回测速度（条/秒）

    # 详细数据
    trades: List[Trade] = field(default_factory=list)
    equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    drawdown_curve: np.ndarray = field(default_factory=lambda: np.array([]))


class HighPerformanceBacktestEngine:
    """高性能回测引擎"""

    def __init__(self, use_jit: bool = True):
        self.use_jit = use_jit and NUMBA_AVAILABLE

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        initial_capital: float = 100000.0,
        commission: float = 0.0003,  # 手续费率
        slippage: float = 0.0001,  # 滑点率
        position_size: float = 0.95,  # 仓位比例
        stop_loss: Optional[float] = None,  # 止损比例
        take_profit: Optional[float] = None,  # 止盈比例
        max_hold_days: Optional[int] = None,  # 最大持仓天数
    ) -> BacktestResult:
        """
        运行回测

        Args:
            data: K线数据（需包含 open, high, low, close, volume 列）
            strategy_func: 策略函数，返回信号（1=买入，-1=卖出，0=持有）
            initial_capital: 初始资金
            commission: 手续费率
            slippage: 滑点率
            position_size: 仓位比例
            stop_loss: 止损比例（如 0.05 表示 5%）
            take_profit: 止盈比例
            max_hold_days: 最大持仓天数

        Returns:
            BacktestResult: 回测结果
        """
        start_time = time.time()

        # 提取数据
        opens = data["open"].values
        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values
        volumes = (
            data["volume"].values if "volume" in data.columns else np.ones(len(data))
        )

        n = len(data)

        # 生成信号
        signals = strategy_func(data)

        # 运行回测
        if self.use_jit:
            trades, equity_curve = self._run_backtest_jit(
                opens,
                highs,
                lows,
                closes,
                volumes,
                signals,
                initial_capital,
                commission,
                slippage,
                position_size,
                stop_loss,
                take_profit,
                max_hold_days,
            )
        else:
            trades, equity_curve = self._run_backtest_normal(
                opens,
                highs,
                lows,
                closes,
                volumes,
                signals,
                initial_capital,
                commission,
                slippage,
                position_size,
                stop_loss,
                take_profit,
                max_hold_days,
            )

        # 计算绩效指标
        result = self._calculate_performance(
            trades, equity_curve, data, initial_capital, start_time
        )

        return result

    def _run_backtest_normal(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        signals: np.ndarray,
        initial_capital: float,
        commission: float,
        slippage: float,
        position_size: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        max_hold_days: Optional[int],
    ) -> Tuple[List[Trade], np.ndarray]:
        """普通回测（无JIT加速）"""
        n = len(opens)
        capital = initial_capital
        position = 0  # 当前仓位
        entry_price = 0.0
        entry_time = 0

        trades = []
        equity_curve = np.zeros(n)

        for i in range(n):
            # 计算当前权益
            if position > 0:
                equity = capital + position * (closes[i] - entry_price)
            else:
                equity = capital

            equity_curve[i] = equity

            # 检查止损止盈
            if position > 0:
                pnl_pct = (closes[i] - entry_price) / entry_price

                # 止损
                if stop_loss and pnl_pct <= -stop_loss:
                    # 卖出
                    capital = equity * (1 - commission)
                    trades.append(
                        Trade(
                            entry_time=entry_time,
                            exit_time=i,
                            entry_price=entry_price,
                            exit_price=closes[i],
                            position=position,
                            pnl=capital - initial_capital,
                            pnl_pct=pnl_pct,
                            hold_days=i - entry_time,
                            exit_reason="止损",
                        )
                    )
                    position = 0
                    continue

                # 止盈
                if take_profit and pnl_pct >= take_profit:
                    capital = equity * (1 - commission)
                    trades.append(
                        Trade(
                            entry_time=entry_time,
                            exit_time=i,
                            entry_price=entry_price,
                            exit_price=closes[i],
                            position=position,
                            pnl=capital - initial_capital,
                            pnl_pct=pnl_pct,
                            hold_days=i - entry_time,
                            exit_reason="止盈",
                        )
                    )
                    position = 0
                    continue

                # 最大持仓天数
                if max_hold_days and (i - entry_time) >= max_hold_days:
                    capital = equity * (1 - commission)
                    trades.append(
                        Trade(
                            entry_time=entry_time,
                            exit_time=i,
                            entry_price=entry_price,
                            exit_price=closes[i],
                            position=position,
                            pnl=capital - initial_capital,
                            pnl_pct=pnl_pct,
                            hold_days=i - entry_time,
                            exit_reason="最大持仓期",
                        )
                    )
                    position = 0
                    continue

            # 处理信号
            signal = signals[i]

            # 买入信号
            if signal == 1 and position == 0:
                # 计算可买数量
                buy_price = opens[i] * (1 + slippage)
                shares = int(capital * position_size / buy_price)
                if shares > 0:
                    position = shares
                    entry_price = buy_price
                    entry_time = i
                    capital -= shares * buy_price * (1 + commission)

            # 卖出信号
            elif signal == -1 and position > 0:
                sell_price = opens[i] * (1 - slippage)
                pnl_pct = (sell_price - entry_price) / entry_price
                capital += position * sell_price * (1 - commission)
                trades.append(
                    Trade(
                        entry_time=entry_time,
                        exit_time=i,
                        entry_price=entry_price,
                        exit_price=sell_price,
                        position=position,
                        pnl=capital - initial_capital,
                        pnl_pct=pnl_pct,
                        hold_days=i - entry_time,
                        exit_reason="信号卖出",
                    )
                )
                position = 0

        return trades, equity_curve

    def _run_backtest_jit(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        signals: np.ndarray,
        initial_capital: float,
        commission: float,
        slippage: float,
        position_size: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        max_hold_days: Optional[int],
    ) -> Tuple[List[Trade], np.ndarray]:
        """JIT加速回测"""
        # 使用JIT加速的核心计算
        trades_raw, equity_curve = self._backtest_core_jit(
            opens,
            closes,
            signals,
            initial_capital,
            commission,
            slippage,
            position_size,
            stop_loss if stop_loss else 0.0,
            take_profit if take_profit else 0.0,
            max_hold_days if max_hold_days else 0,
        )

        # 转换为Trade对象
        trades = []
        for t in trades_raw:
            if t[0] >= 0:  # 有效交易
                trades.append(
                    Trade(
                        entry_time=int(t[0]),
                        exit_time=int(t[1]),
                        entry_price=t[2],
                        exit_price=t[3],
                        position=int(t[4]),
                        pnl=t[5],
                        pnl_pct=t[6],
                        hold_days=int(t[7]),
                        exit_reason="",
                    )
                )

        return trades, equity_curve

    @staticmethod
    @jit(nopython=True)
    def _backtest_core_jit(
        opens: np.ndarray,
        closes: np.ndarray,
        signals: np.ndarray,
        initial_capital: float,
        commission: float,
        slippage: float,
        position_size: float,
        stop_loss: float,
        take_profit: float,
        max_hold_days: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """JIT加速的回测核心"""
        n = len(opens)
        capital = initial_capital
        position = 0
        entry_price = 0.0
        entry_time = 0

        # 预分配数组
        trades = np.zeros(
            (n, 8)
        )  # entry_time, exit_time, entry_price, exit_price, position, pnl, pnl_pct, hold_days
        equity_curve = np.zeros(n)
        trade_count = 0

        for i in range(n):
            # 计算当前权益
            if position > 0:
                equity = capital + position * (closes[i] - entry_price)
            else:
                equity = capital

            equity_curve[i] = equity

            # 检查止损止盈
            if position > 0:
                pnl_pct = (closes[i] - entry_price) / entry_price

                # 止损
                if stop_loss > 0 and pnl_pct <= -stop_loss:
                    capital = equity * (1 - commission)
                    trades[trade_count] = [
                        entry_time,
                        i,
                        entry_price,
                        closes[i],
                        position,
                        capital - initial_capital,
                        pnl_pct,
                        i - entry_time,
                    ]
                    trade_count += 1
                    position = 0
                    continue

                # 止盈
                if take_profit > 0 and pnl_pct >= take_profit:
                    capital = equity * (1 - commission)
                    trades[trade_count] = [
                        entry_time,
                        i,
                        entry_price,
                        closes[i],
                        position,
                        capital - initial_capital,
                        pnl_pct,
                        i - entry_time,
                    ]
                    trade_count += 1
                    position = 0
                    continue

                # 最大持仓天数
                if max_hold_days > 0 and (i - entry_time) >= max_hold_days:
                    capital = equity * (1 - commission)
                    trades[trade_count] = [
                        entry_time,
                        i,
                        entry_price,
                        closes[i],
                        position,
                        capital - initial_capital,
                        pnl_pct,
                        i - entry_time,
                    ]
                    trade_count += 1
                    position = 0
                    continue

            # 处理信号
            signal = signals[i]

            # 买入
            if signal == 1 and position == 0:
                buy_price = opens[i] * (1 + slippage)
                shares = int(capital * position_size / buy_price)
                if shares > 0:
                    position = shares
                    entry_price = buy_price
                    entry_time = i
                    capital -= shares * buy_price * (1 + commission)

            # 卖出
            elif signal == -1 and position > 0:
                sell_price = opens[i] * (1 - slippage)
                pnl_pct = (sell_price - entry_price) / entry_price
                capital += position * sell_price * (1 - commission)
                trades[trade_count] = [
                    entry_time,
                    i,
                    entry_price,
                    sell_price,
                    position,
                    capital - initial_capital,
                    pnl_pct,
                    i - entry_time,
                ]
                trade_count += 1
                position = 0

        return trades[:trade_count], equity_curve

    def _calculate_performance(
        self,
        trades: List[Trade],
        equity_curve: np.ndarray,
        data: pd.DataFrame,
        initial_capital: float,
        start_time: float,
    ) -> BacktestResult:
        """计算绩效指标"""
        end_time = time.time()
        backtest_time = end_time - start_time

        n = len(data)
        final_capital = equity_curve[-1] if len(equity_curve) > 0 else initial_capital

        # 基础指标
        total_return = (final_capital - initial_capital) / initial_capital

        # 年化收益率
        days = n  # 假设数据是日线
        years = days / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 最大回撤
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        max_drawdown = np.min(drawdown)

        # 年化波动率
        returns = np.diff(equity_curve) / equity_curve[:-1]
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0

        # 夏普比率
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0

        # 索提诺比率（只考虑下行风险）
        downside_returns = returns[returns < 0]
        downside_std = (
            np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        )
        sortino_ratio = annual_return / downside_std if downside_std > 0 else 0

        # 卡玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 交易统计
        total_trades = len(trades)
        win_trades = len([t for t in trades if t.pnl > 0])
        loss_trades = len([t for t in trades if t.pnl <= 0])
        win_rate = win_trades / total_trades if total_trades > 0 else 0

        # 平均盈亏
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl <= 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # 盈亏比
        total_win = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 0
        profit_factor = total_win / total_loss if total_loss > 0 else 0

        # 平均持仓天数
        avg_hold_days = np.mean([t.hold_days for t in trades]) if trades else 0

        # 回测速度
        speed = n / backtest_time if backtest_time > 0 else 0

        return BacktestResult(
            symbol=data.index[0] if hasattr(data.index[0], "__str__") else "UNKNOWN",
            start_date=str(data.index[0]) if len(data) > 0 else "",
            end_date=str(data.index[-1]) if len(data) > 0 else "",
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_hold_days=avg_hold_days,
            backtest_time=backtest_time,
            data_points=n,
            speed=speed,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown if len(drawdown) > 0 else np.array([]),
        )

    def generate_report(self, result: BacktestResult) -> str:
        """生成回测报告"""
        report = []
        report.append("=" * 70)
        report.append("回测报告")
        report.append("=" * 70)
        report.append(f"股票代码: {result.symbol}")
        report.append(f"回测区间: {result.start_date} ~ {result.end_date}")
        report.append(f"数据点数: {result.data_points}")
        report.append("")

        report.append("【收益指标】")
        report.append(f"初始资金: {result.initial_capital:,.2f}")
        report.append(f"最终资金: {result.final_capital:,.2f}")
        report.append(f"总收益率: {result.total_return * 100:.2f}%")
        report.append(f"年化收益率: {result.annual_return * 100:.2f}%")
        report.append("")

        report.append("【风险指标】")
        report.append(f"最大回撤: {result.max_drawdown * 100:.2f}%")
        report.append(f"年化波动率: {result.volatility * 100:.2f}%")
        report.append(f"夏普比率: {result.sharpe_ratio:.2f}")
        report.append(f"索提诺比率: {result.sortino_ratio:.2f}")
        report.append(f"卡玛比率: {result.calmar_ratio:.2f}")
        report.append("")

        report.append("【交易统计】")
        report.append(f"总交易次数: {result.total_trades}")
        report.append(f"盈利次数: {result.win_trades}")
        report.append(f"亏损次数: {result.loss_trades}")
        report.append(f"胜率: {result.win_rate * 100:.2f}%")
        report.append(f"平均盈利: {result.avg_win:,.2f}")
        report.append(f"平均亏损: {result.avg_loss:,.2f}")
        report.append(f"盈亏比: {result.profit_factor:.2f}")
        report.append(f"平均持仓天数: {result.avg_hold_days:.1f}")
        report.append("")

        report.append("【性能指标】")
        report.append(f"回测耗时: {result.backtest_time:.4f} 秒")
        report.append(f"回测速度: {result.speed:,.0f} 条/秒")
        report.append(f"JIT加速: {'已启用' if self.use_jit else '未启用'}")
        report.append("")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """测试高性能回测引擎"""
    print("=" * 70)
    print("测试高性能回测引擎")
    print("=" * 70)

    # 生成模拟数据
    np.random.seed(42)
    n = 10000  # 1万条数据

    dates = pd.date_range(start="2020-01-01", periods=n, freq="D")
    closes = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
    opens = closes * (1 + np.random.randn(n) * 0.005)
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.randn(n)) * 0.01)
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.randn(n)) * 0.01)
    volumes = np.random.randint(1000000, 10000000, n)

    data = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=dates,
    )

    print(f"\n生成模拟数据: {n} 条")

    # 定义简单策略（MA金叉死叉）
    def ma_strategy(df):
        ma5 = df["close"].rolling(5).mean()
        ma20 = df["close"].rolling(20).mean()

        signals = np.zeros(len(df))
        signals[ma5 > ma20] = 1  # 金叉买入
        signals[ma5 < ma20] = -1  # 死叉卖出

        return signals

    # 创建回测引擎
    engine = HighPerformanceBacktestEngine(use_jit=True)

    # 运行回测
    print("\n运行回测...")
    result = engine.run_backtest(
        data=data,
        strategy_func=ma_strategy,
        initial_capital=100000,
        commission=0.0003,
        slippage=0.0001,
        stop_loss=0.05,  # 5%止损
        take_profit=0.10,  # 10%止盈
        max_hold_days=20,  # 最大持仓20天
    )

    # 打印报告
    print(engine.generate_report(result))


if __name__ == "__main__":
    main()
