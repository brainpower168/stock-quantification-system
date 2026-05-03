#!/usr/bin/env python3
"""
每日选股分析 + TradingAgents深度决策
整合多空辩论机制，提供更精准的投资建议
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
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from dingtalk_push import DingTalkPusher


class EnhancedStockSelector:
    """增强版选股器 - 整合TradingAgents决策"""

    def __init__(self):
        self.wencai_api_key = os.environ.get("IWENCAI_API_KEY", "")
        self.mx_api_key = os.environ.get("MX_APIKEY", "")
        self.pusher = DingTalkPusher()
        self.trading_agents = None

    def initialize_trading_agents(self):
        """初始化TradingAgents系统"""
        try:
            from trading_agents_live import TradingAgentsLive

            self.trading_agents = TradingAgentsLive()
            if self.trading_agents.initialize():
                print("✓ TradingAgents系统初始化成功")
                return True
            else:
                print("✗ TradingAgents系统初始化失败")
                return False
        except Exception as e:
            print(f"✗ TradingAgents加载失败: {e}")
            return False

    def get_top_main_inflow(self, top_n: int = 20) -> List[Dict]:
        """获取主力资金净流入TOP N"""
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 正在获取主力资金流入TOP{top_n}..."
        )

        # 优先使用妙想API
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

            return []

        except Exception as e:
            print(f"问财API异常: {e}")
            return []

    def _fetch_from_miaoxiang(self, top_n: int) -> List[Dict]:
        """从妙想API获取数据"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"

            params = {
                "pn": 1,
                "pz": top_n * 3,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f62",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f2,f3,f8,f10,f12,f14,f62,f66,f69,f72,f75,f78,f81,f84,f87,f124,f1,f13",
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("diff"):
                    stocks = []
                    for item in data["data"]["diff"]:
                        change_pct = item.get("f3", 0)
                        if change_pct is None or change_pct < 0 or change_pct > 5:
                            continue

                        main_inflow = item.get("f62", 0)
                        if main_inflow is None or main_inflow <= 0:
                            continue

                        stocks.append(
                            {
                                "code": item.get("f12", ""),
                                "name": item.get("f14", ""),
                                "price": item.get("f2", 0) or 0,
                                "change_pct": change_pct,
                                "main_inflow": main_inflow,
                                "ddx": item.get("f69", 0),
                                "ddx_10": item.get("f75", 0),
                                "turnover_rate": item.get("f8", 0),
                                "volume_ratio": item.get("f10", 0),
                            }
                        )

                    print(f"妙想API返回 {len(stocks)} 只股票")
                    return stocks[:top_n]

            return []

        except Exception as e:
            print(f"妙想API异常: {e}")
            return []

    def filter_by_rules(self, stocks: List[Dict]) -> List[Dict]:
        """按交易规则筛选"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 按交易规则筛选...")

        filtered = []
        for stock in stocks:
            # 规则1: 10日DDX > 2
            ddx_10 = stock.get("ddx_10", 0)
            if ddx_10 is None or ddx_10 <= 2:
                stock["reject_reason"] = f"10日DDX={ddx_10:.2f} ≤ 2"
                continue

            # 规则2: 涨幅 < 3%
            change_pct = stock.get("change_pct", 0)
            if change_pct >= 3:
                stock["reject_reason"] = f"涨幅={change_pct:.2f}% ≥ 3%"
                continue

            # 规则3: 主力资金流入 > 5000万
            main_inflow = stock.get("main_inflow", 0)
            if main_inflow < 50000000:
                stock["reject_reason"] = f"主力流入={main_inflow / 1e8:.2f}亿 < 5000万"
                continue

            stock["score"] = self._calculate_score(stock)
            filtered.append(stock)

        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        print(f"筛选后剩余 {len(filtered)} 只股票")
        return filtered

    def _calculate_score(self, stock: Dict) -> float:
        """计算评分"""
        score = 0

        # 主力资金流入 (权重40%)
        main_inflow = stock.get("main_inflow", 0)
        score += min(main_inflow / 1e8, 10) * 4

        # 10日DDX (权重30%)
        ddx_10 = stock.get("ddx_10", 0)
        score += min(ddx_10 * 10, 30)

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

    def analyze_with_trading_agents(
        self, stocks: List[Dict], top_n: int = 3
    ) -> List[Dict]:
        """使用TradingAgents深度分析"""
        if not self.trading_agents:
            print("TradingAgents未初始化，跳过深度分析")
            return stocks

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] TradingAgents深度分析...")

        analyzed = []
        for i, stock in enumerate(stocks[:top_n]):
            print(
                f"\n分析 {i + 1}/{min(len(stocks), top_n)}: {stock['code']} {stock['name']}"
            )

            try:
                # 准备数据
                stock_data = {
                    "price": stock.get("price", 0),
                    "change_pct": stock.get("change_pct", 0),
                    "volume": stock.get("volume", 0),
                    "turnover_rate": stock.get("turnover_rate", 0),
                    "ddx": stock.get("ddx", 0),
                    "ddx_5d": stock.get("ddx_10", 0) / 2,  # 估算
                    "ddx_10d": stock.get("ddx_10", 0),
                    "main_inflow": stock.get("main_inflow", 0),
                    "pe": stock.get("pe", 0),
                    "pb": stock.get("pb", 0),
                    "roe": stock.get("roe", 0),
                }

                # 运行TradingAgents分析
                result = self.trading_agents.analyze_stock(stock["code"])

                # 提取决策
                decision = result["result"]["final_decision"]

                # 添加到股票信息
                stock["trading_agents_decision"] = {
                    "rating": decision.rating.value,
                    "executive_summary": decision.executive_summary,
                    "investment_thesis": decision.investment_thesis[:200]
                    if decision.investment_thesis
                    else "",
                    "price_target": decision.price_target,
                    "time_horizon": decision.time_horizon,
                }

                print(f"  评级: {decision.rating.value}")
                print(f"  摘要: {decision.executive_summary[:50]}...")

                analyzed.append(stock)

            except Exception as e:
                print(f"  分析失败: {e}")
                stock["trading_agents_decision"] = {
                    "rating": "HOLD",
                    "executive_summary": f"分析失败: {str(e)}",
                }
                analyzed.append(stock)

        return analyzed

    def generate_report(self, stocks: List[Dict]) -> str:
        """生成分析报告"""
        report = f"""# 每日选股报告（TradingAgents增强版）

**时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 推荐股票

"""

        if not stocks:
            report += "今日无符合条件的股票\n"
            return report

        for i, stock in enumerate(stocks, 1):
            report += f"""### {i}. {stock["name"]} ({stock["code"]})

| 指标 | 数值 |
|------|------|
| 价格 | {stock["price"]:.2f}元 |
| 涨幅 | {stock["change_pct"]:.2f}% |
| 主力流入 | {stock["main_inflow"] / 1e8:.2f}亿 |
| 10日DDX | {stock["ddx_10"]:.2f} |
| 换手率 | {stock["turnover_rate"]:.2f}% |
| 评分 | {stock["score"]:.1f} |

"""

            # TradingAgents决策
            if "trading_agents_decision" in stock:
                ta = stock["trading_agents_decision"]
                report += f"""**TradingAgents决策**:
- 评级: **{ta["rating"]}**
- 摘要: {ta["executive_summary"][:100]}
- 逻辑: {ta.get("investment_thesis", "N/A")[:100]}
"""
                if ta.get("price_target"):
                    report += f"- 目标价: {ta['price_target']}元\n"
                if ta.get("time_horizon"):
                    report += f"- 持有周期: {ta['time_horizon']}\n"

            report += "\n---\n\n"

        # 添加交易纪律提醒
        report += """## 交易纪律提醒

**买入条件**:
- 涨幅 < 3%
- 主力资金流入 > 5000万
- 10日DDX > 2（稳定性要求）

**止损纪律**:
- 单股最大亏损 5% 必须止损
- 不等回本，不抱侥幸心理

**止盈纪律**:
- 盈利 10% 卖一半
- 盈利 20% 再卖一半
- 主力流出时反弹就卖

**仓位控制**:
- 单股不超过 20%
- 总仓位不超过 80%

---

*本报告由 TradingAgents 多智能体决策系统生成*
"""

        return report

    def run_daily_selection(self, top_n: int = 20, analyze_top: int = 3) -> Dict:
        """运行每日选股"""
        print("\n" + "=" * 60)
        print("每日选股分析（TradingAgents增强版）")
        print("=" * 60 + "\n")

        # Step 1: 获取主力资金流入TOP N
        stocks = self.get_top_main_inflow(top_n)
        if not stocks:
            return {"success": False, "message": "获取股票数据失败"}

        # Step 2: 按交易规则筛选
        filtered = self.filter_by_rules(stocks)

        # Step 3: TradingAgents深度分析
        if self.trading_agents and filtered:
            filtered = self.analyze_with_trading_agents(filtered, analyze_top)

        # Step 4: 生成报告
        report = self.generate_report(filtered)

        # Step 5: 保存报告
        report_dir = Path(__file__).parent.parent / "data"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = (
            report_dir / f"daily_selection_{datetime.now().strftime('%Y%m%d')}.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n报告已保存: {report_path}")

        return {
            "success": True,
            "stocks": filtered,
            "report": report,
            "report_path": str(report_path),
        }


def main():
    """主函数"""
    selector = EnhancedStockSelector()

    # 初始化TradingAgents（可选）
    use_trading_agents = os.environ.get("USE_TRADING_AGENTS", "true").lower() == "true"
    if use_trading_agents:
        selector.initialize_trading_agents()

    # 运行选股
    result = selector.run_daily_selection(top_n=20, analyze_top=3)

    if result["success"]:
        print("\n" + "=" * 60)
        print("选股完成")
        print("=" * 60)
        print(f"筛选出 {len(result['stocks'])} 只股票")
        print(f"报告路径: {result['report_path']}")

        # 打印摘要
        print("\n推荐股票:")
        for i, stock in enumerate(result["stocks"][:5], 1):
            decision = stock.get("trading_agents_decision", {})
            rating = decision.get("rating", "N/A")
            print(f"  {i}. {stock['code']} {stock['name']} - 评级: {rating}")
    else:
        print(f"\n选股失败: {result['message']}")


if __name__ == "__main__":
    main()
