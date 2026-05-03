#!/usr/bin/env python3
"""
实盘监控和预警系统 v2.0
========================
整合反转信号检测 + 买入纪律检查 + DDX资金管理

功能：
1. 持仓监控（止损/止盈预警）
2. 自选股监控（买入信号检测）
3. 反转信号检测（单日主力>10亿 + 涨幅>3%）
4. 每日报告生成

使用方法：
    python position_monitor_v2.py --check      # 单次检查
    python position_monitor_v2.py --watch      # 持续监控
    python position_monitor_v2.py --report     # 生成报告
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PositionMonitorV2:
    """实盘监控和预警系统 v2.0"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 用户持仓（从MEMORY.md读取）
        self.positions = {
            "002916": {
                "name": "深南电路",
                "cost": 295.0,
                "shares": 100,
                "stop_loss": -0.05,
            },
            "603019": {
                "name": "中科曙光",
                "cost": 93.57,
                "shares": 100,
                "stop_loss": -0.05,
            },
            "603931": {
                "name": "格林达",
                "cost": 32.0,
                "shares": 1000,
                "stop_loss": -0.05,
            },
        }

        # 用户自选股
        self.watchlist = [
            "601138",  # 工业富联
            "002475",  # 立讯精密
            "002460",  # 赣锋锂业
            "002281",  # 光迅科技
            "002463",  # 沪电股份
            "300750",  # 宁德时代
            "300476",  # 胜宏科技
            "000988",  # 华工科技
        ]

        # 预警阈值
        self.stop_loss_threshold = self.config.get("stop_loss_threshold", -0.05)  # -5%
        self.take_profit_threshold = self.config.get(
            "take_profit_threshold", 0.10
        )  # +10%
        self.reversal_main_inflow = self.config.get(
            "reversal_main_inflow", 1000000000
        )  # 10亿
        self.reversal_change_pct = self.config.get("reversal_change_pct", 3.0)  # 3%

    def check_positions(self, quotes: Dict[str, Dict]) -> List[Dict]:
        """
        检查持仓状态

        Args:
            quotes: 股票行情字典 {code: {price, change_pct, main_inflow, ddx_10, ...}}

        Returns:
            预警列表
        """
        alerts = []

        for code, position in self.positions.items():
            quote = quotes.get(code, {})
            current_price = quote.get("price", position["cost"])
            change_pct = quote.get("change_pct", 0)
            main_inflow = quote.get("main_inflow", 0)
            ddx_10 = quote.get("ddx_10", 0)

            # 计算盈亏
            profit_pct = (current_price - position["cost"]) / position["cost"]
            profit_amount = (current_price - position["cost"]) * position["shares"]

            # 止损预警
            if profit_pct <= self.stop_loss_threshold:
                alerts.append(
                    {
                        "type": "STOP_LOSS",
                        "code": code,
                        "name": position["name"],
                        "message": f"⚠️ 止损预警：{position['name']}({code}) 亏损{profit_pct * 100:.1f}%，建议止损",
                        "data": {
                            "current_price": current_price,
                            "cost": position["cost"],
                            "profit_pct": profit_pct,
                            "profit_amount": profit_amount,
                            "main_inflow": main_inflow,
                            "ddx_10": ddx_10,
                        },
                    }
                )

            # 止盈预警
            elif profit_pct >= self.take_profit_threshold:
                alerts.append(
                    {
                        "type": "TAKE_PROFIT",
                        "code": code,
                        "name": position["name"],
                        "message": f"✅ 止盈预警：{position['name']}({code}) 盈利{profit_pct * 100:.1f}%，建议止盈",
                        "data": {
                            "current_price": current_price,
                            "cost": position["cost"],
                            "profit_pct": profit_pct,
                            "profit_amount": profit_amount,
                            "main_inflow": main_inflow,
                            "ddx_10": ddx_10,
                        },
                    }
                )

            # 主力流出预警
            if main_inflow < 0 and ddx_10 < 0:
                alerts.append(
                    {
                        "type": "CAPITAL_OUTFLOW",
                        "code": code,
                        "name": position["name"],
                        "message": f"⚠️ 资金流出：{position['name']}({code}) 主力流出{abs(main_inflow) / 100000000:.2f}亿，10日DDX={ddx_10:.3f}",
                        "data": {
                            "current_price": current_price,
                            "main_inflow": main_inflow,
                            "ddx_10": ddx_10,
                        },
                    }
                )

        return alerts

    def check_watchlist(self, quotes: Dict[str, Dict]) -> List[Dict]:
        """
        检查自选股买入信号

        Args:
            quotes: 股票行情字典

        Returns:
            买入信号列表
        """
        signals = []

        for code in self.watchlist:
            quote = quotes.get(code, {})
            if not quote:
                continue

            name = quote.get("name", code)
            price = quote.get("price", 0)
            change_pct = quote.get("change_pct", 0)
            main_inflow = quote.get("main_inflow", 0)
            ddx_10 = quote.get("ddx_10", 0)
            pe = quote.get("pe", 100)
            roe = quote.get("roe", 0)
            profit_growth = quote.get("profit_growth", 0)

            # 买入纪律检查
            checks = {
                "10日DDX>0": ddx_10 > 0,
                "今日主力流入>0": main_inflow > 0,
                "涨幅<3%": abs(change_pct) < 3,
                "PE<50": pe < 50,
                "ROE>10%": roe > 10,
                "净利润增长>0": profit_growth > 0,
            }

            passed = sum(checks.values())

            # 反转信号检测
            is_reversal = (
                main_inflow > self.reversal_main_inflow
                and change_pct > self.reversal_change_pct
                and ddx_10 < 0
            )

            # 常规买入信号
            if passed >= 4 and not is_reversal:
                signals.append(
                    {
                        "type": "BUY_SIGNAL",
                        "code": code,
                        "name": name,
                        "message": f"✅ 买入信号：{name}({code}) 通过{passed}/6项纪律检查",
                        "data": {
                            "price": price,
                            "change_pct": change_pct,
                            "main_inflow": main_inflow,
                            "ddx_10": ddx_10,
                            "checks": checks,
                            "passed": passed,
                        },
                    }
                )

            # 反转信号
            elif is_reversal:
                signals.append(
                    {
                        "type": "REVERSAL_SIGNAL",
                        "code": code,
                        "name": name,
                        "message": f"⚠️ 反转信号：{name}({code}) 单日主力{main_inflow / 100000000:.2f}亿 + 涨幅{change_pct:.1f}%，需次日确认",
                        "data": {
                            "price": price,
                            "change_pct": change_pct,
                            "main_inflow": main_inflow,
                            "ddx_10": ddx_10,
                            "action": "次日确认主力继续流入后再买入",
                        },
                    }
                )

        return signals

    def generate_report(self, quotes: Dict[str, Dict]) -> str:
        """
        生成每日报告

        Args:
            quotes: 股票行情字典

        Returns:
            报告文本
        """
        report = f"# 每日监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        # 持仓概览
        report += "## 一、持仓概览\n\n"
        report += "| 股票 | 代码 | 成本 | 现价 | 盈亏% | 主力流入 | 10日DDX | 建议 |\n"
        report += "|------|------|------|------|-------|----------|---------|------|\n"

        for code, position in self.positions.items():
            quote = quotes.get(code, {})
            current_price = quote.get("price", position["cost"])
            profit_pct = (current_price - position["cost"]) / position["cost"] * 100
            main_inflow = quote.get("main_inflow", 0)
            ddx_10 = quote.get("ddx_10", 0)

            # 建议判断
            if profit_pct <= -5:
                advice = "止损"
            elif profit_pct >= 10:
                advice = "止盈"
            elif ddx_10 > 0:
                advice = "持有"
            else:
                advice = "观望"

            report += f"| {position['name']} | {code} | {position['cost']:.2f} | {current_price:.2f} | {profit_pct:+.1f}% | {main_inflow / 100000000:.2f}亿 | {ddx_10:.3f} | {advice} |\n"

        # 自选股监控
        report += "\n## 二、自选股监控\n\n"
        report += "| 股票 | 代码 | 现价 | 涨幅 | 主力流入 | 10日DDX | 信号类型 |\n"
        report += "|------|------|------|------|----------|---------|----------|\n"

        signals = self.check_watchlist(quotes)
        for signal in signals:
            data = signal["data"]
            report += f"| {signal['name']} | {signal['code']} | {data['price']:.2f} | {data['change_pct']:+.1f}% | {data['main_inflow'] / 100000000:.2f}亿 | {data['ddx_10']:.3f} | {signal['type']} |\n"

        # 预警信息
        alerts = self.check_positions(quotes)
        if alerts:
            report += "\n## 三、预警信息\n\n"
            for alert in alerts:
                report += f"- {alert['message']}\n"

        # 反转信号
        reversal_signals = [s for s in signals if s["type"] == "REVERSAL_SIGNAL"]
        if reversal_signals:
            report += "\n## 四、反转信号\n\n"
            report += "**次日需确认主力继续流入后再买入**\n\n"
            for signal in reversal_signals:
                report += f"- {signal['message']}\n"

        return report

    def save_report(self, report: str, filename: Optional[str] = None):
        """保存报告"""
        if filename is None:
            filename = f"monitor_report_{datetime.now().strftime('%Y-%m-%d')}.md"

        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", filename
        )

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"报告已保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="实盘监控和预警系统 v2.0")
    parser.add_argument("--check", action="store_true", help="单次检查")
    parser.add_argument("--watch", action="store_true", help="持续监控")
    parser.add_argument("--report", action="store_true", help="生成报告")

    args = parser.parse_args()

    monitor = PositionMonitorV2()

    # 模拟行情数据（实际应从API获取）
    quotes = {
        "002916": {
            "name": "深南电路",
            "price": 301.36,
            "change_pct": 0.02,
            "main_inflow": 87040000,
            "ddx_10": 0.301,
        },
        "603019": {
            "name": "中科曙光",
            "price": 92.76,
            "change_pct": 1.18,
            "main_inflow": 736400000,
            "ddx_10": 0.564,
        },
        "603931": {
            "name": "格林达",
            "price": 31.34,
            "change_pct": -2.09,
            "main_inflow": -13930000,
            "ddx_10": 1.028,
        },
        "601138": {
            "name": "工业富联",
            "price": 20.0,
            "change_pct": -1.0,
            "main_inflow": -1725000000,
            "ddx_10": 0.258,
        },
        "002475": {
            "name": "立讯精密",
            "price": 30.0,
            "change_pct": -0.5,
            "main_inflow": -1160000000,
            "ddx_10": 0.226,
        },
        "002460": {
            "name": "赣锋锂业",
            "price": 40.0,
            "change_pct": 6.4,
            "main_inflow": 1131000000,
            "ddx_10": -3.402,
        },
        "002281": {
            "name": "光迅科技",
            "price": 50.0,
            "change_pct": -2.0,
            "main_inflow": -302200000,
            "ddx_10": -0.755,
        },
        "002463": {
            "name": "沪电股份",
            "price": 25.0,
            "change_pct": -1.5,
            "main_inflow": -1274000000,
            "ddx_10": -0.812,
        },
        "300750": {
            "name": "宁德时代",
            "price": 200.0,
            "change_pct": 2.0,
            "main_inflow": 1914000000,
            "ddx_10": 0.16,
        },
        "300476": {
            "name": "胜宏科技",
            "price": 30.0,
            "change_pct": -1.0,
            "main_inflow": -100000000,
            "ddx_10": -1.662,
        },
        "000988": {
            "name": "华工科技",
            "price": 116.0,
            "change_pct": -1.0,
            "main_inflow": -50000000,
            "ddx_10": -6.489,
        },
    }

    if args.check:
        print("\n" + "=" * 60)
        print("持仓检查")
        print("=" * 60 + "\n")

        alerts = monitor.check_positions(quotes)
        if alerts:
            for alert in alerts:
                print(f"{alert['message']}")
        else:
            print("✅ 持仓正常，无预警")

        print("\n" + "=" * 60)
        print("自选股检查")
        print("=" * 60 + "\n")

        signals = monitor.check_watchlist(quotes)
        if signals:
            for signal in signals:
                print(f"{signal['message']}")
        else:
            print("暂无买入信号")

    elif args.report:
        print("\n生成每日报告...\n")
        report = monitor.generate_report(quotes)
        monitor.save_report(report)
        print("\n" + report)

    elif args.watch:
        print("\n持续监控模式（每5分钟检查一次）...")
        print("按 Ctrl+C 停止\n")

        import time

        while True:
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{now}] 检查中...")

                alerts = monitor.check_positions(quotes)
                signals = monitor.check_watchlist(quotes)

                if alerts:
                    print(f"  预警: {len(alerts)} 条")
                    for alert in alerts:
                        print(f"    - {alert['message']}")

                if signals:
                    print(f"  信号: {len(signals)} 条")
                    for signal in signals:
                        print(f"    - {signal['message']}")

                if not alerts and not signals:
                    print("  ✅ 正常")

                time.sleep(300)  # 5分钟

            except KeyboardInterrupt:
                print("\n\n监控已停止")
                break

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
