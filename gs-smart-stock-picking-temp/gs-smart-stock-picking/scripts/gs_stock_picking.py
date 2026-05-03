#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国信证券智能选股接口调用脚本
用于根据各种财务指标和技术指标筛选符合条件的股票
"""

import os
import requests
import json
import urllib3
import ssl
from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SSLAdapter(HTTPAdapter):
    """自定义 SSL 适配器，启用旧版 SSL 重新协商"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

BASE_URL = "https://dgzt.guosen.com.cn/skills/agent"


def smart_stock_picking(searchstring, searchtype, api_key):
    """
    调用国信证券智能选股接口

    Args:
        searchstring: 选股条件，例如："市盈率小于20的银行股"
        searchtype: 搜索类型，可选值：stock, fund, HK_stock, US_stock, NEEQ, index
        api_key: API密钥，用于身份验证

    Returns:
        接口返回的结果
    """
    url = f"{BASE_URL}/mcp/smart_stock_picking"
    params = {
        "searchstring": searchstring,
        "searchtype": searchtype,
        "softName": "agent_skills",
        "apiKey": api_key
    }

    try:
        session = requests.Session()
        session.mount('https://', SSLAdapter())
        response = session.get(url, params=params, timeout=30, verify=False)
        response.raise_for_status()  # 检查HTTP响应状态
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


def print_result(result):
    """
    打印查询结果

    Args:
        result: 接口返回的结果
    """
    if not result:
        print("未获取到结果")
        return

    # 检查结果状态
    if "result" in result:
        results = result["result"]
        if isinstance(results, list) and len(results) > 0:
            code = results[0].get("code", -1)
            msg = results[0].get("msg", "未知错误")
            print(f"状态码: {code}")
            print(f"消息: {msg}")

            if code == 0 and "data" in result and result["data"]:
                # 处理返回的数据
                data = result["data"]
                if isinstance(data, list):
                    for i, obj in enumerate(data):
                        print(f"\n结果 #{i+1}:")
                        if "table" in obj:
                            table = obj["table"]
                            for key, values in table.items():
                                print(f"{key}:")
                                for value in values:
                                    print(f"  - {value}")
                else:
                    print("返回数据格式异常")
            elif code != 0:
                print("查询失败")
        else:
            print("返回数据格式异常")
    else:
        print("返回数据格式异常")


def main():
    """
    主函数
    """
    import argparse

    parser = argparse.ArgumentParser(description="国信证券智能选股接口调用脚本")
    parser.add_argument("--searchstring", required=True, help="选股条件，例如：'市盈率小于20的银行股'")
    parser.add_argument("--searchtype", required=True, choices=["stock", "fund", "HK_stock", "US_stock", "NEEQ", "index"], help="搜索类型")
    parser.add_argument("--api-key", dest="api_key", required=True, help="API Key，用于身份验证")

    args = parser.parse_args()

    print(f"查询条件: {args.searchstring}")
    print(f"搜索类型: {args.searchtype}")
    print("正在查询...")

    result = smart_stock_picking(args.searchstring, args.searchtype, args.api_key)
    print_result(result)


if __name__ == "__main__":
    main()