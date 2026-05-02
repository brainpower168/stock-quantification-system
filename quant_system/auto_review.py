# -*- coding: utf-8 -*-
"""
自动复盘系统 - 从历史交易中学习
功能：
1. 分析哪些策略最有效
2. 分析卖出时机是否合理
3. 生成优化建议
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import warnings

warnings.filterwarnings("ignore")


class AutoReview:
    """自动复盘系统"""

    def __init__(self, journal_dir: str = None):
        if journal_dir is None:
            journal_dir = os.path.join(os.path.dirname(__file__), "trade_journal")

        self.journal_dir = journal_dir
        self.trades_file = os.path.join(journal_dir, "trades.json")
        self.factors_file = os.path.join(journal_dir, "factors.json")

    def review_trades(self, days: int = 30) -> Dict:
        """复盘交易"""
        # 读取交易记录
        with open(self.trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)

        # 筛选已平仓交易
        closed_trades = [t for t in trades if t["status"] == "closed"]

        if len(closed_trades) == 0:
            print("[复盘] 没有已平仓交易")
            return None

        # 时间筛选
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)
            closed_trades = [
                t
                for t in closed_trades
                if datetime.strptime(t["exit_datetime"], "%Y-%m-%d %H:%M:%S")
                >= cutoff_date
            ]

        if len(closed_trades) == 0:
            print(f"[复盘] 最近{days}天没有已平仓交易")
            return None

        print("\n" + "=" * 60)
        print(f"自动复盘 - 最近{days}天")
        print("=" * 60)

        results = {}

        # 1. 策略表现分析
        results["strategy_analysis"] = self._analyze_strategies(closed_trades)

        # 2. 卖出时机分析
        results["exit_analysis"] = self._analyze_exit_timing(closed_trades)

        # 3. 错误交易分析
        results["mistakes"] = self._analyze_mistakes(closed_trades)

        # 4. 优化建议
        results["recommendations"] = self._generate_recommendations(results)

        # 保存复盘结果
        self._save_review(results)

        return results

    def _analyze_strategies(self, trades: List[Dict]) -> Dict:
        """分析策略表现"""
        print("\n[策略表现分析]")

        # 按策略分组
        strategy_groups = {}
        for trade in trades:
            strategy = trade.get("strategy", "unknown")
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(trade)

        # 计算每个策略的统计
        strategy_stats = {}
        for strategy, strategy_trades in strategy_groups.items():
            total = len(strategy_trades)
            wins = len([t for t in strategy_trades if t["pnl_pct"] > 0])
            losses = len([t for t in strategy_trades if t["pnl_pct"] <= 0])

            win_rate = wins / total * 100 if total > 0 else 0
            total_pnl = sum(t["pnl_pct"] for t in strategy_trades)
            avg_pnl = total_pnl / total if total > 0 else 0

            strategy_stats[strategy] = {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_pnl": avg_pnl,
            }

            print(
                f"  {strategy}: {total}笔, 胜率{win_rate:.1f}%, 总收益{total_pnl:+.2f}%"
            )

        # 找出最佳策略
        if strategy_stats:
            best_strategy = max(strategy_stats.items(), key=lambda x: x[1]["total_pnl"])
            print(
                f"\n最佳策略: {best_strategy[0]} (总收益{best_strategy[1]['total_pnl']:+.2f}%)"
            )

        return strategy_stats

    def _analyze_exit_timing(self, trades: List[Dict]) -> Dict:
        """分析卖出时机"""
        print("\n[卖出时机分析]")

        # 按卖出原因分组
        exit_groups = {}
        for trade in trades:
            exit_reason = trade.get("exit_reason", "unknown")
            if exit_reason not in exit_groups:
                exit_groups[exit_reason] = []
            exit_groups[exit_reason].append(trade)

        # 计算每个卖出原因的统计
        exit_stats = {}
        for reason, reason_trades in exit_groups.items():
            total = len(reason_trades)
            avg_pnl = np.mean([t["pnl_pct"] for t in reason_trades])

            exit_stats[reason] = {"count": total, "avg_pnl": avg_pnl}

            print(f"  {reason}: {total}次, 平均收益{avg_pnl:+.2f}%")

        # 分析是否卖早了
        print("\n卖出时机评估:")
        for trade in trades:
            if trade["pnl_pct"] > 5:
                print(
                    f"  {trade['stock_name']}: 盈利{trade['pnl_pct']:+.2f}% - {trade['exit_reason']}"
                )
                if trade["exit_reason"] == "止盈" and trade["pnl_pct"] < 10:
                    print(
                        f"    可能卖早了，盈利{trade['pnl_pct']:.1f}%就止盈，可以考虑持有到+15-20%"
                    )

            elif trade["pnl_pct"] < -3:
                print(
                    f"  {trade['stock_name']}: 亏损{trade['pnl_pct']:+.2f}% - {trade['exit_reason']}"
                )
                if trade["pnl_pct"] < -5:
                    print(f"    亏损超过5%，止损可能设置太宽或执行不及时")

        return exit_stats

    def _analyze_mistakes(self, trades: List[Dict]) -> List[Dict]:
        """分析错误交易"""
        print("\n[错误交易分析]")

        mistakes = []

        # 1. 大亏损交易
        big_losses = [t for t in trades if t["pnl_pct"] < -5]
        if big_losses:
            print(f"\n大亏损交易（亏损>5%）: {len(big_losses)}笔")
            for trade in big_losses:
                mistake = {
                    "type": "big_loss",
                    "stock": trade["stock_name"],
                    "pnl_pct": trade["pnl_pct"],
                    "exit_reason": trade["exit_reason"],
                    "lesson": "止损执行不及时或止损设置太宽",
                }
                mistakes.append(mistake)
                print(
                    f"  {trade['stock_name']}: {trade['pnl_pct']:+.2f}% - {trade['exit_reason']}"
                )

        return mistakes

    def _generate_recommendations(self, results: Dict) -> List[str]:
        """生成优化建议"""
        print("\n" + "=" * 60)
        print("优化建议")
        print("=" * 60)

        recommendations = []

        # 策略建议
        if "strategy_analysis" in results and results["strategy_analysis"]:
            best_strategy = max(
                results["strategy_analysis"].items(), key=lambda x: x[1]["total_pnl"]
            )
            rec = f"1. 策略优化: 多用【{best_strategy[0]}】策略（总收益{best_strategy[1]['total_pnl']:+.2f}%）"
            recommendations.append(rec)
            print(rec)

        # 卖出时机建议
        if "exit_analysis" in results and results["exit_analysis"]:
            worst_exit = min(
                results["exit_analysis"].items(), key=lambda x: x[1]["avg_pnl"]
            )
            rec = f"2. 卖出优化: 【{worst_exit[0]}】卖出效果最差（平均{worst_exit[1]['avg_pnl']:+.2f}%），考虑调整策略"
            recommendations.append(rec)
            print(rec)

        # 风控建议
        if "mistakes" in results and results["mistakes"]:
            big_loss_count = len(
                [m for m in results["mistakes"] if m["type"] == "big_loss"]
            )
            if big_loss_count > 0:
                rec = f"3. 风控优化: 有{big_loss_count}笔大亏损，严格执行5%止损"
                recommendations.append(rec)
                print(rec)

        if len(recommendations) == 0:
            rec = "暂无优化建议，继续积累交易数据"
            recommendations.append(rec)
            print(rec)

        return recommendations

    def _save_review(self, results: Dict):
        """保存复盘结果"""
        review_file = os.path.join(
            self.journal_dir, f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n复盘结果已保存: {review_file}")


def test_auto_review():
    """测试自动复盘系统"""
    print("\n" + "=" * 60)
    print("自动复盘系统测试")
    print("=" * 60)

    review = AutoReview()
    results = review.review_trades(days=30)


if __name__ == "__main__":
    test_auto_review()
