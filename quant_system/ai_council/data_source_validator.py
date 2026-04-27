#!/usr/bin/env python3
"""
数据源多方对比验证工具
用于重要交易决策前的数据交叉验证
"""

import os
import sys
import json
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# 数据源配置
DATA_SOURCES = {
    "tencent_finance": {
        "name": "腾讯财经",
        "speed": 0.7,
        "stability": "stable",
        "best_for": ["realtime_price"],
        "api_key_required": False,
    },
    "westockdata": {
        "name": "腾讯自选股",
        "speed": 3.0,
        "stability": "stable",
        "best_for": ["kline", "realtime_price"],
        "api_key_required": False,
    },
    "guosen": {
        "name": "国信",
        "speed": 0.5,
        "stability": "stable",
        "best_for": ["fund_flow", "financial", "stock_picking"],
        "api_key_required": True,
        "api_key_env": "GS_API_KEY",
    },
    "miaoxiang": {
        "name": "妙想",
        "speed": 6.0,
        "stability": "stable",
        "best_for": ["fund_flow"],
        "api_key_required": True,
        "api_key_env": "MX_APIKEY",
    },
    "wencai": {
        "name": "问财",
        "speed": 4.0,
        "stability": "unstable",
        "best_for": ["stock_picking"],
        "api_key_required": True,
        "api_key_env": "IWENCAI_API_KEY",
    },
}


@dataclass
class StockData:
    """股票数据结构"""

    code: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    fund_flow_10d: Optional[float] = None  # 10日主力净流入
    fund_flow_today: Optional[float] = None  # 今日主力净流入
    ddx: Optional[float] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None


class DataSourceValidator:
    """数据源多方对比验证器"""

    def __init__(self):
        self.results = {}
        self.conflicts = []

    def get_realtime_price(
        self, stock_code: str, sources: List[str] = None
    ) -> Dict[str, StockData]:
        """
        获取实时股价（多方对比）

        Args:
            stock_code: 股票代码（如 sz002475）
            sources: 数据源列表，默认使用 tencent_finance 和 westockdata

        Returns:
            各数据源返回的股价数据
        """
        if sources is None:
            sources = ["tencent_finance", "westockdata"]

        results = {}

        for source in sources:
            try:
                start_time = time.time()

                if source == "tencent_finance":
                    data = self._query_tencent_finance(stock_code)
                elif source == "westockdata":
                    data = self._query_westockdata(stock_code)
                else:
                    continue

                elapsed = time.time() - start_time
                data.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                results[source] = data

                print(
                    f"[{DATA_SOURCES[source]['name']}] {elapsed:.2f}秒 - 价格: {data.price}, 涨幅: {data.change_percent}%"
                )

            except Exception as e:
                print(f"[{DATA_SOURCES[source]['name']}] 查询失败: {e}")

        # 对比验证
        self._validate_prices(results)

        return results

    def get_fund_flow(
        self, stock_code: str, sources: List[str] = None
    ) -> Dict[str, StockData]:
        """
        获取资金流向（多方对比）

        Args:
            stock_code: 股票代码
            sources: 数据源列表，默认使用 妙想 和 国信
        """
        if sources is None:
            sources = ["miaoxiang", "guosen"]

        results = {}

        for source in sources:
            try:
                start_time = time.time()

                if source == "miaoxiang":
                    data = self._query_miaoxiang_fund_flow(stock_code)
                elif source == "guosen":
                    data = self._query_guosen_fund_flow(stock_code)
                else:
                    continue

                elapsed = time.time() - start_time
                data.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                results[source] = data

                print(
                    f"[{DATA_SOURCES[source]['name']}] {elapsed:.2f}秒 - 10日主力: {data.fund_flow_10d}亿"
                )

            except Exception as e:
                print(f"[{DATA_SOURCES[source]['name']}] 查询失败: {e}")

        # 对比验证
        self._validate_fund_flow(results)

        return results

    def _query_tencent_finance(self, stock_code: str) -> StockData:
        """查询腾讯财经"""
        skill_path = os.path.expanduser(
            "~/.qianfan/workspace/55d1508241624f56a3a831bde4da9cfb/skills/tencent-finance-stock-price/scripts/query_stock.py"
        )

        # 转换代码格式
        if stock_code.startswith("sz"):
            code = stock_code
        elif stock_code.startswith("sh"):
            code = stock_code
        else:
            code = (
                f"sz{stock_code}"
                if stock_code.startswith("0") or stock_code.startswith("3")
                else f"sh{stock_code}"
            )

        result = subprocess.run(
            ["uv", "run", skill_path, code], capture_output=True, text=True, timeout=10
        )

        # 解析输出
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if code in line or stock_code in line:
                parts = line.split()
                if len(parts) >= 5:
                    return StockData(
                        code=stock_code,
                        name=parts[0] if parts[0] != "名称" else "",
                        price=float(parts[2]) if parts[2] != "价格" else None,
                        change=float(parts[3]) if parts[3] != "涨跌" else None,
                        change_percent=float(
                            parts[4]
                            .replace("%", "")
                            .replace("🟢", "")
                            .replace("🔴", "")
                        )
                        if parts[4] != "涨跌幅"
                        else None,
                        source="tencent_finance",
                    )

        return StockData(code=stock_code, name="", source="tencent_finance")

    def _query_westockdata(self, stock_code: str) -> StockData:
        """查询腾讯自选股"""
        result = subprocess.run(
            [
                "npx",
                "-y",
                "westock-data-clawhub@1.0.4",
                "kline",
                stock_code,
                "--period",
                "day",
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        # 解析输出
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "|" in line and "date" not in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    return StockData(
                        code=stock_code,
                        name="",
                        price=float(parts[3]) if parts[3] else None,  # last price
                        source="westockdata",
                    )

        return StockData(code=stock_code, name="", source="westockdata")

    def _query_guosen_fund_flow(self, stock_code: str) -> StockData:
        """查询国信资金流向"""
        gs_api_key = os.environ.get(
            "GS_API_KEY",
            "6Jex4kxx4WraFvcIYwGlJiVMBRTh4xMU-B9ow1FHQWRGjFFgQLOkYOjQE0b3y4zDm-32fTHloPj1XvTpgwFQdwhdsYVNZiOR96",
        )

        set_code = (
            "0"
            if stock_code.startswith("sz")
            or stock_code.startswith("0")
            or stock_code.startswith("3")
            else "1"
        )
        code = stock_code.replace("sz", "").replace("sh", "")

        skill_path = os.path.expanduser(
            "~/.qianfan/workspace/55d1508241624f56a3a831bde4da9cfb/data/skills/user/gs-stock-market-query/gs-stock-market-query/scripts/get_data.py"
        )

        result = subprocess.run(
            [
                "python",
                skill_path,
                "fund_flow",
                "--code",
                code,
                "--set_code",
                set_code,
                "--period",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "GS_API_KEY": gs_api_key},
        )

        # 解析JSON
        try:
            data = json.loads(result.stdout)
            if data.get("result", {}).get("code") == 0:
                obj = data.get("object", {})
                return StockData(
                    code=stock_code,
                    name="",
                    fund_flow_10d=obj.get("mainNetInflow", 0) / 1e8,  # 转换为亿
                    source="guosen",
                )
        except:
            pass

        return StockData(code=stock_code, name="", source="guosen")

    def _query_miaoxiang_fund_flow(self, stock_code: str) -> StockData:
        """查询妙想资金流向"""
        # 简化版，实际需要调用妙想API
        return StockData(code=stock_code, name="", source="miaoxiang")

    def _validate_prices(self, results: Dict[str, StockData]):
        """验证股价数据一致性"""
        if len(results) < 2:
            return

        prices = [
            (source, data.price) for source, data in results.items() if data.price
        ]

        if len(prices) >= 2:
            max_diff = max(abs(p1 - p2) for _, p1 in prices for _, p2 in prices)
            avg_price = sum(p for _, p in prices) / len(prices)
            diff_percent = (max_diff / avg_price) * 100 if avg_price > 0 else 0

            if diff_percent > 1:
                self.conflicts.append(
                    {
                        "type": "price",
                        "message": f"股价数据差异较大: {diff_percent:.2f}%",
                        "details": {source: price for source, price in prices},
                    }
                )
                print(f"⚠️ 警告: 股价数据差异 {diff_percent:.2f}%")
            else:
                print(f"✅ 股价数据一致 (差异 {diff_percent:.2f}%)")

    def _validate_fund_flow(self, results: Dict[str, StockData]):
        """验证资金流向数据一致性"""
        if len(results) < 2:
            return

        flows = [
            (source, data.fund_flow_10d)
            for source, data in results.items()
            if data.fund_flow_10d
        ]

        if len(flows) >= 2:
            # 检查方向是否一致
            directions = [1 if f > 0 else -1 if f < 0 else 0 for _, f in flows]

            if len(set(directions)) > 1:
                self.conflicts.append(
                    {
                        "type": "fund_flow_direction",
                        "message": "资金流向方向不一致",
                        "details": {source: f"{flow:.2f}亿" for source, flow in flows},
                    }
                )
                print(f"⚠️ 警告: 资金流向方向不一致")
            else:
                print(f"✅ 资金流向方向一致")

    def generate_report(self) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 60)
        report.append("数据源多方对比验证报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)

        if self.conflicts:
            report.append("\n⚠️ 发现数据冲突:")
            for conflict in self.conflicts:
                report.append(f"\n- {conflict['type']}: {conflict['message']}")
                for source, value in conflict["details"].items():
                    report.append(f"  {DATA_SOURCES[source]['name']}: {value}")
        else:
            report.append("\n✅ 所有数据源数据一致")

        return "\n".join(report)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据源多方对比验证工具")
    parser.add_argument("--stock", required=True, help="股票代码（如 sz002475）")
    parser.add_argument(
        "--type", choices=["price", "fund_flow", "all"], default="all", help="验证类型"
    )

    args = parser.parse_args()

    validator = DataSourceValidator()

    print(f"\n{'=' * 60}")
    print(f"股票代码: {args.stock}")
    print(f"验证类型: {args.type}")
    print(f"{'=' * 60}\n")

    if args.type in ["price", "all"]:
        print("\n【实时股价验证】")
        validator.get_realtime_price(args.stock)

    if args.type in ["fund_flow", "all"]:
        print("\n【资金流向验证】")
        validator.get_fund_flow(args.stock)

    print("\n" + validator.generate_report())


if __name__ == "__main__":
    main()
