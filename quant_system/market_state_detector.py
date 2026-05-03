#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场状态检测系统
- 波动率检测（高/正常/低）
- 趋势强度检测（强/中/弱）
- 市场阶段识别（牛市/熊市/震荡）
- 流动性状态（高/中/低）

参考：FactorWeave-Quant 系统
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class VolatilityLevel(Enum):
    """波动率等级"""

    HIGH = "高波动"
    NORMAL = "正常"
    LOW = "低波动"


class TrendStrength(Enum):
    """趋势强度"""

    STRONG = "强趋势"
    MEDIUM = "中等趋势"
    WEAK = "弱趋势"


class MarketRegime(Enum):
    """市场阶段"""

    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡市"


class LiquidityLevel(Enum):
    """流动性水平"""

    HIGH = "高流动性"
    MEDIUM = "中等流动性"
    LOW = "低流动性"


@dataclass
class MarketState:
    """市场状态"""

    volatility: VolatilityLevel
    trend: TrendStrength
    regime: MarketRegime
    liquidity: LiquidityLevel

    # 详细指标
    volatility_value: float = 0.0
    trend_value: float = 0.0
    ma_position: float = 0.0  # 价格相对MA位置
    volume_ratio: float = 1.0  # 量比

    # 建议策略
    suggested_strategy: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "volatility": self.volatility.value,
            "trend": self.trend.value,
            "regime": self.regime.value,
            "liquidity": self.liquidity.value,
            "volatility_value": self.volatility_value,
            "trend_value": self.trend_value,
            "ma_position": self.ma_position,
            "volume_ratio": self.volume_ratio,
            "suggested_strategy": self.suggested_strategy,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"""
市场状态:
  波动率: {self.volatility.value} ({self.volatility_value:.2f}%)
  趋势强度: {self.trend.value} ({self.trend_value:.2f})
  市场阶段: {self.regime.value}
  流动性: {self.liquidity.value}
  价格位置: {self.ma_position:.2f}% (相对MA20)
  量比: {self.volume_ratio:.2f}
  建议策略: {self.suggested_strategy}
"""


class MarketStateDetector:
    """市场状态检测器"""

    def __init__(
        self,
        volatility_window: int = 20,
        trend_window: int = 60,
        ma_short: int = 5,
        ma_medium: int = 20,
        ma_long: int = 60,
    ):
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        self.ma_short = ma_short
        self.ma_medium = ma_medium
        self.ma_long = ma_long

    def detect(self, data: pd.DataFrame) -> MarketState:
        """
        检测市场状态

        Args:
            data: K线数据（需包含 open, high, low, close, volume 列）

        Returns:
            MarketState: 市场状态
        """
        closes = data["close"].values
        volumes = data["volume"].values if "volume" in data.columns else None

        # 1. 波动率检测
        volatility, volatility_value = self._detect_volatility(closes)

        # 2. 趋势强度检测
        trend, trend_value = self._detect_trend(closes)

        # 3. 市场阶段识别
        regime = self._detect_regime(closes)

        # 4. 流动性检测
        liquidity = (
            self._detect_liquidity(volumes)
            if volumes is not None
            else LiquidityLevel.MEDIUM
        )

        # 5. 价格相对MA位置
        ma_position = self._calculate_ma_position(closes)

        # 6. 量比
        volume_ratio = (
            self._calculate_volume_ratio(volumes) if volumes is not None else 1.0
        )

        # 7. 建议策略
        suggested_strategy = self._suggest_strategy(volatility, trend, regime)

        return MarketState(
            volatility=volatility,
            trend=trend,
            regime=regime,
            liquidity=liquidity,
            volatility_value=volatility_value,
            trend_value=trend_value,
            ma_position=ma_position,
            volume_ratio=volume_ratio,
            suggested_strategy=suggested_strategy,
        )

    def _detect_volatility(self, closes: np.ndarray) -> Tuple[VolatilityLevel, float]:
        """检测波动率"""
        if len(closes) < self.volatility_window:
            return VolatilityLevel.NORMAL, 0.0

        # 计算历史波动率（年化）
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns[-self.volatility_window :]) * np.sqrt(252) * 100

        # 判定等级
        if volatility > 30:  # 年化波动率 > 30%
            level = VolatilityLevel.HIGH
        elif volatility < 15:  # 年化波动率 < 15%
            level = VolatilityLevel.LOW
        else:
            level = VolatilityLevel.NORMAL

        return level, volatility

    def _detect_trend(self, closes: np.ndarray) -> Tuple[TrendStrength, float]:
        """检测趋势强度"""
        if len(closes) < self.trend_window:
            return TrendStrength.WEAK, 0.0

        # 计算ADX（平均趋向指数）
        # 简化版：使用价格变化的一致性
        recent_closes = closes[-self.trend_window :]

        # 计算价格变化方向
        changes = np.diff(recent_closes)
        positive_changes = np.sum(changes > 0)
        negative_changes = np.sum(changes < 0)

        # 趋势强度 = 方向一致性
        total_changes = len(changes)
        if total_changes == 0:
            trend_value = 0
        else:
            trend_value = max(positive_changes, negative_changes) / total_changes * 100

        # 判定等级
        if trend_value >= 70:
            level = TrendStrength.STRONG
        elif trend_value >= 55:
            level = TrendStrength.MEDIUM
        else:
            level = TrendStrength.WEAK

        return level, trend_value

    def _detect_regime(self, closes: np.ndarray) -> MarketRegime:
        """识别市场阶段"""
        if len(closes) < self.ma_long:
            return MarketRegime.SIDEWAYS

        # 计算均线
        ma_short = np.mean(closes[-self.ma_short :])
        ma_medium = np.mean(closes[-self.ma_medium :])
        ma_long = np.mean(closes[-self.ma_long :])

        current_price = closes[-1]

        # 判定市场阶段
        # 牛市：短期 > 中期 > 长期，且价格在均线之上
        if ma_short > ma_medium > ma_long and current_price > ma_long:
            return MarketRegime.BULL

        # 熊市：短期 < 中期 < 长期，且价格在均线之下
        if ma_short < ma_medium < ma_long and current_price < ma_long:
            return MarketRegime.BEAR

        # 否则为震荡市
        return MarketRegime.SIDEWAYS

    def _detect_liquidity(self, volumes: np.ndarray) -> LiquidityLevel:
        """检测流动性"""
        if len(volumes) < 20:
            return LiquidityLevel.MEDIUM

        # 计算成交量变化
        recent_volume = np.mean(volumes[-5:])
        avg_volume = np.mean(volumes[-20:])

        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        # 判定等级
        if volume_ratio > 1.5:
            return LiquidityLevel.HIGH
        elif volume_ratio < 0.7:
            return LiquidityLevel.LOW
        else:
            return LiquidityLevel.MEDIUM

    def _calculate_ma_position(self, closes: np.ndarray) -> float:
        """计算价格相对MA位置"""
        if len(closes) < self.ma_medium:
            return 0.0

        ma = np.mean(closes[-self.ma_medium :])
        current_price = closes[-1]

        position = (current_price - ma) / ma * 100

        return position

    def _calculate_volume_ratio(self, volumes: np.ndarray) -> float:
        """计算量比"""
        if len(volumes) < 20:
            return 1.0

        recent_volume = np.mean(volumes[-5:])
        avg_volume = np.mean(volumes[-20:])

        return recent_volume / avg_volume if avg_volume > 0 else 1.0

    def _suggest_strategy(
        self, volatility: VolatilityLevel, trend: TrendStrength, regime: MarketRegime
    ) -> str:
        """建议策略"""
        # 根据市场状态建议策略
        if regime == MarketRegime.BULL:
            if trend == TrendStrength.STRONG:
                return "趋势跟踪策略（持仓为主，逢低加仓）"
            else:
                return "波段操作策略（高抛低吸，控制仓位）"

        elif regime == MarketRegime.BEAR:
            if volatility == VolatilityLevel.HIGH:
                return "防御策略（轻仓或空仓，等待机会）"
            else:
                return "反弹策略（短线为主，快进快出）"

        else:  # 震荡市
            if volatility == VolatilityLevel.HIGH:
                return "区间交易策略（高抛低吸，严格止损）"
            elif volatility == VolatilityLevel.LOW:
                return "网格交易策略（分批建仓，耐心等待）"
            else:
                return "均值回归策略（低买高卖，控制节奏）"


class StrategySelector:
    """策略选择器（根据市场状态选择策略）"""

    def __init__(self):
        self.detector = MarketStateDetector()

        # 策略映射
        self.strategy_map = {
            (MarketRegime.BULL, TrendStrength.STRONG): "趋势跟踪",
            (MarketRegime.BULL, TrendStrength.MEDIUM): "波段操作",
            (MarketRegime.BULL, TrendStrength.WEAK): "高抛低吸",
            (MarketRegime.BEAR, TrendStrength.STRONG): "空仓观望",
            (MarketRegime.BEAR, TrendStrength.MEDIUM): "短线反弹",
            (MarketRegime.BEAR, TrendStrength.WEAK): "防御为主",
            (MarketRegime.SIDEWAYS, TrendStrength.STRONG): "突破跟踪",
            (MarketRegime.SIDEWAYS, TrendStrength.MEDIUM): "区间交易",
            (MarketRegime.SIDEWAYS, TrendStrength.WEAK): "网格交易",
        }

    def select_strategy(self, data: pd.DataFrame) -> Tuple[str, MarketState]:
        """选择策略"""
        state = self.detector.detect(data)

        key = (state.regime, state.trend)
        strategy = self.strategy_map.get(key, "观望")

        return strategy, state

    def get_strategy_params(self, state: MarketState) -> Dict:
        """获取策略参数建议"""
        params = {
            "position_size": 0.5,  # 默认仓位
            "stop_loss": 0.05,  # 默认止损
            "take_profit": 0.10,  # 默认止盈
            "hold_days": 10,  # 默认持仓天数
        }

        # 根据市场状态调整参数
        if state.regime == MarketRegime.BULL:
            params["position_size"] = 0.8
            params["stop_loss"] = 0.08
            params["take_profit"] = 0.15
            params["hold_days"] = 20

        elif state.regime == MarketRegime.BEAR:
            params["position_size"] = 0.3
            params["stop_loss"] = 0.03
            params["take_profit"] = 0.05
            params["hold_days"] = 5

        else:  # 震荡市
            params["position_size"] = 0.5
            params["stop_loss"] = 0.05
            params["take_profit"] = 0.08
            params["hold_days"] = 10

        # 根据波动率调整
        if state.volatility == VolatilityLevel.HIGH:
            params["position_size"] *= 0.7  # 降低仓位
            params["stop_loss"] *= 1.2  # 放宽止损

        elif state.volatility == VolatilityLevel.LOW:
            params["position_size"] *= 1.2  # 提高仓位

        return params


def main():
    """测试市场状态检测"""
    print("=" * 70)
    print("测试市场状态检测系统")
    print("=" * 70)

    # 生成模拟数据
    np.random.seed(42)
    n = 500

    # 牛市数据
    bull_closes = 100 * np.cumprod(1 + np.random.randn(200) * 0.01 + 0.001)

    # 熊市数据
    bear_closes = bull_closes[-1] * np.cumprod(1 + np.random.randn(150) * 0.015 - 0.002)

    # 震荡市数据
    sideways_closes = bear_closes[-1] * np.cumprod(1 + np.random.randn(150) * 0.01)

    # 合并
    closes = np.concatenate([bull_closes, bear_closes, sideways_closes])
    volumes = np.random.randint(1000000, 10000000, len(closes))

    dates = pd.date_range(start="2020-01-01", periods=len(closes), freq="D")

    data = pd.DataFrame(
        {
            "open": closes * (1 + np.random.randn(len(closes)) * 0.005),
            "high": closes * (1 + np.abs(np.random.randn(len(closes))) * 0.01),
            "low": closes * (1 - np.abs(np.random.randn(len(closes))) * 0.01),
            "close": closes,
            "volume": volumes,
        },
        index=dates,
    )

    print(
        f"\n数据区间: {dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}"
    )
    print(f"数据点数: {len(data)}")

    # 创建检测器
    detector = MarketStateDetector()

    # 检测市场状态
    print("\n" + "=" * 70)
    print("整体市场状态")
    print("=" * 70)
    state = detector.detect(data)
    print(state)

    # 检测不同阶段
    print("\n" + "=" * 70)
    print("分阶段检测")
    print("=" * 70)

    # 牛市阶段
    bull_data = data.iloc[:200]
    bull_state = detector.detect(bull_data)
    print(f"\n【牛市阶段】(前200天)")
    print(bull_state)

    # 熊市阶段
    bear_data = data.iloc[200:350]
    bear_state = detector.detect(bear_data)
    print(f"\n【熊市阶段】(200-350天)")
    print(bear_state)

    # 震荡阶段
    sideways_data = data.iloc[350:]
    sideways_state = detector.detect(sideways_data)
    print(f"\n【震荡阶段】(350天后)")
    print(sideways_state)

    # 策略选择
    print("\n" + "=" * 70)
    print("策略选择建议")
    print("=" * 70)

    selector = StrategySelector()
    strategy, final_state = selector.select_strategy(data)
    params = selector.get_strategy_params(final_state)

    print(f"\n推荐策略: {strategy}")
    print(f"\n策略参数:")
    print(f"  仓位比例: {params['position_size'] * 100:.0f}%")
    print(f"  止损比例: {params['stop_loss'] * 100:.1f}%")
    print(f"  止盈比例: {params['take_profit'] * 100:.1f}%")
    print(f"  持仓天数: {params['hold_days']}天")


if __name__ == "__main__":
    main()
