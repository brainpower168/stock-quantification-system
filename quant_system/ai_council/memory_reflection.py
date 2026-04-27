#!/usr/bin/env python3
"""
Trading Memory Reflection Script

Analyzes trading history and generates insights using the memory system.
Can be run as a scheduled task for periodic learning.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hindsight_memory import get_trading_memory


def analyze_trading_performance(days: int = 30) -> Dict:
    """
    Analyze trading performance over the past N days

    Returns insights, statistics, and recommendations
    """
    memory = get_trading_memory(enabled=False)

    # Get reflection from memory system
    reflection = memory.reflect_on_performance(period_days=days, focus="profitability")

    # Load decisions for detailed analysis
    decisions_file = Path(__file__).parent.parent / "data" / "council_decisions.jsonl"

    if not decisions_file.exists():
        return {
            "insights": "无历史决策记录",
            "recommendations": ["开始记录交易决策以积累经验"],
        }

    decisions = []
    cutoff = datetime.now().timestamp() - days * 86400

    with open(decisions_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                decision = json.loads(line)
                timestamp = datetime.fromisoformat(decision["timestamp"]).timestamp()
                if timestamp >= cutoff:
                    decisions.append(decision)
            except:
                continue

    # Analyze patterns
    analysis = {
        "period": f"过去{days}天",
        "total_decisions": len(decisions),
        "by_decision_type": {},
        "by_stock": {},
        "confidence_distribution": [],
        "recommendations": [],
    }

    # Decision type distribution
    for d in decisions:
        decision_type = d.get("consensus", "UNKNOWN")
        analysis["by_decision_type"][decision_type] = (
            analysis["by_decision_type"].get(decision_type, 0) + 1
        )
        analysis["confidence_distribution"].append(d.get("confidence", 0))

        stock = d.get("stock_code", "UNKNOWN")
        if stock not in analysis["by_stock"]:
            analysis["by_stock"][stock] = {"count": 0, "decisions": []}
        analysis["by_stock"][stock]["count"] += 1
        analysis["by_stock"][stock]["decisions"].append(decision_type)

    # Calculate statistics
    if analysis["confidence_distribution"]:
        analysis["avg_confidence"] = sum(analysis["confidence_distribution"]) / len(
            analysis["confidence_distribution"]
        )
        analysis["high_confidence_count"] = sum(
            1 for c in analysis["confidence_distribution"] if c >= 0.7
        )
    else:
        analysis["avg_confidence"] = 0
        analysis["high_confidence_count"] = 0

    # Generate recommendations
    recommendations = []

    # Check decision balance
    buy_count = analysis["by_decision_type"].get("BUY", 0) + analysis[
        "by_decision_type"
    ].get("STRONG_BUY", 0)
    sell_count = analysis["by_decision_type"].get("SELL", 0) + analysis[
        "by_decision_type"
    ].get("STRONG_SELL", 0)

    if buy_count > sell_count * 3:
        recommendations.append("⚠️ 买入决策过多，可能过于激进，建议增加风险控制")
    elif sell_count > buy_count * 3:
        recommendations.append("⚠️ 卖出决策过多，可能过于保守，检查是否有恐慌性卖出")

    # Check confidence
    if analysis["avg_confidence"] < 0.6:
        recommendations.append("⚠️ 平均置信度较低，建议加强数据分析和模型验证")

    # Check concentration
    if analysis["by_stock"]:
        max_stock_count = max(s["count"] for s in analysis["by_stock"].values())
        if max_stock_count > len(decisions) * 0.3:
            recommendations.append("⚠️ 决策过于集中在少数股票，建议分散关注")

    # Add positive feedback
    if analysis["high_confidence_count"] > len(decisions) * 0.5:
        recommendations.append("✓ 高置信度决策较多，分析质量良好")

    if not recommendations:
        recommendations.append("✓ 交易决策整体健康，继续保持")

    analysis["recommendations"] = recommendations

    # Combine with memory reflection
    analysis["memory_insights"] = reflection.get("insights", "")

    return analysis


def generate_weekly_report() -> str:
    """Generate a weekly trading report"""
    analysis = analyze_trading_performance(days=7)

    report = f"""
# AI Trading Council 周报

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 概览

- 分析周期: {analysis["period"]}
- 总决策数: {analysis["total_decisions"]}
- 平均置信度: {analysis["avg_confidence"]:.2f}

## 决策分布

| 决策类型 | 数量 |
|---------|------|
"""

    for decision_type, count in sorted(analysis["by_decision_type"].items()):
        report += f"| {decision_type} | {count} |\n"

    report += f"""
## 关注股票

"""

    for stock, data in sorted(
        analysis["by_stock"].items(), key=lambda x: x[1]["count"], reverse=True
    )[:5]:
        report += (
            f"- {stock}: {data['count']}次决策 ({', '.join(data['decisions'][:3])})\n"
        )

    report += f"""
## 建议

"""

    for rec in analysis["recommendations"]:
        report += f"- {rec}\n"

    report += f"""
## 记忆系统洞察

{analysis.get("memory_insights", "无")}

---
*此报告由 AI Trading Council 自动生成*
"""

    return report


def update_trade_outcome(stock_code: str, outcome: str, profit_pct: float = None):
    """
    Update the outcome of a past trade decision

    Args:
        stock_code: Stock code
        outcome: "profit" / "loss" / "neutral"
        profit_pct: Actual profit/loss percentage
    """
    memory = get_trading_memory(enabled=False)

    # Store the outcome
    memory.retain_trade_outcome(
        stock_code=stock_code,
        entry_price=0,  # Would need actual data
        exit_price=0,
        profit_pct=profit_pct or 0,
        hold_days=0,
        decision_quality="good"
        if outcome == "profit"
        else "bad"
        if outcome == "loss"
        else "neutral",
    )

    # Generate lesson if significant
    if profit_pct and abs(profit_pct) > 5:
        lesson_type = "盈利经验" if profit_pct > 0 else "亏损教训"
        memory.retain_lesson_learned(
            lesson=f"{stock_code} {lesson_type}: {profit_pct:+.1f}%",
            context=f"需要结合具体交易数据分析",
            related_stocks=[stock_code],
        )

    print(f"✓ 已更新 {stock_code} 的交易结果: {outcome}")


def main():
    parser = argparse.ArgumentParser(description="Trading Memory Reflection")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly report")
    parser.add_argument("--update", type=str, help="Update outcome for stock code")
    parser.add_argument(
        "--outcome",
        type=str,
        choices=["profit", "loss", "neutral"],
        help="Trade outcome",
    )
    parser.add_argument("--profit", type=float, help="Profit/loss percentage")

    args = parser.parse_args()

    if args.weekly:
        report = generate_weekly_report()
        print(report)

        # Save report
        report_file = (
            Path(__file__).parent.parent
            / "data"
            / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_file}")

    elif args.update:
        if not args.outcome:
            print("Error: --outcome required when using --update")
            return
        update_trade_outcome(args.update, args.outcome, args.profit)

    else:
        # Default: analyze performance
        analysis = analyze_trading_performance(args.days)

        print(f"\n{'=' * 60}")
        print(f"AI Trading Council 记忆分析")
        print(f"{'=' * 60}")
        print(f"\n分析周期: {analysis['period']}")
        print(f"总决策数: {analysis['total_decisions']}")
        print(f"平均置信度: {analysis['avg_confidence']:.2f}")

        print(f"\n决策分布:")
        for decision_type, count in sorted(analysis["by_decision_type"].items()):
            print(f"  {decision_type}: {count}")

        print(f"\n建议:")
        for rec in analysis["recommendations"]:
            print(f"  {rec}")

        if analysis.get("memory_insights"):
            print(f"\n记忆洞察:")
            print(analysis["memory_insights"])


if __name__ == "__main__":
    main()
