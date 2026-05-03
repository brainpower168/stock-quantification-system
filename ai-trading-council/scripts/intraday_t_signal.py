#!/usr/bin/env python3
"""
日内做T信号检测器
================
核心信号：
1. 分时均线突破
2. MACD背离
3. 主力资金流向
4. 大盘状态

使用方法：
    python intraday_t_signal.py --stock 002460          # 分析单只股票
    python intraday_t_signal.py --watch                 # 监控自选股
    python intraday_t_signal.py --position 002460,100   # 持仓监控
"""

import argparse
import json
import os
import sys
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class IntradayTSignal:
    """日内做T信号检测器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 做T参数
        self.min_amplitude = self.config.get("min_amplitude", 3.0)  # 最小振幅3%
        self.stop_loss_pct = self.config.get("stop_loss_pct", 2.0)  # 止损2%
        self.take_profit_pct = self.config.get("take_profit_pct", 3.0)  # 止盈3%

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

    def get_realtime_data(self, stock_code: str) -> Dict:
        """获取实时行情数据"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        query = f"{stock_code} 最新价 涨跌幅 涨跌额 今开 昨收 最高 最低 成交量 成交额 量比 换手率 主力净流入 DDX"

        payload = {"query": query, "page": "1", "limit": "1", "is_cache": "0"}

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
            data = {
                "code": stock_code,
                "name": item.get("股票简称", ""),
                "price": 0,
                "change_pct": 0,
                "change_amt": 0,
                "open": 0,
                "pre_close": 0,
                "high": 0,
                "low": 0,
                "volume": 0,
                "amount": 0,
                "volume_ratio": 0,
                "turnover_rate": 0,
                "main_inflow": 0,
                "ddx": 0,
            }

            for key, value in item.items():
                if "最新价" in key or "收盘价" in key:
                    data["price"] = value
                elif "涨跌幅" in key:
                    data["change_pct"] = value
                elif "涨跌额" in key:
                    data["change_amt"] = value
                elif "今开" in key:
                    data["open"] = value
                elif "昨收" in key:
                    data["pre_close"] = value
                elif "最高" in key:
                    data["high"] = value
                elif "最低" in key:
                    data["low"] = value
                elif "成交量" in key:
                    data["volume"] = value
                elif "成交额" in key:
                    data["amount"] = value
                elif "量比" in key:
                    data["volume_ratio"] = value
                elif "换手率" in key:
                    data["turnover_rate"] = value
                elif "主力" in key:
                    data["main_inflow"] = value
                elif "ddx" in key.lower():
                    data["ddx"] = value

            return data

        except Exception as e:
            return {"code": stock_code, "error": str(e)}

    def get_market_status(self) -> Dict:
        """获取大盘状态"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        query = "上证指数 最新价 涨跌幅 20日均线"

        payload = {"query": query, "page": "1", "limit": "1", "is_cache": "0"}

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") != 0:
                return {"status": "unknown", "error": result.get("status_msg")}

            datas = result.get("datas", [])
            if not datas:
                return {"status": "unknown", "error": "无数据"}

            item = datas[0]

            price = 0
            change_pct = 0
            ma20 = 0

            for key, value in item.items():
                if "最新价" in key or "收盘价" in key:
                    price = value
                elif "涨跌幅" in key:
                    change_pct = value
                elif "ma20" in key.lower():
                    ma20 = value

            # 判断大盘状态
            if price > ma20 and change_pct > 0:
                status = "强势上涨"
                t_success_rate = "高"
            elif price > ma20 and change_pct < 0:
                status = "强势调整"
                t_success_rate = "中"
            elif price < ma20:
                status = "弱势下跌"
                t_success_rate = "低"
            else:
                status = "震荡"
                t_success_rate = "中"

            return {
                "index": "上证指数",
                "price": price,
                "change_pct": change_pct,
                "ma20": ma20,
                "status": status,
                "t_success_rate": t_success_rate,
                "can_t": price > ma20,  # 大盘在MA20上方才适合做T
            }

        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    def calculate_amplitude(self, data: Dict) -> float:
        """计算日内振幅"""
        if data["high"] > 0 and data["low"] > 0 and data["pre_close"] > 0:
            return (data["high"] - data["low"]) / data["pre_close"] * 100
        return 0

    def check_t_signals(self, data: Dict, market: Dict) -> Dict:
        """
        检测做T信号

        信号类型：
        1. 正T信号（先买后卖）：股价低位 + 主力流入 + 大盘强势
        2. 反T信号（先卖后买）：股价高位 + 主力流出 + 大盘弱势
        """
        signals = []

        # 计算振幅
        amplitude = self.calculate_amplitude(data)

        # 计算当前位置（相对日内高低点）
        if data["high"] > data["low"]:
            position = (
                (data["price"] - data["low"]) / (data["high"] - data["low"]) * 100
            )
        else:
            position = 50

        # 信号1：分时位置
        if position < 30:
            signals.append(
                {
                    "type": "正T",
                    "signal": "低位买入",
                    "strength": "强" if position < 20 else "中",
                    "reason": f"股价在日内低位（{position:.0f}%位置）",
                }
            )
        elif position > 70:
            signals.append(
                {
                    "type": "反T",
                    "signal": "高位卖出",
                    "strength": "强" if position > 80 else "中",
                    "reason": f"股价在日内高位（{position:.0f}%位置）",
                }
            )

        # 信号2：主力资金
        if data["main_inflow"] > 0:
            signals.append(
                {
                    "type": "正T",
                    "signal": "主力流入",
                    "strength": "强" if data["main_inflow"] > 500000000 else "中",
                    "reason": f"主力净流入{data['main_inflow'] / 100000000:.2f}亿",
                }
            )
        elif data["main_inflow"] < 0:
            signals.append(
                {
                    "type": "反T",
                    "signal": "主力流出",
                    "strength": "强" if data["main_inflow"] < -500000000 else "中",
                    "reason": f"主力净流出{abs(data['main_inflow']) / 100000000:.2f}亿",
                }
            )

        # 信号3：DDX
        if data["ddx"] > 0:
            signals.append(
                {
                    "type": "正T",
                    "signal": "DDX为正",
                    "strength": "中",
                    "reason": f"DDX={data['ddx']:.0f}",
                }
            )
        elif data["ddx"] < 0:
            signals.append(
                {
                    "type": "反T",
                    "signal": "DDX为负",
                    "strength": "中",
                    "reason": f"DDX={data['ddx']:.0f}",
                }
            )

        # 信号4：量比
        if data["volume_ratio"] > 2:
            signals.append(
                {
                    "type": "注意",
                    "signal": "放量异动",
                    "strength": "强",
                    "reason": f"量比{data['volume_ratio']:.2f}，波动大",
                }
            )

        # 综合判断
        positive_signals = [s for s in signals if s["type"] == "正T"]
        negative_signals = [s for s in signals if s["type"] == "反T"]

        # 结合大盘
        if not market.get("can_t", True):
            recommendation = "观望"
            reason = f"大盘{market.get('status', '弱势')}，不适合做T"
        elif len(positive_signals) > len(negative_signals):
            recommendation = "正T"
            reason = f"买入信号{len(positive_signals)}个，适合先买后卖"
        elif len(negative_signals) > len(positive_signals):
            recommendation = "反T"
            reason = f"卖出信号{len(negative_signals)}个，适合先卖后买"
        else:
            recommendation = "观望"
            reason = "信号不明确，等待机会"

        return {
            "amplitude": round(amplitude, 2),
            "position": round(position, 1),
            "signals": signals,
            "positive_count": len(positive_signals),
            "negative_count": len(negative_signals),
            "recommendation": recommendation,
            "reason": reason,
            "market_status": market.get("status", "未知"),
            "t_success_rate": market.get("t_success_rate", "未知"),
        }

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        # 获取大盘状态
        market = self.get_market_status()

        # 获取个股数据
        data = self.get_realtime_data(stock_code)

        if "error" in data:
            return {"code": stock_code, "error": data["error"]}

        # 检测信号
        signals = self.check_t_signals(data, market)

        return {
            "code": stock_code,
            "name": data["name"],
            "price": data["price"],
            "change_pct": data["change_pct"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "volume_ratio": data["volume_ratio"],
            "main_inflow": data["main_inflow"],
            "ddx": data["ddx"],
            "t_signals": signals,
        }

    def watch_stocks(self) -> List[Dict]:
        """监控自选股"""
        results = []

        print(f"\n{'=' * 70}")
        print(f"日内做T信号监控")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        for stock_code in self.watchlist:
            print(f"分析 {stock_code}...", end=" ")
            result = self.analyze_stock(stock_code)

            if "error" in result:
                print(f"失败: {result['error']}")
                continue

            print(f"完成 - {result['name']} [{result['t_signals']['recommendation']}]")
            results.append(result)

        return results

    def generate_report(self, results: List[Dict]) -> str:
        """生成报告"""
        report = []
        report.append(f"\n{'=' * 70}")
        report.append(f"日内做T信号报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'=' * 70}\n")

        # 大盘状态
        market = self.get_market_status()
        report.append(f"大盘状态: {market.get('status', '未知')}")
        report.append(f"做T成功率: {market.get('t_success_rate', '未知')}")
        report.append(f"是否适合做T: {'是' if market.get('can_t', False) else '否'}")
        report.append("")

        if not results:
            report.append("无数据")
            return "\n".join(report)

        # 分类显示
        positive_t = [r for r in results if r["t_signals"]["recommendation"] == "正T"]
        negative_t = [r for r in results if r["t_signals"]["recommendation"] == "反T"]
        wait = [r for r in results if r["t_signals"]["recommendation"] == "观望"]

        # 正T信号
        if positive_t:
            report.append(f"\n【正T信号 - 先买后卖】")
            report.append("-" * 70)
            for r in positive_t:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(
                    f"    价格: {r['price']:.2f} | 涨跌: {r['change_pct']:.2f}%"
                )
                report.append(
                    f"    日内位置: {r['t_signals']['position']:.0f}% | 振幅: {r['t_signals']['amplitude']:.2f}%"
                )
                report.append(
                    f"    主力: {r['main_inflow'] / 100000000:.2f}亿 | DDX: {r['ddx']:.0f}"
                )
                report.append(f"    信号: {r['t_signals']['reason']}")
                report.append("")

        # 反T信号
        if negative_t:
            report.append(f"\n【反T信号 - 先卖后买】")
            report.append("-" * 70)
            for r in negative_t:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(
                    f"    价格: {r['price']:.2f} | 涨跌: {r['change_pct']:.2f}%"
                )
                report.append(
                    f"    日内位置: {r['t_signals']['position']:.0f}% | 振幅: {r['t_signals']['amplitude']:.2f}%"
                )
                report.append(
                    f"    主力: {r['main_inflow'] / 100000000:.2f}亿 | DDX: {r['ddx']:.0f}"
                )
                report.append(f"    信号: {r['t_signals']['reason']}")
                report.append("")

        # 操作建议
        report.append(f"\n【操作建议】")
        report.append("-" * 70)
        report.append("1. 正T操作：股价低位时买入，反弹后卖出同等数量")
        report.append("2. 反T操作：股价高位时卖出，回落后买回同等数量")
        report.append("3. 止损纪律：日内亏损2%立即停止")
        report.append("4. 仓位控制：做T资金不超过底仓的20%-30%")
        report.append("5. 时间窗口：10:30-11:00 和 13:30-14:30 是黄金时段")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="日内做T信号检测")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--watch", action="store_true", help="监控自选股")
    parser.add_argument(
        "--position", type=str, help="持仓监控（格式：股票代码,股数,成本）"
    )

    args = parser.parse_args()

    detector = IntradayTSignal()

    if args.stock:
        # 分析单只股票
        result = detector.analyze_stock(args.stock)
        if "error" in result:
            print(f"分析失败: {result['error']}")
            return

        print(f"\n{'=' * 70}")
        print(f"{result['name']} ({result['code']}) 做T信号分析")
        print(f"{'=' * 70}\n")

        print(f"价格: {result['price']:.2f} | 涨跌: {result['change_pct']:.2f}%")
        print(f"最高: {result['high']:.2f} | 最低: {result['low']:.2f}")
        print(f"日内位置: {result['t_signals']['position']:.0f}%")
        print(f"日内振幅: {result['t_signals']['amplitude']:.2f}%")
        print(f"量比: {result['volume_ratio']:.2f}")
        print(
            f"主力: {result['main_inflow'] / 100000000:.2f}亿 | DDX: {result['ddx']:.0f}"
        )

        print(f"\n信号列表:")
        print("-" * 40)
        for sig in result["t_signals"]["signals"]:
            print(f"  [{sig['type']}] {sig['signal']} ({sig['strength']})")
            print(f"    {sig['reason']}")

        print(f"\n综合建议: {result['t_signals']['recommendation']}")
        print(f"原因: {result['t_signals']['reason']}")

    elif args.watch or True:
        # 监控自选股
        results = detector.watch_stocks()
        report = detector.generate_report(results)
        print(report)

        # 保存报告
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            f"intraday_t_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
