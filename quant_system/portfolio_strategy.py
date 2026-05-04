#!/usr/bin/env python3
"""
组合策略系统
- 多策略投票机制
- 动态权重调整
- 风险分散
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from quant_system.live_trading_validator import SignalType, OptimizedStrategies


@dataclass
class StrategyVote:
    """策略投票"""

    strategy_name: str
    signal: SignalType
    confidence: float
    weight: float
    reason: str


@dataclass
class PortfolioDecision:
    """组合决策"""

    code: str
    name: str
    final_signal: SignalType
    confidence: float
    buy_votes: int
    sell_votes: int
    hold_votes: int
    weighted_score: float
    strategy_votes: List[StrategyVote]
    risk_level: str
    position_size: float  # 建议仓位比例


class MultiStrategyVoting:
    """多策略投票系统"""

    def __init__(self):
        self.strategies = OptimizedStrategies()

        # 策略权重（基于历史表现）
        self.strategy_weights = {
            "ma_cross": 0.25,  # 收益31.16%，胜率75%
            "rsi_reversal": 0.30,  # 收益35.02%，胜率75%
            "strategy_2560": 0.20,  # 收益28.64%
            "breakout_signal": 0.25,  # 收益29.02%
        }

    def vote(self, code: str, name: str, data: pd.DataFrame) -> PortfolioDecision:
        """
        多策略投票

        参数:
            code: 股票代码
            name: 股票名称
            data: OHLCV数据

        返回:
            组合决策
        """
        votes = []

        # MA金叉投票
        signal, confidence, reason = self.strategies.ma_cross_signal(data)
        votes.append(
            StrategyVote(
                strategy_name="ma_cross",
                signal=signal,
                confidence=confidence,
                weight=self.strategy_weights["ma_cross"],
                reason=reason,
            )
        )

        # RSI反转投票
        signal, confidence, reason = self.strategies.rsi_reversal_signal(data)
        votes.append(
            StrategyVote(
                strategy_name="rsi_reversal",
                signal=signal,
                confidence=confidence,
                weight=self.strategy_weights["rsi_reversal"],
                reason=reason,
            )
        )

        # 2560战法投票
        signal, confidence, reason = self.strategies.strategy_2560_signal(data)
        votes.append(
            StrategyVote(
                strategy_name="strategy_2560",
                signal=signal,
                confidence=confidence,
                weight=self.strategy_weights["strategy_2560"],
                reason=reason,
            )
        )

        # 突破信号投票
        signal, confidence, reason = self.strategies.breakout_signal(data)
        votes.append(
            StrategyVote(
                strategy_name="breakout_signal",
                signal=signal,
                confidence=confidence,
                weight=self.strategy_weights["breakout_signal"],
                reason=reason,
            )
        )

        # 统计投票
        buy_votes = sum(1 for v in votes if v.signal == SignalType.BUY)
        sell_votes = sum(1 for v in votes if v.signal == SignalType.SELL)
        hold_votes = sum(1 for v in votes if v.signal == SignalType.HOLD)

        # 计算加权得分
        buy_score = sum(
            v.weight * v.confidence for v in votes if v.signal == SignalType.BUY
        )
        sell_score = sum(
            v.weight * v.confidence for v in votes if v.signal == SignalType.SELL
        )
        weighted_score = buy_score - sell_score

        # 确定最终信号
        if buy_votes >= 3:
            final_signal = SignalType.BUY
            confidence = buy_score
        elif sell_votes >= 3:
            final_signal = SignalType.SELL
            confidence = sell_score
        elif buy_votes >= 2 and buy_votes > sell_votes:
            final_signal = SignalType.BUY
            confidence = buy_score * 0.8  # 降低置信度
        elif sell_votes >= 2 and sell_votes > buy_votes:
            final_signal = SignalType.SELL
            confidence = sell_score * 0.8
        else:
            final_signal = SignalType.HOLD
            confidence = 0.0

        # 风险等级
        if confidence > 0.6:
            risk_level = "低风险"
        elif confidence > 0.3:
            risk_level = "中风险"
        else:
            risk_level = "高风险"

        # 建议仓位
        if final_signal == SignalType.BUY:
            position_size = min(confidence * 0.2, 0.15)  # 最大15%仓位
        else:
            position_size = 0.0

        return PortfolioDecision(
            code=code,
            name=name,
            final_signal=final_signal,
            confidence=confidence,
            buy_votes=buy_votes,
            sell_votes=sell_votes,
            hold_votes=hold_votes,
            weighted_score=weighted_score,
            strategy_votes=votes,
            risk_level=risk_level,
            position_size=position_size,
        )


class PortfolioManager:
    """组合管理器"""

    def __init__(self, total_capital: float = 270000):
        self.total_capital = total_capital
        self.voting_system = MultiStrategyVoting()
        self.positions: Dict[str, Dict] = {}

    def analyze_portfolio(self, stock_list: List[Dict]) -> List[PortfolioDecision]:
        """
        分析股票组合

        参数:
            stock_list: 股票列表 [{"code": "600519", "name": "茅台", "data": df}, ...]

        返回:
            决策列表
        """
        decisions = []

        for stock in stock_list:
            decision = self.voting_system.vote(
                code=stock["code"], name=stock["name"], data=stock["data"]
            )
            decisions.append(decision)

        return decisions

    def allocate_capital(self, decisions: List[PortfolioDecision]) -> Dict[str, float]:
        """
        资金分配

        返回:
            {股票代码: 分配金额}
        """
        allocations = {}
        total_allocation = 0.0

        # 按置信度排序
        buy_decisions = [d for d in decisions if d.final_signal == SignalType.BUY]
        buy_decisions.sort(key=lambda x: x.confidence, reverse=True)

        for decision in buy_decisions:
            # 计算分配金额
            allocation = self.total_capital * decision.position_size

            # 检查总仓位限制（最大80%）
            if total_allocation + allocation > self.total_capital * 0.8:
                allocation = self.total_capital * 0.8 - total_allocation

            if allocation > 0:
                allocations[decision.code] = allocation
                total_allocation += allocation

        return allocations

    def generate_portfolio_report(self, decisions: List[PortfolioDecision]) -> str:
        """生成组合报告"""
        lines = []
        lines.append("# 组合策略报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**总资金**: {self.total_capital:,.0f}元\n\n")

        # 汇总
        buy_count = sum(1 for d in decisions if d.final_signal == SignalType.BUY)
        sell_count = sum(1 for d in decisions if d.final_signal == SignalType.SELL)
        hold_count = sum(1 for d in decisions if d.final_signal == SignalType.HOLD)

        lines.append("## 决策汇总\n\n")
        lines.append(f"- **买入信号**: {buy_count}只\n")
        lines.append(f"- **卖出信号**: {sell_count}只\n")
        lines.append(f"- **持有信号**: {hold_count}只\n\n")

        # 买入建议
        if buy_count > 0:
            lines.append("## 买入建议\n\n")
            lines.append(
                "| 股票 | 代码 | 置信度 | 买入票数 | 卖出票数 | 风险等级 | 建议仓位 |\n"
            )
            lines.append(
                "|------|------|--------|----------|----------|----------|----------|\n"
            )

            for d in decisions:
                if d.final_signal == SignalType.BUY:
                    lines.append(
                        f"| {d.name} | {d.code} | {d.confidence:.2%} | "
                        f"{d.buy_votes}票 | {d.sell_votes}票 | {d.risk_level} | {d.position_size:.1%} |\n"
                    )

        # 资金分配
        allocations = self.allocate_capital(decisions)
        if allocations:
            lines.append("\n## 资金分配\n\n")
            lines.append("| 股票 | 代码 | 分配金额 | 占比 |\n")
            lines.append("|------|------|----------|------|\n")

            for code, amount in allocations.items():
                # 找到对应的决策
                decision = next((d for d in decisions if d.code == code), None)
                if decision:
                    lines.append(
                        f"| {decision.name} | {code} | {amount:,.0f}元 | "
                        f"{amount / self.total_capital:.1%} |\n"
                    )

        # 详细投票
        lines.append("\n## 详细投票\n\n")
        for d in decisions:
            lines.append(f"### {d.name}({d.code})\n\n")
            lines.append(f"**最终决策**: {d.final_signal.value}\n\n")
            lines.append("| 策略 | 信号 | 置信度 | 权重 | 原因 |\n")
            lines.append("|------|------|--------|------|------|\n")

            for vote in d.strategy_votes:
                lines.append(
                    f"| {vote.strategy_name} | {vote.signal.value} | "
                    f"{vote.confidence:.2%} | {vote.weight:.0%} | {vote.reason} |\n"
                )

            lines.append("\n")

        return "".join(lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="组合策略系统")
    parser.add_argument("--capital", type=float, default=270000, help="总资金")

    args = parser.parse_args()

    # 创建组合管理器
    manager = PortfolioManager(total_capital=args.capital)

    print("组合策略系统已创建")
    print(f"总资金: {args.capital:,.0f}元")
    print("\n使用方法:")
    print(
        "  1. 准备股票列表 stock_list = [{'code': '600519', 'name': '茅台', 'data': df}, ...]"
    )
    print("  2. 调用 analyze_portfolio() 分析组合")
    print("  3. 调用 allocate_capital() 分配资金")
    print("  4. 调用 generate_portfolio_report() 生成报告")

    return 0


if __name__ == "__main__":
    sys.exit(main())
