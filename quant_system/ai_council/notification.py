#!/usr/bin/env python3
"""
消息推送模块
支持飞书、钉钉、企业微信、Telegram等平台
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional


class NotificationSender:
    """消息推送基类"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str, **kwargs) -> bool:
        raise NotImplementedError


class FeishuSender(NotificationSender):
    """飞书机器人推送"""

    def send(
        self, message: str, title: str = "AI Trading Council 通知", **kwargs
    ) -> bool:
        """
        发送飞书消息

        飞书机器人Webhook格式:
        https://open.feishu.cn/open-apis/bot/v2/hook/xxx
        """
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": kwargs.get("color", "blue"),
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": message}},
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            }
                        ],
                    },
                ],
            },
        }

        return self._post_request(payload)

    def send_stock_alert(
        self,
        stock_code: str,
        stock_name: str,
        decision: str,
        price: float,
        confidence: float,
        reasons: List[str] = None,
    ) -> bool:
        """发送股票预警消息"""
        # 决策颜色
        color_map = {
            "STRONG_BUY": "green",
            "BUY": "green",
            "HOLD": "yellow",
            "SELL": "red",
            "STRONG_SELL": "red",
        }
        color = color_map.get(decision, "blue")

        # 决策中文
        decision_cn = {
            "STRONG_BUY": "强烈买入",
            "BUY": "买入",
            "HOLD": "持有",
            "SELL": "卖出",
            "STRONG_SELL": "强烈卖出",
        }.get(decision, decision)

        message = f"股票: {stock_name}({stock_code})\n决策: {decision_cn}\n价格: {price}元\n置信度: {confidence:.0%}"

        if reasons:
            message += f"\n\n分析要点:\n" + "\n".join(
                f"• {r[:100]}" for r in reasons[:3]
            )

        return self.send(message, title=f"AI交易信号 - {decision_cn}", color=color)

    def send_daily_report(self, report_content: str, stats: Dict = None) -> bool:
        """发送每日报告"""
        title = "AI Trading Council 每日报告"

        message = report_content[:4000]  # 飞书消息长度限制

        if stats:
            stats_text = f"\n\n📊 统计数据:\n"
            stats_text += f"• 总推荐: {stats.get('total', 0)}\n"
            stats_text += f"• 成功: {stats.get('success', 0)}\n"
            stats_text += f"• 准确率: {stats.get('accuracy', 0):.1f}%"
            message += stats_text

        return self.send(message, title=title, color="blue")

    def _post_request(self, payload: dict) -> bool:
        """发送HTTP请求"""
        try:
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}

            request = urllib.request.Request(
                self.webhook_url, data=data, headers=headers, method="POST"
            )

            response = urllib.request.urlopen(request, timeout=10)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("StatusCode") == 0 or result.get("code") == 0:
                print(f"✅ 飞书消息发送成功")
                return True
            else:
                print(f"❌ 飞书消息发送失败: {result}")
                return False

        except urllib.error.URLError as e:
            print(f"❌ 网络错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False


class DingTalkSender(NotificationSender):
    """钉钉机器人推送"""

    def send(
        self, message: str, title: str = "AI Trading Council 通知", **kwargs
    ) -> bool:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{message}\n\n> 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            },
        }
        return self._post_request(payload)

    def _post_request(self, payload: dict) -> bool:
        try:
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}

            request = urllib.request.Request(
                self.webhook_url, data=data, headers=headers, method="POST"
            )

            response = urllib.request.urlopen(request, timeout=10)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("errcode") == 0:
                print(f"✅ 钉钉消息发送成功")
                return True
            else:
                print(f"❌ 钉钉消息发送失败: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False


class WeComSender(NotificationSender):
    """企业微信机器人推送"""

    def send(self, message: str, **kwargs) -> bool:
        payload = {"msgtype": "markdown", "markdown": {"content": message}}
        return self._post_request(payload)

    def _post_request(self, payload: dict) -> bool:
        try:
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}

            request = urllib.request.Request(
                self.webhook_url, data=data, headers=headers, method="POST"
            )

            response = urllib.request.urlopen(request, timeout=10)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("errcode") == 0:
                print(f"✅ 企业微信消息发送成功")
                return True
            else:
                print(f"❌ 企业微信消息发送失败: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False


class NotificationManager:
    """消息推送管理器"""

    def __init__(self):
        self.senders: Dict[str, NotificationSender] = {}

    def add_feishu(self, webhook_url: str) -> "NotificationManager":
        """添加飞书推送"""
        if webhook_url:
            self.senders["feishu"] = FeishuSender(webhook_url)
        return self

    def add_dingtalk(self, webhook_url: str) -> "NotificationManager":
        """添加钉钉推送"""
        if webhook_url:
            self.senders["dingtalk"] = DingTalkSender(webhook_url)
        return self

    def add_wecom(self, webhook_url: str) -> "NotificationManager":
        """添加企业微信推送"""
        if webhook_url:
            self.senders["wecom"] = WeComSender(webhook_url)
        return self

    def send_all(self, message: str, title: str = "通知", **kwargs) -> Dict[str, bool]:
        """向所有配置的平台发送消息"""
        results = {}
        for name, sender in self.senders.items():
            try:
                results[name] = sender.send(message, title=title, **kwargs)
            except Exception as e:
                print(f"❌ {name} 发送失败: {e}")
                results[name] = False
        return results

    def send_stock_alert(
        self,
        stock_code: str,
        stock_name: str,
        decision: str,
        price: float,
        confidence: float,
        reasons: List[str] = None,
    ) -> Dict[str, bool]:
        """发送股票预警到所有平台"""
        results = {}
        for name, sender in self.senders.items():
            if isinstance(sender, FeishuSender):
                results[name] = sender.send_stock_alert(
                    stock_code, stock_name, decision, price, confidence, reasons
                )
            else:
                # 其他平台使用简单消息
                decision_cn = {
                    "STRONG_BUY": "强烈买入",
                    "BUY": "买入",
                    "HOLD": "持有",
                    "SELL": "卖出",
                    "STRONG_SELL": "强烈卖出",
                }.get(decision, decision)
                message = f"【{decision_cn}】{stock_name}({stock_code})\n价格: {price}元\n置信度: {confidence:.0%}"
                results[name] = sender.send(message, title=f"AI交易信号")
        return results


# 便捷函数
_manager = None


def get_manager() -> NotificationManager:
    """获取消息管理器单例"""
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager


def send_to_feishu(webhook_url: str, message: str, title: str = "通知") -> bool:
    """快速发送飞书消息"""
    sender = FeishuSender(webhook_url)
    return sender.send(message, title=title)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="消息推送工具")
    parser.add_argument("--feishu", type=str, help="飞书Webhook URL")
    parser.add_argument("--dingtalk", type=str, help="钉钉Webhook URL")
    parser.add_argument("--wecom", type=str, help="企业微信Webhook URL")
    parser.add_argument("--message", type=str, required=True, help="消息内容")
    parser.add_argument(
        "--title", type=str, default="AI Trading Council 通知", help="消息标题"
    )

    args = parser.parse_args()

    manager = NotificationManager()

    if args.feishu:
        manager.add_feishu(args.feishu)
    if args.dingtalk:
        manager.add_dingtalk(args.dingtalk)
    if args.wecom:
        manager.add_wecom(args.wecom)

    if not manager.senders:
        print("❌ 请至少配置一个推送平台")
        exit(1)

    results = manager.send_all(args.message, args.title)
    print(f"\n发送结果: {results}")
