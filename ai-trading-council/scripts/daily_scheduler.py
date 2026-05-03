#!/usr/bin/env python3
"""
定时任务：每日选股 + TradingAgents决策 + 钉钉推送
支持手动触发和定时调度
"""

import os
import sys
import json
import time
import schedule
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))
sys.path.insert(0, str(Path(__file__).parent))

from test_trading_agents import MockLLM
from trading_agents_system import TradingAgentsSystem


class DailyStockScheduler:
    """每日选股调度器"""

    def __init__(self):
        self.llm = MockLLM()  # 使用MockLLM，真实环境替换为真实LLM
        self.system = TradingAgentsSystem(self.llm)
        self.output_dir = Path(__file__).parent.parent / "data"
        self.output_dir.mkdir(exist_ok=True)

    def run_daily_selection(self) -> Dict:
        """运行每日选股"""
        print(f"\n{'=' * 60}")
        print(f"每日选股任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        start_time = time.time()

        try:
            # Step 1: 获取股票数据（模拟数据，真实环境从API获取）
            stocks = self._get_stock_data()
            print(f"✓ 获取 {len(stocks)} 只候选股票")

            # Step 2: 筛选
            filtered = self._filter_stocks(stocks)
            print(f"✓ 筛选后剩余 {len(filtered)} 只股票")

            # Step 3: TradingAgents深度分析
            analyzed = self._analyze_with_trading_agents(filtered[:3])
            print(f"✓ TradingAgents分析完成")

            # Step 4: 生成报告
            report = self._generate_report(analyzed)
            print(f"✓ 报告生成完成")

            # Step 5: 推送（可选）
            # self._push_to_dingtalk(report)

            elapsed = time.time() - start_time
            print(f"\n✅ 任务完成，耗时 {elapsed:.1f} 秒")

            return {
                "success": True,
                "stocks": analyzed,
                "report": report,
                "elapsed": elapsed,
            }

        except Exception as e:
            print(f"\n❌ 任务失败: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _get_stock_data(self) -> List[Dict]:
        """获取股票数据（模拟）"""
        # 真实环境：从妙想/问财API获取
        return [
            {
                "code": "600519",
                "name": "贵州茅台",
                "price": 1850,
                "change_pct": 2.5,
                "main_inflow": 5e8,
                "ddx": 2.5,
                "ddx_10": 4.1,
                "turnover_rate": 3.2,
                "pe": 35,
                "pb": 12,
                "roe": 18,
            },
            {
                "code": "000001",
                "name": "平安银行",
                "price": 15.5,
                "change_pct": 1.8,
                "main_inflow": 3e8,
                "ddx": 1.8,
                "ddx_10": 3.2,
                "turnover_rate": 4.5,
                "pe": 6,
                "pb": 0.8,
                "roe": 12,
            },
            {
                "code": "300750",
                "name": "宁德时代",
                "price": 220,
                "change_pct": 3.2,
                "main_inflow": 8e8,
                "ddx": 3.5,
                "ddx_10": 5.8,
                "turnover_rate": 5.1,
                "pe": 45,
                "pb": 8,
                "roe": 15,
            },
        ]

    def _filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """筛选股票"""
        filtered = []
        for stock in stocks:
            # 筛选条件
            main_inflow = stock.get("main_inflow", 0)
            ddx_10 = stock.get("ddx_10", 0)
            change_pct = stock.get("change_pct", 0)

            if main_inflow < 5e7:  # 主力流入 > 5000万
                continue
            if ddx_10 < 0:  # 10日DDX > 0
                continue
            if change_pct > 5:  # 涨幅 < 5%
                continue

            filtered.append(stock)

        # 按主力流入排序
        filtered.sort(key=lambda x: x.get("main_inflow", 0), reverse=True)
        return filtered

    def _analyze_with_trading_agents(self, stocks: List[Dict]) -> List[Dict]:
        """TradingAgents深度分析"""
        analyzed = []

        for i, stock in enumerate(stocks):
            print(f"\n  分析 {i + 1}/{len(stocks)}: {stock['code']} {stock['name']}")

            # 准备分析师报告
            analyst_reports = {
                "market_report": f"""市场分析报告

当前价格: {stock["price"]}元
涨跌幅: {stock["change_pct"]}%
成交量: 15000手
换手率: {stock["turnover_rate"]}%

技术指标:
- 5日均线: {stock["price"] * 0.99:.0f}元
- 10日均线: {stock["price"] * 0.98:.0f}元
- 20日均线: {stock["price"] * 0.96:.0f}元
- RSI: 65
- MACD: 金叉""",
                "fundamentals_report": f"""基本面分析报告

财务指标:
- 市盈率PE: {stock["pe"]}
- 市净率PB: {stock["pb"]}
- ROE: {stock["roe"]}%
- 净利润增长率: 15%

资金流向:
- 主力净流入: {stock["main_inflow"] / 1e6:.0f}万元
- DDX: {stock["ddx"]}
- 10日DDX: {stock["ddx_10"]}""",
                "sentiment_report": """情绪分析报告

市场情绪:
- 涨停基因: 45
- 机构评级: 买入
- 社交媒体情绪: 偏正面""",
                "news_report": """新闻分析报告

1. 公司发布新产品，市场反响良好
2. 机构上调评级至买入""",
            }

            # 运行分析
            result = self.system.run_full_analysis(stock["code"], analyst_reports)

            # 提取决策
            decision = result["final_decision"]
            stock["trading_agents"] = {
                "rating": decision.rating.value,
                "executive_summary": decision.executive_summary,
                "investment_thesis": decision.investment_thesis[:100]
                if decision.investment_thesis
                else "",
                "price_target": decision.price_target,
                "time_horizon": decision.time_horizon,
            }

            print(f"    评级: {decision.rating.value}")
            analyzed.append(stock)

        return analyzed

    def _generate_report(self, stocks: List[Dict]) -> str:
        """生成报告"""
        report_lines = [
            f"# 每日选股报告\n",
            f"\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"\n---\n",
        ]

        for i, stock in enumerate(stocks, 1):
            ta = stock.get("trading_agents", {})
            rating = ta.get("rating", "N/A")

            # 评级emoji
            rating_emoji = {
                "Buy": "🟢 强烈买入",
                "Overweight": "🔵 增持",
                "Hold": "🟡 持有",
                "Underweight": "🟠 减持",
                "Sell": "🔴 卖出",
            }.get(rating, rating)

            report_lines.extend(
                [
                    f"\n## {i}. {stock['name']} ({stock['code']})\n",
                    f"\n**{rating_emoji}**\n",
                    f"\n**基本信息**\n",
                    f"- 价格: {stock['price']}元\n",
                    f"- 涨幅: {stock['change_pct']}%\n",
                    f"- 主力流入: {stock['main_inflow'] / 1e8:.2f}亿\n",
                    f"- 10日DDX: {stock['ddx_10']}\n",
                    f"\n**TradingAgents决策**\n",
                    f"- 摘要: {ta.get('executive_summary', 'N/A')}\n",
                    f"- 逻辑: {ta.get('investment_thesis', 'N/A')[:80]}...\n",
                    f"- 目标价: {ta.get('price_target', 'N/A')}\n",
                    f"- 持有周期: {ta.get('time_horizon', 'N/A')}\n",
                ]
            )

        report = "".join(report_lines)

        # 保存报告
        report_path = (
            self.output_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n报告已保存: {report_path}")
        return report

    def _push_to_dingtalk(self, report: str):
        """推送到钉钉"""
        try:
            from dingtalk_push import DingTalkPusher

            pusher = DingTalkPusher()
            pusher.push_message("每日选股报告", report)
            print("✓ 钉钉推送成功")
        except Exception as e:
            print(f"✗ 钉钉推送失败: {e}")


def run_scheduler():
    """运行定时调度"""
    scheduler = DailyStockScheduler()

    # 配置定时任务
    schedule.every().day.at("09:30").do(scheduler.run_daily_selection)
    schedule.every().day.at("15:00").do(scheduler.run_daily_selection)

    print("定时任务已启动:")
    print("  - 每日 09:30 运行")
    print("  - 每日 15:00 运行")
    print("\n按 Ctrl+C 停止\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n定时任务已停止")


def run_once():
    """运行一次"""
    scheduler = DailyStockScheduler()
    result = scheduler.run_daily_selection()

    if result["success"]:
        print("\n" + "=" * 60)
        print(result["report"])
        print("=" * 60)

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="每日选股定时任务")
    parser.add_argument("--schedule", action="store_true", help="启动定时调度")
    parser.add_argument("--once", action="store_true", help="运行一次")
    args = parser.parse_args()

    if args.schedule:
        run_scheduler()
    elif args.once:
        run_once()
    else:
        # 默认运行一次
        run_once()
