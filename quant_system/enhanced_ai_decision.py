#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版AI决策系统
集成：
1. 热点事件监控
2. 高性能回测
3. 市场状态检测
4. AI Trading Council
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

# 导入新模块
from hot_event_monitor import HotEventMonitor, HotEvent, ImpactDepth
from high_performance_backtest import HighPerformanceBacktestEngine, BacktestResult
from market_state_detector import (
    MarketStateDetector,
    MarketState,
    StrategySelector,
    MarketRegime,
    VolatilityLevel,
    TrendStrength,
)


@dataclass
class EnhancedDecision:
    """增强版决策结果"""

    # 基础信息
    symbol: str
    current_price: float
    decision_time: str

    # 市场状态
    market_state: Optional[MarketState] = None

    # 热点事件
    hot_events: List[HotEvent] = field(default_factory=list)
    industry_events: List[HotEvent] = field(default_factory=list)

    # 回测结果
    backtest_result: Optional[BacktestResult] = None

    # AI决策
    ai_rating: str = "HOLD"  # BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL
    ai_confidence: float = 0.0
    ai_reasoning: str = ""

    # 综合建议
    final_decision: str = "HOLD"
    position_size: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0

    # 风险提示
    risk_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "decision_time": self.decision_time,
            "market_state": self.market_state.to_dict() if self.market_state else None,
            "hot_events_count": len(self.hot_events),
            "industry_events_count": len(self.industry_events),
            "backtest_return": self.backtest_result.total_return
            if self.backtest_result
            else 0,
            "ai_rating": self.ai_rating,
            "ai_confidence": self.ai_confidence,
            "ai_reasoning": self.ai_reasoning,
            "final_decision": self.final_decision,
            "position_size": self.position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_warnings": self.risk_warnings,
        }


class EnhancedAIDecisionSystem:
    """增强版AI决策系统"""

    def __init__(self):
        # 初始化各模块
        self.hot_event_monitor = HotEventMonitor()
        self.backtest_engine = HighPerformanceBacktestEngine(use_jit=True)
        self.market_detector = MarketStateDetector()
        self.strategy_selector = StrategySelector()

        print("增强版AI决策系统已初始化")
        print("  - 热点事件监控: 已启用")
        print("  - 高性能回测: 已启用")
        print("  - 市场状态检测: 已启用")

    def analyze(
        self,
        symbol: str,
        data: pd.DataFrame,
        current_price: Optional[float] = None,
        industry: Optional[str] = None,
    ) -> EnhancedDecision:
        """
        综合分析

        Args:
            symbol: 股票代码
            data: K线数据
            current_price: 当前价格
            industry: 所属行业

        Returns:
            EnhancedDecision: 增强版决策结果
        """
        print(f"\n{'=' * 70}")
        print(f"增强版AI决策分析: {symbol}")
        print(f"{'=' * 70}")

        # 初始化决策对象
        decision = EnhancedDecision(
            symbol=symbol,
            current_price=current_price if current_price else data["close"].iloc[-1],
            decision_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # 1. 市场状态检测
        print("\n[1/4] 市场状态检测...")
        decision.market_state = self.market_detector.detect(data)
        print(f"  波动率: {decision.market_state.volatility.value}")
        print(f"  趋势强度: {decision.market_state.trend.value}")
        print(f"  市场阶段: {decision.market_state.regime.value}")
        print(f"  建议策略: {decision.market_state.suggested_strategy}")

        # 2. 热点事件监控
        print("\n[2/4] 热点事件监控...")
        events = self.hot_event_monitor.fetch_hot_events(limit=20)
        decision.hot_events = events

        # 筛选相关行业事件
        if industry:
            decision.industry_events = self.hot_event_monitor.get_events_by_industry(
                industry
            )

        print(f"  热点事件总数: {len(events)}")
        print(
            f"  深度影响事件: {len([e for e in events if e.impact_depth == ImpactDepth.DEEP])}"
        )
        if decision.industry_events:
            print(f"  {industry}行业相关事件: {len(decision.industry_events)}")

        # 3. 高性能回测
        print("\n[3/4] 策略回测验证...")

        # 根据市场状态选择策略
        strategy_name, _ = self.strategy_selector.select_strategy(data)
        strategy_params = self.strategy_selector.get_strategy_params(
            decision.market_state
        )

        # 定义策略函数（根据市场状态选择）
        def adaptive_strategy(df):
            """自适应策略 - 根据市场状态选择不同策略"""
            df_temp = df.copy()
            signals = np.zeros(len(df))

            if decision.market_state.regime == MarketRegime.SIDEWAYS:
                # 震荡市 → 均值回归策略（布林带）
                df_temp["ma20"] = df_temp["close"].rolling(20).mean()
                df_temp["std20"] = df_temp["close"].rolling(20).std()
                df_temp["upper"] = df_temp["ma20"] + 2 * df_temp["std20"]
                df_temp["lower"] = df_temp["ma20"] - 2 * df_temp["std20"]

                # 下穿下轨买入，上穿上轨卖出
                signals[20:] = np.where(
                    df_temp["close"].values[20:] < df_temp["lower"].values[20:],
                    1,  # 超卖买入
                    np.where(
                        df_temp["close"].values[20:] > df_temp["upper"].values[20:],
                        -1,  # 超买卖出
                        0,  # 其他情况持有
                    ),
                )

            elif decision.market_state.regime == MarketRegime.BULL:
                # 牛市 → 趋势策略（MA金叉）
                df_temp["ma5"] = df_temp["close"].rolling(5).mean()
                df_temp["ma20"] = df_temp["close"].rolling(20).mean()

                signals[20:] = np.where(
                    df_temp["ma5"].values[20:] > df_temp["ma20"].values[20:], 1, -1
                )

            else:  # BEAR
                # 熊市 → 风控策略（空仓或减仓）
                signals[:] = 0  # 空仓

            return signals

        # 运行回测
        decision.backtest_result = self.backtest_engine.run_backtest(
            data=data,
            strategy_func=adaptive_strategy,
            initial_capital=100000,
            stop_loss=strategy_params["stop_loss"],
            take_profit=strategy_params["take_profit"],
            max_hold_days=strategy_params["hold_days"],
        )

        print(f"  回测收益率: {decision.backtest_result.total_return * 100:.2f}%")
        print(f"  最大回撤: {decision.backtest_result.max_drawdown * 100:.2f}%")
        print(f"  夏普比率: {decision.backtest_result.sharpe_ratio:.2f}")
        print(f"  胜率: {decision.backtest_result.win_rate * 100:.1f}%")

        # 4. AI决策（简化版，实际应调用AI Trading Council）
        print("\n[4/4] AI综合决策...")

        # 基于市场状态和回测结果生成决策
        decision.ai_rating, decision.ai_confidence, decision.ai_reasoning = (
            self._generate_ai_decision(
                decision.market_state,
                decision.backtest_result,
                decision.hot_events,
                decision.industry_events,
            )
        )

        print(f"  AI评级: {decision.ai_rating}")
        print(f"  置信度: {decision.ai_confidence * 100:.1f}%")
        print(f"  理由: {decision.ai_reasoning}")

        # 5. 综合建议
        decision.final_decision = decision.ai_rating
        decision.position_size = strategy_params["position_size"]
        decision.stop_loss = strategy_params["stop_loss"]
        decision.take_profit = strategy_params["take_profit"]

        # 6. 风险提示
        decision.risk_warnings = self._generate_risk_warnings(decision)

        print(f"\n{'=' * 70}")
        print("综合建议:")
        print(f"  最终决策: {decision.final_decision}")
        print(f"  建议仓位: {decision.position_size * 100:.0f}%")
        print(f"  止损位: {decision.stop_loss * 100:.1f}%")
        print(f"  止盈位: {decision.take_profit * 100:.1f}%")

        if decision.risk_warnings:
            print(f"\n风险提示:")
            for warning in decision.risk_warnings:
                print(f"  ⚠️ {warning}")

        print(f"{'=' * 70}")

        return decision

    def _generate_ai_decision(
        self,
        market_state: MarketState,
        backtest_result: BacktestResult,
        hot_events: List[HotEvent],
        industry_events: List[HotEvent],
    ) -> Tuple[str, float, str]:
        """生成AI决策（简化版）"""
        score = 50  # 基础分
        reasons = []

        # 1. 市场状态评分
        if market_state.regime.value == "牛市":
            score += 15
            reasons.append("市场处于牛市阶段")
        elif market_state.regime.value == "熊市":
            score -= 15
            reasons.append("市场处于熊市阶段")

        if market_state.trend.value == "强趋势":
            score += 10
            reasons.append("趋势强劲")
        elif market_state.trend.value == "弱趋势":
            score -= 5
            reasons.append("趋势较弱")

        # 2. 回测结果评分
        if backtest_result.total_return > 0.2:
            score += 15
            reasons.append("策略回测表现优秀")
        elif backtest_result.total_return < -0.1:
            score -= 15
            reasons.append("策略回测表现不佳")

        if backtest_result.win_rate > 0.6:
            score += 10
            reasons.append(f"胜率较高({backtest_result.win_rate * 100:.1f}%)")

        if backtest_result.sharpe_ratio > 1.5:
            score += 10
            reasons.append("风险调整收益良好")

        # 3. 热点事件评分
        deep_events = [e for e in hot_events if e.impact_depth == ImpactDepth.DEEP]
        positive_events = [e for e in hot_events if e.sentiment.value == "利好"]

        if len(deep_events) > 3:
            score += 10
            reasons.append("市场热点活跃")

        if len(positive_events) > len(hot_events) * 0.6:
            score += 10
            reasons.append("市场情绪偏乐观")

        # 4. 行业事件评分
        if industry_events:
            positive_industry = [
                e for e in industry_events if e.sentiment.value == "利好"
            ]
            if len(positive_industry) > len(industry_events) * 0.5:
                score += 10
                reasons.append("行业利好较多")

        # 生成评级
        if score >= 80:
            rating = "BUY"
            confidence = 0.8
        elif score >= 65:
            rating = "OVERWEIGHT"
            confidence = 0.65
        elif score >= 50:
            rating = "HOLD"
            confidence = 0.5
        elif score >= 35:
            rating = "UNDERWEIGHT"
            confidence = 0.35
        else:
            rating = "SELL"
            confidence = 0.2

        reasoning = "；".join(reasons) if reasons else "综合分析后建议观望"

        return rating, confidence, reasoning

    def _generate_risk_warnings(self, decision: EnhancedDecision) -> List[str]:
        """生成风险提示"""
        warnings = []

        # 市场风险
        if decision.market_state:
            if decision.market_state.volatility.value == "高波动":
                warnings.append("市场波动率较高，注意控制仓位")

            if decision.market_state.regime.value == "熊市":
                warnings.append("市场处于熊市阶段，谨慎操作")

        # 回测风险
        if decision.backtest_result:
            if decision.backtest_result.max_drawdown < -0.2:
                warnings.append(
                    f"策略历史最大回撤{decision.backtest_result.max_drawdown * 100:.1f}%，注意风险"
                )

            if decision.backtest_result.win_rate < 0.4:
                warnings.append(
                    f"策略胜率较低({decision.backtest_result.win_rate * 100:.1f}%)，需谨慎"
                )

        # 热点风险
        negative_events = [
            e for e in decision.hot_events if e.sentiment.value == "利空"
        ]
        if len(negative_events) > len(decision.hot_events) * 0.5:
            warnings.append("市场利空事件较多，注意风险")

        return warnings

    def generate_report(self, decision: EnhancedDecision) -> str:
        """生成详细报告"""
        report = []
        report.append("=" * 70)
        report.append("增强版AI决策报告")
        report.append("=" * 70)
        report.append(f"股票代码: {decision.symbol}")
        report.append(f"当前价格: {decision.current_price:.2f}")
        report.append(f"分析时间: {decision.decision_time}")
        report.append("")

        # 市场状态
        if decision.market_state:
            report.append("【市场状态】")
            report.append(f"  波动率: {decision.market_state.volatility.value}")
            report.append(f"  趋势强度: {decision.market_state.trend.value}")
            report.append(f"  市场阶段: {decision.market_state.regime.value}")
            report.append(f"  流动性: {decision.market_state.liquidity.value}")
            report.append("")

        # 热点事件
        report.append("【热点事件】")
        report.append(f"  总数: {len(decision.hot_events)}")
        report.append(
            f"  深度影响: {len([e for e in decision.hot_events if e.impact_depth == ImpactDepth.DEEP])}"
        )
        if decision.industry_events:
            report.append(f"  行业相关: {len(decision.industry_events)}")
        report.append("")

        # 回测结果
        if decision.backtest_result:
            report.append("【策略回测】")
            report.append(
                f"  总收益率: {decision.backtest_result.total_return * 100:.2f}%"
            )
            report.append(
                f"  最大回撤: {decision.backtest_result.max_drawdown * 100:.2f}%"
            )
            report.append(f"  夏普比率: {decision.backtest_result.sharpe_ratio:.2f}")
            report.append(f"  胜率: {decision.backtest_result.win_rate * 100:.1f}%")
            report.append("")

        # AI决策
        report.append("【AI决策】")
        report.append(f"  评级: {decision.ai_rating}")
        report.append(f"  置信度: {decision.ai_confidence * 100:.1f}%")
        report.append(f"  理由: {decision.ai_reasoning}")
        report.append("")

        # 综合建议
        report.append("【综合建议】")
        report.append(f"  最终决策: {decision.final_decision}")
        report.append(f"  建议仓位: {decision.position_size * 100:.0f}%")
        report.append(f"  止损位: {decision.stop_loss * 100:.1f}%")
        report.append(f"  止盈位: {decision.take_profit * 100:.1f}%")
        report.append("")

        # 风险提示
        if decision.risk_warnings:
            report.append("【风险提示】")
            for warning in decision.risk_warnings:
                report.append(f"  ⚠️ {warning}")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """测试增强版AI决策系统"""
    print("=" * 70)
    print("测试增强版AI决策系统")
    print("=" * 70)

    # 生成模拟数据
    np.random.seed(42)
    n = 500

    closes = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
    volumes = np.random.randint(1000000, 10000000, n)

    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    data = pd.DataFrame(
        {
            "open": closes * (1 + np.random.randn(n) * 0.005),
            "high": closes * (1 + np.abs(np.random.randn(n)) * 0.01),
            "low": closes * (1 - np.abs(np.random.randn(n)) * 0.01),
            "close": closes,
            "volume": volumes,
        },
        index=dates,
    )

    # 创建决策系统
    system = EnhancedAIDecisionSystem()

    # 运行分析
    decision = system.analyze(symbol="600519", data=data, industry="白酒")

    # 生成报告
    print("\n" + system.generate_report(decision))


if __name__ == "__main__":
    main()
