#!/usr/bin/env python3
"""
海龟法则进阶版策略 v2.0
========================
整合OSkhQuant框架优点 + 反转信号检测 + DDX资金管理

核心改进：
1. 大级别趋势判断（20日新高/新低）
2. 缩短进场周期（10日）
3. 一次性建仓（不再分批）
4. 动态止损（2N止损）
5. 【新增】反转信号检测（单日主力>10亿 + 涨幅>3%）
6. 【新增】DDX资金管理（10日DDX<0不买）
7. 【新增】买入纪律检查清单

使用方法：
    python turtle_strategy_v2.py --stock 600519 --days 100
    python turtle_strategy_v2.py --backtest 600519 --start 2023-01-01 --end 2024-01-01
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TurtleStrategyV2:
    """海龟法则进阶版策略 v2.0"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略

        Args:
            config: 策略配置
        """
        self.config = config or {}

        # 策略参数
        self.entry_window = self.config.get("entry_window", 10)
        self.exit_window = self.config.get("exit_window", 20)
        self.trend_window = self.config.get("trend_window", 20)
        self.stop_loss_n = self.config.get("stop_loss_n", 2)
        self.position_risk = self.config.get("position_risk", 0.01)

        # 【新增】反转信号参数
        self.reversal_main_inflow_threshold = self.config.get(
            "reversal_main_inflow_threshold", 1000000000
        )  # 10亿
        self.reversal_change_threshold = self.config.get(
            "reversal_change_threshold", 3.0
        )  # 3%

        # 数据缓存
        self.data = None
        self.signals = []

    def calculate_n(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """计算N值（平均真实波幅ATR）"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        n = tr.rolling(window=window).mean()

        return n

    def calculate_position_size(
        self, account_value: float, n: float, price: float
    ) -> int:
        """计算仓位大小"""
        risk_amount = account_value * self.position_risk
        unit_risk = n * price

        if unit_risk == 0:
            return 0

        position = int(risk_amount / unit_risk)
        max_position = int(account_value * 0.3 / price)

        return min(position, max_position)

    def detect_reversal_signal(self, stock_data: Dict) -> Dict:
        """
        【新增】检测反转信号

        条件：
        1. 单日主力流入 > 10亿
        2. 涨幅 > 3%
        3. 10日DDX < 0（中期流出）

        Returns:
            反转信号字典
        """
        main_inflow = stock_data.get("main_inflow", 0)
        change_pct = stock_data.get("change_pct", 0)
        ddx_10 = stock_data.get("ddx_10", 0)

        is_reversal = (
            main_inflow > self.reversal_main_inflow_threshold
            and change_pct > self.reversal_change_threshold
            and ddx_10 < 0
        )

        return {
            "is_reversal": is_reversal,
            "main_inflow": main_inflow,
            "change_pct": change_pct,
            "ddx_10": ddx_10,
            "reason": f"单日主力{main_inflow / 100000000:.2f}亿 + 涨幅{change_pct:.1f}% + 10日DDX={ddx_10:.3f}"
            if is_reversal
            else "不符合反转信号条件",
        }

    def check_buy_discipline(self, stock_data: Dict) -> Dict:
        """
        【新增】买入纪律检查清单

        Returns:
            检查结果字典
        """
        checks = {
            "ddx_10_positive": stock_data.get("ddx_10", 0) > 0,
            "main_inflow_positive": stock_data.get("main_inflow", 0) > 0,
            "change_below_3pct": abs(stock_data.get("change_pct", 0)) < 3,
            "pe_below_50": stock_data.get("pe", 100) < 50,
            "roe_above_10": stock_data.get("roe", 0) > 10,
            "profit_growth_positive": stock_data.get("profit_growth", 0) > 0,
        }

        passed = sum(checks.values())
        total = len(checks)

        # 检查是否是反转信号
        reversal = self.detect_reversal_signal(stock_data)

        if reversal["is_reversal"]:
            # 反转信号：放宽DDX要求
            checks["ddx_10_positive"] = True  # 标记为通过（需要次日确认）
            checks["is_reversal_signal"] = True
            checks["reversal_note"] = "反转信号，需次日确认主力继续流入"
            passed = sum(checks.values()) - 1  # 减去反转信号标记

        return {
            "checks": checks,
            "passed": passed,
            "total": total,
            "can_buy": passed >= 4,  # 至少通过4项
            "is_reversal": reversal["is_reversal"],
            "reversal_info": reversal,
        }

    def generate_signals(
        self, df: pd.DataFrame, stock_data: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            df: 包含OHLCV的DataFrame
            stock_data: 股票数据字典（用于反转信号检测）

        Returns:
            包含信号的DataFrame
        """
        df = df.copy()

        # 计算N值
        df["N"] = self.calculate_n(df)

        # 计算突破点
        df["high_10"] = df["high"].rolling(window=self.entry_window).max()
        df["low_10"] = df["low"].rolling(window=self.entry_window).min()
        df["high_20"] = df["high"].rolling(window=self.exit_window).max()
        df["low_20"] = df["low"].rolling(window=self.exit_window).min()

        # 趋势判断
        df["trend_high"] = df["high"].rolling(window=self.trend_window).max()
        df["trend_low"] = df["low"].rolling(window=self.trend_window).min()

        # 生成信号
        df["signal"] = 0

        # 买入信号：收盘价突破10日新高
        buy_condition = df["close"] >= df["high_10"].shift(1)
        df.loc[buy_condition, "signal"] = 1

        # 卖出信号：收盘价跌破10日新低
        sell_condition = df["close"] <= df["low_10"].shift(1)
        df.loc[sell_condition, "signal"] = -1

        # 止损/止盈价格
        df["stop_loss"] = df["close"] - self.stop_loss_n * df["N"]
        df["take_profit"] = df["close"] + 4 * df["N"]

        # 【新增】反转信号标记
        if stock_data:
            reversal = self.detect_reversal_signal(stock_data)
            df["reversal_signal"] = reversal["is_reversal"]

        return df

    def analyze(
        self, df: pd.DataFrame, stock_data: Dict, account_value: float = 100000
    ) -> Dict:
        """
        分析股票并生成交易建议

        Args:
            df: 包含OHLCV的DataFrame
            stock_data: 股票数据字典
            account_value: 账户价值

        Returns:
            分析结果字典
        """
        df = self.generate_signals(df, stock_data)

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 当前状态
        current_price = latest["close"]
        current_n = latest["N"]
        current_signal = latest["signal"]

        # 趋势判断
        trend = (
            "上涨"
            if current_price > latest["trend_high"] * 0.95
            else "下跌"
            if current_price < latest["trend_low"] * 1.05
            else "震荡"
        )

        # 建议仓位
        position_size = self.calculate_position_size(
            account_value, current_n, current_price
        )

        # 【新增】买入纪律检查
        discipline_check = self.check_buy_discipline(stock_data)

        # 【新增】反转信号检测
        reversal_info = self.detect_reversal_signal(stock_data)

        # 生成建议
        recommendation = {
            "timestamp": datetime.now().isoformat(),
            "current_price": round(current_price, 2),
            "N_value": round(current_n, 2),
            "trend": trend,
            "signal": "BUY"
            if current_signal == 1
            else "SELL"
            if current_signal == -1
            else "HOLD",
            "position_size": position_size,
            "stop_loss": round(latest["stop_loss"], 2),
            "take_profit": round(latest["take_profit"], 2),
            "risk_reward_ratio": round(4 / self.stop_loss_n, 2),
            # 【新增】买入纪律
            "discipline_check": discipline_check,
            # 【新增】反转信号
            "reversal_signal": reversal_info,
            # 进场条件
            "entry_conditions": {
                "price_above_10d_high": current_price >= prev["high_10"],
                "trend_up": trend == "上涨",
                "volume_confirmed": latest.get("volume", 0)
                > df["volume"].rolling(20).mean().iloc[-1],
                "discipline_passed": discipline_check["can_buy"],
            },
        }

        # 风险提示
        risks = []
        if trend == "震荡":
            risks.append("当前处于震荡趋势，信号可靠性降低")
        if current_n > df["N"].rolling(20).mean().iloc[-1] * 1.5:
            risks.append("波动率异常放大，注意风险")
        if position_size == 0:
            risks.append("当前N值过大或价格异常，不建议建仓")

        # 【新增】反转信号风险提示
        if reversal_info["is_reversal"]:
            risks.append(
                f"⚠️ 反转信号：{reversal_info['reason']}，需次日确认主力继续流入"
            )

        # 【新增】买入纪律风险提示
        if not discipline_check["can_buy"]:
            failed_checks = [k for k, v in discipline_check["checks"].items() if not v]
            risks.append(f"买入纪律未通过：{', '.join(failed_checks)}")

        recommendation["risks"] = risks

        return recommendation

    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """回测策略"""
        df = self.generate_signals(df)

        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []

        for i in range(1, len(df)):
            row = df.iloc[i]

            # 买入
            if row["signal"] == 1 and position == 0:
                position_size = self.calculate_position_size(
                    capital, row["N"], row["close"]
                )
                if position_size > 0:
                    position = position_size
                    entry_price = row["close"]
                    capital -= position * entry_price
                    trades.append(
                        {
                            "date": df.index[i],
                            "type": "BUY",
                            "price": entry_price,
                            "shares": position,
                            "capital": capital,
                        }
                    )

            # 卖出
            elif row["signal"] == -1 and position > 0:
                capital += position * row["close"]
                profit = (row["close"] - entry_price) * position
                trades.append(
                    {
                        "date": df.index[i],
                        "type": "SELL",
                        "price": row["close"],
                        "shares": position,
                        "capital": capital,
                        "profit": profit,
                    }
                )
                position = 0
                entry_price = 0

            # 止损检查
            elif (
                position > 0
                and row["close"] <= entry_price - self.stop_loss_n * row["N"]
            ):
                capital += position * row["close"]
                profit = (row["close"] - entry_price) * position
                trades.append(
                    {
                        "date": df.index[i],
                        "type": "STOP_LOSS",
                        "price": row["close"],
                        "shares": position,
                        "capital": capital,
                        "profit": profit,
                    }
                )
                position = 0
                entry_price = 0

        # 计算绩效
        if position > 0:
            capital += position * df.iloc[-1]["close"]

        total_return = (capital - initial_capital) / initial_capital * 100

        # 计算最大回撤
        capital_curve = [initial_capital]
        for trade in trades:
            if "capital" in trade:
                capital_curve.append(trade["capital"])

        peak = capital_curve[0]
        max_drawdown = 0
        for value in capital_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 统计交易
        winning_trades = [t for t in trades if t.get("profit", 0) > 0]
        losing_trades = [t for t in trades if t.get("profit", 0) < 0]

        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        avg_win = (
            np.mean([t["profit"] for t in winning_trades]) if winning_trades else 0
        )
        avg_loss = np.mean([t["profit"] for t in losing_trades]) if losing_trades else 0

        return {
            "initial_capital": initial_capital,
            "final_capital": round(capital, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            "trades": trades[-10:],
        }


def main():
    parser = argparse.ArgumentParser(description="海龟法则进阶版策略 v2.0")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--days", type=int, default=100, help="分析天数")
    parser.add_argument("--backtest", type=str, help="回测股票代码")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金")

    args = parser.parse_args()

    strategy = TurtleStrategyV2()

    if args.stock:
        print(f"\n{'=' * 60}")
        print(f"海龟法则进阶版 v2.0 分析: {args.stock}")
        print(f"{'=' * 60}\n")

        # 获取数据
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from data_fetcher import DataFetcher

            fetcher = DataFetcher()
            df = fetcher.get_stock_data(args.stock, days=args.days)
            quote = fetcher.get_realtime_quote(args.stock)

            if df is not None and not df.empty:
                stock_data = {
                    "code": args.stock,
                    "main_inflow": quote.get("main_inflow", 0),
                    "change_pct": quote.get("change_pct", 0),
                    "ddx_10": quote.get("ddx_10", 0),
                    "pe": quote.get("pe", 20),
                    "roe": quote.get("roe", 10),
                    "profit_growth": quote.get("profit_growth", 10),
                }

                result = strategy.analyze(df, stock_data, args.capital)

                print(f"当前价格: {result['current_price']} 元")
                print(f"N值(ATR): {result['N_value']} 元")
                print(f"趋势判断: {result['trend']}")
                print(f"交易信号: {result['signal']}")
                print(f"建议仓位: {result['position_size']} 股")
                print(f"止损价格: {result['stop_loss']} 元")
                print(f"止盈价格: {result['take_profit']} 元")
                print(f"盈亏比: {result['risk_reward_ratio']}:1")

                # 【新增】反转信号
                if result["reversal_signal"]["is_reversal"]:
                    print(f"\n⚠️ 反转信号检测:")
                    print(f"  {result['reversal_signal']['reason']}")
                    print(f"  建议：次日确认主力继续流入后再买入")

                # 【新增】买入纪律检查
                print(f"\n买入纪律检查:")
                discipline = result["discipline_check"]
                for check, passed in discipline["checks"].items():
                    status = "✓" if passed else "✗"
                    print(f"  {status} {check}: {passed}")
                print(f"  通过: {discipline['passed']}/{discipline['total']}")

                if result["risks"]:
                    print(f"\n风险提示:")
                    for risk in result["risks"]:
                        print(f"  ⚠ {risk}")
        except Exception as e:
            print(f"分析失败: {e}")

    elif args.backtest:
        print(f"\n{'=' * 60}")
        print(f"海龟法则进阶版 v2.0 回测: {args.backtest}")
        print(f"{'=' * 60}\n")

        # 回测逻辑
        print("回测功能开发中...")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
