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


class RealtimePushService:
    """实时推送服务"""

    def __init__(self):
        self.pusher = SignalPusher()

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

    def push_position_alert(
        self,
        stock_code: str,
        stock_name: str,
        alert_type: str,
        message: str,
        data: dict,
    ):
        """推送持仓预警"""
        signal_type = SignalType.STOP_LOSS
        if "止盈" in message:
            signal_type = SignalType.TAKE_PROFIT
        elif "资金" in message:
            signal_type = SignalType.FUND_FLOW

        priority = (
            SignalPriority.HIGH if "止损" in alert_type else SignalPriority.MEDIUM
        )

        self.pusher.push_signal(
            signal_type=signal_type,
            stock_code=stock_code,
            stock_name=stock_name,
            title=f"持仓预警 - {alert_type}",
            message=message,
            data=data,
            priority=priority,
            push_dingtalk=True,
        )


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实时推送服务")
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

        print("✅ 测试信号已发送到钉钉")
        print("\n最近信号:")
        for signal in service.pusher.get_recent_signals(3):
            print(f"- {signal['title']}: {signal['stock_name']}")


if __name__ == "__main__":
    main()
