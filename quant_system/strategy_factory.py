# -*- coding: utf-8 -*-
"""
策略工厂模块 - 幻方量化三层策略池中层
- 市场状态识别（趋势市/震荡市）
- 强化学习动态调整策略参数
- 策略切换机制
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class MarketStateDetector:
    """市场状态识别器"""

    def __init__(self):
        self.state = "neutral"
        self.state_score = 0

    def detect(self, data: pd.DataFrame) -> Dict:
        """
        识别市场状态

        返回:
            {
                'state': 'trending'/'oscillating'/'neutral',
                'volatility': 波动率,
                'volume_trend': 成交量趋势,
                'momentum': 动量,
                'confidence': 置信度
            }
        """
        close = data["close"]
        volume = data["volume"]

        # 1. 波动率
        returns = close.pct_change()
        volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)

        # 2. 成交量趋势
        volume_ma5 = volume.rolling(5).mean()
        volume_ma20 = volume.rolling(20).mean()
        volume_trend = volume_ma5.iloc[-1] / volume_ma20.iloc[-1] - 1

        # 3. 动量
        momentum = close.iloc[-1] / close.iloc[-20] - 1

        # 4. 趋势强度（ADX）
        adx = self._calculate_adx(data)

        # 5. 判断市场状态
        if adx > 25 and abs(momentum) > 0.05:
            state = "trending"
            confidence = min(1.0, (adx - 25) / 25 + abs(momentum))
        elif adx < 20 and volatility < 0.3:
            state = "oscillating"
            confidence = min(1.0, (20 - adx) / 20 + (0.3 - volatility) / 0.3)
        else:
            state = "neutral"
            confidence = 0.5

        self.state = state
        self.state_score = confidence

        return {
            "state": state,
            "volatility": volatility,
            "volume_trend": volume_trend,
            "momentum": momentum,
            "adx": adx,
            "confidence": confidence,
        }

    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """计算ADX（平均趋向指数）"""
        high = data["high"]
        low = data["low"]
        close = data["close"]

        # +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # TR
        tr = np.maximum(
            high - low,
            np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))),
        )

        # 平滑
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        # DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

        # ADX
        adx = dx.rolling(period).mean().iloc[-1]

        return adx if not np.isnan(adx) else 20


class StrategyFactory:
    """策略工厂 - 动态调整策略参数"""

    def __init__(self):
        self.detector = MarketStateDetector()
        self.current_strategy = None

    def get_strategy_params(self, market_state: str) -> Dict:
        """根据市场状态获取策略参数"""

        if market_state == "trending":
            # 趋势市：持仓周期长，止损宽，止盈高
            return {
                "holding_period": 5,  # 持仓5天
                "stop_loss": -0.08,  # 止损-8%
                "take_profit_1": 0.10,  # 止盈10%
                "take_profit_2": 0.20,  # 止盈20%
                "take_profit_3": 0.30,  # 止盈30%
                "position_size": 0.20,  # 仓位20%
                "factor_weights": {
                    "momentum": 0.35,
                    "fund_flow": 0.25,
                    "sentiment": 0.20,
                    "fundamental": 0.15,
                    "risk": 0.05,
                },
                "strategy_type": "trend_following",
            }

        elif market_state == "oscillating":
            # 震荡市：快进快出，止损紧，止盈低
            return {
                "holding_period": 1,  # 持仓1天
                "stop_loss": -0.03,  # 止损-3%
                "take_profit_1": 0.03,  # 止盈3%
                "take_profit_2": 0.05,  # 止盈5%
                "take_profit_3": 0.08,  # 止盈8%
                "position_size": 0.10,  # 仓位10%
                "factor_weights": {
                    "momentum": 0.15,
                    "fund_flow": 0.35,
                    "sentiment": 0.25,
                    "fundamental": 0.15,
                    "risk": 0.10,
                },
                "strategy_type": "mean_reversion",
            }

        else:
            # 中性市场：平衡策略
            return {
                "holding_period": 3,  # 持仓3天
                "stop_loss": -0.05,  # 止损-5%
                "take_profit_1": 0.07,  # 止盈7%
                "take_profit_2": 0.12,  # 止盈12%
                "take_profit_3": 0.18,  # 止盈18%
                "position_size": 0.15,  # 仓位15%
                "factor_weights": {
                    "momentum": 0.25,
                    "fund_flow": 0.30,
                    "sentiment": 0.22,
                    "fundamental": 0.18,
                    "risk": 0.05,
                },
                "strategy_type": "balanced",
            }

    def adjust_strategy(self, data: pd.DataFrame) -> Dict:
        """
        动态调整策略

        返回:
            {
                'market_state': 市场状态,
                'strategy_params': 策略参数,
                'adjustment_reason': 调整原因
            }
        """
        # 1. 识别市场状态
        state_info = self.detector.detect(data)
        market_state = state_info["state"]

        # 2. 获取策略参数
        strategy_params = self.get_strategy_params(market_state)

        # 3. 记录调整原因
        adjustment_reason = self._get_adjustment_reason(state_info)

        self.current_strategy = {
            "market_state": market_state,
            "strategy_params": strategy_params,
            "state_info": state_info,
            "adjustment_reason": adjustment_reason,
        }

        return self.current_strategy

    def _get_adjustment_reason(self, state_info: Dict) -> str:
        """获取调整原因"""
        state = state_info["state"]
        volatility = state_info["volatility"]
        momentum = state_info["momentum"]
        adx = state_info["adx"]

        if state == "trending":
            return f"趋势市：ADX={adx:.1f}>25，动量={momentum * 100:.1f}%，延长持仓周期"
        elif state == "oscillating":
            return f"震荡市：ADX={adx:.1f}<20，波动率={volatility * 100:.1f}%，切换高频套利"
        else:
            return f"中性市场：ADX={adx:.1f}，采用平衡策略"

    def should_switch_strategy(self, current_pnl: float, days: int) -> Tuple[bool, str]:
        """
        判断是否需要切换策略

        返回:
            (是否切换, 原因)
        """
        if self.current_strategy is None:
            return False, "未初始化策略"

        strategy_type = self.current_strategy["strategy_params"]["strategy_type"]

        # 趋势策略连续亏损
        if strategy_type == "trend_following":
            if current_pnl < -0.05 and days >= 3:
                return True, "趋势策略连续亏损，切换震荡策略"

        # 震荡策略在趋势市表现差
        if strategy_type == "mean_reversion":
            if current_pnl < -0.03 and days >= 2:
                return True, "震荡策略在趋势市失效，切换趋势策略"

        return False, "当前策略表现正常"


class MetaStrategyGenerator:
    """元策略生成器 - 基于强化学习的策略组合"""

    def __init__(self):
        self.strategies = {
            "trend_following": TrendFollowingStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "momentum": MomentumStrategy(),
        }
        self.strategy_weights = {
            "trend_following": 0.4,
            "mean_reversion": 0.3,
            "momentum": 0.3,
        }

    def generate_signals(self, data: pd.DataFrame, market_state: str) -> Dict:
        """生成组合信号"""
        signals = {}

        for name, strategy in self.strategies.items():
            signal = strategy.generate_signal(data)
            weight = self.strategy_weights[name]
            signals[name] = {
                "signal": signal,
                "weight": weight,
                "weighted_signal": signal * weight,
            }

        # 综合信号
        total_signal = sum(s["weighted_signal"] for s in signals.values())

        # 根据市场状态调整
        if market_state == "trending":
            total_signal *= 1.2  # 放大趋势信号
        elif market_state == "oscillating":
            total_signal *= 0.8  # 缩小信号

        return {
            "signals": signals,
            "total_signal": total_signal,
            "action": "buy"
            if total_signal > 0.5
            else "sell"
            if total_signal < -0.5
            else "hold",
        }

    def update_weights(self, performance: Dict[str, float]):
        """根据表现更新策略权重"""
        total_performance = sum(abs(p) for p in performance.values())

        if total_performance > 0:
            new_weights = {}
            for name, perf in performance.items():
                new_weights[name] = abs(perf) / total_performance

            # 平滑更新
            for name in self.strategy_weights:
                self.strategy_weights[name] = 0.7 * self.strategy_weights[
                    name
                ] + 0.3 * new_weights.get(name, 0.3)


class TrendFollowingStrategy:
    """趋势跟踪策略"""

    def generate_signal(self, data: pd.DataFrame) -> float:
        """生成信号 [-1, 1]"""
        close = data["close"]

        # 均线趋势
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]

        if ma5 > ma20:
            trend_signal = 1
        else:
            trend_signal = -1

        # 动量
        momentum = close.iloc[-1] / close.iloc[-10] - 1
        momentum_signal = np.clip(momentum * 10, -1, 1)

        # 综合信号
        signal = (trend_signal + momentum_signal) / 2

        return np.clip(signal, -1, 1)


class MeanReversionStrategy:
    """均值回归策略"""

    def generate_signal(self, data: pd.DataFrame) -> float:
        """生成信号 [-1, 1]"""
        close = data["close"]

        # 布林带
        ma20 = close.rolling(20).mean().iloc[-1]
        std20 = close.rolling(20).std().iloc[-1]
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        current = close.iloc[-1]

        # 超买超卖
        if current > upper:
            signal = -1  # 超买，卖出
        elif current < lower:
            signal = 1  # 超卖，买入
        else:
            # 均值回归
            signal = -(current - ma20) / (2 * std20)

        return np.clip(signal, -1, 1)


class MomentumStrategy:
    """动量策略"""

    def generate_signal(self, data: pd.DataFrame) -> float:
        """生成信号 [-1, 1]"""
        close = data["close"]

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # RSI信号
        if rsi > 70:
            signal = -1  # 超买
        elif rsi < 30:
            signal = 1  # 超卖
        else:
            signal = (rsi - 50) / 50

        return np.clip(signal, -1, 1)


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("策略工厂模块测试 - 幻方量化三层策略池中层")
    print("=" * 80)

    # 模拟数据
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", "2026-04-30")
    n = len(dates)

    data = pd.DataFrame(
        {
            "close": 100 * (1 + np.random.randn(n).cumsum() * 0.02),
            "high": 102 * (1 + np.random.randn(n).cumsum() * 0.02),
            "low": 98 * (1 + np.random.randn(n).cumsum() * 0.02),
            "volume": np.random.randint(1000000, 10000000, n),
        },
        index=dates,
    )

    # 测试市场状态识别
    print("\n1. 市场状态识别测试")
    print("-" * 80)

    detector = MarketStateDetector()
    state_info = detector.detect(data)

    print(f"市场状态: {state_info['state']}")
    print(f"波动率: {state_info['volatility'] * 100:.1f}%")
    print(f"动量: {state_info['momentum'] * 100:.1f}%")
    print(f"ADX: {state_info['adx']:.1f}")
    print(f"置信度: {state_info['confidence']:.2f}")

    # 测试策略工厂
    print("\n2. 策略工厂测试")
    print("-" * 80)

    factory = StrategyFactory()
    strategy = factory.adjust_strategy(data)

    print(f"市场状态: {strategy['market_state']}")
    print(f"策略类型: {strategy['strategy_params']['strategy_type']}")
    print(f"持仓周期: {strategy['strategy_params']['holding_period']}天")
    print(f"止损: {strategy['strategy_params']['stop_loss'] * 100}%")
    print(f"止盈1: {strategy['strategy_params']['take_profit_1'] * 100}%")
    print(f"因子权重: {strategy['strategy_params']['factor_weights']}")
    print(f"调整原因: {strategy['adjustment_reason']}")

    # 测试元策略生成器
    print("\n3. 元策略生成器测试")
    print("-" * 80)

    generator = MetaStrategyGenerator()
    signals = generator.generate_signals(data, state_info["state"])

    print(f"综合信号: {signals['total_signal']:.3f}")
    print(f"操作建议: {signals['action']}")
    print("\n各策略信号:")
    for name, sig in signals["signals"].items():
        print(f"  {name}: {sig['signal']:.3f} (权重{sig['weight']:.1%})")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
