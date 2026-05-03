#!/usr/bin/env python3
"""
实时信号推送服务
支持WebSocket实时推送 + 钉钉通知
"""

import os
import sys
import json
import time
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# 导入钉钉推送
sys.path.insert(0, str(Path(__file__).parent))
from dingtalk_push import DingTalkPusher

# 导入日志
try:
    from logger_config import get_logger

    logger = get_logger("signal_pusher")
except ImportError:
    import logging

    logger = logging.getLogger("signal_pusher")


class SignalType(Enum):
    """信号类型"""

    STOCK_PICK = "选股信号"
    AI_DECISION = "AI决策"
    POSITION_ALERT = "持仓预警"
    FUND_FLOW = "资金流向"
    BREAKOUT = "突破信号"
    STOP_LOSS = "止损提醒"
    TAKE_PROFIT = "止盈提醒"


class SignalPriority(Enum):
    """信号优先级"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass
class TradingSignal:
    """交易信号"""

    signal_type: str
    stock_code: str
    stock_name: str
    priority: str
    title: str
    message: str
    data: Dict
    timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        md = f"## {self.title}\n\n"
        md += f"**股票**: {self.stock_name}({self.stock_code})\n\n"
        md += f"**类型**: {self.signal_type}\n\n"
        md += f"**优先级**: {self.priority}\n\n"
        md += f"**时间**: {self.timestamp}\n\n"
        md += f"**详情**:\n\n{self.message}\n\n"

        if self.data:
            md += "**数据**:\n\n"
            for key, value in self.data.items():
                md += f"- {key}: {value}\n"

        return md


class SignalPusher:
    """信号推送器"""

    def __init__(self):
        self.dingtalk = DingTalkPusher()
        self.subscribers: List[Callable] = []
        self.signal_history: List[TradingSignal] = []
        self.max_history = 100

        # WebSocket服务
        self.ws_server = None
        self.ws_clients = set()
        self.ws_port = int(os.environ.get("WS_PORT", 8765))

    def subscribe(self, callback: Callable):
        """订阅信号"""
        self.subscribers.append(callback)

    def push_signal(
        self,
        signal_type: SignalType,
        stock_code: str,
        stock_name: str,
        title: str,
        message: str,
        data: Dict = None,
        priority: SignalPriority = SignalPriority.MEDIUM,
        push_dingtalk: bool = True,
    ) -> bool:
        """
        推送信号

        Args:
            signal_type: 信号类型
            stock_code: 股票代码
            stock_name: 股票名称
            title: 标题
            message: 消息内容
            data: 附加数据
            priority: 优先级
            push_dingtalk: 是否推送到钉钉

        Returns:
            是否推送成功
        """
        # 创建信号对象
        signal = TradingSignal(
            signal_type=signal_type.value,
            stock_code=stock_code,
            stock_name=stock_name,
            priority=priority.value,
            title=title,
            message=message,
            data=data or {},
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # 保存到历史
        self.signal_history.append(signal)
        if len(self.signal_history) > self.max_history:
            self.signal_history.pop(0)

        # 通知订阅者
        for callback in self.subscribers:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"通知订阅者失败: {e}")

        # 推送到WebSocket客户端
        if self.ws_clients:
            asyncio.run(self._broadcast_to_ws(signal.to_dict()))

        # 推送到钉钉
        if push_dingtalk:
            success = self.dingtalk.send_markdown(
                title=f"[{priority.value}] {title}", content=signal.to_markdown()
            )
            if success:
                logger.info(f"信号已推送到钉钉: {title}")
            else:
                logger.error(f"推送到钉钉失败: {title}")
            return success

        return True

    async def _broadcast_to_ws(self, data: Dict):
        """广播到WebSocket客户端"""
        if not self.ws_clients:
            return

        message = json.dumps(data, ensure_ascii=False)
        for client in self.ws_clients:
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"WebSocket发送失败: {e}")
                self.ws_clients.discard(client)

    def start_ws_server(self):
        """启动WebSocket服务器（后台线程）"""
        try:
            import websockets
        except ImportError:
            logger.warning("未安装websockets库，WebSocket功能不可用")
            logger.info("安装方法: pip install websockets")
            return False

        async def handle_client(websocket, path):
            """处理WebSocket客户端"""
            self.ws_clients.add(websocket)
            logger.info(f"WebSocket客户端连接: {websocket.remote_address}")

            try:
                # 发送历史信号
                for signal in self.signal_history[-20:]:
                    await websocket.send(
                        json.dumps(signal.to_dict(), ensure_ascii=False)
                    )

                # 保持连接
                async for message in websocket:
                    # 处理客户端消息（如订阅特定股票）
                    logger.debug(f"收到WebSocket消息: {message}")

            except Exception as e:
                logger.error(f"WebSocket连接异常: {e}")
            finally:
                self.ws_clients.discard(websocket)
                logger.info(f"WebSocket客户端断开: {websocket.remote_address}")

        async def start_server():
            """启动服务器"""
            self.ws_server = await websockets.serve(
                handle_client, "0.0.0.0", self.ws_port
            )
            logger.info(f"WebSocket服务器已启动: ws://0.0.0.0:{self.ws_port}")
            await self.ws_server.wait_closed()

        # 在后台线程运行
        def run_server():
            asyncio.run(start_server())

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        return True

    def get_recent_signals(self, limit: int = 20) -> List[Dict]:
        """获取最近信号"""
        return [s.to_dict() for s in self.signal_history[-limit:]]


# 全局单例
_pusher_instance = None


def get_pusher() -> SignalPusher:
    """获取全局推送器实例"""
    global _pusher_instance
    if _pusher_instance is None:
        _pusher_instance = SignalPusher()
    return _pusher_instance


def push_signal(*args, **kwargs) -> bool:
    """推送信号（便捷函数）"""
    return get_pusher().push_signal(*args, **kwargs)


# 示例用法
if __name__ == "__main__":
    # 测试推送
    pusher = SignalPusher()

    # 测试选股信号
    pusher.push_signal(
        signal_type=SignalType.STOCK_PICK,
        stock_code="600519",
        stock_name="贵州茅台",
        title="选股推荐 - A级",
        message="符合选股条件，建议关注",
        data={"涨幅": "2.5%", "主力流入": "5.2亿", "10日DDX": "3.45"},
        priority=SignalPriority.HIGH,
    )

    # 测试AI决策信号
    pusher.push_signal(
        signal_type=SignalType.AI_DECISION,
        stock_code="300750",
        stock_name="宁德时代",
        title="AI Council决策 - BUY",
        message="三模型投票结果: 2票买入, 1票持有",
        data={"LongCat": "BUY (75%)", "讯飞星火": "HOLD (60%)", "智谱GLM": "BUY (80%)"},
        priority=SignalPriority.MEDIUM,
    )

    # 测试持仓预警
    pusher.push_signal(
        signal_type=SignalType.POSITION_ALERT,
        stock_code="002460",
        stock_name="赣锋锂业",
        title="持仓预警 - 接近止损线",
        message="当前亏损-4.5%，接近止损线-5%",
        data={"成本价": "18.5元", "现价": "17.67元", "盈亏": "-4.5%"},
        priority=SignalPriority.HIGH,
    )

    print("\n最近信号:")
    for signal in pusher.get_recent_signals(3):
        print(f"- {signal['title']}: {signal['stock_name']}")
