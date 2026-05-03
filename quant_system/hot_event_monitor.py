#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点事件监控系统
- 30秒实时刷新
- 智能影响深度判定
- TOP20热点
- 推送到用户

参考：AQT (QuantStock) 系统
"""

import json
import time
import schedule
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ImpactDepth(Enum):
    """影响深度等级"""

    DEEP = "深度"  # ≥80
    MEDIUM = "中度"  # ≥50
    SHALLOW = "浅度"  # ≥25
    LIGHT = "轻度"  # <25


class Sentiment(Enum):
    """情绪类型"""

    POSITIVE = "利好"
    NEGATIVE = "利空"
    NEUTRAL = "中性"


@dataclass
class HotEvent:
    """热点事件"""

    title: str  # 事件标题
    content: str  # 事件内容
    source: str  # 来源
    publish_time: str  # 发布时间
    related_stocks: List[str]  # 相关股票
    related_industries: List[str]  # 相关行业

    # 影响分析
    importance: int  # 重要程度 (0-100)
    sentiment: Sentiment  # 情绪
    heat: int  # 热度 (0-100)

    # 计算结果
    impact_score: int = 0  # 影响分数
    impact_depth: ImpactDepth = ImpactDepth.LIGHT  # 影响深度

    def calculate_impact(self):
        """计算影响深度"""
        score = 0

        # 1. 重要程度 (权重30)
        if self.importance >= 90:
            score += 30
        elif self.importance >= 80:
            score += 20
        elif self.importance >= 70:
            score += 10

        # 2. 影响程度 (权重30)
        if self.importance >= 80:
            score += 30  # 高影响
        elif self.importance >= 50:
            score += 15  # 中影响

        # 3. 情绪分析 (权重20)
        if self.sentiment == Sentiment.POSITIVE:
            score += 20
        elif self.sentiment == Sentiment.NEGATIVE:
            score += 10

        # 4. 热度 (权重20)
        if self.heat >= 80:
            score += 20
        elif self.heat >= 50:
            score += 10

        self.impact_score = score

        # 判定影响深度
        if score >= 80:
            self.impact_depth = ImpactDepth.DEEP
        elif score >= 50:
            self.impact_depth = ImpactDepth.MEDIUM
        elif score >= 25:
            self.impact_depth = ImpactDepth.SHALLOW
        else:
            self.impact_depth = ImpactDepth.LIGHT

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "publish_time": self.publish_time,
            "related_stocks": self.related_stocks,
            "related_industries": self.related_industries,
            "importance": self.importance,
            "sentiment": self.sentiment.value,
            "heat": self.heat,
            "impact_score": self.impact_score,
            "impact_depth": self.impact_depth.value,
        }


class HotEventMonitor:
    """热点事件监控器"""

    def __init__(self):
        self.events: List[HotEvent] = []
        self.last_refresh_time: Optional[datetime] = None
        self.refresh_count: int = 0

    def fetch_hot_events(self, limit: int = 20) -> List[HotEvent]:
        """
        获取热点事件

        优先级：
        1. 妙想 API (无限制)
        2. 问财 API (每日有限)
        """
        events = []

        # TODO: 实现从妙想/问财获取热点事件
        # 这里先用模拟数据
        events = self._fetch_from_mock(limit)

        # 计算影响深度
        for event in events:
            event.calculate_impact()

        # 按影响分数排序
        events.sort(key=lambda x: x.impact_score, reverse=True)

        self.events = events[:limit]
        self.last_refresh_time = datetime.now()
        self.refresh_count += 1

        return self.events

    def _fetch_from_mock(self, limit: int) -> List[HotEvent]:
        """模拟数据（实际应从API获取）"""
        mock_events = [
            HotEvent(
                title="AI芯片需求爆发，半导体板块大涨",
                content="受AI算力需求推动，半导体芯片需求持续增长，相关公司业绩预期上调",
                source="财经新闻",
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_stocks=["600519", "002475", "300750"],
                related_industries=["半导体", "芯片", "AI"],
                importance=90,
                sentiment=Sentiment.POSITIVE,
                heat=95,
            ),
            HotEvent(
                title="新能源汽车销量创新高",
                content="新能源汽车销量持续增长，产业链公司受益",
                source="行业报告",
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_stocks=["002460", "300750"],
                related_industries=["新能源", "汽车"],
                importance=85,
                sentiment=Sentiment.POSITIVE,
                heat=80,
            ),
            HotEvent(
                title="央行降准释放流动性",
                content="央行宣布降准0.5个百分点，释放长期资金约1万亿元",
                source="央行公告",
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_stocks=[],
                related_industries=["银行", "券商", "地产"],
                importance=95,
                sentiment=Sentiment.POSITIVE,
                heat=90,
            ),
            HotEvent(
                title="某科技公司业绩不及预期",
                content="某科技公司发布业绩预告，净利润同比下降30%",
                source="公司公告",
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_stocks=["000001"],
                related_industries=["科技"],
                importance=70,
                sentiment=Sentiment.NEGATIVE,
                heat=60,
            ),
            HotEvent(
                title="医药集采结果公布",
                content="新一轮医药集采结果公布，部分药品降价幅度超预期",
                source="医保局",
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_stocks=[],
                related_industries=["医药"],
                importance=75,
                sentiment=Sentiment.NEGATIVE,
                heat=70,
            ),
        ]

        return mock_events[:limit]

    def get_top_events(self, top_n: int = 5) -> List[HotEvent]:
        """获取TOP N热点事件"""
        return self.events[:top_n]

    def get_events_by_depth(self, depth: ImpactDepth) -> List[HotEvent]:
        """按影响深度筛选事件"""
        return [e for e in self.events if e.impact_depth == depth]

    def get_events_by_industry(self, industry: str) -> List[HotEvent]:
        """按行业筛选事件"""
        return [e for e in self.events if industry in e.related_industries]

    def get_events_by_stock(self, stock_code: str) -> List[HotEvent]:
        """按股票筛选事件"""
        return [e for e in self.events if stock_code in e.related_stocks]

    def generate_report(self) -> str:
        """生成热点事件报告"""
        if not self.events:
            return "暂无热点事件"

        report = []
        report.append("=" * 60)
        report.append("热点事件监控报告")
        report.append(
            f"刷新时间: {self.last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report.append(f"刷新次数: {self.refresh_count}")
        report.append("=" * 60)
        report.append("")

        # TOP 5 热点
        report.append("【TOP 5 热点事件】")
        for i, event in enumerate(self.get_top_events(5), 1):
            report.append(f"\n{i}. {event.title}")
            report.append(
                f"   影响深度: {event.impact_depth.value} (分数: {event.impact_score})"
            )
            report.append(f"   情绪: {event.sentiment.value}")
            report.append(f"   热度: {event.heat}")
            report.append(f"   相关行业: {', '.join(event.related_industries)}")
            report.append(
                f"   相关股票: {', '.join(event.related_stocks) if event.related_stocks else '无'}"
            )

        # 按影响深度统计
        report.append("\n" + "=" * 60)
        report.append("【影响深度统计】")
        for depth in ImpactDepth:
            count = len(self.get_events_by_depth(depth))
            report.append(f"{depth.value}: {count}个")

        # 利好/利空统计
        report.append("\n" + "=" * 60)
        report.append("【情绪统计】")
        positive = len([e for e in self.events if e.sentiment == Sentiment.POSITIVE])
        negative = len([e for e in self.events if e.sentiment == Sentiment.NEGATIVE])
        neutral = len([e for e in self.events if e.sentiment == Sentiment.NEUTRAL])
        report.append(f"利好: {positive}个")
        report.append(f"利空: {negative}个")
        report.append(f"中性: {neutral}个")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(
            {
                "last_refresh_time": self.last_refresh_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if self.last_refresh_time
                else None,
                "refresh_count": self.refresh_count,
                "events": [e.to_dict() for e in self.events],
            },
            ensure_ascii=False,
            indent=2,
        )


class HotEventScheduler:
    """热点事件调度器"""

    def __init__(self, monitor: HotEventMonitor, interval_seconds: int = 30):
        self.monitor = monitor
        self.interval_seconds = interval_seconds
        self.is_running = False

    def refresh_job(self):
        """刷新任务"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 刷新热点事件...")
        events = self.monitor.fetch_hot_events()
        print(f"获取到 {len(events)} 个热点事件")

        # 打印TOP 5
        print("\n【TOP 5 热点】")
        for i, event in enumerate(self.monitor.get_top_events(5), 1):
            print(
                f"{i}. {event.title} - {event.impact_depth.value} (分数: {event.impact_score})"
            )

    def start(self):
        """启动调度器"""
        self.is_running = True

        # 立即执行一次
        self.refresh_job()

        # 定时执行
        schedule.every(self.interval_seconds).seconds.do(self.refresh_job)

        print(f"\n热点事件监控已启动，每 {self.interval_seconds} 秒刷新一次")
        print("按 Ctrl+C 停止")

        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止调度器"""
        self.is_running = False
        schedule.clear()
        print("\n热点事件监控已停止")


def main():
    """主函数"""
    # 创建监控器
    monitor = HotEventMonitor()

    # 创建调度器（30秒刷新）
    scheduler = HotEventScheduler(monitor, interval_seconds=30)

    # 启动监控
    scheduler.start()


if __name__ == "__main__":
    main()
