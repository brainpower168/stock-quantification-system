# -*- coding: utf-8 -*-
"""
回测引擎修复前后对比测试
- 对比未来函数修复效果
- 对比交易成本模型
- 对比回测结果差异
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入修复前后的回测引擎
from high_performance_backtest import HighPerformanceBacktestEngine
from backtest_engine_fixed import FixedBacktestEngine, CommissionConfig, SlippageConfig


def fetch_real_stock_data(stock_code: str, days: int = 365) -> pd.DataFrame:
    """从东方财富获取真实A股历史数据"""
    print(f"\n获取 {stock_code} 最近 {days} 天数据...")

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    if stock_code.startswith("6"):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"

    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "end": "20500000",
        "lmt": str(days),
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]

                rows = []
                for kline in klines:
                    parts = kline.split(",")
                    rows.append(
                        {
                            "date": parts[0],
                            "open": float(parts[1]),
                            "close": float(parts[2]),
                            "high": float(parts[3]),
                            "low": float(parts[4]),
                            "volume": float(parts[5]),
                            "amount": float(parts[6]),
                        }
                    )

                df = pd.DataFrame(rows)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)

                print(f"获取成功，共 {len(df)} 条数据")
                print(
                    f"日期范围: {df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}"
                )
                print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

                return df
            else:
                print("API返回数据为空")
                return None
        else:
            print(f"API请求失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"获取数据失败: {e}")
        return None


def ma_cross_strategy_old(data: pd.DataFrame) -> np.ndarray:
    """MA金叉策略（用于旧引擎，返回信号数组）"""
    n = len(data)
    signals = np.zeros(n, dtype=np.int32)

    if n < 30:
        return signals

    # 计算5日和20日均线
    ma5 = data["close"].rolling(5).mean()
    ma20 = data["close"].rolling(20).mean()

    for i in range(1, n):
        # 金叉买入
        if ma5.iloc[i] > ma20.iloc[i] and ma5.iloc[i - 1] <= ma20.iloc[i - 1]:
            signals[i] = 1
        # 死叉卖出
        elif ma5.iloc[i] < ma20.iloc[i] and ma5.iloc[i - 1] >= ma20.iloc[i - 1]:
            signals[i] = -1

    return signals


def ma_cross_strategy_new(data: pd.DataFrame) -> int:
    """MA金叉策略（用于新引擎，返回单个信号）"""
    if len(data) < 30:
        return 0

    # 计算5日和20日均线
    ma5 = data["close"].rolling(5).mean()
    ma20 = data["close"].rolling(20).mean()

    # 金叉买入，死叉卖出
    if ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-2] <= ma20.iloc[-2]:
        return 1  # 买入
    elif ma5.iloc[-1] < ma20.iloc[-1] and ma5.iloc[-2] >= ma20.iloc[-2]:
        return -1  # 卖出
    else:
        return 0  # 持有


def compare_backtest(stock_code: str, stock_name: str):
    """对比修复前后的回测结果"""

    print(f"\n{'=' * 80}")
    print(f"对比测试: {stock_name} ({stock_code})")
    print(f"{'=' * 80}")

    # 获取数据
    data = fetch_real_stock_data(stock_code, days=365)
    if data is None or len(data) < 50:
        print(f"跳过 {stock_name}，数据不足")
        return None

    # 准备数据格式
    data_old = data.copy()
    data_new = data.copy()

    print(f"\n{'=' * 80}")
    print("1. 修复前回测引擎（存在未来函数）")
    print(f"{'=' * 80}")

    # 旧引擎回测（禁用JIT避免兼容性问题）
    old_engine = HighPerformanceBacktestEngine(use_jit=False)
    old_result = old_engine.run_backtest(
        data_old, ma_cross_strategy_old, initial_capital=100000
    )

    print(f"\n修复前结果:")
    print(f"  总收益率: {old_result.total_return:.2%}")
    print(f"  年化收益: {old_result.annual_return:.2%}")
    print(f"  最大回撤: {old_result.max_drawdown:.2%}")
    print(f"  夏普比率: {old_result.sharpe_ratio:.2f}")
    print(f"  胜率: {old_result.win_rate:.2%}")
    print(f"  交易次数: {old_result.total_trades}")
    print(
        f"  回测速度: {old_result.backtest_time:.4f}秒 ({old_result.data_points / old_result.backtest_time:.0f}条/秒)"
    )

    print(f"\n{'=' * 80}")
    print("2. 修复后回测引擎（无未来函数 + 完整交易成本）")
    print(f"{'=' * 80}")

    # 新引擎回测
    new_engine = FixedBacktestEngine(
        commission_config=CommissionConfig(),  # 默认A股交易成本
        slippage_config=SlippageConfig(),
    )
    new_result = new_engine.run_backtest(
        data_new, ma_cross_strategy_new, initial_capital=100000
    )

    print(f"\n修复后结果:")
    print(f"  总收益率: {new_result.total_return:.2%}")
    print(f"  年化收益: {new_result.annual_return:.2%}")
    print(f"  最大回撤: {new_result.max_drawdown:.2%}")
    print(f"  夏普比率: {new_result.sharpe_ratio:.2f}")
    print(f"  胜率: {new_result.win_rate:.2%}")
    print(f"  交易次数: {new_result.total_trades}")
    print(
        f"  回测速度: {new_result.backtest_time:.4f}秒 ({new_result.data_points / new_result.backtest_time:.0f}条/秒)"
    )

    print(f"\n{'=' * 80}")
    print("3. 差异分析")
    print(f"{'=' * 80}")

    # 计算差异
    return_diff = new_result.total_return - old_result.total_return
    drawdown_diff = new_result.max_drawdown - old_result.max_drawdown
    sharpe_diff = new_result.sharpe_ratio - old_result.sharpe_ratio
    winrate_diff = new_result.win_rate - old_result.win_rate

    print(f"\n收益率变化: {return_diff:+.2%}")
    print(f"最大回撤变化: {drawdown_diff:+.2%}")
    print(f"夏普比率变化: {sharpe_diff:+.2f}")
    print(f"胜率变化: {winrate_diff:+.2%}")

    # 分析原因
    print(f"\n差异原因分析:")
    if return_diff < 0:
        print(f"  ✅ 修复后收益率下降 {abs(return_diff):.2%}，这是正常的！")
        print(f"     - 未来函数修复：信号基于昨日数据，无法看到未来")
        print(f"     - 交易成本增加：印花税+佣金+过户费+滑点")
    else:
        print(f"  ⚠️ 修复后收益率上升 {return_diff:.2%}，需要检查！")

    if new_result.total_trades < old_result.total_trades:
        print(
            f"  📊 交易次数减少 {old_result.total_trades - new_result.total_trades} 次"
        )
        print(f"     - 可能原因：未来函数修复后，信号更保守")

    # 返回对比结果
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "old_result": {
            "total_return": old_result.total_return,
            "annual_return": old_result.annual_return,
            "max_drawdown": old_result.max_drawdown,
            "sharpe_ratio": old_result.sharpe_ratio,
            "win_rate": old_result.win_rate,
            "total_trades": old_result.total_trades,
        },
        "new_result": {
            "total_return": new_result.total_return,
            "annual_return": new_result.annual_return,
            "max_drawdown": new_result.max_drawdown,
            "sharpe_ratio": new_result.sharpe_ratio,
            "win_rate": new_result.win_rate,
            "total_trades": new_result.total_trades,
        },
        "diff": {
            "return_diff": return_diff,
            "drawdown_diff": drawdown_diff,
            "sharpe_diff": sharpe_diff,
            "winrate_diff": winrate_diff,
        },
    }


def main():
    """主函数"""

    print("\n" + "=" * 80)
    print("回测引擎修复前后对比测试")
    print("=" * 80)
    print("\n测试目标:")
    print("1. 验证未来函数修复效果")
    print("2. 验证交易成本模型改进")
    print("3. 对比回测结果差异")
    print("\n修复内容:")
    print("- 未来函数：信号从当日收盘价生成 → 昨日数据生成，今日开盘执行")
    print("- 交易成本：简单费率 → 印花税+佣金+过户费+滑点+冲击成本")

    # 测试股票列表
    stocks = [
        ("600519", "贵州茅台"),
        ("300750", "宁德时代"),
        ("000001", "平安银行"),
        ("002475", "立讯精密"),
        ("601318", "中国平安"),
    ]

    all_results = []

    for stock_code, stock_name in stocks:
        result = compare_backtest(stock_code, stock_name)
        if result:
            all_results.append(result)

    # 生成汇总报告
    print(f"\n{'=' * 80}")
    print("汇总报告")
    print(f"{'=' * 80}")

    print(
        f"\n{'股票':<12} {'修复前收益':>12} {'修复后收益':>12} {'差异':>10} {'修复前胜率':>10} {'修复后胜率':>10}"
    )
    print("-" * 80)

    for result in all_results:
        print(
            f"{result['stock_name']:<12} "
            f"{result['old_result']['total_return']:>12.2%} "
            f"{result['new_result']['total_return']:>12.2%} "
            f"{result['diff']['return_diff']:>+10.2%} "
            f"{result['old_result']['win_rate']:>10.2%} "
            f"{result['new_result']['win_rate']:>10.2%}"
        )

    # 计算平均差异
    avg_return_diff = np.mean([r["diff"]["return_diff"] for r in all_results])
    avg_drawdown_diff = np.mean([r["diff"]["drawdown_diff"] for r in all_results])
    avg_winrate_diff = np.mean([r["diff"]["winrate_diff"] for r in all_results])

    print(f"\n平均差异:")
    print(f"  收益率: {avg_return_diff:+.2%}")
    print(f"  最大回撤: {avg_drawdown_diff:+.2%}")
    print(f"  胜率: {avg_winrate_diff:+.2%}")

    print(f"\n{'=' * 80}")
    print("结论")
    print(f"{'=' * 80}")

    if avg_return_diff < 0:
        print(f"\n✅ 修复后收益率平均下降 {abs(avg_return_diff):.2%}，符合预期！")
        print(f"   - 未来函数修复消除了虚假收益")
        print(f"   - 完整交易成本更接近真实情况")
        print(f"   - 回测结果更可信，可用于实盘决策")
    else:
        print(f"\n⚠️ 修复后收益率平均上升 {avg_return_diff:.2%}，需要检查原因！")

    # 保存报告
    report_path = "data/backtest_fix_comparison.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 回测引擎修复前后对比报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 修复内容\n\n")
        f.write("### 1. 未来函数修复\n\n")
        f.write("- **修复前**: 信号基于当日收盘价生成（能看到未来）\n")
        f.write("- **修复后**: 信号基于昨日数据生成，今日开盘执行\n\n")

        f.write("### 2. 交易成本模型\n\n")
        f.write("- **修复前**: 简单费率（买入0.03%，卖出0.13%）\n")
        f.write("- **修复后**: 完整模型\n")
        f.write("  - 印花税：卖出千分之一\n")
        f.write("  - 佣金：万分之三，最低5元\n")
        f.write("  - 过户费：十万分之一\n")
        f.write("  - 滑点：基础0.01% + 成交量冲击\n\n")

        f.write("## 对比结果\n\n")
        f.write("| 股票 | 修复前收益 | 修复后收益 | 差异 | 修复前胜率 | 修复后胜率 |\n")
        f.write("|------|------------|------------|------|------------|------------|\n")

        for result in all_results:
            f.write(
                f"| {result['stock_name']} | "
                f"{result['old_result']['total_return']:.2%} | "
                f"{result['new_result']['total_return']:.2%} | "
                f"{result['diff']['return_diff']:+.2%} | "
                f"{result['old_result']['win_rate']:.2%} | "
                f"{result['new_result']['win_rate']:.2%} |\n"
            )

        f.write(f"\n## 平均差异\n\n")
        f.write(f"- 收益率: {avg_return_diff:+.2%}\n")
        f.write(f"- 最大回撤: {avg_drawdown_diff:+.2%}\n")
        f.write(f"- 胜率: {avg_winrate_diff:+.2%}\n")

        f.write(f"\n## 结论\n\n")
        if avg_return_diff < 0:
            f.write(
                f"✅ 修复后收益率平均下降 {abs(avg_return_diff):.2%}，符合预期。\n\n"
            )
            f.write("**原因分析**:\n")
            f.write("1. 未来函数修复消除了虚假收益\n")
            f.write("2. 完整交易成本更接近真实情况\n")
            f.write("3. 回测结果更可信，可用于实盘决策\n")
        else:
            f.write(f"⚠️ 修复后收益率平均上升 {avg_return_diff:.2%}，需要进一步检查。\n")

    print(f"\n报告已保存到: {report_path}")

    return all_results


if __name__ == "__main__":
    main()
