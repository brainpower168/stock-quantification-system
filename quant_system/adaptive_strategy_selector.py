#!/usr/bin/env python3
"""
自适应策略选择器
根据股票类型、市场状态、风险偏好自动选择最优策略
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class StockType(Enum):
    """股票类型"""

    HIGH_VOLATILITY_GROWTH = "高波动成长股"  # 宁德时代、立讯精密
    STABLE_BLUE_CHIP = "稳定蓝筹股"  # 茅台、中国平安
    BANK_STOCK = "银行股"  # 平安银行
    THEME_STOCK = "题材股"  # 妖股、连板股


class MarketRegime(Enum):
    """市场状态"""

    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡市"


class RiskPreference(Enum):
    """风险偏好"""

    AGGRESSIVE = "激进型"  # 追求高收益
    BALANCED = "稳健型"  # 平衡收益与风险
    CONSERVATIVE = "保守型"  # 控制回撤


@dataclass
class StrategyPerformance:
    """策略表现"""

    name: str
    avg_return: float
    avg_win_rate: float
    avg_drawdown: float
    best_for: List[StockType]
    risk_level: str  # high, medium, low


# 策略表现数据（基于回测结果）
STRATEGY_PERFORMANCES = {
    "ma_cross": StrategyPerformance(
        name="均线交叉",
        avg_return=22.63,
        avg_win_rate=37.56,
        avg_drawdown=-21.78,
        best_for=[StockType.HIGH_VOLATILITY_GROWTH],
        risk_level="high",
    ),
    "rsi_reversal": StrategyPerformance(
        name="RSI反转",
        avg_return=18.40,
        avg_win_rate=62.00,
        avg_drawdown=-18.34,
        best_for=[StockType.STABLE_BLUE_CHIP],
        risk_level="medium",
    ),
    "breakout_signal": StrategyPerformance(
        name="突破信号",
        avg_return=18.08,
        avg_win_rate=43.57,
        avg_drawdown=-17.14,
        best_for=[StockType.HIGH_VOLATILITY_GROWTH, StockType.BANK_STOCK],
        risk_level="medium",
    ),
    "strategy_2560": StrategyPerformance(
        name="2560战法",
        avg_return=16.70,
        avg_win_rate=34.38,
        avg_drawdown=-19.00,
        best_for=[StockType.HIGH_VOLATILITY_GROWTH],
        risk_level="high",
    ),
    "tail_market": StrategyPerformance(
        name="尾盘选股",
        avg_return=10.50,
        avg_win_rate=78.19,
        avg_drawdown=-12.25,
        best_for=[StockType.STABLE_BLUE_CHIP, StockType.BANK_STOCK],
        risk_level="low",
    ),
    "bollinger_band": StrategyPerformance(
        name="布林带",
        avg_return=9.81,
        avg_win_rate=60.00,
        avg_drawdown=-13.42,
        best_for=[StockType.STABLE_BLUE_CHIP],
        risk_level="low",
    ),
    "overnight_holding": StrategyPerformance(
        name="一夜持股",
        avg_return=5.94,
        avg_win_rate=48.35,
        avg_drawdown=-11.21,
        best_for=[StockType.BANK_STOCK],
        risk_level="low",
    ),
}

# 股票类型识别规则
STOCK_TYPE_RULES = {
    # 高波动成长股：高PE、高换手率、高波动
    StockType.HIGH_VOLATILITY_GROWTH: {
        "pe_min": 30,
        "turnover_rate_min": 3,
        "volatility_min": 2.5,
    },
    # 稳定蓝筹股：低PE、稳定盈利、低波动
    StockType.STABLE_BLUE_CHIP: {
        "pe_max": 30,
        "roe_min": 15,
        "volatility_max": 2.0,
    },
    # 银行股：行业=银行
    StockType.BANK_STOCK: {
        "industry": "银行",
    },
}


class AdaptiveStrategySelector:
    """自适应策略选择器"""

    def __init__(self):
        self.strategy_performances = STRATEGY_PERFORMANCES
        self.stock_type_rules = STOCK_TYPE_RULES

    def identify_stock_type(
        self,
        code: str,
        pe: float = None,
        roe: float = None,
        turnover_rate: float = None,
        volatility: float = None,
        industry: str = None,
    ) -> StockType:
        """
        识别股票类型

        Args:
            code: 股票代码
            pe: 市盈率
            roe: 净资产收益率
            turnover_rate: 换手率
            volatility: 波动率
            industry: 行业

        Returns:
            股票类型
        """
        # 银行股特殊处理
        if industry and "银行" in industry:
            return StockType.BANK_STOCK

        # 根据代码判断（已知股票）
        known_stocks = {
            "600519": StockType.STABLE_BLUE_CHIP,  # 茅台
            "300750": StockType.HIGH_VOLATILITY_GROWTH,  # 宁德时代
            "000001": StockType.BANK_STOCK,  # 平安银行
            "002475": StockType.HIGH_VOLATILITY_GROWTH,  # 立讯精密
            "601318": StockType.STABLE_BLUE_CHIP,  # 中国平安
            "601138": StockType.HIGH_VOLATILITY_GROWTH,  # 工业富联
            "002460": StockType.HIGH_VOLATILITY_GROWTH,  # 赣锋锂业
            "002281": StockType.HIGH_VOLATILITY_GROWTH,  # 光迅科技
            "002463": StockType.HIGH_VOLATILITY_GROWTH,  # 沪电股份
            "300476": StockType.HIGH_VOLATILITY_GROWTH,  # 胜宏科技
            "000988": StockType.HIGH_VOLATILITY_GROWTH,  # 华工科技
        }

        if code in known_stocks:
            return known_stocks[code]

        # 根据指标判断
        if pe and turnover_rate and volatility:
            if pe > 30 and turnover_rate > 3 and volatility > 2.5:
                return StockType.HIGH_VOLATILITY_GROWTH
            elif pe < 30 and roe and roe > 15 and volatility < 2.0:
                return StockType.STABLE_BLUE_CHIP

        # 默认返回高波动成长股
        return StockType.HIGH_VOLATILITY_GROWTH

    def select_strategy(
        self,
        stock_type: StockType,
        risk_preference: RiskPreference = RiskPreference.BALANCED,
        market_regime: MarketRegime = MarketRegime.SIDEWAYS,
    ) -> List[Tuple[str, float]]:
        """
        选择最优策略

        Args:
            stock_type: 股票类型
            risk_preference: 风险偏好
            market_regime: 市场状态

        Returns:
            策略列表 [(策略名, 权重), ...]
        """
        # 筛选适合该股票类型的策略
        suitable_strategies = []
        for strategy_name, perf in self.strategy_performances.items():
            if stock_type in perf.best_for:
                suitable_strategies.append((strategy_name, perf))

        if not suitable_strategies:
            # 如果没有完全匹配的，返回所有策略
            suitable_strategies = list(self.strategy_performances.items())

        # 根据风险偏好筛选
        if risk_preference == RiskPreference.CONSERVATIVE:
            # 保守型：只选低风险策略
            suitable_strategies = [
                (name, perf)
                for name, perf in suitable_strategies
                if perf.risk_level == "low"
            ]
        elif risk_preference == RiskPreference.AGGRESSIVE:
            # 激进型：优先高风险策略
            suitable_strategies.sort(key=lambda x: x[1].avg_return, reverse=True)
        else:
            # 稳健型：平衡收益与风险
            suitable_strategies.sort(key=lambda x: x[1].avg_win_rate, reverse=True)

        # 根据市场状态调整
        if market_regime == MarketRegime.BULL:
            # 牛市：优先高收益策略
            suitable_strategies.sort(key=lambda x: x[1].avg_return, reverse=True)
        elif market_regime == MarketRegime.BEAR:
            # 熊市：优先低回撤策略
            suitable_strategies.sort(key=lambda x: x[1].avg_drawdown, reverse=True)

        # 计算权重（基于综合评分）
        def calculate_score(perf: StrategyPerformance) -> float:
            # 综合评分 = 收益率 * 0.4 + 胜率 * 0.3 - 回撤 * 0.3
            return (
                perf.avg_return * 0.4
                + perf.avg_win_rate * 0.3
                + abs(perf.avg_drawdown) * 0.3
            )

        scored_strategies = [
            (name, calculate_score(perf)) for name, perf in suitable_strategies
        ]

        # 归一化权重
        total_score = sum(score for _, score in scored_strategies)
        if total_score > 0:
            weighted_strategies = [
                (name, score / total_score) for name, score in scored_strategies
            ]
        else:
            # 均匀分配
            n = len(scored_strategies)
            weighted_strategies = [(name, 1.0 / n) for name, _ in scored_strategies]

        return weighted_strategies[:3]  # 返回前3个策略

    def get_strategy_recommendation(
        self,
        code: str,
        stock_name: str = None,
        pe: float = None,
        roe: float = None,
        turnover_rate: float = None,
        volatility: float = None,
        industry: str = None,
        risk_preference: RiskPreference = RiskPreference.BALANCED,
        market_regime: MarketRegime = MarketRegime.SIDEWAYS,
    ) -> Dict:
        """
        获取策略推荐

        Returns:
            推荐结果字典
        """
        # 识别股票类型
        stock_type = self.identify_stock_type(
            code, pe, roe, turnover_rate, volatility, industry
        )

        # 选择策略
        strategies = self.select_strategy(stock_type, risk_preference, market_regime)

        # 构建推荐结果
        result = {
            "code": code,
            "name": stock_name or code,
            "stock_type": stock_type.value,
            "risk_preference": risk_preference.value,
            "market_regime": market_regime.value,
            "recommended_strategies": [],
            "strategy_details": [],
        }

        for strategy_name, weight in strategies:
            perf = self.strategy_performances[strategy_name]
            result["recommended_strategies"].append(
                {
                    "name": strategy_name,
                    "display_name": perf.name,
                    "weight": f"{weight:.1%}",
                    "expected_return": f"{perf.avg_return:.2f}%",
                    "win_rate": f"{perf.avg_win_rate:.2f}%",
                    "max_drawdown": f"{perf.avg_drawdown:.2f}%",
                    "risk_level": perf.risk_level,
                }
            )

        # 策略组合建议
        if len(strategies) >= 2:
            result["portfolio_suggestion"] = {
                "primary": strategies[0][0],
                "secondary": strategies[1][0] if len(strategies) > 1 else None,
                "allocation": f"{strategies[0][1]:.0%} + {strategies[1][1]:.0%}"
                if len(strategies) > 1
                else f"{strategies[0][1]:.0%}",
            }

        return result

    def generate_report(self, result: Dict) -> str:
        """生成Markdown格式报告"""
        lines = []

        lines.append(f"# 策略推荐报告")
        lines.append(f"\n**股票**: {result['name']}({result['code']})")
        lines.append(f"**类型**: {result['stock_type']}")
        lines.append(f"**风险偏好**: {result['risk_preference']}")
        lines.append(f"**市场状态**: {result['market_regime']}\n")

        lines.append("## 推荐策略")
        lines.append("\n| 策略 | 权重 | 预期收益 | 胜率 | 最大回撤 | 风险等级 |")
        lines.append("|------|------|----------|------|----------|----------|")

        for strategy in result["recommended_strategies"]:
            lines.append(
                f"| {strategy['display_name']} | {strategy['weight']} | "
                f"{strategy['expected_return']} | {strategy['win_rate']} | "
                f"{strategy['max_drawdown']} | {strategy['risk_level']} |"
            )

        if "portfolio_suggestion" in result:
            lines.append("\n## 组合建议")
            portfolio = result["portfolio_suggestion"]
            lines.append(f"- **主策略**: {portfolio['primary']}")
            if portfolio["secondary"]:
                lines.append(f"- **辅助策略**: {portfolio['secondary']}")
            lines.append(f"- **仓位分配**: {portfolio['allocation']}")

        lines.append("\n## 使用方法")
        lines.append("```bash")
        lines.append(f"# 使用主策略分析")
        lines.append(
            f"python quant_system/strategy_backtest_validator.py --stock {result['code']} --strategy {result['recommended_strategies'][0]['name']}"
        )
        lines.append("```")

        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自适应策略选择器")
    parser.add_argument("--stock", type=str, required=True, help="股票代码")
    parser.add_argument("--name", type=str, help="股票名称")
    parser.add_argument("--pe", type=float, help="市盈率")
    parser.add_argument("--roe", type=float, help="ROE")
    parser.add_argument("--turnover", type=float, help="换手率")
    parser.add_argument("--volatility", type=float, help="波动率")
    parser.add_argument("--industry", type=str, help="行业")
    parser.add_argument(
        "--risk",
        choices=["aggressive", "balanced", "conservative"],
        default="balanced",
        help="风险偏好",
    )
    parser.add_argument(
        "--market",
        choices=["bull", "bear", "sideways"],
        default="sideways",
        help="市场状态",
    )
    parser.add_argument(
        "--output", choices=["json", "markdown"], default="markdown", help="输出格式"
    )
    parser.add_argument("--save", type=str, help="保存报告到文件")

    args = parser.parse_args()

    # 创建选择器
    selector = AdaptiveStrategySelector()

    # 风险偏好映射
    risk_map = {
        "aggressive": RiskPreference.AGGRESSIVE,
        "balanced": RiskPreference.BALANCED,
        "conservative": RiskPreference.CONSERVATIVE,
    }

    # 市场状态映射
    market_map = {
        "bull": MarketRegime.BULL,
        "bear": MarketRegime.BEAR,
        "sideways": MarketRegime.SIDEWAYS,
    }

    # 获取推荐
    result = selector.get_strategy_recommendation(
        code=args.stock,
        stock_name=args.name,
        pe=args.pe,
        roe=args.roe,
        turnover_rate=args.turnover,
        volatility=args.volatility,
        industry=args.industry,
        risk_preference=risk_map[args.risk],
        market_regime=market_map[args.market],
    )

    # 生成报告
    if args.output == "markdown":
        report = selector.generate_report(result)
    else:
        report = json.dumps(result, ensure_ascii=False, indent=2)

    # 打印报告
    print("\n" + "=" * 60)
    print(report)

    # 保存报告
    if args.save:
        output_path = Path(args.save)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存到: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
