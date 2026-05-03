#!/usr/bin/env python3
"""
策略回测工具 v2
==============
测试"最笨交易法"策略的历史表现

修复：
- 止损后冷却期（5天不买）
- 自动买入信号

使用方法：
    python backtest_strategy_v2.py --stock 002460 --days 90
    python backtest_strategy_v2.py --stock 002460 --entry 80 --days 60
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_historical_data(stock_code: str, days: int = 60) -> pd.DataFrame:
    """获取历史K线数据"""
    import urllib.request

    url = "https://openapi.iwencai.com/v1/query2data"
    api_key = os.environ.get("IWENCAI_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 30)

    query = f"{stock_code} 日K线 {start_date.strftime('%Y%m%d')}至{end_date.strftime('%Y%m%d')} 开盘价 最高价 最低价 收盘价 涨跌幅 成交量"

    payload = {"query": query, "page": "1", "limit": "100", "is_cache": "1"}

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    response = urllib.request.urlopen(request, timeout=30)
    result = json.loads(response.read().decode("utf-8"))

    if result.get("status_code") != 0:
        print(f"获取数据失败: {result.get('status_msg')}")
        return None

    datas = result.get("datas", [])
    if not datas:
        print("无数据返回")
        return None

    # 解析数据
    df = pd.DataFrame()
    for item in datas:
        for key, value in item.items():
            if "收盘价" in key:
                date_str = key.split("[")[1].rstrip("]")
                df.loc[date_str, "close"] = value
            elif "开盘价" in key:
                date_str = key.split("[")[1].rstrip("]")
                df.loc[date_str, "open"] = value
            elif "涨跌幅" in key:
                date_str = key.split("[")[1].rstrip("]")
                df.loc[date_str, "pct_chg"] = value

    df = df.sort_index()
    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标"""
    df = df.copy()
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma5"] = df["close"].rolling(window=5).mean()
    df["is_zt"] = df["pct_chg"] >= 9.9
    df["zt_count_10d"] = df["is_zt"].rolling(window=10).sum()
    df["price_vs_ma20"] = (df["close"] - df["ma20"]) / df["ma20"] * 100
    return df


def backtest_strategy(
    df: pd.DataFrame, entry_price: Optional[float] = None, cooldown_days: int = 5
) -> Dict:
    """
    回测策略

    Args:
        df: K线数据
        entry_price: 指定买入价（模拟持仓）
        cooldown_days: 止损后冷却天数
    """
    df = calculate_indicators(df)

    signals = []
    position = None
    trades = []
    last_sell_idx = -cooldown_days - 1  # 上次卖出位置

    for i in range(20, len(df)):
        date = df.index[i]
        row = df.iloc[i]

        # 指定买入价模拟持仓
        if entry_price and position is None and i == 20:
            position = {
                "entry_date": date,
                "entry_price": entry_price,
                "shares": 100,
            }
            signals.append(
                {
                    "date": date,
                    "type": "BUY",
                    "price": entry_price,
                    "reason": f"模拟买入价 {entry_price}",
                }
            )

        # 买入信号检测
        if position is None:
            # 检查冷却期
            if i - last_sell_idx < cooldown_days:
                continue

            has_zt = row["zt_count_10d"] > 0
            above_ma20 = row["close"] > row["ma20"]
            near_ma20 = abs(row["price_vs_ma20"]) <= 3

            if has_zt and (above_ma20 or near_ma20):
                signals.append(
                    {
                        "date": date,
                        "type": "BUY",
                        "price": row["close"],
                        "reason": f"涨停{row['zt_count_10d']}次，MA20={row['ma20']:.2f}",
                    }
                )
                position = {
                    "entry_date": date,
                    "entry_price": row["close"],
                    "shares": 100,
                }

        # 卖出信号检测
        if position:
            profit_pct = (row["close"] - position["entry_price"]) / position[
                "entry_price"
            ]

            # 止盈
            if profit_pct >= 0.50:
                signals.append(
                    {
                        "date": date,
                        "type": "SELL",
                        "price": row["close"],
                        "reason": f"涨幅{profit_pct * 100:.1f}%，超过50%清仓",
                    }
                )
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "entry": position["entry_price"],
                        "exit_date": date,
                        "exit": row["close"],
                        "profit_pct": profit_pct * 100,
                        "type": "止盈",
                    }
                )
                last_sell_idx = i
                position = None

            elif profit_pct >= 0.30:
                signals.append(
                    {
                        "date": date,
                        "type": "SELL_HALF",
                        "price": row["close"],
                        "reason": f"涨幅{profit_pct * 100:.1f}%，减仓一半",
                    }
                )

            # 止损：跌破20日均线
            elif row["close"] < row["ma20"]:
                signals.append(
                    {
                        "date": date,
                        "type": "STOP_LOSS",
                        "price": row["close"],
                        "reason": f"跌破MA20={row['ma20']:.2f}，止损",
                    }
                )
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "entry": position["entry_price"],
                        "exit_date": date,
                        "exit": row["close"],
                        "profit_pct": profit_pct * 100,
                        "type": "止损",
                    }
                )
                last_sell_idx = i
                position = None

    # 统计
    if trades:
        total_profit = sum(t["profit_pct"] for t in trades)
        win_count = sum(1 for t in trades if t["profit_pct"] > 0)
        win_rate = win_count / len(trades) * 100
        avg_profit = total_profit / len(trades)
    else:
        total_profit = 0
        win_rate = 0
        avg_profit = 0

    return {
        "signals": signals,
        "trades": trades,
        "stats": {
            "total_trades": len(trades),
            "win_trades": win_count if trades else 0,
            "win_rate": win_rate,
            "total_profit_pct": total_profit,
            "avg_profit_pct": avg_profit,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="策略回测 v2")
    parser.add_argument("--stock", type=str, required=True, help="股票代码")
    parser.add_argument("--days", type=int, default=90, help="回测天数")
    parser.add_argument("--entry", type=float, help="模拟买入价")
    parser.add_argument("--cooldown", type=int, default=5, help="止损后冷却天数")

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"策略回测 v2: {args.stock}")
    print(f"{'=' * 60}\n")

    print(f"获取历史数据（{args.days}天）...")
    df = get_historical_data(args.stock, args.days)

    if df is None or df.empty:
        print("获取数据失败")
        return

    print(f"获取到 {len(df)} 条数据\n")

    print("运行回测...")
    result = backtest_strategy(df, args.entry, args.cooldown)

    # 输出结果
    print(f"\n{'=' * 40}")
    print(f"回测结果")
    print(f"{'=' * 40}")
    stats = result["stats"]
    print(f"总交易次数: {stats['total_trades']}")
    print(f"盈利次数: {stats['win_trades']}")
    print(f"胜率: {stats['win_rate']:.1f}%")
    print(f"总收益: {stats['total_profit_pct']:.2f}%")
    print(f"平均收益: {stats['avg_profit_pct']:.2f}%")

    if result["trades"]:
        print(f"\n交易记录:")
        print("-" * 60)
        for t in result["trades"]:
            print(f"  {t['entry_date']} 买入 {t['entry']:.2f}")
            print(f"  {t['exit_date']} 卖出 {t['exit']:.2f} ({t['type']})")
            print(f"  收益: {t['profit_pct']:.2f}%")
            print()

    if result["signals"]:
        print(f"\n最近信号:")
        print("-" * 60)
        for sig in result["signals"][-10:]:
            print(f"  {sig['date']}: {sig['type']} @ {sig['price']:.2f}")
            print(f"    {sig['reason']}")


if __name__ == "__main__":
    main()
