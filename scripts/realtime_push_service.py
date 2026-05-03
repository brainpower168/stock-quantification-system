#!/usr/bin/env python3
"""
实时推送集成脚本
将信号推送集成到选股、AI Council、持仓监控
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from signal_pusher import SignalPusher, SignalType, SignalPriority
from daily_stock_selector import DailyStockSelector
from council_engine import CouncilEngine
from position_monitor import PositionMonitor


class RealtimePushService:
    """实时推送服务"""

    def __init__(self):
        self.pusher = SignalPusher()
        self.selector = DailyStockSelector()
        self.council = CouncilEngine()
        self.monitor = PositionMonitor()

        # 订阅持仓预警
        self.monitor.subscribe_alert(self._on_position_alert)

    def _on_position_alert(self, alert):
        """持仓预警回调"""
        priority = (
            SignalPriority.HIGH
            if alert["severity"] == "HIGH"
            else SignalPriority.MEDIUM
        )

        signal_type = SignalType.STOP_LOSS
        if "止盈" in alert["message"]:
            signal_type = SignalType.TAKE_PROFIT
        elif "资金" in alert["message"]:
            signal_type = SignalType.FUND_FLOW

        self.pusher.push_signal(
            signal_type=signal_type,
            stock_code=alert["stock_code"],
            stock_name=alert["stock_name"],
            title=f"持仓预警 - {alert['alert_type']}",
            message=alert["message"],
            priority=priority,
            push_dingtalk=True,
        )

    def push_stock_picks(self, recommendations: dict):
        """推送选股结果"""
        for grade, stocks in recommendations.items():
            if not stocks:
                continue

            # 只推送A级和B级
            if grade not in ["A级", "B级"]:
                continue

            priority = SignalPriority.HIGH if grade == "A级" else SignalPriority.MEDIUM

            for stock in stocks[:3]:  # 每个等级最多推送3只
                self.pusher.push_signal(
                    signal_type=SignalType.STOCK_PICK,
                    stock_code=stock["code"],
                    stock_name=stock["name"],
                    title=f"选股推荐 - {grade}",
                    message=f"符合选股条件，建议关注",
                    data={
                        "涨幅": f"{stock.get('change_pct', 'N/A')}%",
                        "主力流入": f"{stock.get('main_inflow', 'N/A')}亿",
                        "10日DDX": stock.get("ddx_10d", "N/A"),
                    },
                    priority=priority,
                    push_dingtalk=True,
                )

    def push_ai_decision(self, stock_code: str, stock_name: str, decision):
        """推送AI决策"""
        # 决策优先级
        priority_map = {
            "STRONG_BUY": SignalPriority.HIGH,
            "BUY": SignalPriority.MEDIUM,
            "HOLD": SignalPriority.LOW,
            "SELL": SignalPriority.MEDIUM,
            "STRONG_SELL": SignalPriority.HIGH,
        }

        priority = priority_map.get(decision.final_decision, SignalPriority.MEDIUM)

        # 构建投票详情
        vote_details = {}
        for vote in decision.votes:
            vote_details[vote.model_name] = f"{vote.decision} ({vote.confidence:.0%})"

        self.pusher.push_signal(
            signal_type=SignalType.AI_DECISION,
            stock_code=stock_code,
            stock_name=stock_name,
            title=f"AI Council决策 - {decision.final_decision}",
            message=decision.reasoning[:200] + "...",
            data={"置信度": f"{decision.confidence:.2%}", **vote_details},
            priority=priority,
            push_dingtalk=True,
        )

    def push_breakout_signal(self, stock_code: str, stock_name: str, data: dict):
        """推送突破信号"""
        self.pusher.push_signal(
            signal_type=SignalType.BREAKOUT,
            stock_code=stock_code,
            stock_name=stock_name,
            title="突破信号 - DDX刚转正",
            message="DDX从负转正，可能是启动信号",
            data=data,
            priority=SignalPriority.HIGH,
            push_dingtalk=True,
        )

    def push_fund_flow_alert(self, stock_code: str, stock_name: str, data: dict):
        """推送资金流向预警"""
        priority = (
            SignalPriority.HIGH
            if data.get("main_inflow", 0) < -1e8
            else SignalPriority.MEDIUM
        )

        self.pusher.push_signal(
            signal_type=SignalType.FUND_FLOW,
            stock_code=stock_code,
            stock_name=stock_name,
            title="资金流向预警",
            message=f"主力{'流出' if data['main_inflow'] < 0 else '流入'}{abs(data['main_inflow']) / 1e8:.2f}亿",
            data=data,
            priority=priority,
            push_dingtalk=True,
        )

    def run_daily_task(self):
        """运行每日任务"""
        print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始每日任务 ===")

        # 1. 选股
        print("\n1. 选股中...")
        top_stocks = self.selector.get_top_main_inflow(top_n=20)
        recommendations = self.selector.grade_stocks(top_stocks)
        self.push_stock_picks(recommendations)
        print(f"   已推送选股结果")

        # 2. 持仓监控
        print("\n2. 检查持仓...")
        alerts = self.monitor.check_alerts()
        print(f"   发现 {len(alerts)} 个预警")

        # 3. 资金流向监控
        print("\n3. 检查资金流向...")
        flows = self.monitor.check_fund_flows()
        for flow in flows:
            if abs(flow["main_inflow"]) > 1e8:  # 超过1亿
                self.push_fund_flow_alert(flow["stock_code"], flow["stock_name"], flow)

        print(f"\n✅ 每日任务完成")

    def start_monitoring(self, interval: int = 300):
        """
        启动持续监控

        Args:
            interval: 检查间隔（秒），默认5分钟
        """
        print(f"\n=== 启动实时监控 ===")
        print(f"检查间隔: {interval}秒")
        print(f"按 Ctrl+C 停止")

        # 启动WebSocket服务器
        if self.pusher.start_ws_server():
            print("WebSocket服务器已启动")

        try:
            while True:
                self.run_daily_task()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实时推送服务")
    parser.add_argument(
        "--mode",
        choices=["once", "monitor"],
        default="once",
        help="运行模式: once=单次运行, monitor=持续监控",
    )
    parser.add_argument(
        "--interval", type=int, default=300, help="监控间隔（秒），默认300秒"
    )
    parser.add_argument("--test", action="store_true", help="测试模式，发送测试信号")

    args = parser.parse_args()

    service = RealtimePushService()

    if args.test:
        # 测试模式
        print("=== 测试模式 ===")

        # 测试选股推送
        service.pusher.push_signal(
            signal_type=SignalType.STOCK_PICK,
            stock_code="600519",
            stock_name="贵州茅台",
            title="选股推荐 - A级",
            message="符合选股条件，建议关注",
            data={"涨幅": "2.5%", "主力流入": "5.2亿", "10日DDX": "3.45"},
            priority=SignalPriority.HIGH,
        )

        print("✅ 测试信号已发送")

    elif args.mode == "once":
        # 单次运行
        service.run_daily_task()

    else:
        # 持续监控
        service.start_monitoring(args.interval)


if __name__ == "__main__":
    main()
