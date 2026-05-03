#!/usr/bin/env python3
"""
监控数据导出器
导出Prometheus格式的指标数据
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from logger_config import get_logger

    logger = get_logger("metrics_exporter")
except ImportError:
    import logging

    logger = logging.getLogger("metrics_exporter")


@dataclass
class MetricPoint:
    """指标数据点"""

    name: str
    value: float
    labels: Dict[str, str]
    timestamp: int


class MetricsExporter:
    """指标导出器"""

    def __init__(self):
        self.metrics: List[MetricPoint] = []
        self.last_export_time = 0
        self.export_interval = 60  # 60秒导出一次

    def add_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """添加指标"""
        self.metrics.append(
            MetricPoint(
                name=name,
                value=value,
                labels=labels or {},
                timestamp=int(time.time() * 1000),
            )
        )

    def export_position_metrics(self, positions: List[Dict]):
        """导出持仓指标"""
        for pos in positions:
            labels = {"stock_code": pos["stock_code"], "stock_name": pos["stock_name"]}

            # 持仓市值
            self.add_metric("position_market_value", pos["market_value"], labels)

            # 盈亏
            self.add_metric("position_profit_loss", pos["profit_loss"], labels)

            # 盈亏率
            self.add_metric("position_profit_loss_pct", pos["profit_loss_pct"], labels)

            # 持仓数量
            self.add_metric("position_shares", pos["shares"], labels)

    def export_fund_flow_metrics(self, flows: List[Dict]):
        """导出资金流向指标"""
        for flow in flows:
            labels = {
                "stock_code": flow["stock_code"],
                "stock_name": flow["stock_name"],
            }

            # 主力流入（亿元）
            self.add_metric("fund_main_inflow", flow["main_inflow"] / 1e8, labels)

            # DDX
            self.add_metric("fund_ddx", flow["ddx"], labels)

            # DDX趋势（正为1，负为-1）
            ddx_trend = 1 if flow["ddx"] > 0 else -1
            self.add_metric("fund_ddx_trend", ddx_trend, labels)

    def export_signal_metrics(self, signals: List[Dict]):
        """导出信号指标"""
        # 按类型统计
        type_counts = {}
        for signal in signals:
            signal_type = signal["signal_type"]
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

        for signal_type, count in type_counts.items():
            self.add_metric("signal_count", count, {"type": signal_type})

        # 总信号数
        self.add_metric("signal_total", len(signals))

    def export_system_metrics(self, stats: Dict):
        """导出系统指标"""
        # API调用次数
        self.add_metric("api_calls_total", stats.get("api_calls", 0))

        # 成功率
        self.add_metric("api_success_rate", stats.get("success_rate", 0))

        # 缓存命中率
        self.add_metric("cache_hit_rate", stats.get("cache_hit_rate", 0))

        # 活跃持仓数
        self.add_metric("active_positions", stats.get("active_positions", 0))

    def to_prometheus_format(self) -> str:
        """转换为Prometheus格式"""
        lines = []

        # 按指标名分组
        grouped = {}
        for metric in self.metrics:
            if metric.name not in grouped:
                grouped[metric.name] = []
            grouped[metric.name].append(metric)

        # 生成Prometheus格式
        for name, points in grouped.items():
            # 添加HELP和TYPE
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} gauge")

            # 添加数据点
            for point in points:
                if point.labels:
                    labels_str = ",".join(
                        [f'{k}="{v}"' for k, v in point.labels.items()]
                    )
                    lines.append(f"{name}{{{labels_str}}} {point.value}")
                else:
                    lines.append(f"{name} {point.value}")

            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def save_to_file(self, filepath: str):
        """保存到文件"""
        prom_data = self.to_prometheus_format()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prom_data)

        logger.info(f"指标已导出到: {filepath}")

    def clear(self):
        """清空指标"""
        self.metrics.clear()


class PrometheusHTTPServer:
    """Prometheus HTTP服务器"""

    def __init__(self, port: int = 9090):
        self.port = port
        self.exporter = MetricsExporter()
        self.server = None

    def start(self):
        """启动HTTP服务器"""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        exporter = self.exporter

        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/metrics":
                    # 生成指标数据
                    prom_data = exporter.to_prometheus_format()

                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(prom_data.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                # 不输出访问日志
                pass

        self.server = HTTPServer(("0.0.0.0", self.port), MetricsHandler)
        logger.info(f"Prometheus HTTP服务器已启动: http://0.0.0.0:{self.port}/metrics")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("服务器已停止")
            self.server.shutdown()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="监控数据导出器")
    parser.add_argument("--port", type=int, default=9090, help="HTTP端口")
    parser.add_argument("--export-file", type=str, help="导出到文件")
    parser.add_argument("--test", action="store_true", help="测试模式")

    args = parser.parse_args()

    exporter = MetricsExporter()

    if args.test:
        # 测试模式
        print("=== 测试模式 ===")

        # 添加测试指标
        exporter.add_metric(
            "position_market_value",
            100000,
            {"stock_code": "600519", "stock_name": "贵州茅台"},
        )

        exporter.add_metric(
            "position_profit_loss",
            5000,
            {"stock_code": "600519", "stock_name": "贵州茅台"},
        )

        exporter.add_metric(
            "fund_main_inflow", 5.2, {"stock_code": "600519", "stock_name": "贵州茅台"}
        )

        # 输出Prometheus格式
        print("\nPrometheus格式:")
        print(exporter.to_prometheus_format())

    elif args.export_file:
        # 导出到文件
        exporter.save_to_file(args.export_file)

    else:
        # 启动HTTP服务器
        server = PrometheusHTTPServer(args.port)
        server.start()


if __name__ == "__main__":
    main()
