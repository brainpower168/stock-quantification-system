#!/usr/bin/env python3
"""
尾盘30分钟选股策略
==================
核心逻辑：尾盘买入，规避盘中风险，次日可随时卖出

选股条件：
1. 涨幅 3%-5%
2. 量比 > 1
3. 主力资金流入
4. 股价在均价线上方
5. DDX > 0

使用方法：
    python tail_market_selector.py          # 筛选自选股
    python tail_market_selector.py --scan   # 全市场扫描
    python tail_market_selector.py --watch  # 持续监控
"""

import argparse
import json
import os
import sys
from datetime import datetime, time
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TailMarketSelector:
    """尾盘30分钟选股器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 选股参数
        self.min_change_pct = self.config.get("min_change_pct", 3.0)  # 最小涨幅
        self.max_change_pct = self.config.get("max_change_pct", 5.0)  # 最大涨幅
        self.min_volume_ratio = self.config.get("min_volume_ratio", 1.0)  # 最小量比
        self.min_turnover_rate = self.config.get("min_turnover_rate", 5.0)  # 最小换手率
        self.max_turnover_rate = self.config.get(
            "max_turnover_rate", 10.0
        )  # 最大换手率

        # 用户自选股
        self.watchlist = [
            "601138",  # 工业富联
            "002475",  # 立讯精密
            "002460",  # 赣锋锂业
            "002281",  # 光迅科技
            "002463",  # 沪电股份
            "300750",  # 宁德时代
            "300476",  # 胜宏科技
            "000988",  # 华工科技
        ]

    def check_tail_market_conditions(
        self,
        stock_data: Dict,
        realtime_data: Optional[Dict] = None,
    ) -> Dict:
        """
        检查尾盘买入条件

        Args:
            stock_data: 股票数据（涨幅、量比、换手率、主力资金等）
            realtime_data: 分时数据（均价线、分时走势等）

        Returns:
            检查结果
        """
        checks = {}

        # 1. 涨幅控制（3%-5%）
        change_pct = stock_data.get("change_pct", 0)
        checks["change_range"] = {
            "name": "涨幅3%-5%",
            "passed": self.min_change_pct <= change_pct <= self.max_change_pct,
            "value": change_pct,
            "detail": f"涨幅 {change_pct:.2f}%",
        }

        # 2. 量比 > 1
        volume_ratio = stock_data.get("volume_ratio", 0)
        checks["volume_ratio"] = {
            "name": "量比 > 1",
            "passed": volume_ratio > self.min_volume_ratio,
            "value": volume_ratio,
            "detail": f"量比 {volume_ratio:.2f}",
        }

        # 3. 换手率（5%-10%）
        turnover_rate = stock_data.get("turnover_rate", 0)
        checks["turnover_rate"] = {
            "name": "换手率5%-10%",
            "passed": self.min_turnover_rate <= turnover_rate <= self.max_turnover_rate,
            "value": turnover_rate,
            "detail": f"换手率 {turnover_rate:.2f}%",
        }

        # 4. 主力资金流入
        main_inflow = stock_data.get("main_inflow", 0)
        checks["main_inflow"] = {
            "name": "主力资金流入",
            "passed": main_inflow > 0,
            "value": main_inflow,
            "detail": f"主力净流入 {main_inflow / 100000000:.2f}亿",
        }

        # 5. DDX > 0（融合现有策略）
        ddx_10 = stock_data.get("ddx_10", 0)
        checks["ddx_positive"] = {
            "name": "10日DDX > 0",
            "passed": ddx_10 > 0,
            "value": ddx_10,
            "detail": f"10日DDX {ddx_10:.0f}",
            "required": True,
        }

        # 6. 股价在均价线上方（如果有分时数据）
        if realtime_data:
            price = realtime_data.get("price", 0)
            avg_price = realtime_data.get("avg_price", 0)
            checks["above_avg_price"] = {
                "name": "股价在均价线上方",
                "passed": price > avg_price,
                "value": price,
                "detail": f"现价 {price:.2f}，均价 {avg_price:.2f}",
            }

        # 计算得分
        total_weight = len(checks)
        passed_count = sum(1 for c in checks.values() if c["passed"])
        score = passed_count / total_weight * 100 if total_weight > 0 else 0

        # 判断是否可以买入
        # 必须：DDX > 0
        ddx_pass = checks.get("ddx_positive", {}).get("passed", False)
        # 至少满足3个条件
        min_conditions = passed_count >= 3

        can_buy = ddx_pass and min_conditions

        return {
            "checks": checks,
            "score": round(score, 1),
            "passed_count": passed_count,
            "total_count": total_weight,
            "can_buy": can_buy,
            "recommendation": "BUY" if can_buy else "WAIT",
        }

    def analyze_stock(self, stock_code: str, stock_name: str = "") -> Dict:
        """分析单只股票"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 查询尾盘数据
        query = f"{stock_code} 最新价 涨跌幅 量比 换手率 主力净流入 10日DDX"

        payload = {"query": query, "page": "1", "limit": "1", "is_cache": "1"}

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") != 0:
                return {"code": stock_code, "error": result.get("status_msg")}

            datas = result.get("datas", [])
            if not datas:
                return {"code": stock_code, "error": "无数据"}

            item = datas[0]

            # 解析数据
            stock_data = {
                "code": stock_code,
                "name": stock_name or item.get("股票简称", ""),
                "price": 0,
                "change_pct": 0,
                "volume_ratio": 0,
                "turnover_rate": 0,
                "main_inflow": 0,
                "ddx_10": 0,
            }

            for key, value in item.items():
                if "收盘价" in key or "最新价" in key:
                    stock_data["price"] = value
                elif "涨跌幅" in key:
                    stock_data["change_pct"] = value
                elif "量比" in key:
                    stock_data["volume_ratio"] = value
                elif "换手率" in key:
                    stock_data["turnover_rate"] = value
                elif "主力" in key:
                    stock_data["main_inflow"] = value
                elif "ddx" in key.lower():
                    stock_data["ddx_10"] = value

            # 检查条件
            check_result = self.check_tail_market_conditions(stock_data)

            return {
                "code": stock_code,
                "name": stock_data["name"],
                "price": stock_data["price"],
                "change_pct": stock_data["change_pct"],
                "volume_ratio": stock_data["volume_ratio"],
                "turnover_rate": stock_data["turnover_rate"],
                "main_inflow": stock_data["main_inflow"],
                "ddx_10": stock_data["ddx_10"],
                "check_result": check_result,
            }

        except Exception as e:
            return {"code": stock_code, "error": str(e)}

    def scan_watchlist(self) -> List[Dict]:
        """扫描自选股"""
        results = []

        print(f"\n{'=' * 60}")
        print(f"尾盘30分钟选股 - 自选股扫描")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        for stock_code in self.watchlist:
            print(f"分析 {stock_code}...", end=" ")
            result = self.analyze_stock(stock_code)

            if "error" in result:
                print(f"失败: {result['error']}")
                continue

            print(f"完成 - {result['name']}")

            if result.get("check_result", {}).get("can_buy"):
                results.append(result)

        # 按得分排序
        results.sort(key=lambda x: x["check_result"]["score"], reverse=True)

        return results

    def generate_report(self, results: List[Dict]) -> str:
        """生成选股报告"""
        report = []
        report.append(f"\n{'=' * 60}")
        report.append(f"尾盘30分钟选股报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'=' * 60}\n")

        if not results:
            report.append("今日无符合条件的股票")
            return "\n".join(report)

        report.append(f"符合条件股票: {len(results)} 只\n")

        for i, r in enumerate(results, 1):
            report.append(f"{i}. {r['name']} ({r['code']})")
            report.append(f"   价格: {r['price']:.2f} 元")
            report.append(f"   涨幅: {r['change_pct']:.2f}%")
            report.append(f"   量比: {r['volume_ratio']:.2f}")
            report.append(f"   换手率: {r['turnover_rate']:.2f}%")
            report.append(f"   主力流入: {r['main_inflow'] / 100000000:.2f}亿")
            report.append(f"   10日DDX: {r['ddx_10']:.0f}")
            report.append(f"   得分: {r['check_result']['score']} 分")
            report.append("")

        report.append("\n买入建议:")
        report.append("-" * 40)
        report.append("1. 2:50-2:55 下单买入")
        report.append("2. 次日高开冲高卖出")
        report.append("3. 次日低开立即止损")
        report.append("4. 严格执行纪律，不贪心")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="尾盘30分钟选股")
    parser.add_argument("--scan", action="store_true", help="扫描自选股")
    parser.add_argument("--watch", action="store_true", help="持续监控")

    args = parser.parse_args()

    selector = TailMarketSelector()

    if args.scan or True:
        results = selector.scan_watchlist()
        report = selector.generate_report(results)
        print(report)

        # 保存报告
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            f"tail_market_report_{datetime.now().strftime('%Y%m%d')}.txt",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
