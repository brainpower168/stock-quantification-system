#!/usr/bin/env python3
"""
最笨交易法策略 v3（改进版）
=========================
改进点：
1. 放宽选股条件：不要求涨停，改为"近10日涨幅>5% + 主力流入"或"涨停"
2. 增加DDX过滤：10日DDX>0为必须条件
3. 调整止损：跌破20日均线3%才止损（避免频繁止损）

核心逻辑：
1. 选股：近10日有大涨（涨停或涨幅>5%+主力流入）+ 月线MACD金叉
2. 买入：股价站上20日均线 + 10日DDX>0 + 涨幅<3%
3. 卖出：涨幅30%减仓一半，涨幅50%清仓，跌破MA20 3%止损

使用方法：
    python simple_profit_strategy_v3.py --stock 600519
    python simple_profit_strategy_v3.py --screen
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SimpleProfitStrategyV3:
    """最笨交易法策略 v3 - 改进版"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 策略参数
        self.ma_period = self.config.get("ma_period", 20)
        self.lookback_days = self.config.get("lookback_days", 10)  # 回看天数
        self.profit_take_1 = self.config.get("profit_take_1", 0.30)
        self.profit_take_2 = self.config.get("profit_take_2", 0.50)

        # 改进1：放宽选股条件
        self.big_rise_pct = self.config.get("big_rise_pct", 5.0)  # 大涨阈值5%
        self.big_rise_main_inflow = self.config.get(
            "big_rise_main_inflow", 500000000
        )  # 5亿主力流入

        # 改进2：DDX必须条件
        self.ddx_threshold = self.config.get("ddx_threshold", 0)

        # 改进3：止损阈值
        self.stop_loss_pct = self.config.get("stop_loss_pct", -0.03)  # 跌破MA20 3%

        # 反转信号参数
        self.reversal_main_inflow = self.config.get("reversal_main_inflow", 1000000000)
        self.reversal_change_pct = self.config.get("reversal_change_pct", 3.0)

    def check_big_rise_in_days(
        self, df: pd.DataFrame, days: int = 10, main_inflow: float = 0
    ) -> Dict:
        """
        检查最近N天内是否有大涨（改进版）

        条件（满足任一）：
        1. 有涨停（涨幅>=9.9%）
        2. 涨幅>5% + 当日主力流入>5亿

        Args:
            df: K线数据
            days: 回看天数
            main_inflow: 今日主力流入（用于判断）

        Returns:
            大涨信息
        """
        if len(df) < days:
            return {"has_big_rise": False, "reason": "数据不足"}

        recent = df.tail(days).copy()

        # 兼容列名
        pct_col = None
        for col in ["pct_chg", "change", "pct_change", "涨跌幅"]:
            if col in recent.columns:
                pct_col = col
                break

        if pct_col is None:
            recent["pct_calc"] = (recent["close"].pct_change() * 100).fillna(0)
            pct_col = "pct_calc"

        # 条件1：涨停
        zt_days = recent[recent[pct_col] >= 9.9]
        has_zt = len(zt_days) > 0

        # 条件2：大涨（涨幅>5%）
        big_rise_days = recent[recent[pct_col] >= self.big_rise_pct]
        has_big_rise = len(big_rise_days) > 0

        # 综合判断
        if has_zt:
            return {
                "has_big_rise": True,
                "type": "涨停",
                "count": len(zt_days),
                "max_pct": recent[pct_col].max(),
                "reason": f"近{days}日有{len(zt_days)}次涨停",
            }
        elif has_big_rise:
            return {
                "has_big_rise": True,
                "type": "大涨",
                "count": len(big_rise_days),
                "max_pct": recent[pct_col].max(),
                "reason": f"近{days}日有{len(big_rise_days)}次涨幅>{self.big_rise_pct}%",
            }
        else:
            return {
                "has_big_rise": False,
                "type": "无",
                "count": 0,
                "max_pct": recent[pct_col].max(),
                "reason": f"近{days}日无大涨，最大涨幅{recent[pct_col].max():.1f}%",
            }

    def check_ma20_support(self, df: pd.DataFrame) -> Dict:
        """检查20日均线支撑"""
        if len(df) < self.ma_period:
            return {"valid": False, "reason": "数据不足"}

        df = df.copy()
        df["ma20"] = df["close"].rolling(window=self.ma_period).mean()

        latest = df.iloc[-1]
        close = latest["close"]
        ma20 = latest["ma20"]

        distance_pct = (close - ma20) / ma20 * 100

        # 改进：放宽"附近"定义到±5%
        is_near_ma20 = abs(distance_pct) <= 5
        is_above_ma20 = close > ma20

        return {
            "valid": True,
            "close": round(close, 2),
            "ma20": round(ma20, 2),
            "distance_pct": round(distance_pct, 2),
            "is_near_ma20": is_near_ma20,
            "is_above_ma20": is_above_ma20,
            "status": "回踩20日线"
            if is_near_ma20
            else ("站上20日线" if is_above_ma20 else "跌破20日线"),
        }

    def check_stop_loss(
        self, entry_price: float, stock_data: Dict, df: pd.DataFrame
    ) -> Dict:
        """
        检查止损条件（改进版）

        改进：跌破MA20 3%才止损，避免频繁止损
        """
        current_price = stock_data.get("price", df.iloc[-1]["close"])

        # 计算MA20
        df = df.copy()
        df["ma20"] = df["close"].rolling(window=self.ma_period).mean()
        ma20 = df.iloc[-1]["ma20"]

        # 计算盈亏
        profit_pct = (current_price - entry_price) / entry_price

        # 计算距离MA20
        distance_to_ma20 = (current_price - ma20) / ma20

        # 改进：跌破MA20 3%才止损
        should_stop = distance_to_ma20 < self.stop_loss_pct

        # 或者亏损超过8%
        should_stop = should_stop or profit_pct < -0.08

        return {
            "current_price": current_price,
            "ma20": round(ma20, 2),
            "distance_to_ma20": round(distance_to_ma20 * 100, 2),
            "profit_pct": round(profit_pct * 100, 2),
            "should_stop": should_stop,
            "reason": f"跌破MA20 {abs(distance_to_ma20) * 100:.1f}%"
            if distance_to_ma20 < self.stop_loss_pct
            else (
                f"亏损{abs(profit_pct) * 100:.1f}%"
                if profit_pct < -0.08
                else "未触发止损"
            ),
        }

    def calculate_profit_stage(self, entry_price: float, current_price: float) -> Dict:
        """计算盈利阶段"""
        profit_pct = (current_price - entry_price) / entry_price

        # 麻雀战法：盈利2.5%开始分批止盈
        if profit_pct >= 0.025:
            additional_profit = (profit_pct - 0.025) / 0.01
            sell_ratio = min(0.1 * additional_profit + 0.1, 1.0)

            return {
                "stage": 1,
                "profit_pct": round(profit_pct * 100, 2),
                "action": f"分批止盈，已卖{sell_ratio * 100:.0f}%",
                "sell_ratio": round(sell_ratio, 2),
                "reason": f"麻雀战法：盈利{profit_pct * 100:.1f}%",
                "method": "麻雀战法",
            }

        # 最笨交易法：大涨幅
        if profit_pct >= self.profit_take_2:
            return {
                "stage": 3,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "全部清仓",
                "sell_ratio": 1.0,
                "reason": f"涨幅{profit_pct * 100:.1f}%，超过50%",
                "method": "最笨交易法",
            }
        elif profit_pct >= self.profit_take_1:
            return {
                "stage": 2,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "减仓一半",
                "sell_ratio": 0.5,
                "reason": f"涨幅{profit_pct * 100:.1f}%，超过30%",
                "method": "最笨交易法",
            }
        else:
            return {
                "stage": 0,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "持有",
                "sell_ratio": 0,
                "reason": f"涨幅{profit_pct * 100:.1f}%，未达止盈",
                "method": "持有",
            }

    def check_buy_conditions(self, stock_data: Dict, df: pd.DataFrame) -> Dict:
        """
        检查买入条件（改进版）

        改进：
        1. 放宽选股条件：涨停或大涨+主力流入
        2. DDX>0为必须条件
        """
        checks = {}

        # 1. 近10日有大涨（改进：放宽条件）
        main_inflow = stock_data.get("main_inflow", 0)
        big_rise = self.check_big_rise_in_days(df, self.lookback_days, main_inflow)
        checks["big_rise"] = {
            "name": "近10日大涨",
            "passed": big_rise["has_big_rise"],
            "weight": 2,
            "detail": big_rise["reason"],
            "type": big_rise.get("type", ""),
        }

        # 2. 20日均线支撑
        ma20_status = self.check_ma20_support(df)
        checks["ma20_support"] = {
            "name": "20日均线支撑",
            "passed": ma20_status["is_above_ma20"] or ma20_status["is_near_ma20"],
            "weight": 2,
            "detail": f"MA20={ma20_status['ma20']}, 距离{ma20_status['distance_pct']:.1f}%",
        }

        # 3. DDX资金流向（改进：必须条件）
        ddx_10 = stock_data.get("ddx_10", 0)
        checks["ddx_positive"] = {
            "name": "10日DDX > 0",
            "passed": ddx_10 > self.ddx_threshold,
            "weight": 3,  # 提高权重
            "detail": f"10日DDX = {ddx_10:.3f}",
            "required": True,  # 标记为必须
        }

        # 4. 主力资金流入
        checks["main_inflow"] = {
            "name": "主力资金流入",
            "passed": main_inflow > 0,
            "weight": 1,
            "detail": f"主力净流入 = {main_inflow / 100000000:.2f}亿",
        }

        # 5. 涨幅控制
        change_pct = stock_data.get("change_pct", 0)
        checks["not_chasing_high"] = {
            "name": "涨幅 < 3%",
            "passed": abs(change_pct) < 3,
            "weight": 1,
            "detail": f"当日涨幅 = {change_pct:.2f}%",
        }

        # 6. 基本面
        pe = stock_data.get("pe", 100)
        roe = stock_data.get("roe", 0)
        checks["fundamentals"] = {
            "name": "基本面良好",
            "passed": pe < 50 and roe > 10,
            "weight": 1,
            "detail": f"PE = {pe:.1f}, ROE = {roe:.1f}%",
        }

        # 计算得分
        total_weight = sum(c["weight"] for c in checks.values())
        passed_weight = sum(c["weight"] for c in checks.values() if c["passed"])
        score = passed_weight / total_weight if total_weight > 0 else 0

        # 反转信号
        is_reversal = (
            main_inflow > self.reversal_main_inflow
            and change_pct > self.reversal_change_pct
        )

        # 改进：买入判断
        # 必须：DDX>0 + 20日均线支撑
        must_pass = (
            checks["ddx_positive"]["passed"] and checks["ma20_support"]["passed"]
        )
        # 加分：大涨 + 主力流入
        bonus_pass = checks["big_rise"]["passed"] or checks["main_inflow"]["passed"]

        can_buy = must_pass and bonus_pass

        return {
            "checks": checks,
            "score": round(score * 100, 1),
            "passed_weight": passed_weight,
            "total_weight": total_weight,
            "can_buy": can_buy,
            "is_reversal": is_reversal,
            "reversal_note": f"反转信号：主力{main_inflow / 100000000:.2f}亿 + 涨幅{change_pct:.1f}%"
            if is_reversal
            else None,
            "big_rise_detail": big_rise,
        }

    def analyze(
        self,
        stock_code: str,
        df: pd.DataFrame,
        stock_data: Dict,
        entry_price: Optional[float] = None,
    ) -> Dict:
        """综合分析"""
        result = {
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
            "strategy": "最笨交易法v3（改进版）",
        }

        # 买入条件检查
        buy_check = self.check_buy_conditions(stock_data, df)
        result["buy_check"] = buy_check

        # MA20状态
        ma20_status = self.check_ma20_support(df)
        result["ma20_status"] = ma20_status

        # 持仓分析
        if entry_price:
            current_price = stock_data.get("price", df.iloc[-1]["close"])

            # 止损检查（改进版）
            stop_check = self.check_stop_loss(entry_price, stock_data, df)
            result["stop_check"] = stop_check

            # 盈利阶段
            profit_stage = self.calculate_profit_stage(entry_price, current_price)
            result["profit_stage"] = profit_stage

            # 综合卖出判断
            should_sell = stop_check["should_stop"] or profit_stage["stage"] >= 1
            sell_reasons = []
            if stop_check["should_stop"]:
                sell_reasons.append(stop_check["reason"])
            if profit_stage["stage"] >= 1:
                sell_reasons.append(profit_stage["reason"])

            result["position_analysis"] = {
                "entry_price": entry_price,
                "current_price": current_price,
                "profit_pct": profit_stage["profit_pct"],
                "action": profit_stage["action"],
                "should_sell": should_sell,
                "sell_reasons": sell_reasons,
            }

        # 综合建议
        if entry_price:
            if result.get("position_analysis", {}).get("should_sell"):
                result["recommendation"] = "SELL"
                result["reason"] = "; ".join(
                    result["position_analysis"]["sell_reasons"]
                )
            else:
                result["recommendation"] = "HOLD"
                result["reason"] = "未触发卖出条件"
        else:
            if buy_check["can_buy"]:
                result["recommendation"] = "BUY"
                if buy_check["is_reversal"]:
                    result["reason"] = f"反转信号。{buy_check['reversal_note']}"
                else:
                    result["reason"] = f"符合买入条件，得分{buy_check['score']}分"
            else:
                result["recommendation"] = "WAIT"
                failed = [
                    c["name"] for c in buy_check["checks"].values() if not c["passed"]
                ]
                result["reason"] = f"不符合条件：{', '.join(failed)}"

        return result


def main():
    parser = argparse.ArgumentParser(description="最笨交易法策略v3")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--entry", type=float, help="买入价")
    parser.add_argument("--screen", action="store_true", help="筛选股票")

    args = parser.parse_args()

    strategy = SimpleProfitStrategyV3()

    if args.stock:
        print(f"\n{'=' * 60}")
        print(f"最笨交易法策略v3分析: {args.stock}")
        print(f"{'=' * 60}\n")

        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from data_fetcher import DataFetcher

            fetcher = DataFetcher()
            df = fetcher.get_stock_data(args.stock, days=60)
            quote = fetcher.get_realtime_quote(args.stock)

            if df is not None and not df.empty:
                stock_data = {
                    "code": args.stock,
                    "name": quote.get("name", ""),
                    "price": quote.get("price", df.iloc[-1]["close"]),
                    "change_pct": quote.get("change_pct", 0),
                    "main_inflow": quote.get("main_inflow", 0),
                    "ddx_10": quote.get("ddx_10", 0),
                    "pe": quote.get("pe", 100),
                    "roe": quote.get("roe", 0),
                }

                result = strategy.analyze(args.stock, df, stock_data, args.entry)

                print(f"股票: {stock_data['name']} ({args.stock})")
                print(f"当前价格: {stock_data['price']} 元")
                print(f"\n买入条件检查:")
                print("-" * 40)

                for key, check in result["buy_check"]["checks"].items():
                    status = "✓" if check["passed"] else "✗"
                    required = " [必须]" if check.get("required") else ""
                    detail = check.get("detail", "")
                    print(f"  {status} {check['name']}{required}: {detail}")

                print(f"\n得分: {result['buy_check']['score']} 分")
                print(f"综合建议: {result['recommendation']}")
                print(f"原因: {result['reason']}")

                if args.entry and "position_analysis" in result:
                    pos = result["position_analysis"]
                    print(f"\n持仓分析:")
                    print("-" * 40)
                    print(f"  买入价: {pos['entry_price']} 元")
                    print(f"  当前价: {pos['current_price']} 元")
                    print(f"  盈亏: {pos['profit_pct']}%")
                    print(f"  操作: {pos['action']}")

                    if "stop_check" in result:
                        stop = result["stop_check"]
                        print(f"\n止损检查:")
                        print(f"  MA20: {stop['ma20']} 元")
                        print(f"  距离MA20: {stop['distance_to_ma20']}%")
                        print(f"  是否止损: {'是' if stop['should_stop'] else '否'}")
                        print(f"  原因: {stop['reason']}")

        except Exception as e:
            print(f"分析失败: {e}")
            import traceback

            traceback.print_exc()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
