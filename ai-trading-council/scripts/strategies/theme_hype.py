#!/usr/bin/env python3
"""
题材炒作策略
============
用于捕捉热点题材股票，不看传统技术指标

核心逻辑：
- 有题材热点 = 不看DDX，看资金和情绪
- 板块效应 > 单股指标
- 热点题材要敢于上车

触发条件：
1. 最近有涨停（3日内）
2. 主力流入 > 5000万
3. 换手率 > 5%（活跃）
4. 板块/题材有热度

使用方法：
    python theme_hype.py --stock 603256
    python theme_hype.py --screen
    python theme_hype.py --hot-themes
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ThemeHypeStrategy:
    """题材炒作策略检测器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 热点题材关键词
        self.hot_keywords = [
            "AI",
            "人工智能",
            "算力",
            "芯片",
            "半导体",
            "新能源",
            "固态电池",
            "光伏",
            "储能",
            "稀土",
            "有色金属",
            "黄金",
            "军工",
            "卫星",
            "航天",
            "机器人",
            "无人驾驶",
            "氢能源",
            "核聚变",
            "量子计算",
        ]

    def query_wencai(self, query: str) -> Optional[List[Dict]]:
        """查询问财API"""
        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {"query": query, "page": "1", "limit": "30", "is_cache": "0"}

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
        # 查询基本信息
        query = f"{stock_code} 涨跌幅 主力资金流向 换手率 最新价 所属板块"
        datas = self.query_wencai(query)

        if not datas:
            return {"code": stock_code, "error": "查询失败"}

        data = datas[0]

        # 查询近期涨停情况
        query_limit = f"{stock_code} 3日内涨停"
        limit_datas = self.query_wencai(query_limit)
        has_limit_up = len(limit_datas) > 0 if limit_datas else False

        # 判断题材热度
        theme_score = self.calculate_theme_score(
            has_limit_up=has_limit_up,
            main_flow=data.get("主力资金流向", 0),
            turnover=data.get("换手率", 0),
            change_pct=data.get("最新涨跌幅", 0),
        )

        return {
            "code": stock_code,
            "name": data.get("股票简称", ""),
            "price": data.get("最新价", 0),
            "change_pct": data.get("最新涨跌幅", 0),
            "main_flow": data.get("主力资金流向", 0),
            "turnover": data.get("换手率", 0),
            "sector": data.get("所属板块", ""),
            "has_limit_up": has_limit_up,
            "theme_score": theme_score["score"],
            "theme_level": theme_score["level"],
            "reason": theme_score["reason"],
        }

    def calculate_theme_score(
        self,
        has_limit_up: bool,
        main_flow: float,
        turnover: float,
        change_pct: float,
    ) -> Dict:
        """计算题材热度分数"""
        score = 0
        reasons = []

        # 条件1：近期有涨停
        if has_limit_up:
            score += 30
            reasons.append("3日内有涨停（有涨停基因）")
        else:
            reasons.append("近期无涨停")

        # 条件2：主力流入
        if main_flow > 100000000:  # 1亿
            score += 30
            reasons.append(f"主力大额流入{main_flow / 100000000:.2f}亿")
        elif main_flow > 50000000:  # 5000万
            score += 20
            reasons.append(f"主力流入{main_flow / 100000000:.2f}亿")
        elif main_flow > 0:
            score += 10
            reasons.append(f"主力小幅流入")
        else:
            reasons.append(f"主力流出")

        # 条件3：换手率
        if turnover > 10:
            score += 20
            reasons.append(f"换手率{turnover:.1f}%（高度活跃）")
        elif turnover > 5:
            score += 15
            reasons.append(f"换手率{turnover:.1f}%（活跃）")
        else:
            reasons.append(f"换手率{turnover:.1f}%（不活跃）")

        # 条件4：涨幅
        if 0 < change_pct < 3:
            score += 20
            reasons.append(f"涨幅{change_pct:.2f}%（适合买入）")
        elif 3 <= change_pct < 5:
            score += 10
            reasons.append(f"涨幅{change_pct:.2f}%（偏高）")
        elif change_pct >= 5:
            score += 5
            reasons.append(f"涨幅{change_pct:.2f}%（追高需谨慎）")
        elif change_pct < 0:
            reasons.append(f"跌幅{abs(change_pct):.2f}%")

        # 判断题材热度等级
        if score >= 70:
            level = "🔥 高热度"
        elif score >= 50:
            level = "⚠️ 中等热度"
        else:
            level = "⏸️ 低热度"

        return {"score": score, "level": level, "reason": " | ".join(reasons)}

    def screen_stocks(self) -> List[Dict]:
        """筛选题材炒作股票"""
        print("正在筛选题材炒作股票...")

        # 查询近期有涨停、主力流入的股票
        query = "3日内有涨停，主力资金流入大于5000万，换手率大于5%，涨幅小于5%，按主力流入排序"
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
                "turnover": data.get("换手率", 0),
                "sector": data.get("所属板块", ""),
                "has_limit_up": True,
            }

            # 计算题材分数
            theme = self.calculate_theme_score(
                has_limit_up=True,
                main_flow=result["main_flow"],
                turnover=result["turnover"],
                change_pct=result["change_pct"],
            )
            result["theme_score"] = theme["score"]
            result["theme_level"] = theme["level"]
            result["reason"] = theme["reason"]

            results.append(result)

        return results

    def get_hot_themes(self) -> List[Dict]:
        """获取热点题材"""
        print("正在获取热点题材...")

        # 查询涨幅最大的板块
        query = "板块涨幅前20名"
        datas = self.query_wencai(query)

        if not datas:
            return []

        results = []
        for data in datas[:20]:
            results.append(
                {
                    "name": data.get("板块名称", ""),
                    "change_pct": data.get("涨跌幅", 0),
                    "lead_stock": data.get("领涨股", ""),
                }
            )

        return results

    def print_report(self, results: List[Dict], title: str = "题材炒作报告"):
        """打印报告"""
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"核心原则: 有题材不看DDX | 板块效应 > 单股指标 | 热点要敢于上车")
        print(f"{'=' * 60}\n")

        # 按分数排序
        results.sort(key=lambda x: x.get("theme_score", 0), reverse=True)

        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('name', r.get('code'))} {r.get('theme_level', '')}")
            print(f"   代码: {r.get('code')}")
            print(f"   现价: {r.get('price', 0):.2f}元")
            print(f"   涨幅: {r.get('change_pct', 0):.2f}%")
            print(f"   主力: {r.get('main_flow', 0) / 100000000:.2f}亿")
            print(f"   换手: {r.get('turnover', 0):.1f}%")
            print(f"   板块: {r.get('sector', 'N/A')}")
            print(f"   涨停: {'是' if r.get('has_limit_up') else '否'}")
            print(f"   分数: {r.get('theme_score', 0)}分")
            print(f"   原因: {r.get('reason')}")
            print()

        # 统计
        high = len([r for r in results if r.get("theme_score", 0) >= 70])
        medium = len([r for r in results if 50 <= r.get("theme_score", 0) < 70])

        print(f"{'=' * 60}")
        print(
            f"统计: 高热度 {high}只 | 中等热度 {medium}只 | 低热度 {len(results) - high - medium}只"
        )
        print(f"{'=' * 60}\n")

        print("⚠️ 风险提示:")
        print("  - 题材炒作风险高，快进快出")
        print("  - 不看DDX，看资金和情绪")
        print("  - 设好止损，亏损5%必须走")
        print("  - 不恋战，有赚就跑")


def main():
    parser = argparse.ArgumentParser(description="题材炒作策略")
    parser.add_argument("--stock", type=str, help="分析单只股票")
    parser.add_argument("--screen", action="store_true", help="筛选股票")
    parser.add_argument("--hot-themes", action="store_true", help="获取热点题材")

    args = parser.parse_args()

    strategy = ThemeHypeStrategy()

    if args.stock:
        result = strategy.analyze_stock(args.stock)
        strategy.print_report([result], f"题材炒作分析 - {args.stock}")

    elif args.screen:
        results = strategy.screen_stocks()
        if results:
            strategy.print_report(results, "题材炒作筛选结果")

    elif args.hot_themes:
        results = strategy.get_hot_themes()
        print("\n🔥 热点题材:")
        for i, r in enumerate(results, 1):
            print(
                f"{i}. {r['name']}: +{r['change_pct']:.2f}% (领涨: {r['lead_stock']})"
            )

    else:
        # 默认筛选
        results = strategy.screen_stocks()
        if results:
            strategy.print_report(results, "题材炒作筛选结果")


if __name__ == "__main__":
    main()
