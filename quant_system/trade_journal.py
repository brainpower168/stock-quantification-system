# -*- coding: utf-8 -*-
"""
交易记录系统 - 记录每笔交易，自动复盘优化
功能：
1. 记录买卖操作（价格、数量、理由、因子数据）
2. 自动计算盈亏
3. 分析哪些因子最有效
4. 生成周报/月报
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings("ignore")


class TradeJournal:
    """交易记录系统"""

    def __init__(self, journal_dir: str = None):
        if journal_dir is None:
            journal_dir = os.path.join(os.path.dirname(__file__), "trade_journal")

        self.journal_dir = journal_dir
        self.trades_file = os.path.join(journal_dir, "trades.json")
        self.factors_file = os.path.join(journal_dir, "factors.json")

        # 创建目录
        os.makedirs(journal_dir, exist_ok=True)

        # 初始化文件
        self._init_files()

    def _init_files(self):
        """初始化JSON文件"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        if not os.path.exists(self.factors_file):
            with open(self.factors_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def record_buy(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        shares: int,
        reason: str,
        strategy: str = "manual",
        stop_loss: float = None,
        target_price: float = None,
        factors: Dict = None,
        notes: str = "",
    ) -> str:
        """
        记录买入操作

        返回:
            trade_id: 交易ID
        """
        # 生成交易ID
        trade_id = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 计算金额
        amount = price * shares

        # 默认止损价（-5%）
        if stop_loss is None:
            stop_loss = price * 0.95

        # 读取现有记录
        with open(self.trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)

        # 添加买入记录
        new_trade = {
            "trade_id": trade_id,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "action": "buy",
            "price": price,
            "shares": shares,
            "amount": amount,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "strategy": strategy,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "status": "holding",
            "exit_price": None,
            "exit_datetime": None,
            "pnl_pct": None,
            "pnl_amount": None,
            "hold_days": None,
            "exit_reason": None,
            "notes": notes,
        }

        trades.append(new_trade)

        # 保存
        with open(self.trades_file, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

        # 记录因子数据
        if factors:
            self._record_factors(trade_id, factors)

        print(f"[买入记录] {stock_name}({stock_code}) {shares}股 @ {price}元")
        print(f"  交易ID: {trade_id}")
        print(f"  止损价: {stop_loss:.2f}元")
        if target_price:
            print(f"  目标价: {target_price:.2f}元")

        return trade_id

    def record_sell(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = "manual",
        notes: str = "",
    ) -> Dict:
        """
        记录卖出操作

        返回:
            交易结果统计
        """
        # 读取交易记录
        with open(self.trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)

        # 查找对应交易
        trade_idx = None
        for i, trade in enumerate(trades):
            if trade["trade_id"] == trade_id:
                trade_idx = i
                break

        if trade_idx is None:
            print(f"[错误] 未找到交易ID: {trade_id}")
            return None

        trade = trades[trade_idx]

        # 计算盈亏
        entry_price = trade["price"]
        shares = trade["shares"]

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        pnl_amount = (exit_price - entry_price) * shares

        # 计算持仓天数
        entry_datetime = datetime.strptime(trade["datetime"], "%Y-%m-%d %H:%M:%S")
        exit_datetime = datetime.now()
        hold_days = (exit_datetime - entry_datetime).days

        # 更新记录
        trades[trade_idx]["status"] = "closed"
        trades[trade_idx]["exit_price"] = exit_price
        trades[trade_idx]["exit_datetime"] = exit_datetime.strftime("%Y-%m-%d %H:%M:%S")
        trades[trade_idx]["pnl_pct"] = pnl_pct
        trades[trade_idx]["pnl_amount"] = pnl_amount
        trades[trade_idx]["hold_days"] = hold_days
        trades[trade_idx]["exit_reason"] = exit_reason
        trades[trade_idx]["notes"] = notes

        # 保存
        with open(self.trades_file, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

        # 输出结果
        print(
            f"[卖出记录] {trade['stock_name']}({trade['stock_code']}) {shares}股 @ {exit_price}元"
        )
        print(f"  盈亏: {pnl_pct:+.2f}% ({pnl_amount:+.2f}元)")
        print(f"  持仓天数: {hold_days}天")
        print(f"  卖出原因: {exit_reason}")

        return {
            "trade_id": trade_id,
            "stock_code": trade["stock_code"],
            "stock_name": trade["stock_name"],
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "hold_days": hold_days,
            "exit_reason": exit_reason,
        }

    def _record_factors(self, trade_id: str, factors: Dict):
        """记录因子数据"""
        with open(self.factors_file, "r", encoding="utf-8") as f:
            factors_list = json.load(f)

        # 因子分类
        factor_categories = {
            "ddx": ["ddx", "ddy", "ddz"],
            "fund_flow": ["main_flow", "super_large", "large", "medium", "small"],
            "technical": ["rsi", "kdj", "macd", "ma5", "ma10", "ma20"],
            "fundamental": ["pe", "pb", "roe", "revenue_growth", "profit_growth"],
            "sentiment": ["sentiment_score", "news_count", "hot_rank"],
        }

        for factor_name, factor_value in factors.items():
            # 确定因子类别
            category = "other"
            for cat, keywords in factor_categories.items():
                if any(kw in factor_name.lower() for kw in keywords):
                    category = cat
                    break

            factors_list.append(
                {
                    "trade_id": trade_id,
                    "factor_name": factor_name,
                    "factor_value": factor_value,
                    "factor_category": category,
                }
            )

        with open(self.factors_file, "w", encoding="utf-8") as f:
            json.dump(factors_list, f, ensure_ascii=False, indent=2)

    def get_open_trades(self) -> List[Dict]:
        """获取当前持仓"""
        with open(self.trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)
        return [t for t in trades if t["status"] == "holding"]

    def get_closed_trades(self, days: int = 30) -> List[Dict]:
        """获取已平仓交易"""
        with open(self.trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)

        closed_trades = [t for t in trades if t["status"] == "closed"]

        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)
            closed_trades = [
                t
                for t in closed_trades
                if datetime.strptime(t["exit_datetime"], "%Y-%m-%d %H:%M:%S")
                >= cutoff_date
            ]

        return closed_trades

    def analyze_performance(self, days: int = 30) -> Dict:
        """分析交易表现"""
        closed_trades = self.get_closed_trades(days)

        if len(closed_trades) == 0:
            print(f"[分析] 最近{days}天没有已平仓交易")
            return None

        # 基础统计
        total_trades = len(closed_trades)
        win_trades = len([t for t in closed_trades if t["pnl_pct"] > 0])
        loss_trades = len([t for t in closed_trades if t["pnl_pct"] <= 0])

        win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0

        total_pnl_pct = sum(t["pnl_pct"] for t in closed_trades)
        avg_pnl_pct = total_pnl_pct / total_trades

        avg_win = (
            np.mean([t["pnl_pct"] for t in closed_trades if t["pnl_pct"] > 0])
            if win_trades > 0
            else 0
        )
        avg_loss = (
            np.mean([t["pnl_pct"] for t in closed_trades if t["pnl_pct"] <= 0])
            if loss_trades > 0
            else 0
        )

        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # 最大盈利/亏损
        max_win = max(t["pnl_pct"] for t in closed_trades)
        max_loss = min(t["pnl_pct"] for t in closed_trades)

        # 平均持仓天数
        avg_hold_days = np.mean([t["hold_days"] for t in closed_trades])

        results = {
            "period_days": days,
            "total_trades": total_trades,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct,
            "avg_pnl_pct": avg_pnl_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_loss_ratio": profit_loss_ratio,
            "max_win": max_win,
            "max_loss": max_loss,
            "avg_hold_days": avg_hold_days,
        }

        return results

    def generate_report(self, report_type: str = "weekly") -> str:
        """生成报告"""
        days_map = {"daily": 1, "weekly": 7, "monthly": 30}
        days = days_map.get(report_type, 7)

        # 分析表现
        performance = self.analyze_performance(days)

        if performance is None:
            return f"最近{days}天没有交易记录"

        # 生成报告
        report = []
        report.append("=" * 60)
        report.append(f"交易报告 - {report_type.upper()}")
        report.append(f"统计周期: 最近{days}天")
        report.append("=" * 60)

        report.append("\n[基础统计]")
        report.append(f"总交易次数: {performance['total_trades']}")
        report.append(f"盈利次数: {performance['win_trades']}")
        report.append(f"亏损次数: {performance['loss_trades']}")
        report.append(f"胜率: {performance['win_rate']:.1f}%")

        report.append("\n[收益统计]")
        report.append(f"总收益: {performance['total_pnl_pct']:+.2f}%")
        report.append(f"平均收益: {performance['avg_pnl_pct']:+.2f}%")
        report.append(f"平均盈利: {performance['avg_win']:+.2f}%")
        report.append(f"平均亏损: {performance['avg_loss']:+.2f}%")
        report.append(f"盈亏比: {performance['profit_loss_ratio']:.2f}")

        report.append("\n[风险统计]")
        report.append(f"最大盈利: {performance['max_win']:+.2f}%")
        report.append(f"最大亏损: {performance['max_loss']:+.2f}%")
        report.append(f"平均持仓: {performance['avg_hold_days']:.1f}天")

        # 当前持仓
        open_trades = self.get_open_trades()
        if len(open_trades) > 0:
            report.append("\n[当前持仓]")
            for trade in open_trades:
                report.append(
                    f"  {trade['stock_name']}({trade['stock_code']}) "
                    f"{trade['shares']}股 @ {trade['price']:.2f}元 "
                    f"止损{trade['stop_loss']:.2f}元"
                )

        report.append("\n" + "=" * 60)

        report_text = "\n".join(report)

        # 保存报告
        report_file = os.path.join(
            self.journal_dir,
            f"report_{report_type}_{datetime.now().strftime('%Y%m%d')}.txt",
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)

        print(report_text)
        return report_text


def test_trade_journal():
    """测试交易记录系统"""
    print("\n" + "=" * 60)
    print("交易记录系统测试")
    print("=" * 60)

    journal = TradeJournal()

    # 模拟买入
    trade_id = journal.record_buy(
        stock_code="600519",
        stock_name="贵州茅台",
        price=1800.0,
        shares=100,
        reason="DDX连续5日流入，主力资金强劲",
        strategy="尾盘选股",
        stop_loss=1710.0,  # -5%
        target_price=1980.0,  # +10%
        factors={
            "ddx_10d": 2.5,
            "main_flow": 5.2,
            "rsi": 45,
            "pe": 35,
            "sentiment_score": 75,
        },
    )

    # 模拟卖出
    journal.record_sell(
        trade_id=trade_id, exit_price=1850.0, exit_reason="止盈", notes="达到目标价附近"
    )

    # 生成报告
    journal.generate_report("weekly")


if __name__ == "__main__":
    test_trade_journal()
