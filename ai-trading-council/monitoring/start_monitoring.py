#!/usr/bin/env python3
"""
监控服务启动脚本
启动Prometheus指标导出器
"""

import os
import sys
import time
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from metrics_exporter import MetricsExporter, PrometheusHTTPServer
from position_monitor import PositionMonitor
from signal_pusher import get_pusher


class MonitoringService:
    """监控服务"""

    def __init__(self, port: int = 9091):
        self.port = port
        self.exporter = MetricsExporter()
        self.monitor = PositionMonitor()
        self.pusher = get_pusher()
        self.running = False

    def collect_metrics(self):
        """收集指标"""
        # 清空旧指标
        self.exporter.clear()

        # 收集持仓指标
        positions = self.monitor.get_positions_status()
        self.exporter.export_position_metrics(positions)

        # 收集资金流向指标
        flows = self.monitor.check_fund_flows()
        self.exporter.export_fund_flow_metrics(flows)

        # 收集信号指标
        signals = self.pusher.get_recent_signals(100)
        self.exporter.export_signal_metrics(signals)

        # 收集系统指标
        stats = {
            "api_calls": 0,  # TODO: 实现API调用统计
            "success_rate": 0.95,
            "cache_hit_rate": 0.85,
            "active_positions": len(positions),
        }
        self.exporter.export_system_metrics(stats)

    def start_background_collector(self, interval: int = 30):
        """启动后台指标收集器"""

        def collector():
            while self.running:
                try:
                    self.collect_metrics()
                except Exception as e:
                    print(f"收集指标失败: {e}")
                time.sleep(interval)

        self.running = True
        thread = threading.Thread(target=collector, daemon=True)
        thread.start()
        print(f"后台指标收集器已启动（间隔{interval}秒）")

    def start(self):
        """启动监控服务"""
        print(f"\n=== 启动监控服务 ===")
        print(f"Prometheus端口: {self.port}")
        print(f"访问地址: http://localhost:{self.port}/metrics")
        print(f"按 Ctrl+C 停止")

        # 启动后台收集器
        self.start_background_collector(interval=30)

        # 启动HTTP服务器
        server = PrometheusHTTPServer(self.port)
        server.exporter = self.exporter
        server.start()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="监控服务")
    parser.add_argument("--port", type=int, default=9091, help="Prometheus端口")

    args = parser.parse_args()

    service = MonitoringService(args.port)
    service.start()


if __name__ == "__main__":
    main()
