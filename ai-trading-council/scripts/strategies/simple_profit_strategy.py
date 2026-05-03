#!/usr/bin/env python3
"""
最笨交易法策略（Simple Profit Strategy）
=========================================
来源：抖音"熊猫有财"视频《小资金做大的秘密！最笨交易法》

核心逻辑：
1. 选股：10日内有涨停 + 月线MACD金叉 + 回踩20日均线
2. 买入：股价站上20日均线 + 量能放大
3. 卖出：涨幅30%减仓1/3，涨幅50%再减仓一半，跌破20日均线离场

融合现有策略：
- DDX资金流向（10日DDX > 0）
- 反转信号检测（单日主力>10亿 + 涨幅>3%）
- 买入纪律检查清单

使用方法：
    python simple_profit_strategy.py --stock 600519
    python simple_profit_strategy.py --screen  # 筛选符合条件的股票
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


class SimpleProfitStrategy:
    """最笨交易法策略"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略

        Args:
            config: 策略配置
        """
        self.config = config or {}

        # 策略参数
        self.ma_period = self.config.get("ma_period", 20)  # 20日均线
        self.zt_days = self.config.get("zt_days", 10)  # 涨停天数
        self.profit_take_1 = self.config.get("profit_take_1", 0.30)  # 第一次减仓30%
        self.profit_take_2 = self.config.get("profit_take_2", 0.50)  # 第二次减仓50%

        # DDX参数
        self.ddx_threshold = self.config.get("ddx_threshold", 0)  # 10日DDX阈值

        # 反转信号参数
        self.reversal_main_inflow = self.config.get(
            "reversal_main_inflow", 1000000000
        )  # 10亿
        self.reversal_change_pct = self.config.get("reversal_change_pct", 3.0)  # 3%

    def check_zt_in_days(self, df: pd.DataFrame, days: int = 10) -> bool:
        """
        检查最近N天内是否有涨停

        Args:
            df: K线数据
            days: 天数

        Returns:
            是否有涨停
        """
        if len(df) < days:
            return False

        recent = df.tail(days).copy()

        # 兼容不同的列名
        pct_col = None
        for col in ["pct_chg", "change", "pct_change", "涨跌幅"]:
            if col in recent.columns:
                pct_col = col
                break

        if pct_col is None:
            # 计算涨跌幅
            recent["pct_calc"] = (recent["close"].pct_change() * 100).fillna(0)
            pct_col = "pct_calc"

        # 涨停判断：涨幅 >= 9.9%（考虑四舍五入）
        zt_condition = recent[pct_col] >= 9.9
        return zt_condition.any()

    def check_monthly_macd_golden_cross(self, df_monthly: pd.DataFrame) -> bool:
        """
        检查月线MACD金叉

        Args:
            df_monthly: 月线数据

        Returns:
            是否金叉
        """
        if df_monthly is None or len(df_monthly) < 2:
            return False

        # 计算MACD
        close = df_monthly["close"]
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2

        # 金叉判断：DIF上穿DEA，且在零轴上方
        latest = len(df_monthly) - 1
        prev = latest - 1

        # 零轴上方金叉
        is_golden_cross = (
            dif.iloc[prev] < dea.iloc[prev]  # 前一日DIF < DEA
            and dif.iloc[latest] > dea.iloc[latest]  # 当日DIF > DEA
            and dif.iloc[latest] > 0  # DIF在零轴上方
        )

        return is_golden_cross

    def check_ma20_support(self, df: pd.DataFrame) -> Dict:
        """
        检查20日均线支撑

        Args:
            df: 日线数据

        Returns:
            支撑状态字典
        """
        if len(df) < self.ma_period:
            return {"valid": False, "reason": "数据不足"}

        # 计算20日均线
        df = df.copy()
        df["ma20"] = df["close"].rolling(window=self.ma_period).mean()

        latest = df.iloc[-1]
        close = latest["close"]
        ma20 = latest["ma20"]

        # 判断位置
        distance_pct = (close - ma20) / ma20 * 100

        # 回踩判断：股价在20日均线附近（±3%）
        is_near_ma20 = abs(distance_pct) <= 3

        # 站上判断：股价在20日均线上方
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

    def calculate_profit_stage(self, entry_price: float, current_price: float) -> Dict:
        """
        计算盈利阶段，决定卖出比例

        融合两种止盈策略：
        1. 最笨交易法：涨幅30%减仓1/3，涨幅50%再减仓一半
        2. 麻雀战法：盈利2.5%后，每涨1%卖10%仓位

        Args:
            entry_price: 买入价
            current_price: 当前价

        Returns:
            卖出建议字典
        """
        profit_pct = (current_price - entry_price) / entry_price

        # 麻雀战法模式二：分批止盈
        # 盈利2.5%开始，每涨1%卖10%
        if profit_pct >= 0.025:
            # 计算应该卖出的比例
            # 从2.5%开始，每涨1%卖10%
            additional_profit = (profit_pct - 0.025) / 0.01  # 超过2.5%的1%倍数
            sell_ratio = min(
                0.1 * additional_profit + 0.1, 1.0
            )  # 初始卖10%，之后每1%加10%

            return {
                "stage": 1,
                "profit_pct": round(profit_pct * 100, 2),
                "action": f"分批止盈，已卖{sell_ratio * 100:.0f}%",
                "sell_ratio": round(sell_ratio, 2),
                "reason": f"麻雀战法：盈利{profit_pct * 100:.1f}%，分批止盈",
                "method": "麻雀战法",
            }

        # 最笨交易法：大涨幅分批卖出
        if profit_pct >= self.profit_take_2:  # 50%
            return {
                "stage": 3,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "全部清仓",
                "sell_ratio": 1.0,
                "reason": f"最笨交易法：涨幅{profit_pct * 100:.1f}%，超过50%，全部离场",
                "method": "最笨交易法",
            }
        elif profit_pct >= self.profit_take_1:  # 30%
            return {
                "stage": 2,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "减仓一半",
                "sell_ratio": 0.5,
                "reason": f"最笨交易法：涨幅{profit_pct * 100:.1f}%，超过30%，减仓一半",
                "method": "最笨交易法",
            }
        else:
            return {
                "stage": 0,
                "profit_pct": round(profit_pct * 100, 2),
                "action": "持有",
                "sell_ratio": 0,
                "reason": f"涨幅{profit_pct * 100:.1f}%，未达止盈条件",
                "method": "持有",
            }

    def calculate_sparrow_profit(
        self, entry_price: float, current_price: float
    ) -> Dict:
        """
        麻雀战法三种模式止盈计算

        模式一：到点必走 - 次日成本价+2.5%卖出
        模式二：分批止盈 - 盈利2.5%后每涨1%卖10%
        模式三：趋势持有 - 利润回撤2.5%清仓

        Args:
            entry_price: 买入价
            current_price: 当前价

        Returns:
            三种模式的止盈建议
        """
        profit_pct = (current_price - entry_price) / entry_price

        # 模式一：到点必走
        mode1 = {
            "name": "到点必走",
            "target_profit": 2.5,
            "current_profit": round(profit_pct * 100, 2),
            "should_sell": profit_pct >= 0.025,
            "action": "卖出" if profit_pct >= 0.025 else "等待",
            "reason": f"目标+2.5%，当前{profit_pct * 100:.1f}%",
        }

        # 模式二：分批止盈
        if profit_pct >= 0.025:
            additional_profit = (profit_pct - 0.025) / 0.01
            sell_ratio = min(0.1 * additional_profit + 0.1, 1.0)
        else:
            sell_ratio = 0

        mode2 = {
            "name": "分批止盈",
            "current_profit": round(profit_pct * 100, 2),
            "sell_ratio": round(sell_ratio, 2),
            "action": f"卖出{sell_ratio * 100:.0f}%" if sell_ratio > 0 else "持有",
            "reason": f"盈利{profit_pct * 100:.1f}%，已卖{sell_ratio * 100:.0f}%",
        }

        # 模式三：趋势持有（需要历史最高价）
        mode3 = {
            "name": "趋势持有",
            "current_profit": round(profit_pct * 100, 2),
            "stop_profit": -2.5,  # 利润回撤2.5%清仓
            "action": "持有，利润回撤2.5%清仓",
            "reason": "趋势持有，持续创新高持有，走势疲软分批减仓",
        }

        return {
            "mode1_point_exit": mode1,
            "mode2_batch_profit": mode2,
            "mode3_trend_hold": mode3,
            "recommendation": "模式二（分批止盈）" if profit_pct >= 0.025 else "等待",
        }

    def check_buy_conditions(self, stock_data: Dict, df: pd.DataFrame) -> Dict:
        """
        检查买入条件

        Args:
            stock_data: 股票数据（包含DDX等）
            df: K线数据

        Returns:
            买入条件检查结果
        """
        checks = {}

        # 1. 10日内有涨停
        checks["zt_in_10d"] = {
            "name": "10日内涨停",
            "passed": self.check_zt_in_days(df, self.zt_days),
            "weight": 2,  # 重要条件，权重高
        }

        # 2. 20日均线支撑
        ma20_status = self.check_ma20_support(df)
        checks["ma20_support"] = {
            "name": "20日均线支撑",
            "passed": ma20_status["is_above_ma20"] or ma20_status["is_near_ma20"],
            "weight": 2,
            "detail": ma20_status,
        }

        # 3. DDX资金流向（融合现有策略）
        ddx_10 = stock_data.get("ddx_10", 0)
        checks["ddx_positive"] = {
            "name": "10日DDX > 0",
            "passed": ddx_10 > self.ddx_threshold,
            "weight": 2,
            "detail": f"10日DDX = {ddx_10:.3f}",
        }

        # 4. 主力资金流入
        main_inflow = stock_data.get("main_inflow", 0)
        checks["main_inflow"] = {
            "name": "主力资金流入",
            "passed": main_inflow > 0,
            "weight": 1,
            "detail": f"主力净流入 = {main_inflow / 100000000:.2f}亿",
        }

        # 5. 涨幅控制（不追高）
        change_pct = stock_data.get("change_pct", 0)
        checks["not_chasing_high"] = {
            "name": "涨幅 < 3%",
            "passed": abs(change_pct) < 3,
            "weight": 1,
            "detail": f"当日涨幅 = {change_pct:.2f}%",
        }

        # 6. 基本面（PE、ROE）
        pe = stock_data.get("pe", 100)
        roe = stock_data.get("roe", 0)
        checks["fundamentals"] = {
            "name": "基本面良好",
            "passed": pe < 50 and roe > 10,
            "weight": 1,
            "detail": f"PE = {pe:.1f}, ROE = {roe:.1f}%",
        }

        # 计算加权得分
        total_weight = sum(c["weight"] for c in checks.values())
        passed_weight = sum(c["weight"] for c in checks.values() if c["passed"])
        score = passed_weight / total_weight if total_weight > 0 else 0

        # 反转信号检测
        is_reversal = (
            main_inflow > self.reversal_main_inflow
            and change_pct > self.reversal_change_pct
        )

        # 判断是否可以买入
        # 必须条件：涨停 + 20日均线
        must_pass = checks["zt_in_10d"]["passed"] and checks["ma20_support"]["passed"]
        # 加分条件：DDX + 主力流入
        bonus_pass = checks["ddx_positive"]["passed"] or checks["main_inflow"]["passed"]

        can_buy = must_pass and (bonus_pass or is_reversal)

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
        }

    def check_sell_conditions(
        self, entry_price: float, stock_data: Dict, df: pd.DataFrame
    ) -> Dict:
        """
        检查卖出条件

        Args:
            entry_price: 买入价
            stock_data: 股票数据
            df: K线数据

        Returns:
            卖出条件检查结果
        """
        current_price = stock_data.get("price", df.iloc[-1]["close"])

        # 1. 盈利阶段
        profit_stage = self.calculate_profit_stage(entry_price, current_price)

        # 2. 跌破20日均线
        ma20_status = self.check_ma20_support(df)
        break_ma20 = not ma20_status["is_above_ma20"]

        # 3. 主力资金流出
        main_inflow = stock_data.get("main_inflow", 0)
        ddx_10 = stock_data.get("ddx_10", 0)
        capital_outflow = main_inflow < 0 and ddx_10 < 0

        # 综合判断
        should_sell = False
        sell_reason = []

        if profit_stage["stage"] >= 1:
            should_sell = True
            sell_reason.append(profit_stage["reason"])

        if break_ma20:
            should_sell = True
            sell_reason.append("跌破20日均线，立即离场")

        if capital_outflow:
            sell_reason.append("主力资金流出，注意风险")

        return {
            "current_price": current_price,
            "entry_price": entry_price,
            "profit_stage": profit_stage,
            "break_ma20": break_ma20,
            "capital_outflow": capital_outflow,
            "should_sell": should_sell,
            "sell_reason": sell_reason,
            "urgency": "高"
            if break_ma20
            else ("中" if profit_stage["stage"] >= 1 else "低"),
        }

    def analyze(
        self,
        stock_code: str,
        df: pd.DataFrame,
        stock_data: Dict,
        entry_price: Optional[float] = None,
    ) -> Dict:
        """
        综合分析股票

        Args:
            stock_code: 股票代码
            df: K线数据
            stock_data: 股票数据
            entry_price: 买入价（可选，用于持仓分析）

        Returns:
            分析结果
        """
        result = {
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
            "strategy": "最笨交易法 + 麻雀战法",
        }

        # 买入条件检查
        buy_check = self.check_buy_conditions(stock_data, df)
        result["buy_check"] = buy_check

        # 20日均线状态
        ma20_status = self.check_ma20_support(df)
        result["ma20_status"] = ma20_status

        # 如果有持仓，检查卖出条件
        if entry_price:
            current_price = stock_data.get("price", df.iloc[-1]["close"])

            # 卖出条件检查
            sell_check = self.check_sell_conditions(entry_price, stock_data, df)
            result["sell_check"] = sell_check

            # 麻雀战法三种模式
            sparrow_profit = self.calculate_sparrow_profit(entry_price, current_price)
            result["sparrow_profit"] = sparrow_profit

            result["position_analysis"] = {
                "entry_price": entry_price,
                "current_price": current_price,
                "profit_pct": sell_check["profit_stage"]["profit_pct"],
                "action": sell_check["profit_stage"]["action"],
                "method": sell_check["profit_stage"].get("method", ""),
                # 麻雀战法建议
                "sparrow_recommendation": sparrow_profit["recommendation"],
            }

        # 综合建议
        if entry_price:
            # 持仓分析
            if result.get("sell_check", {}).get("should_sell"):
                result["recommendation"] = "SELL"
                result["reason"] = "; ".join(result["sell_check"]["sell_reason"])
            else:
                result["recommendation"] = "HOLD"
                result["reason"] = "未触发卖出条件，继续持有"
        else:
            # 买入分析
            if buy_check["can_buy"]:
                result["recommendation"] = "BUY"
                if buy_check["is_reversal"]:
                    result["reason"] = (
                        f"反转信号，可考虑买入。{buy_check['reversal_note']}"
                    )
                else:
                    result["reason"] = f"符合买入条件，得分{buy_check['score']}分"
            else:
                result["recommendation"] = "WAIT"
                failed = [
                    c["name"] for c in buy_check["checks"].values() if not c["passed"]
                ]
                result["reason"] = f"不符合买入条件：{', '.join(failed)}"

        return result

    def screen_stocks(self, stock_list: List[str], data_fetcher) -> List[Dict]:
        """
        筛选符合条件的股票

        Args:
            stock_list: 股票代码列表
            data_fetcher: 数据获取器

        Returns:
            符合条件的股票列表
        """
        results = []

        for stock_code in stock_list:
            try:
                # 获取数据
                df = data_fetcher.get_stock_data(stock_code, days=60)
                quote = data_fetcher.get_realtime_quote(stock_code)

                if df is None or df.empty:
                    continue

                stock_data = {
                    "code": stock_code,
                    "name": quote.get("name", ""),
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change_pct", 0),
                    "main_inflow": quote.get("main_inflow", 0),
                    "ddx_10": quote.get("ddx_10", 0),
                    "pe": quote.get("pe", 100),
                    "roe": quote.get("roe", 0),
                }

                # 分析
                analysis = self.analyze(stock_code, df, stock_data)

                if analysis["recommendation"] == "BUY":
                    results.append(
                        {
                            "code": stock_code,
                            "name": stock_data["name"],
                            "price": stock_data["price"],
                            "change_pct": stock_data["change_pct"],
                            "score": analysis["buy_check"]["score"],
                            "is_reversal": analysis["buy_check"]["is_reversal"],
                            "reason": analysis["reason"],
                        }
                    )

            except Exception as e:
                print(f"分析 {stock_code} 失败: {e}")
                continue

        # 按得分排序
        results.sort(key=lambda x: x["score"], reverse=True)

        return results


def main():
    parser = argparse.ArgumentParser(description="最笨交易法策略")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--entry", type=float, help="买入价（用于持仓分析）")
    parser.add_argument("--screen", action="store_true", help="筛选股票")
    parser.add_argument("--capital", type=float, default=100000, help="账户资金")

    args = parser.parse_args()

    strategy = SimpleProfitStrategy()

    if args.stock:
        print(f"\n{'=' * 60}")
        print(f"最笨交易法策略分析: {args.stock}")
        print(f"{'=' * 60}\n")

        # 获取数据
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
                print(f"当日涨跌: {stock_data['change_pct']:.2f}%")
                print(f"\n买入条件检查:")
                print("-" * 40)

                for key, check in result["buy_check"]["checks"].items():
                    status = "✓" if check["passed"] else "✗"
                    detail = check.get("detail", "")
                    print(f"  {status} {check['name']}: {detail}")

                print(f"\n得分: {result['buy_check']['score']} 分")
                print(f"综合建议: {result['recommendation']}")
                print(f"原因: {result['reason']}")

                if args.entry:
                    print(f"\n持仓分析:")
                    print("-" * 40)
                    pos = result.get("position_analysis", {})
                    print(f"  买入价: {pos.get('entry_price')} 元")
                    print(f"  当前价: {pos.get('current_price')} 元")
                    print(f"  盈亏: {pos.get('profit_pct')}%")
                    print(f"  操作: {pos.get('action')}")
                    if pos.get("method"):
                        print(f"  方法: {pos.get('method')}")

                    # 麻雀战法三种模式
                    if "sparrow_profit" in result:
                        print(f"\n麻雀战法止盈建议:")
                        print("-" * 40)
                        sparrow = result["sparrow_profit"]

                        # 模式一
                        m1 = sparrow["mode1_point_exit"]
                        print(f"  模式一（到点必走）: {m1['action']} - {m1['reason']}")

                        # 模式二
                        m2 = sparrow["mode2_batch_profit"]
                        print(f"  模式二（分批止盈）: {m2['action']} - {m2['reason']}")

                        # 模式三
                        m3 = sparrow["mode3_trend_hold"]
                        print(f"  模式三（趋势持有）: {m3['action']}")

                        print(f"\n  推荐: {sparrow['recommendation']}")

        except Exception as e:
            print(f"分析失败: {e}")
            import traceback

            traceback.print_exc()

    elif args.screen:
        print(f"\n{'=' * 60}")
        print(f"最笨交易法策略筛选")
        print(f"{'=' * 60}\n")

        # 自选股列表
        watchlist = [
            "601138",  # 工业富联
            "002475",  # 立讯精密
            "002460",  # 赣锋锂业
            "002281",  # 光迅科技
            "002463",  # 沪电股份
            "300750",  # 宁德时代
            "300476",  # 胜宏科技
            "000988",  # 华工科技
        ]

        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from data_fetcher import DataFetcher

            fetcher = DataFetcher()
            results = strategy.screen_stocks(watchlist, fetcher)

            if results:
                print(f"筛选结果（共{len(results)}只）:\n")
                for i, r in enumerate(results, 1):
                    reversal_mark = " [反转信号]" if r["is_reversal"] else ""
                    print(f"{i}. {r['name']} ({r['code']})")
                    print(f"   价格: {r['price']} 元 | 涨跌: {r['change_pct']:.2f}%")
                    print(f"   得分: {r['score']} 分{reversal_mark}")
                    print(f"   原因: {r['reason']}")
                    print()
            else:
                print("没有找到符合条件的股票")

        except Exception as e:
            print(f"筛选失败: {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
