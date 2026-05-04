#!/usr/bin/env python3
"""
测试策略参数优化
使用真实A股数据测试参数优化效果
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from quant_system.strategy_param_optimizer import StrategyParamOptimizer


def generate_realistic_data(days: int = 250, seed: int = 42) -> pd.DataFrame:
    """
    生成模拟的真实市场数据
    包含趋势、波动、成交量等特征
    """
    np.random.seed(seed)

    # 生成日期
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    # 生成价格（带趋势和波动）
    returns = np.random.randn(days) * 0.02  # 日收益率2%波动
    trend = np.linspace(0, 0.3, days)  # 30%年度趋势
    prices = 100 * np.exp(np.cumsum(returns + trend / days))

    # 生成OHLCV
    data = pd.DataFrame(
        {
            "date": dates,
            "open": prices * (1 + np.random.randn(days) * 0.01),
            "high": prices * (1 + np.abs(np.random.randn(days) * 0.02)),
            "low": prices * (1 - np.abs(np.random.randn(days) * 0.02)),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, days),
        }
    )
    data.set_index("date", inplace=True)

    return data


def test_ma_cross_optimization():
    """测试MA金叉策略参数优化"""
    print("\n" + "=" * 60)
    print("测试MA金叉策略参数优化")
    print("=" * 60)

    # 生成数据
    data = generate_realistic_data(days=250, seed=42)

    # 创建优化器
    optimizer = StrategyParamOptimizer()

    # 优化参数
    result = optimizer.optimize_ma_cross(
        data, short_range=(3, 10), long_range=(15, 30), step=1
    )

    # 打印结果
    print(f"\n最优参数: {result.best_params}")
    print(f"最优收益: {result.best_return:.2%}")
    print(f"最优胜率: {result.best_win_rate:.2%}")
    print(f"最大回撤: {result.best_drawdown:.2%}")

    # Top 5参数
    print("\nTop 5参数组合:")
    sorted_results = sorted(
        result.all_results, key=lambda x: x["total_return"], reverse=True
    )[:5]

    for i, res in enumerate(sorted_results, 1):
        print(
            f"  {i}. MA({res['short_ma']},{res['long_ma']}) - "
            f"收益: {res['total_return']:.2%}, "
            f"胜率: {res['win_rate']:.2%}"
        )

    return result


def test_rsi_optimization():
    """测试RSI反转策略参数优化"""
    print("\n" + "=" * 60)
    print("测试RSI反转策略参数优化")
    print("=" * 60)

    # 生成数据
    data = generate_realistic_data(days=250, seed=42)

    # 创建优化器
    optimizer = StrategyParamOptimizer()

    # 优化参数
    result = optimizer.optimize_rsi_reversal(
        data,
        period_range=(7, 21),
        oversold_range=(20, 35),
        overbought_range=(65, 80),
        step=2,
    )

    # 打印结果
    print(f"\n最优参数: {result.best_params}")
    print(f"最优收益: {result.best_return:.2%}")
    print(f"最优胜率: {result.best_win_rate:.2%}")
    print(f"最大回撤: {result.best_drawdown:.2%}")

    return result


def test_2560_optimization():
    """测试2560战法参数优化"""
    print("\n" + "=" * 60)
    print("测试2560战法参数优化")
    print("=" * 60)

    # 生成数据
    data = generate_realistic_data(days=250, seed=42)

    # 创建优化器
    optimizer = StrategyParamOptimizer()

    # 优化参数（减少搜索范围以加快速度）
    result = optimizer.optimize_strategy_2560(
        data,
        ma_range=(20, 30),
        vol_short_range=(3, 7),
        vol_long_range=(50, 70),
        touch_range=(0.01, 0.03),
    )

    # 打印结果
    print(f"\n最优参数: {result.best_params}")
    print(f"最优收益: {result.best_return:.2%}")
    print(f"最优胜率: {result.best_win_rate:.2%}")
    print(f"最大回撤: {result.best_drawdown:.2%}")

    return result


def test_breakout_optimization():
    """测试突破信号策略参数优化"""
    print("\n" + "=" * 60)
    print("测试突破信号策略参数优化")
    print("=" * 60)

    # 生成数据
    data = generate_realistic_data(days=250, seed=42)

    # 创建优化器
    optimizer = StrategyParamOptimizer()

    # 优化参数
    result = optimizer.optimize_breakout(data, high_range=(10, 30), low_range=(5, 15))

    # 打印结果
    print(f"\n最优参数: {result.best_params}")
    print(f"最优收益: {result.best_return:.2%}")
    print(f"最优胜率: {result.best_win_rate:.2%}")
    print(f"最大回撤: {result.best_drawdown:.2%}")

    return result


def generate_optimization_report(results: list) -> str:
    """生成优化报告"""
    lines = []
    lines.append("# 策略参数优化报告\n")
    lines.append(f"**优化时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**数据周期**: 250个交易日\n\n")

    # 汇总表
    lines.append("## 优化结果汇总\n\n")
    lines.append("| 策略 | 最优参数 | 最优收益 | 最优胜率 | 最大回撤 |\n")
    lines.append("|------|----------|----------|----------|----------|\n")

    for result in results:
        params_str = str(result.best_params).replace("{", "").replace("}", "")[:40]
        lines.append(
            f"| {result.strategy_name} | {params_str} | "
            f"{result.best_return:.2%} | "
            f"{result.best_win_rate:.2%} | "
            f"{result.best_drawdown:.2%} |\n"
        )

    # 详细结果
    lines.append("\n## 详细优化结果\n\n")

    for result in results:
        lines.append(f"### {result.strategy_name}\n\n")
        lines.append(f"**最优参数**: `{result.best_params}`\n\n")

        # Top 5参数
        sorted_results = sorted(
            result.all_results, key=lambda x: x["total_return"], reverse=True
        )[:5]

        lines.append("**Top 5参数组合**:\n\n")
        for i, res in enumerate(sorted_results, 1):
            if result.strategy_name == "ma_cross":
                params = f"MA({res['short_ma']},{res['long_ma']})"
            elif result.strategy_name == "rsi_reversal":
                params = f"RSI({res['period']},{res['oversold']},{res['overbought']})"
            elif result.strategy_name == "strategy_2560":
                params = f"MA{res['ma_period']}/Vol{res['vol_short']}/{res['vol_long']}"
            elif result.strategy_name == "breakout_signal":
                params = f"High{res['high_period']}/Low{res['low_period']}"
            else:
                params = str(res)

            lines.append(
                f"{i}. {params} - 收益: {res['total_return']:.2%}, "
                f"胜率: {res['win_rate']:.2%}\n"
            )

        lines.append("\n")

    return "".join(lines)


def main():
    """主函数"""
    print("=" * 60)
    print("策略参数优化测试")
    print("=" * 60)

    # 测试各策略优化
    results = []

    # 1. MA金叉
    result1 = test_ma_cross_optimization()
    results.append(result1)

    # 2. RSI反转
    result2 = test_rsi_optimization()
    results.append(result2)

    # 3. 2560战法
    result3 = test_2560_optimization()
    results.append(result3)

    # 4. 突破信号
    result4 = test_breakout_optimization()
    results.append(result4)

    # 生成报告
    print("\n" + "=" * 60)
    print("生成优化报告")
    print("=" * 60)

    report = generate_optimization_report(results)

    # 保存报告
    output_path = PROJECT_ROOT / "data" / "strategy_optimization_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存到: {output_path}")
    print("\n" + report)

    return results


if __name__ == "__main__":
    main()
