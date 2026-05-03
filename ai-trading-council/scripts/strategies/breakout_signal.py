#!/usr/bin/env python3
"""
突破信号策略
============
用于捕捉正在启动的股票，避免错过短线爆发机会

核心逻辑：
- DDX刚转正（昨天负，今天正）+ 主力流入 = 可能是启动信号
- 不要求DDX稳定性，敢于上车
- 适合短线操作，快进快出

触发条件：
1. 今日DDX > 0
2. 昨日DDX < 0（刚转正）
3. 今日主力流入 > 3000万
4. 涨幅 < 5%（不追涨停）

使用方法：
    python breakout_signal.py --stock 603256
    python breakout_signal.py --screen
    python breakout_signal.py --watch
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BreakoutSignalStrategy:
    """突破信号策略检测器"""

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

    def query_wencai(self, query: str) -> Optional[List[Dict]]:
        """查询问财API"""
        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {"query": query, "page": "1", "limit": "20", "is_cache": "0"}

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") == 0:
                return result.get("datas", [])
        except Exception as e:
            print(f"查询失败: {e}")

        return None

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        # 查询DDX和主力资金
        query = f"{stock_code} DDX 主力资金流向 涨跌幅 最新价"
        datas = self.query_wencai(query)

        if not datas:
            return {"code": stock_code, "error": "查询失败"}

        data = datas[0]

        # 获取10日DDX趋势
        query_ddx = f"{stock_code} 10日DDX"
        ddx_datas = self.query_wencai(query_ddx)

        if ddx_datas:
            ddx_data = ddx_datas[0]
            today_ddx = ddx_data.get("ddx[20260429]", 0)
            yesterday_ddx = ddx_data.get("ddx[20260428]", 0)
        else:
            today_ddx = data.get("ddx", 0)
            yesterday_ddx = 0

        # 判断突破信号
        signal = self.check_breakout_signal(
            today_ddx=today_ddx,
            yesterday_ddx=yesterday_ddx,
            main_flow=data.get("主力资金流向", 0),
            change_pct=data.get("最新涨跌幅", 0),
        )

        return {
            "code": stock_code,
            "name": data.get("股票简称", ""),
            "price": data.get("最新价", 0),
            "change_pct": data.get("最新涨跌幅", 0),
            "main_flow": data.get("主力资金流向", 0),
            "today_ddx": today_ddx,
            "yesterday_ddx": yesterday_ddx,
            "signal": signal["type"],
            "score": signal["score"],
            "reason": signal["reason"],
        }

    def check_breakout_signal(
        self,
        today_ddx: float,
        yesterday_ddx: float,
        main_flow: float,
        change_pct: float,
    ) -> Dict:
        """检查突破信号"""
        score = 0
        reasons = []

        # 条件1：今日DDX > 0
        if today_ddx > 0:
            score += 25
            reasons.append("今日DDX转正")
        else:
            return {"type": "无信号", "score": 0, "reason": "今日DDX未转正"}

        # 条件2：昨日DDX < 0（刚转正）
        if yesterday_ddx < 0:
            score += 30
            reasons.append("DDX刚转正（突破信号）")
        else:
            reasons.append("DDX连续为正")

        # 条件3：主力流入 > 3000万
        if main_flow > 30000000:
            score += 25
            reasons.append(f"主力流入{main_flow / 100000000:.2f}亿")
        elif main_flow > 0:
            score += 10
            reasons.append(f"主力小幅流入{main_flow / 100000000:.2f}亿")
        else:
            reasons.append(f"主力流出{abs(main_flow) / 100000000:.2f}亿")

        # 条件4：涨幅 < 5%
        if 0 < change_pct < 3:
            score += 20
            reasons.append(f"涨幅{change_pct:.2f}%，适合买入")
        elif 3 <= change_pct < 5:
            score += 10
            reasons.append(f"涨幅{change_pct:.2f}%，偏高")
        elif change_pct >= 5:
            reasons.append(f"涨幅{change_pct:.2f}%，不追高")
            score -= 10

        # 判断信号类型
        if score >= 70:
            signal_type = "强突破"
        elif score >= 50:
            signal_type = "弱突破"
        else:
            signal_type = "观望"

        return {
            "type": signal_type,
            "score": score,
            "reason": " | ".join(reasons),
        }

    def screen_stocks(self) -> List[Dict]:
        """筛选突破信号股票"""
        print("正在筛选突破信号股票...")

        # 查询DDX刚转正的股票
        query = (
            "DDX大于0，昨日DDX小于0，主力资金流入大于3000万，涨幅小于5%，按主力流入排序"
        )
        datas = self.query_wencai(query)

        if not datas:
            print("未找到符合条件的股票")
            return []

        results = []
        for data in datas[:20]:
            result = {
                "code": data.get("股票代码", ""),
                "name": data.get("股票简称", ""),
                "price": data.get("最新价", 0),
                "change_pct": data.get("最新涨跌幅", 0),
                "main_flow": data.get("主力资金流向", 0),
                "ddx": data.get("ddx", 0),
            }

            # 计算信号分数
            signal = self.check_breakout_signal(
                today_ddx=result["ddx"],
                yesterday_ddx=-1,  # 假设昨日为负
                main_flow=result["main_flow"],
                change_pct=result["change_pct"],
            )
            result["signal"] = signal["type"]
            result["score"] = signal["score"]
            result["reason"] = signal["reason"]

            results.append(result)

        return results

    def watch_portfolio(self) -> List[Dict]:
        """监控自选股"""
        print("正在监控自选股...")
        results = []

        for code in self.watchlist:
            result = self.analyze_stock(code)
            results.append(result)
            print(
                f"{result.get('name', code)}: {result.get('signal', 'N/A')} ({result.get('score', 0)}分)"
            )

        return results

    def print_report(self, results: List[Dict], title: str = "突破信号报告"):
        """打印报告"""
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        # 按分数排序
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        for i, r in enumerate(results, 1):
            signal_emoji = {"强突破": "🚀", "弱突破": "⚠️", "观望": "⏸️"}.get(
                r.get("signal", "观望"), "❓"
            )

            print(f"{i}. {r.get('name', r.get('code'))} {signal_emoji}")
            print(f"   代码: {r.get('code')}")
            print(f"   现价: {r.get('price', 0):.2f}元")
            print(f"   涨幅: {r.get('change_pct', 0):.2f}%")
            print(f"   主力: {r.get('main_flow', 0) / 100000000:.2f}亿")
            print(f"   DDX: {r.get('today_ddx', 0):.1f}")
            print(f"   信号: {r.get('signal')} ({r.get('score')}分)")
            print(f"   原因: {r.get('reason')}")
            print()

        # 统计
        strong = len([r for r in results if r.get("signal") == "强突破"])
        weak = len([r for r in results if r.get("signal") == "弱突破"])

        print(f"{'=' * 60}")
        print(
            f"统计: 强突破 {strong}只 | 弱突破 {weak}只 | 观望 {len(results) - strong - weak}只"
        )
        print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="突破信号策略")
    parser.add_argument("--stock", type=str, help="分析单只股票")
    parser.add_argument("--screen", action="store_true", help="筛选股票")
    parser.add_argument("--watch", action="store_true", help="监控自选股")

    args = parser.parse_args()

    strategy = BreakoutSignalStrategy()

    if args.stock:
        result = strategy.analyze_stock(args.stock)
        strategy.print_report([result], f"突破信号分析 - {args.stock}")

    elif args.screen:
        results = strategy.screen_stocks()
        if results:
            strategy.print_report(results, "突破信号筛选结果")

    elif args.watch:
        results = strategy.watch_portfolio()
        strategy.print_report(results, "自选股突破信号监控")

    else:
        # 默认监控自选股
        results = strategy.watch_portfolio()
        strategy.print_report(results, "自选股突破信号监控")


if __name__ == "__main__":
    main()
