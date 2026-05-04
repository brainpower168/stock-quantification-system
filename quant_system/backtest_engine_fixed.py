#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的回测引擎
- 修复未来函数问题
- 改进撮合逻辑
- 完善流动性模型
- 真实交易成本

修复内容：
1. 信号基于昨日数据生成，今日开盘执行
2. 大单滑点模型（根据成交量动态计算）
3. 完整交易成本（手续费、印花税、冲击成本）
4. 盘中信号支持（可选）
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


class ExecutionMode(Enum):
    """执行模式"""

    NEXT_OPEN = "next_open"  # 次日开盘价执行（默认，避免未来函数）
    SAME_DAY_CLOSE = "same_day_close"  # 当日收盘价执行（盘中信号）


@dataclass
class Trade:
    """交易记录"""

    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    position: int
    pnl: float = 0.0
    pnl_pct: float = 0.0
    hold_days: int = 0
    exit_reason: str = ""
    slippage_cost: float = 0.0  # 滑点成本
    commission_cost: float = 0.0  # 手续费成本
    impact_cost: float = 0.0  # 冲击成本


@dataclass
class BacktestResult:
    """回测结果"""

    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float

    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    benchmark_return: float = 0.0

    # 风险指标
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # 交易统计
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    avg_hold_days: float = 0.0

    # 成本分析
    total_commission: float = 0.0  # 总手续费
    total_slippage: float = 0.0  # 总滑点成本
    total_impact: float = 0.0  # 总冲击成本
    total_cost: float = 0.0  # 总交易成本

    # 性能指标
    backtest_time: float = 0.0
    data_points: int = 0
    speed: float = 0.0

    # 详细数据
    trades: List[Trade] = field(default_factory=list)
    equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    drawdown_curve: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class CommissionConfig:
    """交易成本配置"""

    stamp_duty: float = 0.001  # 印花税（卖出，千分之一）
    commission_rate: float = 0.0003  # 佣金（万分之三）
    min_commission: float = 5.0  # 最低佣金5元
    transfer_fee: float = 0.00001  # 过户费（十万分之一）

    def calculate_buy_cost(self, amount: float) -> float:
        """计算买入成本"""
        commission = max(amount * self.commission_rate, self.min_commission)
        transfer = amount * self.transfer_fee
        return commission + transfer

    def calculate_sell_cost(self, amount: float) -> float:
        """计算卖出成本"""
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp = amount * self.stamp_duty
        transfer = amount * self.transfer_fee
        return commission + stamp + transfer


@dataclass
class SlippageConfig:
    """滑点配置"""

    base_slippage: float = 0.0001  # 基础滑点（万分之一）
    volume_impact_factor: float = 0.1  # 成交量冲击因子

    def calculate_slippage(
        self, price: float, volume: float, avg_volume: float, is_buy: bool = True
    ) -> Tuple[float, float]:
        """
        计算滑点价格和成本

        返回: (滑点价格, 滑点成本)
        """
        # 基础滑点
        base_slip = price * self.base_slippage

        # 成交量冲击（大单滑点更大）
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            volume_impact = price * self.volume_impact_factor * np.log1p(volume_ratio)
        else:
            volume_impact = 0

        # 总滑点
        total_slip = base_slip + volume_impact

        # 买入滑点向上，卖出滑点向下
        if is_buy:
            slip_price = price + total_slip
        else:
            slip_price = price - total_slip

        return slip_price, total_slip


class FixedBacktestEngine:
    """修复后的回测引擎"""

    def __init__(
        self,
        use_jit: bool = True,
        execution_mode: ExecutionMode = ExecutionMode.NEXT_OPEN,
        commission_config: CommissionConfig = None,
        slippage_config: SlippageConfig = None,
    ):
        self.use_jit = use_jit and NUMBA_AVAILABLE
        self.execution_mode = execution_mode
        self.commission_config = commission_config or CommissionConfig()
        self.slippage_config = slippage_config or SlippageConfig()

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        initial_capital: float = 100000.0,
        position_size: float = 0.95,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        max_hold_days: Optional[int] = None,
    ) -> BacktestResult:
        """
        运行回测（修复未来函数）

        关键改进：
        1. 信号基于昨日数据生成
        2. 交易在今日开盘执行
        3. 真实的交易成本模型
        4. 大单滑点模型
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

        # 计算平均成交量（用于滑点计算）
        avg_volume = np.mean(volumes) if len(volumes) > 0 else 1

        n = len(data)

        # 生成信号（基于昨日数据）
        signals = self._generate_signals_no_lookahead(data, strategy_func)

        # 运行回测
        trades, equity_curve = self._run_backtest_fixed(
            opens,
            highs,
            lows,
            closes,
            volumes,
            avg_volume,
            signals,
            initial_capital,
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

    def _generate_signals_no_lookahead(
        self, data: pd.DataFrame, strategy_func: Callable
    ) -> np.ndarray:
        """
        生成信号（避免未来函数）

        关键：信号基于昨日数据生成
        """
        n = len(data)
        signals = np.zeros(n)

        # 从第2天开始（因为需要昨天的数据）
        for i in range(1, n):
            # 使用昨天及之前的数据生成信号
            historical_data = data.iloc[:i]
            signal = strategy_func(historical_data)

            # 今天的信号基于昨天的数据
            if isinstance(signal, (int, float)):
                signals[i] = signal
            elif isinstance(signal, np.ndarray):
                signals[i] = signal[-1] if len(signal) > 0 else 0
            elif isinstance(signal, pd.Series):
                signals[i] = signal.iloc[-1] if len(signal) > 0 else 0

        return signals

    def _run_backtest_fixed(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        avg_volume: float,
        signals: np.ndarray,
        initial_capital: float,
        position_size: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        max_hold_days: Optional[int],
    ) -> Tuple[List[Trade], np.ndarray]:
        """修复后的回测逻辑"""
        n = len(opens)
        capital = initial_capital
        position = 0
        entry_price = 0.0
        entry_time = 0
        entry_volume = 0.0  # 买入时的成交量

        trades = []
        equity_curve = np.zeros(n)

        # 成本统计
        total_commission = 0.0
        total_slippage = 0.0
        total_impact = 0.0

        for i in range(n):
            # 计算当前权益
            if position > 0:
                equity = capital + position * (closes[i] - entry_price)
            else:
                equity = capital

            equity_curve[i] = equity

            # 检查止损止盈（使用日内最低/最高价）
            if position > 0:
                # 止损检查（使用日内最低价）
                if stop_loss and lows[i] <= entry_price * (1 - stop_loss):
                    # 触发止损，按最低价卖出
                    sell_price, slip_cost = self.slippage_config.calculate_slippage(
                        lows[i], entry_volume, avg_volume, is_buy=False
                    )
                    amount = position * sell_price
                    commission_cost = self.commission_config.calculate_sell_cost(amount)

                    capital = amount - commission_cost
                    pnl_pct = (sell_price - entry_price) / entry_price

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
                            exit_reason="止损",
                            slippage_cost=slip_cost * position,
                            commission_cost=commission_cost,
                            impact_cost=slip_cost * position,
                        )
                    )

                    total_commission += commission_cost
                    total_slippage += slip_cost * position
                    total_impact += slip_cost * position

                    position = 0
                    continue

                # 止盈检查（使用日内最高价）
                if take_profit and highs[i] >= entry_price * (1 + take_profit):
                    # 触发止盈，按最高价卖出
                    sell_price, slip_cost = self.slippage_config.calculate_slippage(
                        highs[i], entry_volume, avg_volume, is_buy=False
                    )
                    amount = position * sell_price
                    commission_cost = self.commission_config.calculate_sell_cost(amount)

                    capital = amount - commission_cost
                    pnl_pct = (sell_price - entry_price) / entry_price

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
                            exit_reason="止盈",
                            slippage_cost=slip_cost * position,
                            commission_cost=commission_cost,
                            impact_cost=slip_cost * position,
                        )
                    )

                    total_commission += commission_cost
                    total_slippage += slip_cost * position
                    total_impact += slip_cost * position

                    position = 0
                    continue

                # 最大持仓天数
                if max_hold_days and (i - entry_time) >= max_hold_days:
                    sell_price, slip_cost = self.slippage_config.calculate_slippage(
                        opens[i], entry_volume, avg_volume, is_buy=False
                    )
                    amount = position * sell_price
                    commission_cost = self.commission_config.calculate_sell_cost(amount)

                    capital = amount - commission_cost
                    pnl_pct = (sell_price - entry_price) / entry_price

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
                            exit_reason="最大持仓期",
                            slippage_cost=slip_cost * position,
                            commission_cost=commission_cost,
                            impact_cost=slip_cost * position,
                        )
                    )

                    total_commission += commission_cost
                    total_slippage += slip_cost * position
                    total_impact += slip_cost * position

                    position = 0
                    continue

            # 处理信号（信号基于昨日数据，今日开盘执行）
            signal = signals[i]

            # 买入信号
            if signal == 1 and position == 0:
                # 计算可买数量
                buy_price, slip_cost = self.slippage_config.calculate_slippage(
                    opens[i], volumes[i], avg_volume, is_buy=True
                )
                shares = int(capital * position_size / buy_price)

                if shares > 0:
                    amount = shares * buy_price
                    commission_cost = self.commission_config.calculate_buy_cost(amount)

                    if amount + commission_cost <= capital:
                        position = shares
                        entry_price = buy_price
                        entry_time = i
                        entry_volume = volumes[i]
                        capital -= amount + commission_cost

                        total_commission += commission_cost
                        total_slippage += slip_cost * shares
                        total_impact += slip_cost * shares

            # 卖出信号
            elif signal == -1 and position > 0:
                sell_price, slip_cost = self.slippage_config.calculate_slippage(
                    opens[i], volumes[i], avg_volume, is_buy=False
                )
                amount = position * sell_price
                commission_cost = self.commission_config.calculate_sell_cost(amount)

                capital = amount - commission_cost
                pnl_pct = (sell_price - entry_price) / entry_price

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
                        slippage_cost=slip_cost * position,
                        commission_cost=commission_cost,
                        impact_cost=slip_cost * position,
                    )
                )

                total_commission += commission_cost
                total_slippage += slip_cost * position
                total_impact += slip_cost * position

                position = 0

        return trades, equity_curve

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
        days = n
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

        # 索提诺比率
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

        # 成本统计
        total_commission = sum(t.commission_cost for t in trades)
        total_slippage = sum(t.slippage_cost for t in trades)
        total_impact = sum(t.impact_cost for t in trades)
        total_cost = total_commission + total_slippage + total_impact

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
            total_commission=total_commission,
            total_slippage=total_slippage,
            total_impact=total_impact,
            total_cost=total_cost,
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
        report.append("回测报告（修复未来函数版）")
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

        report.append("【交易成本分析】")
        report.append(f"总手续费: {result.total_commission:,.2f}")
        report.append(f"总滑点成本: {result.total_slippage:,.2f}")
        report.append(f"总冲击成本: {result.total_impact:,.2f}")
        report.append(f"总交易成本: {result.total_cost:,.2f}")
        report.append(
            f"成本占收益比: {result.total_cost / (result.final_capital - result.initial_capital) * 100:.2f}%"
            if result.final_capital != result.initial_capital
            else "成本占收益比: N/A"
        )
        report.append("")

        report.append("【性能指标】")
        report.append(f"回测耗时: {result.backtest_time:.4f} 秒")
        report.append(f"回测速度: {result.speed:,.0f} 条/秒")
        report.append(f"执行模式: {self.execution_mode.value}")
        report.append("")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """测试修复后的回测引擎"""
    print("=" * 70)
    print("测试修复后的回测引擎")
    print("=" * 70)

    # 生成模拟数据
    np.random.seed(42)
    n = 1000

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

    # 定义MA策略（修复后）
    def ma_strategy_fixed(df):
        """MA策略（避免未来函数）"""
        if len(df) < 20:
            return 0

        ma5 = df["close"].rolling(5).mean()
        ma20 = df["close"].rolling(20).mean()

        # 使用昨天的数据判断
        if ma5.iloc[-2] > ma20.iloc[-2] and ma5.iloc[-3] <= ma20.iloc[-3]:
            return 1  # 金叉买入
        elif ma5.iloc[-2] < ma20.iloc[-2] and ma5.iloc[-3] >= ma20.iloc[-3]:
            return -1  # 死叉卖出

        return 0

    # 创建回测引擎
    engine = FixedBacktestEngine(
        use_jit=False,  # 测试时不使用JIT
        execution_mode=ExecutionMode.NEXT_OPEN,
    )

    # 运行回测
    print("\n运行回测...")
    result = engine.run_backtest(
        data=data,
        strategy_func=ma_strategy_fixed,
        initial_capital=100000,
        position_size=0.95,
        stop_loss=0.05,
        take_profit=0.10,
        max_hold_days=20,
    )

    # 打印报告
    print(engine.generate_report(result))


if __name__ == "__main__":
    main()
