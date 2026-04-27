#!/usr/bin/env python3
"""
趋势跟踪选股系统
识别翻倍潜力股
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from selector_integration import StockDataFetcher


class TrendFollower:
    """趋势跟踪选股系统 - 识别翻倍潜力股"""

    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.iwencai_apikey = os.environ.get("IWENCAI_API_KEY", "")

    def find_trending_stocks(self, limit: int = 20) -> List[Dict]:
        """寻找趋势向上的股票"""
        print("正在扫描趋势股...")

        # 查询条件：均线多头 + 主力流入 + 业绩增长
        query = """
        均线多头排列（MA5>MA10>MA20>MA60）
        主力资金近5日净流入大于3亿
        净利润增长率大于20%
        ROE大于12%
        KDJ小于70
        近20日涨幅小于30%
        """

        try:
            import urllib.request

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_apikey}",
                "Content-Type": "application/json",
            }

            payload = {
                "query": "均线多头排列 主力资金近5日净流入大于3亿 净利润增长率大于20% ROE大于12% KDJ小于70 近20日涨幅小于30%",
                "page": "1",
                "limit": str(limit),
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            stocks = []
            datas = result.get("datas", [])

            for item in datas:
                stock = self._parse_stock(item)
                if stock:
                    stocks.append(stock)

            return stocks

        except Exception as e:
            print(f"查询失败: {e}")
            return []

    def _parse_stock(self, item: Dict) -> Optional[Dict]:
        """解析股票数据"""
        try:
            stock = {
                "code": item.get("股票代码", "").replace(".SH", "").replace(".SZ", ""),
                "name": item.get("股票简称", ""),
                "price": self._parse_value(item.get("最新价", 0)),
                "change_pct": self._parse_value(item.get("最新涨跌幅", 0)),
                "kdj": self._parse_value(item.get("KDJ", 50)),
                "rsi": self._parse_value(item.get("RSI", 50)),
                "capital_flow": self._parse_value(item.get("主力资金流向", 0)) / 1e8,
                "roe": self._parse_value(item.get("ROE", 0)),
                "profit_growth": self._parse_value(item.get("净利润增长率", 0)),
                "pe": self._parse_value(item.get("市盈率", 0)),
            }

            if stock["code"] and stock["price"] > 0:
                return stock

        except:
            pass

        return None

    def _parse_value(self, value) -> float:
        """解析数值"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace("%", "").replace(",", ""))
            except:
                return 0
        return 0

    def calculate_trend_score(self, stock: Dict) -> Dict:
        """计算趋势得分"""
        score = 0
        signals = []

        # 1. 均线多头（核心条件）
        score += 30
        signals.append("均线多头排列")

        # 2. 主力资金
        capital = stock.get("capital_flow", 0)
        if capital > 10:
            score += 25
            signals.append(f"主力大额流入{capital:.1f}亿")
        elif capital > 5:
            score += 15
            signals.append(f"主力流入{capital:.1f}亿")
        elif capital > 0:
            score += 5
            signals.append(f"主力流入{capital:.1f}亿")

        # 3. 业绩增长
        profit_growth = stock.get("profit_growth", 0)
        if profit_growth > 50:
            score += 20
            signals.append(f"业绩高增长{profit_growth:.0f}%")
        elif profit_growth > 30:
            score += 15
            signals.append(f"业绩增长{profit_growth:.0f}%")
        elif profit_growth > 0:
            score += 5
            signals.append(f"业绩正增长{profit_growth:.0f}%")

        # 4. ROE
        roe = stock.get("roe", 0)
        if roe > 20:
            score += 15
            signals.append(f"ROE优秀{roe:.0f}%")
        elif roe > 15:
            score += 10
            signals.append(f"ROE良好{roe:.0f}%")

        # 5. 技术面
        kdj = stock.get("kdj", 50)
        rsi = stock.get("rsi", 50)

        if kdj < 50:
            score += 10
            signals.append(f"KDJ健康{kdj:.0f}")
        elif kdj > 80:
            score -= 10

        if rsi < 60:
            score += 5
            signals.append(f"RSI健康{rsi:.0f}")
        elif rsi > 70:
            score -= 5

        # 6. 估值
        pe = stock.get("pe", 0)
        if 0 < pe < 30:
            score += 5
            signals.append(f"估值合理PE{pe:.0f}")

        return {"score": score, "signals": signals, "rating": self._get_rating(score)}

    def _get_rating(self, score: int) -> str:
        """评级"""
        if score >= 80:
            return "★★★★★ 翻倍潜力"
        elif score >= 60:
            return "★★★★ 强势趋势"
        elif score >= 40:
            return "★★★ 趋势向上"
        else:
            return "★★ 一般"

    def scan(self, top_n: int = 10) -> List[Dict]:
        """扫描趋势股"""
        stocks = self.find_trending_stocks(limit=30)

        results = []
        for stock in stocks:
            trend = self.calculate_trend_score(stock)
            stock["trend_score"] = trend["score"]
            stock["signals"] = trend["signals"]
            stock["rating"] = trend["rating"]
            results.append(stock)

        # 按得分排序
        results.sort(key=lambda x: x["trend_score"], reverse=True)

        return results[:top_n]

    def generate_report(self, stocks: List[Dict]) -> str:
        """生成报告"""
        lines = [
            "# 趋势跟踪选股报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "**策略说明**: 均线多头 + 主力流入 + 业绩增长，适合中线持有1-3个月",
            "",
            "---",
            "",
            "## 翻倍潜力股",
            "",
        ]

        for i, s in enumerate(stocks, 1):
            if s["trend_score"] >= 60:
                lines.append(f"### {i}. {s['name']}({s['code']})")
                lines.append(f"")
                lines.append(f"| 项目 | 数值 |")
                lines.append(f"|------|------|")
                lines.append(f"| 趋势得分 | **{s['trend_score']}** |")
                lines.append(f"| 评级 | **{s['rating']}** |")
                lines.append(f"| 价格 | {s['price']:.2f}元 |")
                lines.append(f"| 主力资金 | {s['capital_flow']:.1f}亿 |")
                lines.append(f"| 业绩增长 | {s['profit_growth']:.0f}% |")
                lines.append(f"| ROE | {s['roe']:.0f}% |")
                lines.append(f"| KDJ/RSI | {s['kdj']:.0f} / {s['rsi']:.0f} |")
                lines.append(f"")

                lines.append(f"**信号**:")
                for signal in s["signals"]:
                    lines.append(f"- {signal}")

                lines.append(f"")
                lines.append(f"**操作建议**:")
                lines.append(f"- 买入价: {s['price'] * 0.98:.2f} - {s['price']:.2f}元")
                lines.append(f"- 止损价: {s['price'] * 0.90:.2f}元（-10%）")
                lines.append(
                    f"- 目标价: {s['price'] * 1.30:.2f} - {s['price'] * 1.50:.2f}元（+30%~50%）"
                )
                lines.append(f"- 持有周期: 1-3个月")
                lines.append(f"")
                lines.append(f"---")
                lines.append(f"")

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="趋势跟踪选股系统")
    parser.add_argument("--scan", action="store_true", help="扫描趋势股")
    parser.add_argument("--top", type=int, default=10, help="显示前N只")

    args = parser.parse_args()

    follower = TrendFollower()

    if args.scan:
        print(f"\n{'=' * 60}")
        print(f"趋势跟踪选股 - 寻找翻倍潜力股")
        print(f"{'=' * 60}\n")

        stocks = follower.scan(top_n=args.top)

        print(f"\n发现 {len(stocks)} 只趋势股:\n")

        for i, s in enumerate(stocks, 1):
            print(f"[{i}] {s['name']}({s['code']})")
            print(f"    得分: {s['trend_score']} | {s['rating']}")
            print(f"    价格: {s['price']:.2f}元 | 主力: {s['capital_flow']:.1f}亿")
            print(f"    业绩: {s['profit_growth']:.0f}% | ROE: {s['roe']:.0f}%")
            print(f"    信号: {', '.join(s['signals'][:3])}")
            print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
