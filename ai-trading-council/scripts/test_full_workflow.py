#!/usr/bin/env python3
"""
完整流程测试：选股 + TradingAgents决策
"""

import os
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))
sys.path.insert(0, str(Path(__file__).parent))

from test_trading_agents import MockLLM
from trading_agents_system import TradingAgentsSystem, render_decision_report


def test_full_workflow():
    """测试完整流程"""
    print("\n" + "=" * 60)
    print("完整流程测试：选股 + TradingAgents决策")
    print("=" * 60 + "\n")

    # Step 1: 模拟选股结果
    print("【Step 1】模拟选股结果...")
    mock_stocks = [
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
    print(f"  选出 {len(mock_stocks)} 只股票")
    for stock in mock_stocks:
        print(
            f"    - {stock['code']} {stock['name']}: 主力+{stock['main_inflow'] / 1e8:.1f}亿, DDX={stock['ddx_10']:.1f}"
        )

    # Step 2: TradingAgents深度分析
    print("\n【Step 2】TradingAgents深度分析...")
    llm = MockLLM()
    system = TradingAgentsSystem(llm)

    analyzed_stocks = []
    for i, stock in enumerate(mock_stocks):
        print(f"\n  分析 {i + 1}/{len(mock_stocks)}: {stock['code']} {stock['name']}")

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
- 5日DDX: {stock["ddx_10"] / 2:.1f}
- 10日DDX: {stock["ddx_10"]}""",
            "sentiment_report": """情绪分析报告

市场情绪:
- 涨停基因: 45
- 机构评级: 买入
- 社交媒体情绪: 偏正面

资金情绪:
- 主力资金趋势: 流入
- 散户情绪: 乐观""",
            "news_report": """新闻分析报告

1. 公司发布新产品，市场反响良好
2. 机构上调评级至买入
3. 北向资金连续3日净流入""",
        }

        # 运行分析
        result = system.run_full_analysis(stock["code"], analyst_reports)

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
        print(f"    摘要: {decision.executive_summary[:40]}...")

        analyzed_stocks.append(stock)

    # Step 3: 生成报告
    print("\n【Step 3】生成报告...")

    report_lines = [
        "# 每日选股报告（TradingAgents增强版）\n",
        f"**时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "\n---\n",
        "\n## 选股结果\n",
    ]

    for i, stock in enumerate(analyzed_stocks, 1):
        ta = stock.get("trading_agents", {})
        report_lines.extend(
            [
                f"\n### {i}. {stock['name']} ({stock['code']})\n",
                f"\n**基本信息**\n",
                f"- 价格: {stock['price']}元\n",
                f"- 涨幅: {stock['change_pct']}%\n",
                f"- 主力流入: {stock['main_inflow'] / 1e8:.2f}亿\n",
                f"- 10日DDX: {stock['ddx_10']}\n",
                f"\n**TradingAgents决策**\n",
                f"- 评级: **{ta.get('rating', 'N/A')}**\n",
                f"- 摘要: {ta.get('executive_summary', 'N/A')}\n",
                f"- 逻辑: {ta.get('investment_thesis', 'N/A')[:80]}...\n",
                f"- 目标价: {ta.get('price_target', 'N/A')}\n",
                f"- 持有周期: {ta.get('time_horizon', 'N/A')}\n",
            ]
        )

    report = "".join(report_lines)

    # 保存报告
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "enhanced_selection_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存: {report_path}")

    # 打印报告
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    return analyzed_stocks


if __name__ == "__main__":
    test_full_workflow()
