#!/usr/bin/env python3
"""
实盘验证系统
- 使用优化后的策略参数进行模拟交易
- 实时监控持仓表现
- 自动执行交易信号
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SignalType(Enum):
    """信号类型"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Position:
    """持仓信息"""

    code: str
    name: str
    shares: int
    cost_price: float
    current_price: float
    profit_loss: float
    profit_loss_pct: float
    buy_date: str
    strategy: str


@dataclass
class TradeSignal:
    """交易信号"""

    code: str
    name: str
    signal_type: SignalType
    price: float
    strategy: str
    confidence: float
    reason: str
    timestamp: str


class OptimizedStrategies:
    """优化后的策略集合"""

    def __init__(self):
        # 优化后的参数
        self.ma_params = {"short": 6, "long": 30}
        self.rsi_params = {"period": 11, "oversold": 34, "overbought": 75}
        self.strategy_2560_params = {
            "ma_period": 27,
            "vol_short": 3,
            "vol_long": 55,
            "touch_distance": 0.015,
        }
        self.breakout_params = {"high_period": 10, "low_period": 6}

    def ma_cross_signal(self, data: pd.DataFrame) -> Tuple[SignalType, float, str]:
        """
        MA金叉策略（优化后参数）
        返回: (信号类型, 置信度, 原因)
        """
        if len(data) < self.ma_params["long"]:
            return SignalType.HOLD, 0.0, "数据不足"

        close = data["close"]
        ma_short = close.rolling(self.ma_params["short"]).mean()
        ma_long = close.rolling(self.ma_params["long"]).mean()

        # 金叉
        golden_cross = (ma_short.iloc[-1] > ma_long.iloc[-1]) and (
            ma_short.iloc[-2] <= ma_long.iloc[-2]
        )

        # 死叉
        death_cross = (ma_short.iloc[-1] < ma_long.iloc[-1]) and (
            ma_short.iloc[-2] >= ma_long.iloc[-2]
        )

        if golden_cross:
            # 计算置信度（基于均线距离）
            distance = abs(ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1]
            confidence = min(distance * 10, 1.0)
            return (
                SignalType.BUY,
                confidence,
                f"MA{self.ma_params['short']}上穿MA{self.ma_params['long']}",
            )

        if death_cross:
            distance = abs(ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1]
            confidence = min(distance * 10, 1.0)
            return (
                SignalType.SELL,
                confidence,
                f"MA{self.ma_params['short']}下穿MA{self.ma_params['long']}",
            )

        return SignalType.HOLD, 0.0, "无信号"

    def rsi_reversal_signal(self, data: pd.DataFrame) -> Tuple[SignalType, float, str]:
        """
        RSI反转策略（优化后参数）
        """
        if len(data) < self.rsi_params["period"]:
            return SignalType.HOLD, 0.0, "数据不足"

        close = data["close"]
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_params["period"]).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_params["period"]).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        # 超卖买入
        if current_rsi < self.rsi_params["oversold"]:
            confidence = (self.rsi_params["oversold"] - current_rsi) / self.rsi_params[
                "oversold"
            ]
            return (
                SignalType.BUY,
                confidence,
                f"RSI={current_rsi:.1f}超卖（阈值{self.rsi_params['oversold']}）",
            )

        # 超买卖出
        if current_rsi > self.rsi_params["overbought"]:
            confidence = (current_rsi - self.rsi_params["overbought"]) / (
                100 - self.rsi_params["overbought"]
            )
            return (
                SignalType.SELL,
                confidence,
                f"RSI={current_rsi:.1f}超买（阈值{self.rsi_params['overbought']}）",
            )

        return SignalType.HOLD, 0.0, f"RSI={current_rsi:.1f}正常"

    def strategy_2560_signal(self, data: pd.DataFrame) -> Tuple[SignalType, float, str]:
        """
        2560战法（优化后参数）
        """
        params = self.strategy_2560_params
        if len(data) < params["vol_long"]:
            return SignalType.HOLD, 0.0, "数据不足"

        close = data["close"]
        volume = data["volume"]

        ma = close.rolling(params["ma_period"]).mean()
        ma_vol_short = volume.rolling(params["vol_short"]).mean()
        ma_vol_long = volume.rolling(params["vol_long"]).mean()

        # 回踩均线
        distance = abs(close.iloc[-1] - ma.iloc[-1]) / ma.iloc[-1]
        touch_ma = distance < params["touch_distance"]

        # 量能条件
        volume_ok = ma_vol_short.iloc[-1] > ma_vol_long.iloc[-1]

        if touch_ma and volume_ok:
            confidence = 1.0 - distance / params["touch_distance"]
            return SignalType.BUY, confidence, f"回踩MA{params['ma_period']}，量能支持"

        # 跌破均线止损
        if close.iloc[-1] < ma.iloc[-1] * 0.97:
            return SignalType.SELL, 0.8, f"跌破MA{params['ma_period']} 3%"

        return SignalType.HOLD, 0.0, "无信号"

    def breakout_signal(self, data: pd.DataFrame) -> Tuple[SignalType, float, str]:
        """
        突破信号策略（优化后参数）
        """
        params = self.breakout_params
        if len(data) < params["high_period"]:
            return SignalType.HOLD, 0.0, "数据不足"

        high = data["high"]
        low = data["low"]
        close = data["close"]

        high_n = high.rolling(params["high_period"]).max()
        low_n = low.rolling(params["low_period"]).min()

        # 突破
        breakout = close.iloc[-1] > high_n.iloc[-2]
        # 跌破
        breakdown = close.iloc[-1] < low_n.iloc[-2]

        if breakout:
            distance = (close.iloc[-1] - high_n.iloc[-2]) / high_n.iloc[-2]
            confidence = min(distance * 10, 1.0)
            return SignalType.BUY, confidence, f"突破{params['high_period']}日高点"

        if breakdown:
            distance = (low_n.iloc[-2] - close.iloc[-1]) / low_n.iloc[-2]
            confidence = min(distance * 10, 1.0)
            return SignalType.SELL, confidence, f"跌破{params['low_period']}日低点"

        return SignalType.HOLD, 0.0, "无信号"


class LiveTradingValidator:
    """实盘验证系统"""

    def __init__(self, initial_capital: float = 270000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.strategies = OptimizedStrategies()
        self.trade_history = []

    def analyze_stock(
        self, code: str, name: str, data: pd.DataFrame
    ) -> List[TradeSignal]:
        """
        分析股票，生成交易信号

        返回: 所有策略的信号列表
        """
        signals = []

        # MA金叉
        signal_type, confidence, reason = self.strategies.ma_cross_signal(data)
        signals.append(
            TradeSignal(
                code=code,
                name=name,
                signal_type=signal_type,
                price=data["close"].iloc[-1],
                strategy="ma_cross",
                confidence=confidence,
                reason=reason,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

        # RSI反转
        signal_type, confidence, reason = self.strategies.rsi_reversal_signal(data)
        signals.append(
            TradeSignal(
                code=code,
                name=name,
                signal_type=signal_type,
                price=data["close"].iloc[-1],
                strategy="rsi_reversal",
                confidence=confidence,
                reason=reason,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

        # 2560战法
        signal_type, confidence, reason = self.strategies.strategy_2560_signal(data)
        signals.append(
            TradeSignal(
                code=code,
                name=name,
                signal_type=signal_type,
                price=data["close"].iloc[-1],
                strategy="strategy_2560",
                confidence=confidence,
                reason=reason,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

        # 突破信号
        signal_type, confidence, reason = self.strategies.breakout_signal(data)
        signals.append(
            TradeSignal(
                code=code,
                name=name,
                signal_type=signal_type,
                price=data["close"].iloc[-1],
                strategy="breakout_signal",
                confidence=confidence,
                reason=reason,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

        return signals

    def get_combined_signal(
        self, signals: List[TradeSignal]
    ) -> Tuple[SignalType, float, str]:
        """
        组合信号（投票机制）

        返回: (最终信号, 置信度, 原因)
        """
        buy_votes = 0
        sell_votes = 0
        buy_confidence = 0.0
        sell_confidence = 0.0

        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                buy_votes += 1
                buy_confidence += signal.confidence
            elif signal.signal_type == SignalType.SELL:
                sell_votes += 1
                sell_confidence += signal.confidence

        total = len(signals)

        # 买入信号：至少2个策略投票
        if buy_votes >= 2 and buy_votes > sell_votes:
            avg_confidence = buy_confidence / buy_votes
            return SignalType.BUY, avg_confidence, f"{buy_votes}/{total}策略投票买入"

        # 卖出信号：至少2个策略投票
        if sell_votes >= 2 and sell_votes > buy_votes:
            avg_confidence = sell_confidence / sell_votes
            return SignalType.SELL, avg_confidence, f"{sell_votes}/{total}策略投票卖出"

        return (
            SignalType.HOLD,
            0.0,
            f"买入{buy_votes}票，卖出{sell_votes}票，未达成共识",
        )

    def execute_trade(self, signal: TradeSignal, shares: int = None):
        """执行交易"""
        if signal.signal_type == SignalType.BUY:
            # 买入
            if shares is None:
                # 默认使用10%资金
                shares = int(self.cash * 0.1 / signal.price)

            if shares > 0 and self.cash >= shares * signal.price:
                cost = shares * signal.price
                self.cash -= cost

                # 创建持仓
                self.positions[signal.code] = Position(
                    code=signal.code,
                    name=signal.name,
                    shares=shares,
                    cost_price=signal.price,
                    current_price=signal.price,
                    profit_loss=0.0,
                    profit_loss_pct=0.0,
                    buy_date=datetime.now().strftime("%Y-%m-%d"),
                    strategy=signal.strategy,
                )

                # 记录交易
                self.trade_history.append(
                    {
                        "type": "buy",
                        "code": signal.code,
                        "name": signal.name,
                        "price": signal.price,
                        "shares": shares,
                        "strategy": signal.strategy,
                        "timestamp": signal.timestamp,
                    }
                )

                return (
                    True,
                    f"买入成功：{signal.name}({signal.code}) {shares}股 @ {signal.price:.2f}元",
                )

        elif signal.signal_type == SignalType.SELL:
            # 卖出
            if signal.code in self.positions:
                position = self.positions[signal.code]
                revenue = position.shares * signal.price
                self.cash += revenue

                # 计算盈亏
                profit_loss = (signal.price - position.cost_price) * position.shares
                profit_loss_pct = (
                    signal.price - position.cost_price
                ) / position.cost_price

                # 记录交易
                self.trade_history.append(
                    {
                        "type": "sell",
                        "code": signal.code,
                        "name": signal.name,
                        "price": signal.price,
                        "shares": position.shares,
                        "strategy": signal.strategy,
                        "profit_loss": profit_loss,
                        "profit_loss_pct": profit_loss_pct,
                        "timestamp": signal.timestamp,
                    }
                )

                # 删除持仓
                del self.positions[signal.code]

                return (
                    True,
                    f"卖出成功：{signal.name}({signal.code}) {position.shares}股 @ {signal.price:.2f}元，盈亏: {profit_loss:.2f}元 ({profit_loss_pct:.2%})",
                )

        return False, "未执行交易"

    def update_positions(self, price_data: Dict[str, float]):
        """更新持仓市值"""
        for code, position in self.positions.items():
            if code in price_data:
                position.current_price = price_data[code]
                position.profit_loss = (
                    position.current_price - position.cost_price
                ) * position.shares
                position.profit_loss_pct = (
                    position.current_price - position.cost_price
                ) / position.cost_price

    def get_portfolio_summary(self) -> Dict:
        """获取组合摘要"""
        total_market_value = sum(
            p.shares * p.current_price for p in self.positions.values()
        )
        total_profit_loss = sum(p.profit_loss for p in self.positions.values())
        total_value = self.cash + total_market_value
        total_return = (total_value - self.initial_capital) / self.initial_capital

        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions": len(self.positions),
            "market_value": total_market_value,
            "profit_loss": total_profit_loss,
            "total_value": total_value,
            "total_return": total_return,
            "trade_count": len(self.trade_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        summary = self.get_portfolio_summary()

        lines = []
        lines.append("# 实盘验证报告\n")
        lines.append(
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        # 组合摘要
        lines.append("## 组合摘要\n\n")
        lines.append(f"- **初始资金**: {summary['initial_capital']:,.0f}元\n")
        lines.append(f"- **现金余额**: {summary['cash']:,.0f}元\n")
        lines.append(f"- **持仓数量**: {summary['positions']}只\n")
        lines.append(f"- **持仓市值**: {summary['market_value']:,.0f}元\n")
        lines.append(f"- **总资产**: {summary['total_value']:,.0f}元\n")
        lines.append(f"- **总盈亏**: {summary['profit_loss']:,.0f}元\n")
        lines.append(f"- **总收益率**: {summary['total_return']:.2%}\n")
        lines.append(f"- **交易次数**: {summary['trade_count']}次\n\n")

        # 持仓明细
        if self.positions:
            lines.append("## 持仓明细\n\n")
            lines.append("| 股票 | 代码 | 持股 | 成本价 | 现价 | 盈亏 | 收益率 |\n")
            lines.append("|------|------|------|--------|------|------|--------|\n")

            for pos in self.positions.values():
                lines.append(
                    f"| {pos.name} | {pos.code} | {pos.shares}股 | "
                    f"{pos.cost_price:.2f}元 | {pos.current_price:.2f}元 | "
                    f"{pos.profit_loss:.2f}元 | {pos.profit_loss_pct:.2%} |\n"
                )

        # 交易历史
        if self.trade_history:
            lines.append("\n## 交易历史\n\n")
            lines.append("| 时间 | 类型 | 股票 | 价格 | 数量 | 策略 | 盈亏 |\n")
            lines.append("|------|------|------|------|------|------|------|\n")

            for trade in self.trade_history[-10:]:  # 最近10笔
                profit_str = (
                    f"{trade.get('profit_loss', 0):.2f}元"
                    if trade["type"] == "sell"
                    else "-"
                )
                lines.append(
                    f"| {trade['timestamp']} | {trade['type']} | "
                    f"{trade['name']} | {trade['price']:.2f}元 | "
                    f"{trade['shares']}股 | {trade['strategy']} | {profit_str} |\n"
                )

        return "".join(lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实盘验证系统")
    parser.add_argument("--capital", type=float, default=270000, help="初始资金")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--name", type=str, help="股票名称")

    args = parser.parse_args()

    # 创建验证系统
    validator = LiveTradingValidator(initial_capital=args.capital)

    print("实盘验证系统已创建")
    print(f"初始资金: {args.capital:,.0f}元")
    print("\n使用方法:")
    print("  1. 调用 analyze_stock() 分析股票")
    print("  2. 调用 get_combined_signal() 获取组合信号")
    print("  3. 调用 execute_trade() 执行交易")
    print("  4. 调用 generate_report() 生成报告")

    return 0


if __name__ == "__main__":
    sys.exit(main())
