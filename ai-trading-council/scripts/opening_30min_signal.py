#!/usr/bin/env python3
"""
开盘30分钟信号检测器
====================
核心逻辑：通过开盘30分钟的走势判断全天涨跌

六句口诀：
1. 先涨后跌，跌破开盘价 → 赶紧跑
2. 先涨后跌，未破开盘价 → 继续持有
3. 先跌后反弹，未破开盘价 → 反弹卖出
4. 先跌后反弹，突破开盘价 → 可以跟进
5. 小幅拉升，震荡放量 → 重点盯紧
6. 震荡无方向，量能低迷 → 远离观望

使用方法：
    python opening_30min_signal.py --stock 002460
    python opening_30min_signal.py --watch
"""

import argparse
import json
import os
import sys
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Opening30MinSignal:
    """开盘30分钟信号检测器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

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

    def get_intraday_data(self, stock_code: str) -> Dict:
        """获取日内分时数据"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 查询今日分时数据
        query = f"{stock_code} 今日分时 今开 最新价 最高 最低 成交量 成交额"

        payload = {"query": query, "page": "1", "limit": "50", "is_cache": "0"}

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

            # 解析数据
            item = datas[0]
            data = {
                "code": stock_code,
                "name": item.get("股票简称", ""),
                "open": 0,
                "price": 0,
                "high": 0,
                "low": 0,
                "volume": 0,
                "amount": 0,
            }

            for key, value in item.items():
                if "今开" in key:
                    data["open"] = value
                elif "最新价" in key:
                    data["price"] = value
                elif "最高" in key:
                    data["high"] = value
                elif "最低" in key:
                    data["low"] = value
                elif "成交量" in key:
                    data["volume"] = value
                elif "成交额" in key:
                    data["amount"] = value

            return data

        except Exception as e:
            return {"code": stock_code, "error": str(e)}

    def analyze_opening_pattern(
        self,
        open_price: float,
        current_price: float,
        high: float,
        low: float,
        volume: int = 0,
        avg_volume: int = 0,
    ) -> Dict:
        """
        分析开盘30分钟走势形态

        Args:
            open_price: 开盘价
            current_price: 当前价
            high: 最高价
            low: 最低价
            volume: 成交量
            avg_volume: 平均成交量

        Returns:
            形态分析结果
        """
        # 检查开盘价是否有效
        if open_price <= 0:
            return {
                "pattern": "数据异常",
                "signal": "无法判断",
                "action": "观望",
                "confidence": "低",
                "reason": "开盘价数据无效，无法分析",
                "high_vs_open": 0,
                "low_vs_open": 0,
                "current_vs_open": 0,
                "amplitude": 0,
                "volume_status": "未知",
                "broke_open": False,
                "above_open": False,
            }

        # 计算关键指标
        high_vs_open = (high - open_price) / open_price * 100  # 最高点相对开盘价
        low_vs_open = (low - open_price) / open_price * 100  # 最低点相对开盘价
        current_vs_open = (
            (current_price - open_price) / open_price * 100
        )  # 当前相对开盘价

        # 判断走势顺序
        # 先涨后跌：最高点出现在开盘价上方，最低点出现在最高点之后
        # 先跌后涨：最低点出现在开盘价下方，最高点出现在最低点之后

        # 简化判断：根据当前价格与开盘价的关系
        broke_open = current_price < open_price  # 跌破开盘价
        above_open = current_price > open_price  # 站上开盘价

        # 判断形态
        pattern = ""
        signal = ""
        action = ""
        confidence = "中"

        # 计算振幅
        amplitude = (high - low) / open_price * 100

        # 判断量能
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        volume_status = (
            "放量" if volume_ratio > 1.5 else ("缩量" if volume_ratio < 0.7 else "正常")
        )

        # 六种形态判断
        if high > open_price and current_price < open_price:
            # 先涨后跌，跌破开盘价
            pattern = "先涨后跌，跌破开盘价"
            signal = "第1句"
            action = "赶紧跑"
            confidence = "高" if volume_status == "放量" else "中"
            reason = f"主力诱多出逃，最高涨{high_vs_open:.2f}%，现跌{abs(current_vs_open):.2f}%"

        elif high > open_price and current_price >= open_price * 0.99:
            # 先涨后跌，未破开盘价
            pattern = "先涨后跌，未破开盘价"
            signal = "第2句"
            action = "继续持有"
            confidence = "中"
            reason = f"散户获利了结，主力洗盘，最高涨{high_vs_open:.2f}%"

        elif low < open_price and current_price < open_price and current_price >= low:
            # 先跌后反弹，未破开盘价
            pattern = "先跌后反弹，未破开盘价"
            signal = "第3句"
            action = "反弹卖出"
            confidence = "高"
            reason = f"散户抄底，主力已跑，最低跌{abs(low_vs_open):.2f}%"

        elif low < open_price and current_price > open_price:
            # 先跌后反弹，突破开盘价
            pattern = "先跌后反弹，突破开盘价"
            signal = "第4句"
            action = "可以跟进"
            confidence = "高" if volume_status == "放量" else "中"
            reason = f"强势主力抄底，最低跌{abs(low_vs_open):.2f}%，现涨{current_vs_open:.2f}%"

        elif abs(current_vs_open) < 3 and amplitude < 5:
            # 小幅震荡
            if volume_status == "放量":
                pattern = "小幅拉升，震荡放量"
                signal = "第5句"
                action = "重点盯紧"
                confidence = "中"
                reason = "主力压价吸筹，随时可能拉升"
            else:
                pattern = "震荡无方向，量能低迷"
                signal = "第6句"
                action = "远离观望"
                confidence = "中"
                reason = "无主力参与，短线难有表现"

        else:
            # 其他情况
            if current_price > open_price:
                pattern = "强势上涨"
                signal = "看多"
                action = "持有"
                confidence = "高" if volume_status == "放量" else "中"
                reason = f"站上开盘价，涨幅{current_vs_open:.2f}%"
            else:
                pattern = "弱势下跌"
                signal = "看空"
                action = "观望"
                confidence = "高" if volume_status == "放量" else "中"
                reason = f"跌破开盘价，跌幅{abs(current_vs_open):.2f}%"

        return {
            "pattern": pattern,
            "signal": signal,
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "high_vs_open": round(high_vs_open, 2),
            "low_vs_open": round(low_vs_open, 2),
            "current_vs_open": round(current_vs_open, 2),
            "amplitude": round(amplitude, 2),
            "volume_status": volume_status,
            "broke_open": broke_open,
            "above_open": above_open,
        }

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        data = self.get_intraday_data(stock_code)

        if "error" in data:
            return {"code": stock_code, "error": data["error"]}

        # 分析形态
        pattern = self.analyze_opening_pattern(
            open_price=data["open"],
            current_price=data["price"],
            high=data["high"],
            low=data["low"],
            volume=data["volume"],
        )

        return {
            "code": stock_code,
            "name": data["name"],
            "open": data["open"],
            "price": data["price"],
            "high": data["high"],
            "low": data["low"],
            "change_pct": (data["price"] - data["open"]) / data["open"] * 100
            if data["open"] > 0
            else 0,
            "pattern": pattern,
        }

    def watch_stocks(self) -> List[Dict]:
        """监控自选股"""
        results = []

        print(f"\n{'=' * 70}")
        print(f"开盘30分钟信号监控")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        for stock_code in self.watchlist:
            print(f"分析 {stock_code}...", end=" ")
            result = self.analyze_stock(stock_code)

            if "error" in result:
                print(f"失败: {result['error']}")
                continue

            print(f"完成 - {result['name']} [{result['pattern']['action']}]")
            results.append(result)

        return results

    def generate_report(self, results: List[Dict]) -> str:
        """生成报告"""
        report = []
        report.append(f"\n{'=' * 70}")
        report.append(f"开盘30分钟信号报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'=' * 70}\n")

        if not results:
            report.append("无数据")
            return "\n".join(report)

        # 按信号分类
        run_stocks = [r for r in results if "跑" in r["pattern"]["action"]]
        hold_stocks = [r for r in results if "持有" in r["pattern"]["action"]]
        buy_stocks = [r for r in results if "跟进" in r["pattern"]["action"]]
        sell_stocks = [r for r in results if "卖出" in r["pattern"]["action"]]
        watch_stocks = [r for r in results if "盯紧" in r["pattern"]["action"]]
        wait_stocks = [r for r in results if "观望" in r["pattern"]["action"]]

        # 赶紧跑
        if run_stocks:
            report.append(f"\n【赶紧跑 - 主力出逃】")
            report.append("-" * 70)
            for r in run_stocks:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(f"    开盘: {r['open']:.2f} | 当前: {r['price']:.2f}")
                report.append(
                    f"    最高: {r['high']:.2f} ({r['pattern']['high_vs_open']:+.2f}%)"
                )
                report.append(f"    形态: {r['pattern']['pattern']}")
                report.append(f"    原因: {r['pattern']['reason']}")
                report.append(f"    置信度: {r['pattern']['confidence']}")
                report.append("")

        # 可以跟进
        if buy_stocks:
            report.append(f"\n【可以跟进 - 主力抄底】")
            report.append("-" * 70)
            for r in buy_stocks:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(f"    开盘: {r['open']:.2f} | 当前: {r['price']:.2f}")
                report.append(
                    f"    最低: {r['low']:.2f} ({r['pattern']['low_vs_open']:.2f}%)"
                )
                report.append(f"    形态: {r['pattern']['pattern']}")
                report.append(f"    原因: {r['pattern']['reason']}")
                report.append(f"    置信度: {r['pattern']['confidence']}")
                report.append("")

        # 继续持有
        if hold_stocks:
            report.append(f"\n【继续持有 - 主力洗盘】")
            report.append("-" * 70)
            for r in hold_stocks:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(f"    开盘: {r['open']:.2f} | 当前: {r['price']:.2f}")
                report.append(f"    形态: {r['pattern']['pattern']}")
                report.append(f"    原因: {r['pattern']['reason']}")
                report.append("")

        # 反弹卖出
        if sell_stocks:
            report.append(f"\n【反弹卖出 - 主力已跑】")
            report.append("-" * 70)
            for r in sell_stocks:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(f"    开盘: {r['open']:.2f} | 当前: {r['price']:.2f}")
                report.append(f"    形态: {r['pattern']['pattern']}")
                report.append(f"    原因: {r['pattern']['reason']}")
                report.append("")

        # 重点盯紧
        if watch_stocks:
            report.append(f"\n【重点盯紧 - 主力吸筹】")
            report.append("-" * 70)
            for r in watch_stocks:
                report.append(f"  {r['name']} ({r['code']})")
                report.append(f"    开盘: {r['open']:.2f} | 当前: {r['price']:.2f}")
                report.append(f"    量能: {r['pattern']['volume_status']}")
                report.append(f"    形态: {r['pattern']['pattern']}")
                report.append("")

        # 六句口诀
        report.append(f"\n【六句口诀】")
        report.append("-" * 70)
        report.append("1. 先涨后跌，跌破开盘价 → 赶紧跑")
        report.append("2. 先涨后跌，未破开盘价 → 继续持有")
        report.append("3. 先跌后反弹，未破开盘价 → 反弹卖出")
        report.append("4. 先跌后反弹，突破开盘价 → 可以跟进")
        report.append("5. 小幅拉升，震荡放量 → 重点盯紧")
        report.append("6. 震荡无方向，量能低迷 → 远离观望")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="开盘30分钟信号检测")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--watch", action="store_true", help="监控自选股")

    args = parser.parse_args()

    detector = Opening30MinSignal()

    if args.stock:
        # 分析单只股票
        result = detector.analyze_stock(args.stock)
        if "error" in result:
            print(f"分析失败: {result['error']}")
            return

        print(f"\n{'=' * 70}")
        print(f"{result['name']} ({result['code']}) 开盘30分钟分析")
        print(f"{'=' * 70}\n")

        print(f"开盘价: {result['open']:.2f}")
        print(f"当前价: {result['price']:.2f}")
        print(
            f"最高价: {result['high']:.2f} ({result['pattern']['high_vs_open']:+.2f}%)"
        )
        print(f"最低价: {result['low']:.2f} ({result['pattern']['low_vs_open']:.2f}%)")
        print(f"振幅: {result['pattern']['amplitude']:.2f}%")
        print(f"量能: {result['pattern']['volume_status']}")

        print(f"\n形态: {result['pattern']['pattern']}")
        print(f"信号: {result['pattern']['signal']}")
        print(f"操作: {result['pattern']['action']}")
        print(f"原因: {result['pattern']['reason']}")
        print(f"置信度: {result['pattern']['confidence']}")

    else:
        # 监控自选股
        results = detector.watch_stocks()
        report = detector.generate_report(results)
        print(report)

        # 保存报告
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            f"opening_30min_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
