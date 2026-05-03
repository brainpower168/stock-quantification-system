# -*- coding: utf-8 -*-
"""
真实A股数据回测
使用东方财富API获取历史数据
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from strategy_backtest_validator import StrategyBacktestValidator


def fetch_real_stock_data(stock_code: str, days: int = 365) -> pd.DataFrame:
    """
    从东方财富获取真实A股历史数据

    参数:
        stock_code: 股票代码（如 600519）
        days: 获取天数

    返回:
        OHLCV DataFrame
    """
    print(f"\n获取 {stock_code} 最近 {days} 天数据...")

    # 东方财富日K线API
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # 判断市场代码
    if stock_code.startswith("6"):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"

    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日K
        "fqt": "1",  # 前复权
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


def backtest_real_stocks():
    """用真实A股数据回测"""

    print("\n" + "=" * 60)
    print("真实A股数据策略回测")
    print("=" * 60)

    # 测试股票列表
    stocks = [
        ("600519", "贵州茅台"),
        ("300750", "宁德时代"),
        ("000001", "平安银行"),
        ("002475", "立讯精密"),
        ("601318", "中国平安"),
    ]

    all_results = {}

    for stock_code, stock_name in stocks:
        print(f"\n{'=' * 60}")
        print(f"回测股票: {stock_name} ({stock_code})")
        print("=" * 60)

        # 获取数据
        data = fetch_real_stock_data(stock_code, days=365)

        if data is None or len(data) < 50:
            print(f"跳过 {stock_name}，数据不足")
            continue

        # 运行回测
        validator = StrategyBacktestValidator(initial_capital=100000)
        results = validator.run_all_strategies(data)

        # 保存结果
        all_results[stock_code] = {
            "name": stock_name,
            "results": results,
        }

        # 生成单个股票报告
        report = validator.generate_report()
        print("\n" + report)

    # 生成汇总报告
    print("\n" + "=" * 60)
    print("汇总报告")
    print("=" * 60)

    # 统计各策略在不同股票上的表现
    strategy_stats = {}

    for stock_code, data in all_results.items():
        for strategy_name, result in data["results"].items():
            if "error" not in result:
                if strategy_name not in strategy_stats:
                    strategy_stats[strategy_name] = {
                        "returns": [],
                        "win_rates": [],
                        "max_drawdowns": [],
                    }

                strategy_stats[strategy_name]["returns"].append(result["total_return"])
                strategy_stats[strategy_name]["win_rates"].append(result["win_rate"])
                strategy_stats[strategy_name]["max_drawdowns"].append(
                    result["max_drawdown"]
                )

    # 计算平均表现
    print("\n各策略平均表现:")
    print("-" * 60)
    print(f"{'策略':<20} {'平均收益':>10} {'平均胜率':>10} {'平均回撤':>10}")
    print("-" * 60)

    avg_results = []
    for strategy_name, stats in strategy_stats.items():
        avg_return = np.mean(stats["returns"])
        avg_win_rate = np.mean(stats["win_rates"])
        avg_drawdown = np.mean(stats["max_drawdowns"])

        print(
            f"{strategy_name:<20} {avg_return:>10.2%} {avg_win_rate:>10.2%} {avg_drawdown:>10.2%}"
        )

        avg_results.append(
            {
                "strategy": strategy_name,
                "avg_return": avg_return,
                "avg_win_rate": avg_win_rate,
                "avg_drawdown": avg_drawdown,
            }
        )

    # 找出最优策略
    best_strategy = max(avg_results, key=lambda x: x["avg_return"])

    print("\n" + "=" * 60)
    print(f"最优策略: {best_strategy['strategy']}")
    print(f"平均收益率: {best_strategy['avg_return']:.2%}")
    print(f"平均胜率: {best_strategy['avg_win_rate']:.2%}")
    print(f"平均最大回撤: {best_strategy['avg_drawdown']:.2%}")
    print("=" * 60)

    # 保存报告
    report_path = "data/strategy_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 真实A股数据策略回测报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 测试股票\n\n")
        for stock_code, data in all_results.items():
            f.write(f"- {data['name']} ({stock_code})\n")

        f.write("\n## 各策略平均表现\n\n")
        f.write("| 策略 | 平均收益 | 平均胜率 | 平均回撤 |\n")
        f.write("|------|----------|----------|----------|\n")

        for result in sorted(avg_results, key=lambda x: x["avg_return"], reverse=True):
            f.write(
                f"| {result['strategy']} | {result['avg_return']:.2%} | {result['avg_win_rate']:.2%} | {result['avg_drawdown']:.2%} |\n"
            )

        f.write(f"\n## 最优策略\n\n")
        f.write(f"**{best_strategy['strategy']}**\n\n")
        f.write(f"- 平均收益率: {best_strategy['avg_return']:.2%}\n")
        f.write(f"- 平均胜率: {best_strategy['avg_win_rate']:.2%}\n")
        f.write(f"- 平均最大回撤: {best_strategy['avg_drawdown']:.2%}\n")

    print(f"\n报告已保存到: {report_path}")

    return all_results


if __name__ == "__main__":
    backtest_real_stocks()
