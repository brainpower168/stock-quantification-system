#!/usr/bin/env python3
"""
策略整合器 v2.0
整合海龟法则v2、多Agent辩论v2、反转信号检测、买入纪律检查
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategies"))

# 优先使用v2版本
try:
    from strategies.turtle_strategy_v2 import TurtleStrategyV2 as TurtleStrategy
    from strategies.council_debate_v2 import DebateOrchestratorV2 as DebateOrchestrator
except ImportError:
    from strategies.turtle_strategy import TurtleStrategy
    from strategies.council_debate import DebateOrchestrator

from data_fetcher import DataFetcher

# 舆情分析
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sentiment"))
    from sentiment.sentiment_analyzer import SentimentAnalyzer

    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False


class StrategyIntegrator:
    """策略整合器 v2.0"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.turtle = TurtleStrategy()
        self.debater = DebateOrchestrator()

        # 舆情分析器
        if SENTIMENT_AVAILABLE:
            tavily_key = os.environ.get(
                "TAVILY_API_KEY",
                "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",
            )
            longcat_key = os.environ.get(
                "LONGCAT_API_KEY", "ak_2hA4hD5K28mC0Vd6PL1mu1qk3dX6r"
            )
            miao_key = os.environ.get(
                "MX_APIKEY", "mkt_TWs49QJsDQJn-tVRHqPwmdWmTFO5_vqSpwUPfN-Ti6M"
            )
            self.sentiment = SentimentAnalyzer(tavily_key, longcat_key, miao_key)
        else:
            self.sentiment = None

    def analyze_stock(
        self, stock_code: str, account_value: float = 100000, real_data: Dict = None
    ) -> Dict:
        """
        综合分析股票

        Args:
            stock_code: 股票代码
            account_value: 账户价值
            real_data: 实盘数据（可选，优先使用）

        Returns:
            综合分析结果
        """
        print(f"\n{'=' * 60}")
        print(f"综合分析: {stock_code}")
        print(f"{'=' * 60}\n")

        # 使用实盘数据或获取数据
        if real_data:
            df = real_data.get("df")
            quote = real_data.get("quote", {})
        else:
            df = self.fetcher.get_stock_data(stock_code, days=100)
            quote = self.fetcher.get_realtime_quote(stock_code)

        # 构建stock_data字典（用于反转信号检测）
        stock_data = {
            "main_inflow": quote.get("main_inflow", 0),
            "change_pct": quote.get("change_pct", 0),
            "ddx_10": quote.get("ddx_10", 0),
            "ddx_5": quote.get("ddx_5", 0),
            "ddx_3": quote.get("ddx_3", 0),
            "pe": quote.get("pe", 100),
            "roe": quote.get("roe", 0),
            "profit_growth": quote.get("profit_growth", 0),
        }

        # 1. 海龟法则分析
        print("【海龟法则分析】")
        turtle_result = self.turtle.analyze(df, stock_data, account_value)

        print(f"  信号: {turtle_result['signal']}")
        print(f"  趋势: {turtle_result['trend']}")
        print(f"  建议仓位: {turtle_result['position_size']} 股")
        print(f"  止损价: {turtle_result['stop_loss']} 元")
        print(f"  止盈价: {turtle_result['take_profit']} 元")

        # 2. 多Agent辩论
        print("\n【多Agent辩论】")
        debate_result = self.debater.run_debate(quote, rounds=2)

        print(f"  共识: {debate_result.consensus.value}")
        print(f"  置信度: {debate_result.confidence * 100:.0f}%")

        # 3. 综合决策（加入DDX权重）
        print("\n【综合决策】")

        # DDX决策（最重要）
        ddx_10 = quote.get("ddx_10", 0)
        ddx_5 = quote.get("ddx_5", 0)
        ddx_3 = quote.get("ddx_3", 0)
        main_inflow = quote.get("main_inflow", 0)

        # DDX评分
        ddx_score = 0
        if ddx_10 > 0:
            ddx_score += 0.4  # 10日DDX权重40%
        if ddx_5 > 0:
            ddx_score += 0.3  # 5日DDX权重30%
        if ddx_3 > 0:
            ddx_score += 0.2  # 3日DDX权重20%
        if main_inflow > 0:
            ddx_score += 0.1  # 今日主力流入权重10%

        # 反转信号检测（重要！）
        # 条件：单日主力流入>10亿 + 涨幅>3% + 10日DDX<0
        reversal_signal = False
        reversal_reason = ""
        change_pct = quote.get("change_pct", 0)

        if main_inflow > 1000000000 and change_pct > 3 and ddx_10 < 0:
            reversal_signal = True
            reversal_reason = f"反转信号：主力流入{main_inflow / 100000000:.1f}亿 + 涨幅{change_pct:.1f}% + 10日DDX={ddx_10:.3f}"
            print(f"\n【反转信号】⚠️")
            print(f"  {reversal_reason}")
            print(f"  建议：次日观察主力流向，继续流入则确认反转，转为流出则诱多")

        # 权重分配
        ddx_weight = 0.5  # DDX最重要
        turtle_weight = 0.2  # 海龟法则
        debate_weight = 0.3  # 多Agent辩论

        # 信号转换
        signal_map = {"BUY": 1, "HOLD": 0, "SELL": -1}

        stance_map = {"看多": 1, "中性": 0, "看空": -1}

        turtle_score = signal_map.get(turtle_result["signal"], 0) * turtle_result.get(
            "confidence", 0.5
        )
        debate_score = (
            stance_map.get(debate_result.consensus.value, 0) * debate_result.confidence
        )

        # 综合得分
        final_score = (
            ddx_score * ddx_weight
            + turtle_score * turtle_weight
            + debate_score * debate_weight
        )

        # 最终决策
        if final_score > 0.3:
            final_decision = "BUY"
            action = "建议买入"
        elif final_score < -0.3:
            final_decision = "SELL"
            action = "建议卖出"
        else:
            final_decision = "HOLD"
            action = "建议持有"

        print(f"  DDX得分: {ddx_score:.2f} (10日={ddx_10}, 5日={ddx_5}, 3日={ddx_3})")
        print(f"  海龟得分: {turtle_score:.2f}")
        print(f"  辩论得分: {debate_score:.2f}")
        print(f"  综合得分: {final_score:.2f}")
        print(f"  最终决策: {final_decision} ({action})")

        # 4. 风险提示
        risks = turtle_result.get("risks", [])
        if debate_result.consensus.value == "看空":
            risks.append("多Agent辩论看空")

        # 【新增】舆情分析
        sentiment_result = None
        if self.sentiment:
            print("\n【舆情分析】")
            try:
                sentiment_report = self.sentiment.analyze_stock(
                    stock_code, quote.get("name", stock_code), days=7
                )
                sentiment_result = {
                    "overall_sentiment": sentiment_report.overall_sentiment,
                    "sentiment_level": sentiment_report.sentiment_level.value,
                    "news_count": sentiment_report.news_count,
                    "positive_count": sentiment_report.positive_count,
                    "negative_count": sentiment_report.negative_count,
                    "key_topics": sentiment_report.key_topics[:3],
                    "risk_warnings": sentiment_report.risk_warnings[:3],
                    "opportunities": sentiment_report.opportunities[:3],
                }

                print(f"  舆情评分: {sentiment_report.overall_sentiment:.1f}")
                print(f"  情感等级: {sentiment_report.sentiment_level.value}")
                print(
                    f"  新闻数量: {sentiment_report.news_count} (正面{sentiment_report.positive_count}/负面{sentiment_report.negative_count})"
                )

                # 添加舆情风险
                if sentiment_report.overall_sentiment < -5:
                    risks.append(
                        f"舆情极度看空（评分{sentiment_report.overall_sentiment:.1f}）"
                    )
                elif sentiment_report.overall_sentiment < -3:
                    risks.append(
                        f"舆情偏空（评分{sentiment_report.overall_sentiment:.1f}）"
                    )

                # 添加舆情风险预警
                risks.extend(sentiment_report.risk_warnings[:2])

            except Exception as e:
                print(f"  舆情分析失败: {e}")

        if risks:
            print("\n【风险提示】")
            for risk in risks:
                print(f"  ⚠ {risk}")

        # 5. 操作建议
        print("\n【操作建议】")
        if final_decision == "BUY":
            print(f"  买入价: {turtle_result['current_price']} 元")
            print(f"  仓位: {turtle_result['position_size']} 股")
            print(f"  止损: {turtle_result['stop_loss']} 元")
            print(f"  止盈: {turtle_result['take_profit']} 元")
        elif final_decision == "SELL":
            print(f"  建议卖出，控制风险")
        else:
            print(f"  暂时观望，等待明确信号")

        return {
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
            "ddx": {
                "ddx_10": ddx_10,
                "ddx_5": ddx_5,
                "ddx_3": ddx_3,
                "main_inflow": main_inflow,
                "ddx_score": ddx_score,
            },
            "reversal_signal": reversal_signal,
            "reversal_reason": reversal_reason,
            "turtle": turtle_result,
            "debate": {
                "consensus": debate_result.consensus.value,
                "confidence": debate_result.confidence,
                "bull_args": debate_result.bull_arguments,
                "bear_args": debate_result.bear_arguments,
            },
            "final_decision": final_decision,
            "final_score": final_score,
            "risks": risks,
        }

    def batch_analyze(
        self, stock_codes: List[str], account_value: float = 100000
    ) -> List[Dict]:
        """
        批量分析股票

        Args:
            stock_codes: 股票代码列表
            account_value: 账户价值

        Returns:
            分析结果列表
        """
        results = []

        for code in stock_codes:
            try:
                result = self.analyze_stock(code, account_value)
                results.append(result)
            except Exception as e:
                print(f"分析 {code} 失败: {e}")

        return results

    def generate_report(self, results: List[Dict], output_path: str = None) -> str:
        """
        生成分析报告

        Args:
            results: 分析结果列表
            output_path: 输出路径

        Returns:
            报告内容
        """
        report = f"# 策略分析报告\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 汇总
        buy_stocks = [r for r in results if r["final_decision"] == "BUY"]
        sell_stocks = [r for r in results if r["final_decision"] == "SELL"]
        hold_stocks = [r for r in results if r["final_decision"] == "HOLD"]

        report += f"## 汇总\n\n"
        report += f"- 建议买入: {len(buy_stocks)} 只\n"
        report += f"- 建议持有: {len(hold_stocks)} 只\n"
        report += f"- 建议卖出: {len(sell_stocks)} 只\n\n"

        # 详细分析
        for result in results:
            report += f"## {result['stock_code']}\n\n"
            report += f"**决策**: {result['final_decision']}\n\n"
            report += f"**得分**: {result['final_score']:.2f}\n\n"

            report += f"### 海龟法则\n"
            report += f"- 信号: {result['turtle']['signal']}\n"
            report += f"- 趋势: {result['turtle']['trend']}\n"
            report += f"- 止损: {result['turtle']['stop_loss']} 元\n"
            report += f"- 止盈: {result['turtle']['take_profit']} 元\n\n"

            report += f"### 多Agent辩论\n"
            report += f"- 共识: {result['debate']['consensus']}\n"
            report += f"- 置信度: {result['debate']['confidence'] * 100:.0f}%\n\n"

            if result["risks"]:
                report += f"### 风险提示\n"
                for risk in result["risks"]:
                    report += f"- {risk}\n"
                report += "\n"

        # 保存报告
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n报告已保存: {output_path}")

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="策略整合器")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--stocks", type=str, help="多个股票代码（逗号分隔）")
    parser.add_argument("--capital", type=float, default=100000, help="账户资金")
    parser.add_argument("--output", type=str, help="报告输出路径")

    args = parser.parse_args()

    integrator = StrategyIntegrator()

    if args.stock:
        result = integrator.analyze_stock(args.stock, args.capital)

        if args.output:
            integrator.generate_report([result], args.output)

    elif args.stocks:
        stocks = args.stocks.split(",")
        results = integrator.batch_analyze(stocks, args.capital)

        if args.output:
            integrator.generate_report(results, args.output)

    else:
        # 默认分析自选股
        default_stocks = ["600519", "000001", "300750"]
        print(f"分析默认股票: {', '.join(default_stocks)}")
        results = integrator.batch_analyze(default_stocks, args.capital)

        if args.output:
            integrator.generate_report(results, args.output)


if __name__ == "__main__":
    main()
