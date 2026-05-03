#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统版本对比回测 - v2.0 vs v4.0
对比不同止损参数下的实际收益
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("系统版本对比回测 - v2.0 vs v4.0")
print("=" * 60)

# 模拟交易数据（基于用户历史交易）
trades = [
    {"stock": "华工科技", "entry": 120.5, "exit": 114.0, "result": "loss"},
    {"stock": "格林达", "entry": 32.0, "exit": 33.18, "result": "profit"},
    {"stock": "川能动力", "entry": 18.5, "exit": 18.82, "result": "profit"},
    {"stock": "新泉股份", "entry": 45.0, "exit": 41.4, "result": "loss"},
    {"stock": "纳百川", "entry": 28.0, "exit": 27.16, "result": "loss"},
    {"stock": "飞荣达", "entry": 36.55, "exit": 38.0, "result": "profit"},  # 假设盈利
    {"stock": "中科曙光", "entry": 113.0, "exit": 94.0, "result": "loss"},  # 大亏损
    {
        "stock": "深南电路",
        "entry": 295.0,
        "exit": 310.0,
        "result": "profit",
    },  # 假设盈利
]

# 不同止损参数
stop_loss_versions = {
    "v2.0": 0.20,  # 20%止损
    "v3.0": 0.10,  # 10%止损
    "v4.0": 0.05,  # 5%止损
}

results = {}

for version, stop_loss in stop_loss_versions.items():
    print(f"\n{version} (止损{stop_loss * 100:.0f}%)")
    print("-" * 60)

    total_profit = 0
    wins = 0
    losses = 0
    max_loss = 0

    for trade in trades:
        entry = trade["entry"]
        exit_price = trade["exit"]
        pnl_pct = (exit_price - entry) / entry

        # 应用止损
        if pnl_pct < -stop_loss:
            # 触发止损
            actual_pnl_pct = -stop_loss
            result = "stopped"
        else:
            actual_pnl_pct = pnl_pct
            result = trade["result"]

        total_profit += actual_pnl_pct

        if actual_pnl_pct > 0:
            wins += 1
        else:
            losses += 1
            max_loss = min(max_loss, actual_pnl_pct)

        print(
            f"  {trade['stock']:8s} | 入场{entry:7.2f} | 出场{exit_price:7.2f} | "
            f"原始{pnl_pct * 100:+6.2f}% | 实际{actual_pnl_pct * 100:+6.2f}% | {result}"
        )

    win_rate = wins / len(trades) * 100
    avg_profit = total_profit / len(trades) * 100

    results[version] = {
        "win_rate": win_rate,
        "total_profit": total_profit * 100,
        "avg_profit": avg_profit,
        "wins": wins,
        "losses": losses,
        "max_loss": max_loss * 100,
    }

# 对比结果
print("\n" + "=" * 60)
print("对比结果")
print("=" * 60)

comparison_df = pd.DataFrame(results).T
comparison_df.columns = [
    "胜率(%)",
    "总收益(%)",
    "平均收益(%)",
    "盈利次数",
    "亏损次数",
    "最大单笔亏损(%)",
]

print(comparison_df.to_string())

# 关键结论
print("\n" + "=" * 60)
print("关键结论")
print("=" * 60)

v2 = results["v2.0"]
v4 = results["v4.0"]

print(
    f"胜率变化: {v2['win_rate']:.1f}% → {v4['win_rate']:.1f}% ({v4['win_rate'] - v2['win_rate']:+.1f}%)"
)
print(
    f"总收益变化: {v2['total_profit']:.2f}% → {v4['total_profit']:.2f}% ({v4['total_profit'] - v2['total_profit']:+.2f}%)"
)
print(
    f"最大亏损变化: {v2['max_loss']:.2f}% → {v4['max_loss']:.2f}% ({v4['max_loss'] - v2['max_loss']:+.2f}%)"
)

if v4["total_profit"] > v2["total_profit"]:
    print("\n结论: v4.0虽然胜率可能降低，但总收益更高，风险控制更好")
else:
    print("\n结论: v4.0需要更多实盘验证")

# 盈亏比分析
print("\n" + "=" * 60)
print("盈亏比分析")
print("=" * 60)

for version, data in results.items():
    if data["losses"] > 0:
        avg_win = data["total_profit"] / data["wins"] if data["wins"] > 0 else 0
        avg_loss = data["total_profit"] / data["losses"] if data["losses"] > 0 else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        print(
            f"{version}: 平均盈利{avg_win:.2f}% / 平均亏损{avg_loss:.2f}% = 盈亏比{profit_loss_ratio:.2f}"
        )
