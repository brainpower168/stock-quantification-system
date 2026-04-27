#!/usr/bin/env python3
"""
Performance Tracker - 策略表现跟踪系统

跟踪和分析交易策略的表现，包括：
1. 决策准确率统计
2. 策略收益归因
3. 因子有效性分析
4. AI模型表现对比
5. 定期报告生成

使用方式：
    python performance_tracker.py --report          # 生成报告
    python performance_tracker.py --analyze         # 分析策略表现
    python performance_tracker.py --compare         # 对比AI模型
    python performance_tracker.py --update-outcome  # 更新交易结果
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


class DecisionOutcome(Enum):
    CORRECT = "correct"  # 决策正确
    WRONG = "wrong"  # 决策错误
    NEUTRAL = "neutral"  # 中性


@dataclass
class TradeRecord:
    """交易记录"""

    stock_code: str
    stock_name: str
    decision: str  # BUY / SELL / HOLD
    confidence: float
    timestamp: str
    capital_flow: float
    ddx_10d: float
    price_at_decision: float
    actual_outcome: Optional[str] = None  # profit / loss / neutral
    profit_pct: Optional[float] = None
    outcome_verified: bool = False


class PerformanceTracker:
    """策略表现跟踪器"""

    def __init__(self):
        self.data_dir = SCRIPT_DIR.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        # 数据文件
        self.decisions_file = self.data_dir / "council_decisions.jsonl"
        self.trades_file = self.data_dir / "trade_records.jsonl"
        self.performance_file = self.data_dir / "performance_stats.json"

        # 加载历史数据
        self.decisions = self._load_decisions()
        self.trades = self._load_trades()

    def _load_decisions(self) -> List[Dict]:
        """加载决策记录"""
        if not self.decisions_file.exists():
            return []

        decisions = []
        with open(self.decisions_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    decisions.append(json.loads(line))
                except:
                    continue

        return decisions

    def _load_trades(self) -> List[Dict]:
        """加载交易记录"""
        if not self.trades_file.exists():
            return []

        trades = []
        with open(self.trades_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except:
                    continue

        return trades

    def _save_trades(self):
        """保存交易记录"""
        with open(self.trades_file, "w", encoding="utf-8") as f:
            for trade in self.trades:
                f.write(json.dumps(trade, ensure_ascii=False) + "\n")

    def record_trade(self, record: TradeRecord):
        """记录交易"""
        trade_dict = {
            "stock_code": record.stock_code,
            "stock_name": record.stock_name,
            "decision": record.decision,
            "confidence": record.confidence,
            "timestamp": record.timestamp,
            "capital_flow": record.capital_flow,
            "ddx_10d": record.ddx_10d,
            "price_at_decision": record.price_at_decision,
            "actual_outcome": record.actual_outcome,
            "profit_pct": record.profit_pct,
            "outcome_verified": record.outcome_verified,
        }

        self.trades.append(trade_dict)
        self._save_trades()

        logger.info(f"记录交易: {record.stock_code} {record.decision}")

    def update_outcome(self, stock_code: str, outcome: str, profit_pct: float):
        """更新交易结果"""
        # 找到最近的未验证交易
        for trade in reversed(self.trades):
            if trade["stock_code"] == stock_code and not trade.get("outcome_verified"):
                trade["actual_outcome"] = outcome
                trade["profit_pct"] = profit_pct
                trade["outcome_verified"] = True
                self._save_trades()
                logger.info(f"更新结果: {stock_code} {outcome} ({profit_pct}%)")
                return True

        logger.warning(f"未找到 {stock_code} 的未验证交易")
        return False

    def analyze_decision_accuracy(self, days: int = 30) -> Dict:
        """分析决策准确率"""
        cutoff = datetime.now() - timedelta(days=days)

        stats = {
            "total": 0,
            "verified": 0,
            "correct": 0,
            "wrong": 0,
            "neutral": 0,
            "by_decision_type": defaultdict(
                lambda: {"total": 0, "correct": 0, "wrong": 0}
            ),
            "by_confidence": {
                "high": {"total": 0, "correct": 0},  # confidence >= 0.7
                "medium": {"total": 0, "correct": 0},  # 0.5 <= confidence < 0.7
                "low": {"total": 0, "correct": 0},  # confidence < 0.5
            },
        }

        for trade in self.trades:
            try:
                trade_time = datetime.fromisoformat(trade["timestamp"])
                if trade_time < cutoff:
                    continue

                stats["total"] += 1

                if trade.get("outcome_verified"):
                    stats["verified"] += 1

                    outcome = trade.get("actual_outcome", "neutral")
                    decision = trade.get("decision", "HOLD")

                    # 判断决策是否正确
                    if decision in ["BUY", "STRONG_BUY"]:
                        if outcome == "profit":
                            stats["correct"] += 1
                            stats["by_decision_type"][decision]["correct"] += 1
                        elif outcome == "loss":
                            stats["wrong"] += 1
                            stats["by_decision_type"][decision]["wrong"] += 1
                        else:
                            stats["neutral"] += 1

                    elif decision in ["SELL", "STRONG_SELL"]:
                        if outcome == "loss":  # 卖出后下跌，决策正确
                            stats["correct"] += 1
                            stats["by_decision_type"][decision]["correct"] += 1
                        elif outcome == "profit":  # 卖出后上涨，决策错误
                            stats["wrong"] += 1
                            stats["by_decision_type"][decision]["wrong"] += 1
                        else:
                            stats["neutral"] += 1

                    stats["by_decision_type"][decision]["total"] += 1

                    # 按置信度分类
                    confidence = trade.get("confidence", 0.5)
                    if confidence >= 0.7:
                        level = "high"
                    elif confidence >= 0.5:
                        level = "medium"
                    else:
                        level = "low"

                    stats["by_confidence"][level]["total"] += 1
                    if outcome == "profit" and decision in ["BUY", "STRONG_BUY"]:
                        stats["by_confidence"][level]["correct"] += 1

            except Exception as e:
                continue

        # 计算准确率
        if stats["verified"] > 0:
            stats["accuracy"] = stats["correct"] / stats["verified"]
        else:
            stats["accuracy"] = 0

        return stats

    def analyze_factor_effectiveness(self, days: int = 30) -> Dict:
        """分析因子有效性"""
        cutoff = datetime.now() - timedelta(days=days)

        factor_stats = {
            "capital_flow": {
                "positive": {"total": 0, "profit": 0, "avg_profit": 0},
                "negative": {"total": 0, "profit": 0, "avg_profit": 0},
            },
            "ddx_10d": {
                "positive": {"total": 0, "profit": 0, "avg_profit": 0},
                "negative": {"total": 0, "profit": 0, "avg_profit": 0},
            },
            "confidence": {
                "high": {"total": 0, "profit": 0, "avg_profit": 0},
                "medium": {"total": 0, "profit": 0, "avg_profit": 0},
                "low": {"total": 0, "profit": 0, "avg_profit": 0},
            },
        }

        profits = {
            "capital_flow_positive": [],
            "capital_flow_negative": [],
            "ddx_positive": [],
            "ddx_negative": [],
            "confidence_high": [],
            "confidence_medium": [],
            "confidence_low": [],
        }

        for trade in self.trades:
            try:
                trade_time = datetime.fromisoformat(trade["timestamp"])
                if trade_time < cutoff:
                    continue

                if not trade.get("outcome_verified"):
                    continue

                if trade.get("decision") not in ["BUY", "STRONG_BUY"]:
                    continue

                profit_pct = trade.get("profit_pct", 0)
                capital_flow = trade.get("capital_flow", 0)
                ddx_10d = trade.get("ddx_10d", 0)
                confidence = trade.get("confidence", 0.5)

                # 资金流向
                if capital_flow > 0:
                    factor_stats["capital_flow"]["positive"]["total"] += 1
                    if profit_pct and profit_pct > 0:
                        factor_stats["capital_flow"]["positive"]["profit"] += 1
                    profits["capital_flow_positive"].append(profit_pct or 0)
                else:
                    factor_stats["capital_flow"]["negative"]["total"] += 1
                    if profit_pct and profit_pct > 0:
                        factor_stats["capital_flow"]["negative"]["profit"] += 1
                    profits["capital_flow_negative"].append(profit_pct or 0)

                # DDX
                if ddx_10d > 0:
                    factor_stats["ddx_10d"]["positive"]["total"] += 1
                    if profit_pct and profit_pct > 0:
                        factor_stats["ddx_10d"]["positive"]["profit"] += 1
                    profits["ddx_positive"].append(profit_pct or 0)
                else:
                    factor_stats["ddx_10d"]["negative"]["total"] += 1
                    if profit_pct and profit_pct > 0:
                        factor_stats["ddx_10d"]["negative"]["profit"] += 1
                    profits["ddx_negative"].append(profit_pct or 0)

                # 置信度
                if confidence >= 0.7:
                    level = "high"
                elif confidence >= 0.5:
                    level = "medium"
                else:
                    level = "low"

                factor_stats["confidence"][level]["total"] += 1
                if profit_pct and profit_pct > 0:
                    factor_stats["confidence"][level]["profit"] += 1
                profits[f"confidence_{level}"].append(profit_pct or 0)

            except Exception as e:
                continue

        # 计算平均收益
        for key in profits:
            if profits[key]:
                avg = sum(profits[key]) / len(profits[key])
                if "capital_flow_positive" in key:
                    factor_stats["capital_flow"]["positive"]["avg_profit"] = avg
                elif "capital_flow_negative" in key:
                    factor_stats["capital_flow"]["negative"]["avg_profit"] = avg
                elif "ddx_positive" in key:
                    factor_stats["ddx_10d"]["positive"]["avg_profit"] = avg
                elif "ddx_negative" in key:
                    factor_stats["ddx_10d"]["negative"]["avg_profit"] = avg
                elif "confidence_high" in key:
                    factor_stats["confidence"]["high"]["avg_profit"] = avg
                elif "confidence_medium" in key:
                    factor_stats["confidence"]["medium"]["avg_profit"] = avg
                elif "confidence_low" in key:
                    factor_stats["confidence"]["low"]["avg_profit"] = avg

        return factor_stats

    def compare_ai_models(self, days: int = 30) -> Dict:
        """对比AI模型表现"""
        cutoff = datetime.now() - timedelta(days=days)

        model_stats = defaultdict(
            lambda: {
                "total": 0,
                "correct": 0,
                "wrong": 0,
                "avg_confidence": 0,
                "confidences": [],
            }
        )

        for decision in self.decisions:
            try:
                decision_time = datetime.fromisoformat(decision["timestamp"])
                if decision_time < cutoff:
                    continue

                votes = decision.get("council_votes", {})

                for model_name, vote in votes.items():
                    if vote.get("error"):
                        continue

                    model_stats[model_name]["total"] += 1
                    model_stats[model_name]["confidences"].append(
                        vote.get("confidence", 0.5)
                    )

                    # 这里需要与交易结果关联
                    # 简化处理：统计投票分布

            except Exception as e:
                continue

        # 计算平均置信度
        for model in model_stats:
            if model_stats[model]["confidences"]:
                model_stats[model]["avg_confidence"] = sum(
                    model_stats[model]["confidences"]
                ) / len(model_stats[model]["confidences"])
            del model_stats[model]["confidences"]  # 移除原始数据

        return dict(model_stats)

    def generate_report(self, days: int = 30) -> str:
        """生成表现报告"""
        accuracy = self.analyze_decision_accuracy(days)
        factors = self.analyze_factor_effectiveness(days)
        models = self.compare_ai_models(days)

        report = f"""
# 策略表现报告

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
分析周期: 过去 {days} 天

## 决策准确率

- 总决策数: {accuracy["total"]}
- 已验证: {accuracy["verified"]}
- 正确: {accuracy["correct"]}
- 错误: {accuracy["wrong"]}
- **准确率: {accuracy["accuracy"] * 100:.1f}%**

### 按决策类型

| 决策类型 | 总数 | 正确 | 错误 | 准确率 |
|---------|------|------|------|--------|
"""

        for decision_type, stats in accuracy["by_decision_type"].items():
            if stats["total"] > 0:
                acc = stats["correct"] / stats["total"] * 100
                report += f"| {decision_type} | {stats['total']} | {stats['correct']} | {stats['wrong']} | {acc:.1f}% |\n"

        report += f"""
### 按置信度

| 置信度 | 总数 | 正确 | 准确率 |
|--------|------|------|--------|
"""

        for level in ["high", "medium", "low"]:
            stats = accuracy["by_confidence"][level]
            if stats["total"] > 0:
                acc = stats["correct"] / stats["total"] * 100
                report += f"| {level} | {stats['total']} | {stats['correct']} | {acc:.1f}% |\n"

        report += f"""
## 因子有效性

### 资金流向

| 类型 | 交易数 | 盈利数 | 平均收益 |
|------|--------|--------|---------|
| 流入 | {factors["capital_flow"]["positive"]["total"]} | {factors["capital_flow"]["positive"]["profit"]} | {factors["capital_flow"]["positive"]["avg_profit"]:.2f}% |
| 流出 | {factors["capital_flow"]["negative"]["total"]} | {factors["capital_flow"]["negative"]["profit"]} | {factors["capital_flow"]["negative"]["avg_profit"]:.2f}% |

### 10日DDX

| 类型 | 交易数 | 盈利数 | 平均收益 |
|------|--------|--------|---------|
| 正值 | {factors["ddx_10d"]["positive"]["total"]} | {factors["ddx_10d"]["positive"]["profit"]} | {factors["ddx_10d"]["positive"]["avg_profit"]:.2f}% |
| 负值 | {factors["ddx_10d"]["negative"]["total"]} | {factors["ddx_10d"]["negative"]["profit"]} | {factors["ddx_10d"]["negative"]["avg_profit"]:.2f}% |

## AI模型表现

| 模型 | 决策数 | 平均置信度 |
|------|--------|-----------|
"""

        for model, stats in models.items():
            report += (
                f"| {model} | {stats['total']} | {stats['avg_confidence']:.2f} |\n"
            )

        report += f"""
## 建议

"""

        # 根据数据生成建议
        if accuracy["accuracy"] >= 0.6:
            report += "- ✅ 决策准确率良好，继续保持当前策略\n"
        else:
            report += "- ⚠️ 决策准确率偏低，建议优化策略参数\n"

        if (
            factors["capital_flow"]["positive"]["avg_profit"]
            > factors["capital_flow"]["negative"]["avg_profit"]
        ):
            report += "- ✅ 资金流向因子有效，继续关注主力资金\n"
        else:
            report += "- ⚠️ 资金流向因子效果不佳，需重新评估\n"

        if factors["ddx_10d"]["positive"]["avg_profit"] > 0:
            report += "- ✅ 10日DDX因子有效，坚持红线规则\n"
        else:
            report += "- ⚠️ 10日DDX因子效果不佳，考虑调整阈值\n"

        report += """
---
*报告由 Performance Tracker 自动生成*
"""

        return report

    def save_stats(self):
        """保存统计数据"""
        stats = {
            "last_updated": datetime.now().isoformat(),
            "decision_accuracy": self.analyze_decision_accuracy(30),
            "factor_effectiveness": self.analyze_factor_effectiveness(30),
            "model_performance": self.compare_ai_models(30),
        }

        with open(self.performance_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logger.info(f"统计数据已保存: {self.performance_file}")


def main():
    parser = argparse.ArgumentParser(description="Performance Tracker")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--analyze", action="store_true", help="分析策略表现")
    parser.add_argument("--compare", action="store_true", help="对比AI模型")
    parser.add_argument(
        "--update-outcome",
        type=str,
        help="更新交易结果: 股票代码,结果(profit/loss),盈亏百分比",
    )
    parser.add_argument("--days", type=int, default=30, help="分析天数")
    parser.add_argument("--save", action="store_true", help="保存统计数据")

    args = parser.parse_args()

    tracker = PerformanceTracker()

    if args.update_outcome:
        parts = args.update_outcome.split(",")
        if len(parts) >= 3:
            tracker.update_outcome(parts[0], parts[1], float(parts[2]))
        else:
            print("用法: --update-outcome 股票代码,结果(profit/loss),盈亏百分比")

    elif args.report:
        report = tracker.generate_report(args.days)
        print(report)

        # 保存报告
        report_file = (
            tracker.data_dir
            / f"performance_report_{datetime.now().strftime('%Y%m%d')}.md"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_file}")

    elif args.analyze:
        accuracy = tracker.analyze_decision_accuracy(args.days)
        factors = tracker.analyze_factor_effectiveness(args.days)

        print(f"\n决策准确率: {accuracy['accuracy'] * 100:.1f}%")
        print(f"总决策: {accuracy['total']}, 已验证: {accuracy['verified']}")
        print(f"正确: {accuracy['correct']}, 错误: {accuracy['wrong']}")

        print(f"\n因子有效性:")
        print(
            f"  资金流入平均收益: {factors['capital_flow']['positive']['avg_profit']:.2f}%"
        )
        print(
            f"  资金流出平均收益: {factors['capital_flow']['negative']['avg_profit']:.2f}%"
        )
        print(f"  DDX正值平均收益: {factors['ddx_10d']['positive']['avg_profit']:.2f}%")
        print(f"  DDX负值平均收益: {factors['ddx_10d']['negative']['avg_profit']:.2f}%")

    elif args.compare:
        models = tracker.compare_ai_models(args.days)

        print("\nAI模型表现对比:")
        for model, stats in models.items():
            print(
                f"  {model}: {stats['total']}次决策, 平均置信度 {stats['avg_confidence']:.2f}"
            )

    if args.save:
        tracker.save_stats()

    if not any([args.report, args.analyze, args.compare, args.update_outcome]):
        parser.print_help()


if __name__ == "__main__":
    main()
