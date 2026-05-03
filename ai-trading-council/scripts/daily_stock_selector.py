#!/usr/bin/env python3
"""
每日选股分析
使用问财API获取主力资金流入数据，筛选符合条件的股票
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from dingtalk_push import DingTalkPusher


class DailyStockSelector:
    """每日选股器"""

    def __init__(self):
        self.wencai_api_key = os.environ.get("IWENCAI_API_KEY", "")
        self.mx_api_key = os.environ.get("MX_APIKEY", "")
        self.pusher = DingTalkPusher()

    def get_top_main_inflow(self, top_n: int = 20) -> List[Dict]:
        """
        获取主力资金净流入TOP N

        筛选条件：
        - 涨幅 0-5%
        - 主力资金流入 > 0
        - 非ST股
        - 非新股
        """
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 正在获取主力资金流入TOP{top_n}..."
        )

        # 优先使用妙想API（东方财富）
        if self.mx_api_key:
            result = self._fetch_from_miaoxiang(top_n)
            if result:
                return result

        # 备用问财API
        if self.wencai_api_key:
            result = self._fetch_from_wencai(top_n)
            if result:
                return result

        print("未配置API Key或API不可用")
        return []

    def _fetch_from_wencai(self, top_n: int) -> List[Dict]:
        """从问财API获取数据"""
        try:
            url = "https://api.wencai.com/v1/stock/screen"
            headers = {
                "Authorization": f"Bearer {self.wencai_api_key}",
                "Content-Type": "application/json",
            }

            # 问财查询语句
            query = f"主力资金净流入>0;涨幅0到5%;非ST;非新股;按主力资金净流入降序;前{top_n}名"

            data = {
                "query": query,
                "fields": [
                    "股票代码",
                    "股票简称",
                    "最新价",
                    "涨跌幅",
                    "主力资金净流入",
                    "DDX",
                    "10日DDX",
                    "换手率",
                    "量比",
                ],
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    stocks = []
                    for item in result.get("data", []):
                        stocks.append(
                            {
                                "code": item.get("股票代码", ""),
                                "name": item.get("股票简称", ""),
                                "price": item.get("最新价", 0),
                                "change_pct": item.get("涨跌幅", 0),
                                "main_inflow": item.get("主力资金净流入", 0),
                                "ddx": item.get("DDX", 0),
                                "ddx_10": item.get("10日DDX", 0),
                                "turnover_rate": item.get("换手率", 0),
                                "volume_ratio": item.get("量比", 0),
                            }
                        )
                    print(f"问财API返回 {len(stocks)} 只股票")
                    return stocks

            print(f"问财API返回错误: {response.status_code}")
            return []

        except Exception as e:
            print(f"问财API异常: {e}")
            return []

    def _fetch_from_miaoxiang(self, top_n: int) -> List[Dict]:
        """从妙想API获取数据"""
        try:
            # 使用东方财富API
            url = "https://push2.eastmoney.com/api/qt/clist/get"

            params = {
                "pn": 1,
                "pz": top_n * 3,  # 获取更多，后面筛选
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f62",  # 按主力资金排序
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # A股
                "fields": "f2,f3,f8,f10,f12,f14,f62,f66,f69,f72,f75,f78,f81,f84,f87,f124,f1,f13",
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("diff"):
                    stocks = []
                    for item in data["data"]["diff"]:
                        change_pct = item.get("f3", 0)
                        # 筛选涨幅0-5%
                        # f3已经是百分比数值（如8.25表示8.25%）
                        if change_pct is None or change_pct < 0 or change_pct > 5:
                            continue

                        main_inflow = item.get("f62", 0)
                        # 筛选主力流入>0
                        if main_inflow is None or main_inflow <= 0:
                            continue

                        stocks.append(
                            {
                                "code": item.get("f12", ""),
                                "name": item.get("f14", ""),
                                "price": item.get("f2", 0) or 0,
                                "change_pct": change_pct
                                if change_pct
                                else 0,  # 已经是百分比
                                "main_inflow": main_inflow,
                                "ddx": item.get("f69", 0),  # DDX
                                "ddx_10": item.get("f75", 0),  # 10日DDX
                                "turnover_rate": item.get("f8", 0),  # 换手率
                                "volume_ratio": item.get("f10", 0),  # 量比
                            }
                        )

                    print(f"妙想API返回 {len(stocks)} 只股票")
                    return stocks[:top_n]

            print(f"妙想API返回错误: {response.status_code}")
            return []

        except Exception as e:
            print(f"妙想API异常: {e}")
            return []

    def filter_by_rules(self, stocks: List[Dict]) -> List[Dict]:
        """
        按交易规则筛选

        规则（2026-04-28 更新，吸取中兴通讯教训）：
        1. 10日DDX > 2（必须，稳定性要求）
        2. 涨幅 < 3%（不追高）
        3. 主力资金流入 > 5000万

        注意：单日流入不代表持续，资金趋势稳定性比单日流入量更重要！
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 按交易规则筛选...")

        filtered = []
        for stock in stocks:
            # 规则1: 10日DDX > 2（吸取中兴通讯教训，提高门槛）
            ddx_10 = stock.get("ddx_10", 0)
            if ddx_10 is None or ddx_10 <= 2:
                stock["reject_reason"] = f"10日DDX={ddx_10:.2f} ≤ 2（稳定性不足）"
                continue

            # 规则2: 涨幅 < 3%
            change_pct = stock.get("change_pct", 0)
            if change_pct >= 3:
                stock["reject_reason"] = f"涨幅={change_pct:.2f}% ≥ 3%"
                continue

            # 规则3: 主力资金流入 > 5000万
            main_inflow = stock.get("main_inflow", 0)
            if main_inflow < 50000000:  # 5000万
                stock["reject_reason"] = f"主力流入={main_inflow / 1e8:.2f}亿 < 5000万"
                continue

            # 通过筛选
            stock["score"] = self._calculate_score(stock)
            filtered.append(stock)

        # 按评分排序
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)

        print(f"筛选后剩余 {len(filtered)} 只股票")
        return filtered

    def _calculate_score(self, stock: Dict) -> float:
        """计算评分"""
        score = 0

        # 主力资金流入 (权重40%)
        main_inflow = stock.get("main_inflow", 0)
        score += min(main_inflow / 1e8, 10) * 4  # 最高40分

        # 10日DDX (权重30%)
        ddx_10 = stock.get("ddx_10", 0)
        score += min(ddx_10 * 10, 30)  # 最高30分

        # 涨幅适中 (权重20%)
        change_pct = stock.get("change_pct", 0)
        if 0 < change_pct < 2:
            score += 20
        elif 2 <= change_pct < 3:
            score += 10

        # 换手率 (权重10%)
        turnover = stock.get("turnover_rate", 0)
        if 3 < turnover < 10:
            score += 10
        elif 1 < turnover <= 3 or 10 <= turnover < 15:
            score += 5

        return score

    def generate_report(self, stocks: List[Dict], top_n: int = 5) -> str:
        """生成分析报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        report = f"""## 📊 每日选股分析报告
**时间**: {now}

---

### ✅ 筛选条件（吸取中兴通讯教训）
- 10日DDX > 2（资金趋势稳定）
- 涨幅 < 3%（不追高）
- 主力资金流入 > 5000万

**重要**：单日流入不代表持续，资金趋势稳定性比单日流入量更重要！

---

### 🎯 推荐股票 (TOP {min(top_n, len(stocks))})

"""

        if not stocks:
            report += "⚠️ 今日无符合条件的股票\n"
        else:
            for i, stock in enumerate(stocks[:top_n], 1):
                code = stock.get("code", "")
                name = stock.get("name", "")
                price = stock.get("price", 0)
                change_pct = stock.get("change_pct", 0)
                main_inflow = stock.get("main_inflow", 0) / 1e8
                ddx_10 = stock.get("ddx_10", 0)
                score = stock.get("score", 0)

                report += f"""**{i}. {name}({code})** - 评分: {score:.0f}分

| 指标 | 数值 |
|------|------|
| 最新价 | {price:.2f}元 |
| 涨跌幅 | {change_pct:+.2f}% |
| 主力流入 | {main_inflow:+.2f}亿 |
| 10日DDX | {ddx_10:.2f} |

"""

        report += """---

### ⚠️ 风险提示
- 以上仅供参考，不构成投资建议
- 请结合自身风险承受能力决策
- 严格执行止损纪律

---

**DuMate AI Trading Council**
"""

        return report

    def run(self, top_n: int = 20, push: bool = False) -> List[Dict]:
        """运行选股分析"""
        print(f"\n{'=' * 50}")
        print(f"每日选股分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 50}\n")

        # 1. 获取TOP N主力流入
        stocks = self.get_top_main_inflow(top_n)

        if not stocks:
            print("未获取到数据")
            return []

        # 2. 按规则筛选
        filtered = self.filter_by_rules(stocks)

        # 3. 生成报告
        report = self.generate_report(filtered, top_n=5)

        # 保存报告
        report_path = (
            Path(__file__).parent.parent
            / "data"
            / f"daily_report_{datetime.now().strftime('%Y%m%d')}.md"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")

        # 4. 推送到钉钉
        if push:
            print("\n推送到钉钉...")
            success = self.pusher.send_markdown("每日选股分析", report)
            if success:
                print("✅ 推送成功")
            else:
                print("❌ 推送失败")

        return filtered


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="每日选股分析")
    parser.add_argument("--top", type=int, default=20, help="获取TOP N股票")
    parser.add_argument(
        "--push", action="store_true", help="推送到钉钉（仅定时任务使用）"
    )

    args = parser.parse_args()

    selector = DailyStockSelector()
    stocks = selector.run(top_n=args.top, push=args.push)

    print(f"\n筛选结果: {len(stocks)} 只股票")
    for stock in stocks[:5]:
        print(
            f"  - {stock.get('name')}({stock.get('code')}): 评分{stock.get('score', 0):.0f}"
        )


if __name__ == "__main__":
    main()
