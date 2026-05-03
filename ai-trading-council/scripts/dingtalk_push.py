#!/usr/bin/env python3
"""
钉钉推送工具
支持发送消息到钉钉聊天窗口
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


class DingTalkPusher:
    """钉钉消息推送"""

    def __init__(self):
        self.app_key = os.environ.get("DINGTALK_APP_KEY", "dingh7idn85i7zuwku3e")
        self.app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
        self.agent_id = os.environ.get("DINGTALK_AGENT_ID", "4492440487")
        self.user_id = os.environ.get("DINGTALK_USER_ID", "0118312631069")
        self._access_token = None
        self._token_expire_time = 0

    def get_access_token(self) -> str:
        """获取access_token"""
        # 检查缓存
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token

        url = f"https://oapi.dingtalk.com/gettoken?appkey={self.app_key}&appsecret={self.app_secret}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("errcode") == 0:
                    self._access_token = result["access_token"]
                    self._token_expire_time = time.time() + 7000  # 提前200秒过期
                    return self._access_token
                else:
                    print(f"获取access_token失败: {result}")
                    return None
        except Exception as e:
            print(f"获取access_token异常: {e}")
            return None

    def send_message(self, message: str, msg_type: str = "text") -> bool:
        """
        发送消息到钉钉聊天窗口

        Args:
            message: 消息内容
            msg_type: 消息类型 (text/markdown)

        Returns:
            是否发送成功
        """
        token = self.get_access_token()
        if not token:
            print("无法获取access_token")
            return False

        url = f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token={token}"

        if msg_type == "markdown":
            data = {
                "agent_id": self.agent_id,
                "userid_list": self.user_id,
                "msg": {
                    "msgtype": "markdown",
                    "markdown": {"title": "股票分析报告", "text": message},
                },
            }
        else:
            data = {
                "agent_id": self.agent_id,
                "userid_list": self.user_id,
                "msg": {"msgtype": "text", "text": {"content": message}},
            }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("errcode") == 0:
                    print(f"消息发送成功, task_id: {result.get('task_id')}")
                    return True
                else:
                    print(f"消息发送失败: {result}")
                    return False
        except Exception as e:
            print(f"消息发送异常: {e}")
            return False

    def send_markdown(self, title: str, content: str) -> bool:
        """发送Markdown消息"""
        full_content = f"# {title}\n\n{content}"
        return self.send_message(full_content, msg_type="markdown")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(
            "用法: python dingtalk_push.py --message '消息内容' [--type text|markdown]"
        )
        print("   或: python dingtalk_push.py --title '标题' --content '内容'")
        sys.exit(1)

    pusher = DingTalkPusher()

    # 解析参数
    args = sys.argv[1:]
    message = None
    title = None
    content = None
    msg_type = "text"

    i = 0
    while i < len(args):
        if args[i] == "--message" and i + 1 < len(args):
            message = args[i + 1]
            i += 2
        elif args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == "--content" and i + 1 < len(args):
            content = args[i + 1]
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            msg_type = args[i + 1]
            i += 2
        else:
            i += 1

    # 发送消息
    if title and content:
        success = pusher.send_markdown(title, content)
    elif message:
        success = pusher.send_message(message, msg_type)
    else:
        print("请提供消息内容")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
