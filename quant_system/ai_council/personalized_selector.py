#!/usr/bin/env python3
"""
个性化选股引擎
基于用户交易历史和偏好进行选股
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from selector_integration import StockDataFetcher


class PersonalizedSelector:
    """个性化选股引擎"""

    def __init__(self, profile_path: str = None):
        self.profile = self._load_profile(profile_path)
        self.fetcher = StockDataFetcher()

    def _load_profile(self, profile_path: str = None) -> Dict:
        """加载用户画像"""
        if profile_path is None:
            profile_path = Path(__file__).parent.parent / "config" / "user_profile.json"

        if Path(profile_path).exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "lucky_stocks": {"stocks": []},
            "avoid_stocks": {"stocks": []},
            "preferred_sectors": {"sectors": []},
            "trading_rules": {
                "entry": {
                    "capital_flow_min": 3,
                    "kdj_max": 70,
                    "rsi_max": 65,
                    "change_5d_max": 10,
                }
            },
        }

    def calculate_personal_score(self, stock_data: Dict) -> Dict:
        """计算个性化得分"""
        score = 0
        reasons = []
        warnings = []

        # 1. 财神股加分
        lucky_stocks = self.profile.get("lucky_stocks", {}).get("stocks", [])
        stock_code = stock_data.get("code", "")
        for lucky in lucky_stocks:
            if lucky["code"] == stock_code:
                score += 20
                reasons.append(
                    f"财神股：{lucky['name']}，历史盈利{lucky['total_profit']:.0f}元"
                )
                break

        # 2. 避雷股减分
        avoid_stocks = self.profile.get("avoid_stocks", {}).get("stocks", [])
        for avoid in avoid_stocks:
            if avoid["code"] == stock_code:
                score -= 30
                warnings.append(
                    f"历史亏损股：{avoid['name']}，亏损{avoid['total_loss']:.0f}元"
                )
                break

        # 3. 板块偏好
        preferred_sectors = self.profile.get("preferred_sectors", {}).get("sectors", [])
        stock_sectors = stock_data.get("sectors", [])
        for sector in preferred_sectors:
            if sector["name"] in stock_sectors:
                score += int(sector["weight"] * 10)
                reasons.append(f"优势板块：{sector['name']}")

        # 4. 资金流向
        capital_flow = stock_data.get("capital_flow", 0)
        rules = self.profile.get("trading_rules", {}).get("entry", {})
        capital_min = rules.get("capital_flow_min", 3)

        if capital_flow > 10:
            score += 25
            reasons.append(f"主力大额流入：{capital_flow:.1f}亿")
        elif capital_flow > capital_min:
            score += 15
            reasons.append(f"主力流入：{capital_flow:.1f}亿")
        elif capital_flow < -5:
            score -= 20
            warnings.append(f"主力流出：{capital_flow:.1f}亿")

        # 5. 技术指标
        kdj = stock_data.get("kdj", 50)
        rsi = stock_data.get("rsi", 50)
        kdj_max = rules.get("kdj_max", 70)
        rsi_max = rules.get("rsi_max", 65)

        if kdj < 20:
            score += 15
            reasons.append(f"KDJ超卖：{kdj:.1f}")
        elif kdj > kdj_max:
            score -= 15
            warnings.append(f"KDJ超买：{kdj:.1f}")

        if rsi < 30:
            score += 10
            reasons.append(f"RSI超卖：{rsi:.1f}")
        elif rsi > rsi_max:
            score -= 10
            warnings.append(f"RSI超买：{rsi:.1f}")

        # 6. 近期涨幅
        change_5d = stock_data.get("change_5d", 0)
        change_max = rules.get("change_5d_max", 10)

        if change_5d > change_max:
            score -= 10
            warnings.append(f"近5日涨幅过大：{change_5d:.1f}%")
        elif change_5d < -10:
            score += 5
            reasons.append(f"近5日跌幅较大：{change_5d:.1f}%")

        return {
            "score": score,
            "reasons": reasons,
            "warnings": warnings,
            "recommendation": self._get_recommendation(score),
        }

    def _get_recommendation(self, score: int) -> str:
        """根据得分给出建议"""
        if score >= 40:
            return "强烈推荐"
        elif score >= 20:
            return "推荐"
        elif score >= 0:
            return "观望"
        elif score >= -20:
            return "谨慎"
        else:
            return "不建议"

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        # 获取数据
        stock_data = self.fetcher.fetch_stock_data(stock_code)

        # 计算个性化得分
        personal = self.calculate_personal_score(stock_data)

        return {
            "code": stock_code,
            "name": stock_data.get("name", stock_code),
            "price": stock_data.get("price", 0),
            "change_pct": stock_data.get("change_pct", 0),
            "capital_flow": stock_data.get("capital_flow", 0),
            "kdj": stock_data.get("kdj", 50),
            "rsi": stock_data.get("rsi", 50),
            "personal_score": personal["score"],
            "recommendation": personal["recommendation"],
            "reasons": personal["reasons"],
            "warnings": personal["warnings"],
            "data_source": stock_data.get("data_source", "unknown"),
        }

    def scan_opportunities(self, stock_list: List[str] = None) -> List[Dict]:
        """扫描机会"""
        if stock_list is None:
            # 默认扫描财神股 + 自选股
            lucky_codes = [
                s["code"]
                for s in self.profile.get("lucky_stocks", {}).get("stocks", [])
            ]
            holding_codes = [
                h["code"] for h in self.profile.get("current_holdings", [])
            ]
            stock_list = list(set(lucky_codes + holding_codes))

        results = []
        for code in stock_list:
            try:
                result = self.analyze_stock(code)
                results.append(result)
                print(
                    f"  {result['name']}({code}): 得分{result['personal_score']} - {result['recommendation']}"
                )
            except Exception as e:
                print(f"  {code}: 分析失败 - {e}")

        # 按得分排序
        results.sort(key=lambda x: x["personal_score"], reverse=True)
        return results

    def get_lucky_stock_alerts(self) -> List[Dict]:
        """财神股异动提醒"""
        lucky_stocks = self.profile.get("lucky_stocks", {}).get("stocks", [])
        alerts = []

        for stock in lucky_stocks:
            try:
                data = self.fetcher.fetch_stock_data(stock["code"])
                capital_flow = data.get("capital_flow", 0)

                # 主力流入超过3亿，提醒
                if capital_flow > 3:
                    alerts.append(
                        {
                            "code": stock["code"],
                            "name": stock["name"],
                            "capital_flow": capital_flow,
                            "price": data.get("price", 0),
                            "change_pct": data.get("change_pct", 0),
                            "message": f"财神股{stock['name']}主力流入{capital_flow:.1f}亿！",
                        }
                    )
            except:
                pass

        return alerts

    def generate_report(self, results: List[Dict]) -> str:
        """生成选股报告"""
        lines = [
            "# 个性化选股报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 推荐股票",
            "",
        ]

        for r in results:
            if r["personal_score"] >= 20:
                lines.append(f"### {r['name']}({r['code']})")
                lines.append(f"")
                lines.append(f"| 项目 | 数值 |")
                lines.append(f"|------|------|")
                lines.append(f"| 得分 | **{r['personal_score']}** |")
                lines.append(f"| 建议 | **{r['recommendation']}** |")
                lines.append(f"| 价格 | {r['price']:.2f}元 |")
                lines.append(f"| 主力资金 | {r['capital_flow']:.1f}亿 |")
                lines.append(f"| KDJ/RSI | {r['kdj']:.1f} / {r['rsi']:.1f} |")
                lines.append(f"")

                if r["reasons"]:
                    lines.append(f"**优势**:")
                    for reason in r["reasons"]:
                        lines.append(f"- {reason}")

                if r["warnings"]:
                    lines.append(f"")
                    lines.append(f"**风险**:")
                    for warning in r["warnings"]:
                        lines.append(f"- {warning}")

                lines.append(f"")
                lines.append(f"---")
                lines.append(f"")

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="个性化选股引擎")
    parser.add_argument("--stock", type=str, help="分析单只股票")
    parser.add_argument("--scan", action="store_true", help="扫描财神股和持仓股")
    parser.add_argument("--alert", action="store_true", help="财神股异动提醒")
    parser.add_argument("--top", type=int, default=5, help="显示前N只")

    args = parser.parse_args()

    selector = PersonalizedSelector()

    if args.stock:
        result = selector.analyze_stock(args.stock)
        print(f"\n{'=' * 50}")
        print(f"股票: {result['name']}({result['code']})")
        print(f"得分: {result['personal_score']}")
        print(f"建议: {result['recommendation']}")
        print(f"价格: {result['price']:.2f}元")
        print(f"主力资金: {result['capital_flow']:.1f}亿")
        print(f"KDJ/RSI: {result['kdj']:.1f} / {result['rsi']:.1f}")
        if result["reasons"]:
            print(f"\n优势:")
            for r in result["reasons"]:
                print(f"  + {r}")
        if result["warnings"]:
            print(f"\n风险:")
            for w in result["warnings"]:
                print(f"  - {w}")
        print(f"{'=' * 50}")

    elif args.scan:
        print(f"\n扫描财神股和持仓股...")
        results = selector.scan_opportunities()

        print(f"\n{'=' * 50}")
        print(f"推荐股票 (得分>=20):")
        print(f"{'=' * 50}")

        for r in results[: args.top]:
            if r["personal_score"] >= 20:
                print(
                    f"  {r['name']}({r['code']}): 得分{r['personal_score']} - {r['recommendation']}"
                )

    elif args.alert:
        print(f"\n财神股异动监控...")
        alerts = selector.get_lucky_stock_alerts()

        if alerts:
            print(f"\n发现 {len(alerts)} 个异动:")
            for alert in alerts:
                print(f"  {alert['message']}")
                print(
                    f"    价格: {alert['price']:.2f}元, 涨跌: {alert['change_pct']:.2f}%"
                )
        else:
            print("暂无异动")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
