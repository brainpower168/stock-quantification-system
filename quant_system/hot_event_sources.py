#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点事件数据源
- 妙想 API
- 问财 API
- 新闻 API
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

# 导入热点事件类
from hot_event_monitor import HotEvent, Sentiment


class HotEventDataSource:
    """热点事件数据源基类"""

    def fetch(self, limit: int = 20) -> List[HotEvent]:
        """获取热点事件"""
        raise NotImplementedError


class MiaoXiangSource(HotEventDataSource):
    """妙想数据源"""

    def __init__(self):
        self.api_key = os.getenv("MX_APIKEY", "")
        self.base_url = "https://api.miaoxiang.com"  # 示例URL

    def fetch(self, limit: int = 20) -> List[HotEvent]:
        """从妙想获取热点事件"""
        if not self.api_key:
            print("警告: 未配置 MX_APIKEY")
            return []

        try:
            # TODO: 实现真实的API调用
            # 这里需要根据妙想API文档实现
            pass

        except Exception as e:
            print(f"妙想API调用失败: {e}")
            return []

        return []


class WenCaiSource(HotEventDataSource):
    """问财数据源"""

    def __init__(self):
        self.api_key = os.getenv("IWENCAI_API_KEY", "")
        self.base_url = "https://api.iwencai.com"  # 示例URL

    def fetch(self, limit: int = 20) -> List[HotEvent]:
        """从问财获取热点事件"""
        if not self.api_key:
            print("警告: 未配置 IWENCAI_API_KEY")
            return []

        try:
            # TODO: 实现真实的API调用
            # 这里需要根据问财API文档实现
            pass

        except Exception as e:
            print(f"问财API调用失败: {e}")
            return []

        return []


class NewsSource(HotEventDataSource):
    """新闻数据源（使用已有的新闻搜索skill）"""

    def __init__(self):
        self.news_api_url = "https://news-api.example.com"  # 示例URL

    def fetch(self, limit: int = 20) -> List[HotEvent]:
        """从新闻API获取热点事件"""
        try:
            # TODO: 调用新闻搜索skill
            # 可以使用已有的 news-search skill
            pass

        except Exception as e:
            print(f"新闻API调用失败: {e}")
            return []

        return []


class EastMoneySource(HotEventDataSource):
    """东方财富数据源（免费）"""

    def __init__(self):
        self.base_url = "https://emweb.eastmoney.com"

    def fetch(self, limit: int = 20) -> List[HotEvent]:
        """从东方财富获取热点事件"""
        try:
            # 东方财富热点事件API
            url = "https://emweb.eastmoney.com/Info/Topic/TopicList"
            params = {"type": "hot", "ps": limit, "p": 1}

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return self._parse_eastmoney_data(data)

        except Exception as e:
            print(f"东方财富API调用失败: {e}")

        return []

    def _parse_eastmoney_data(self, data: dict) -> List[HotEvent]:
        """解析东方财富数据"""
        events = []

        try:
            if data and "data" in data:
                for item in data["data"]:
                    # 解析相关股票
                    related_stocks = []
                    if "codes" in item:
                        related_stocks = item["codes"].split(",")[:5]

                    # 解析相关行业
                    related_industries = []
                    if "industry" in item:
                        related_industries = [item["industry"]]

                    # 判断情绪
                    sentiment = Sentiment.NEUTRAL
                    title = item.get("title", "")
                    if any(
                        word in title
                        for word in ["利好", "大涨", "突破", "创新高", "增长"]
                    ):
                        sentiment = Sentiment.POSITIVE
                    elif any(
                        word in title
                        for word in ["利空", "大跌", "亏损", "下滑", "风险"]
                    ):
                        sentiment = Sentiment.NEGATIVE

                    event = HotEvent(
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        source="东方财富",
                        publish_time=item.get(
                            "showtime", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ),
                        related_stocks=related_stocks,
                        related_industries=related_industries,
                        importance=self._calculate_importance(item),
                        sentiment=sentiment,
                        heat=item.get("heat", 50),
                    )
                    events.append(event)

        except Exception as e:
            print(f"解析东方财富数据失败: {e}")

        return events

    def _calculate_importance(self, item: dict) -> int:
        """计算重要程度"""
        score = 50  # 基础分

        # 根据阅读量
        read_count = item.get("readcount", 0)
        if read_count > 100000:
            score += 30
        elif read_count > 50000:
            score += 20
        elif read_count > 10000:
            score += 10

        # 根据评论量
        comment_count = item.get("commentcount", 0)
        if comment_count > 1000:
            score += 20
        elif comment_count > 500:
            score += 10

        return min(score, 100)


class HotEventAggregator:
    """热点事件聚合器"""

    def __init__(self):
        self.sources = [
            # EastMoneySource(),  # 东方财富（免费，优先）
            # MiaoXiangSource(),   # 妙想（需要API Key）
            # WenCaiSource(),      # 问财（需要API Key）
            # NewsSource(),        # 新闻
        ]

    def add_source(self, source: HotEventDataSource):
        """添加数据源"""
        self.sources.append(source)

    def fetch_all(self, limit: int = 20) -> List[HotEvent]:
        """从所有数据源获取热点事件"""
        all_events = []

        for source in self.sources:
            try:
                events = source.fetch(limit)
                all_events.extend(events)
            except Exception as e:
                print(f"数据源 {source.__class__.__name__} 获取失败: {e}")

        # 去重（按标题）
        seen_titles = set()
        unique_events = []
        for event in all_events:
            if event.title not in seen_titles:
                seen_titles.add(event.title)
                unique_events.append(event)

        # 按影响分数排序
        unique_events.sort(key=lambda x: x.impact_score, reverse=True)

        return unique_events[:limit]


def main():
    """测试数据源"""
    # 创建聚合器
    aggregator = HotEventAggregator()

    # 添加东方财富数据源
    aggregator.add_source(EastMoneySource())

    # 获取热点事件
    events = aggregator.fetch_all(limit=10)

    print(f"获取到 {len(events)} 个热点事件")

    for i, event in enumerate(events, 1):
        print(f"\n{i}. {event.title}")
        print(f"   来源: {event.source}")
        print(f"   影响深度: {event.impact_depth.value}")


if __name__ == "__main__":
    main()
