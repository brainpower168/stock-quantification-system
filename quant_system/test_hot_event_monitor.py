#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点事件监控测试脚本
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hot_event_monitor import HotEventMonitor, HotEventScheduler


def test_basic():
    """测试基础功能"""
    print("=" * 60)
    print("测试热点事件监控系统")
    print("=" * 60)

    # 创建监控器
    monitor = HotEventMonitor()

    # 获取热点事件
    events = monitor.fetch_hot_events(limit=10)

    print(f"\n获取到 {len(events)} 个热点事件")

    # 打印所有事件
    for i, event in enumerate(events, 1):
        print(f"\n{i}. {event.title}")
        print(f"   内容: {event.content[:50]}...")
        print(f"   来源: {event.source}")
        print(f"   发布时间: {event.publish_time}")
        print(f"   相关行业: {', '.join(event.related_industries)}")
        print(
            f"   相关股票: {', '.join(event.related_stocks) if event.related_stocks else '无'}"
        )
        print(f"   重要程度: {event.importance}")
        print(f"   情绪: {event.sentiment.value}")
        print(f"   热度: {event.heat}")
        print(f"   影响分数: {event.impact_score}")
        print(f"   影响深度: {event.impact_depth.value}")

    # 生成报告
    print("\n" + monitor.generate_report())

    # 导出JSON
    print("\n" + "=" * 60)
    print("JSON输出:")
    print("=" * 60)
    print(monitor.to_json())


def test_scheduler():
    """测试调度器（30秒刷新）"""
    print("\n" + "=" * 60)
    print("测试调度器（30秒刷新）")
    print("=" * 60)
    print("提示: 按 Ctrl+C 停止")
    print()

    # 创建监控器
    monitor = HotEventMonitor()

    # 创建调度器（30秒刷新）
    scheduler = HotEventScheduler(monitor, interval_seconds=30)

    # 启动
    scheduler.start()


def test_filter():
    """测试筛选功能"""
    print("\n" + "=" * 60)
    print("测试筛选功能")
    print("=" * 60)

    # 创建监控器
    monitor = HotEventMonitor()

    # 获取热点事件
    monitor.fetch_hot_events(limit=20)

    # 按影响深度筛选
    from hot_event_monitor import ImpactDepth

    deep_events = monitor.get_events_by_depth(ImpactDepth.DEEP)
    print(f"\n深度影响事件: {len(deep_events)}个")

    medium_events = monitor.get_events_by_depth(ImpactDepth.MEDIUM)
    print(f"中度影响事件: {len(medium_events)}个")

    # 按行业筛选
    tech_events = monitor.get_events_by_industry("科技")
    print(f"\n科技行业事件: {len(tech_events)}个")

    # 按股票筛选
    stock_events = monitor.get_events_by_stock("600519")
    print(f"600519相关事件: {len(stock_events)}个")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="热点事件监控测试")
    parser.add_argument(
        "--mode",
        choices=["basic", "scheduler", "filter"],
        default="basic",
        help="测试模式: basic(基础), scheduler(调度器), filter(筛选)",
    )

    args = parser.parse_args()

    if args.mode == "basic":
        test_basic()
    elif args.mode == "scheduler":
        test_scheduler()
    elif args.mode == "filter":
        test_filter()
