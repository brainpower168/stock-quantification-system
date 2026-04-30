#!/usr/bin/env python3
"""
智能选股引擎 v2.0
整合舆情评分到选股流程
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入舆情分析器
try:
    from stock_sentiment_analyzer import StockSentimentAnalyzer

    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    logging.warning("舆情分析器未安装，将跳过舆情评分")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SmartStockSelector:
    """智能选股引擎"""

    # 选股条件配置
    DEFAULT_CONFIG = {
        # 基础筛选条件
        "filters": {
            "change_pct_min": 0,  # 涨幅最小值
            "change_pct_max": 5,  # 涨幅最大值（从3%放宽到5%）
            "capital_flow_min": 3000,  # 主力流入最小值（万元）
            "ddx_10d_min": 0,  # 10日DDX最小值
            "ddx_5d_min": 0,  # 5日DDX最小值（加分项）
            "pe_max": 50,  # 市盈率最大值
            "roe_min": 10,  # ROE最小值
        },
        # 评分权重
        "weights": {
            "capital_flow": 0.25,  # 资金流向权重
            "ddx": 0.25,  # DDX权重
            "sentiment": 0.20,  # 舆情评分权重
            "technical": 0.15,  # 技术指标权重
            "fundamental": 0.15,  # 基本面权重
        },
        # 分级推荐阈值
        "grade_thresholds": {
            "A": {"min_score": 70, "change_max": 3},  # A级：强烈推荐
            "B": {"min_score": 60, "change_max": 5},  # B级：可以关注
            "C": {"min_score": 50, "change_max": 7},  # C级：追高需谨慎
        },
        # 舆情评分阈值
        "sentiment_thresholds": {
            "high_risk": 30,  # 高风险阈值
            "medium_risk": 50,  # 中风险阈值
        },
    }

    def __init__(self, config: Dict = None):
        """初始化选股引擎"""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.sentiment_analyzer = None

        if SENTIMENT_AVAILABLE:
            self.sentiment_analyzer = StockSentimentAnalyzer()
            logger.info("舆情分析器已加载")
        else:
            logger.warning("舆情分析器未加载，舆情评分将为默认值50")

    def fetch_stock_data(self, stock_code: str) -> Dict:
        """获取股票数据（从妙想/问财API）"""
        # 这里需要调用实际的数据获取API
        # 暂时返回模拟数据结构
        return {
            "code": stock_code,
            "name": "",
            "price": 0,
            "change_pct": 0,
            "capital_flow": 0,
            "ddx_1d": 0,
            "ddx_5d": 0,
            "ddx_10d": 0,
            "pe": 0,
            "roe": 0,
            "kdj": 50,
            "rsi": 50,
        }

    def calculate_sentiment_score(
        self, stock_code: str, stock_name: str = None
    ) -> Dict:
        """计算舆情评分"""
        if not self.sentiment_analyzer:
            return {
                "score": 50,
                "sentiment": "neutral",
                "risk_level": "unknown",
                "news_count": 0,
                "alerts": [],
            }

        try:
            report = self.sentiment_analyzer.analyze(stock_code, stock_name, days=7)
            return {
                "score": report.get("sentiment_score", 50),
                "sentiment": report.get("sentiment", "neutral"),
                "risk_level": report.get("risk_level", {}).get("level", "unknown"),
                "news_count": report.get("news_count", 0),
                "alerts": report.get("alerts", []),
                "positives": report.get("positives", []),
            }
        except Exception as e:
            logger.error(f"舆情分析失败 {stock_code}: {e}")
            return {
                "score": 50,
                "sentiment": "neutral",
                "risk_level": "unknown",
                "news_count": 0,
                "alerts": [],
            }

    def calculate_capital_score(self, stock_data: Dict) -> Dict:
        """计算资金流向评分"""
        score = 0
        reasons = []
        warnings = []

        capital_flow = stock_data.get("capital_flow", 0)  # 万元
        ddx_1d = stock_data.get("ddx_1d", 0)
        ddx_5d = stock_data.get("ddx_5d", 0)
        ddx_10d = stock_data.get("ddx_10d", 0)

        # 主力流入评分
        if capital_flow > 10000:  # >1亿
            score += 30
            reasons.append(f"主力大额流入：{capital_flow / 10000:.1f}亿")
        elif capital_flow > 5000:  # >5000万
            score += 20
            reasons.append(f"主力流入：{capital_flow / 10000:.1f}亿")
        elif capital_flow > 1000:  # >1000万
            score += 10
            reasons.append(f"主力小幅流入：{capital_flow / 10000:.1f}亿")
        elif capital_flow < -5000:  # <-5000万
            score -= 20
            warnings.append(f"主力流出：{abs(capital_flow) / 10000:.1f}亿")

        # DDX评分
        if ddx_10d > 2:
            score += 25
            reasons.append(f"10日DDX强势：{ddx_10d:.2f}")
        elif ddx_10d > 0:
            score += 15
            reasons.append(f"10日DDX转正：{ddx_10d:.2f}")
        elif ddx_10d < -1:
            score -= 15
            warnings.append(f"10日DDX弱势：{ddx_10d:.2f}")

        # 5日DDX加分
        if ddx_5d > 0:
            score += 10
            reasons.append(f"5日DDX向上：{ddx_5d:.2f}")

        # 当日DDX
        if ddx_1d > 0:
            score += 5
            reasons.append(f"当日DDX正：{ddx_1d:.2f}")

        return {
            "score": max(0, min(100, score)),
            "reasons": reasons,
            "warnings": warnings,
        }

    def calculate_technical_score(self, stock_data: Dict) -> Dict:
        """计算技术指标评分"""
        score = 50
        reasons = []
        warnings = []

        kdj = stock_data.get("kdj", 50)
        rsi = stock_data.get("rsi", 50)
        change_pct = stock_data.get("change_pct", 0)

        # KDJ
        if kdj < 20:
            score += 15
            reasons.append(f"KDJ超卖：{kdj:.1f}")
        elif kdj > 80:
            score -= 15
            warnings.append(f"KDJ超买：{kdj:.1f}")

        # RSI
        if rsi < 30:
            score += 10
            reasons.append(f"RSI超卖：{rsi:.1f}")
        elif rsi > 70:
            score -= 10
            warnings.append(f"RSI超买：{rsi:.1f}")

        # 涨幅
        if 0 < change_pct < 3:
            score += 10
            reasons.append(f"涨幅适中：{change_pct:.2f}%")
        elif 3 <= change_pct < 5:
            score += 5
            reasons.append(f"涨幅偏高：{change_pct:.2f}%")
        elif change_pct > 7:
            score -= 10
            warnings.append(f"涨幅过大：{change_pct:.2f}%")

        return {
            "score": max(0, min(100, score)),
            "reasons": reasons,
            "warnings": warnings,
        }

    def calculate_fundamental_score(self, stock_data: Dict) -> Dict:
        """计算基本面评分"""
        score = 50
        reasons = []
        warnings = []

        pe = stock_data.get("pe", 0)
        roe = stock_data.get("roe", 0)

        # PE
        if 0 < pe < 20:
            score += 15
            reasons.append(f"估值偏低：PE={pe:.1f}")
        elif 20 <= pe < 50:
            score += 5
        elif pe > 100:
            score -= 10
            warnings.append(f"估值偏高：PE={pe:.1f}")

        # ROE
        if roe > 20:
            score += 20
            reasons.append(f"盈利能力强：ROE={roe:.1f}%")
        elif roe > 10:
            score += 10
            reasons.append(f"盈利能力良好：ROE={roe:.1f}%")
        elif roe < 5:
            score -= 10
            warnings.append(f"盈利能力弱：ROE={roe:.1f}%")

        return {
            "score": max(0, min(100, score)),
            "reasons": reasons,
            "warnings": warnings,
        }

    def calculate_total_score(self, stock_data: Dict, sentiment_data: Dict) -> Dict:
        """计算综合评分"""
        weights = self.config["weights"]

        # 各维度评分
        capital = self.calculate_capital_score(stock_data)
        technical = self.calculate_technical_score(stock_data)
        fundamental = self.calculate_fundamental_score(stock_data)
        sentiment_score = sentiment_data.get("score", 50)

        # 加权总分
        total_score = (
            capital["score"] * weights["capital_flow"]
            + stock_data.get("ddx_10d", 0) * 10 * weights["ddx"]  # DDX单独计算
            + sentiment_score * weights["sentiment"]
            + technical["score"] * weights["technical"]
            + fundamental["score"] * weights["fundamental"]
        )

        # 合并原因和警告
        all_reasons = capital["reasons"] + technical["reasons"] + fundamental["reasons"]
        all_warnings = (
            capital["warnings"] + technical["warnings"] + fundamental["warnings"]
        )

        # 添加舆情信息
        if sentiment_data.get("alerts"):
            all_warnings.extend(
                [a.get("title", "") for a in sentiment_data["alerts"][:3]]
            )
        if sentiment_data.get("positives"):
            all_reasons.extend(
                [p.get("title", "") for p in sentiment_data["positives"][:3]]
            )

        return {
            "total_score": round(total_score, 1),
            "capital_score": capital["score"],
            "technical_score": technical["score"],
            "fundamental_score": fundamental["score"],
            "sentiment_score": sentiment_score,
            "reasons": all_reasons,
            "warnings": all_warnings,
        }

    def get_grade(self, total_score: float, change_pct: float) -> str:
        """获取推荐等级"""
        thresholds = self.config["grade_thresholds"]

        if (
            total_score >= thresholds["A"]["min_score"]
            and change_pct <= thresholds["A"]["change_max"]
        ):
            return "A"  # 强烈推荐
        elif (
            total_score >= thresholds["B"]["min_score"]
            and change_pct <= thresholds["B"]["change_max"]
        ):
            return "B"  # 可以关注
        elif (
            total_score >= thresholds["C"]["min_score"]
            and change_pct <= thresholds["C"]["change_max"]
        ):
            return "C"  # 追高需谨慎
        else:
            return "D"  # 不推荐

    def analyze_stock(self, stock_code: str, stock_name: str = None) -> Dict:
        """分析单只股票"""
        logger.info(f"分析股票: {stock_code}")

        # 获取股票数据
        stock_data = self.fetch_stock_data(stock_code)
        if stock_name:
            stock_data["name"] = stock_name

        # 获取舆情评分
        sentiment_data = self.calculate_sentiment_score(stock_code, stock_name)

        # 计算综合评分
        score_result = self.calculate_total_score(stock_data, sentiment_data)

        # 获取推荐等级
        grade = self.get_grade(
            score_result["total_score"], stock_data.get("change_pct", 0)
        )

        return {
            "code": stock_code,
            "name": stock_data.get("name", stock_code),
            "price": stock_data.get("price", 0),
            "change_pct": stock_data.get("change_pct", 0),
            "capital_flow": stock_data.get("capital_flow", 0),
            "ddx_10d": stock_data.get("ddx_10d", 0),
            "grade": grade,
            **score_result,
            "sentiment_data": sentiment_data,
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def screen_stocks(self, stock_list: List[str], top_n: int = 10) -> List[Dict]:
        """批量筛选股票"""
        logger.info(f"开始筛选 {len(stock_list)} 只股票...")

        results = []

        # 并行分析
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.analyze_stock, code): code for code in stock_list
            }

            for future in as_completed(futures):
                code = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(
                        f"  {result['name']}({code}): 得分{result['total_score']}, 等级{result['grade']}"
                    )
                except Exception as e:
                    logger.error(f"  {code}: 分析失败 - {e}")

        # 按综合评分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # 分级展示
        graded_results = {"A": [], "B": [], "C": [], "D": []}
        for r in results:
            graded_results[r["grade"]].append(r)

        logger.info(
            f"筛选完成: A级{len(graded_results['A'])}只, B级{len(graded_results['B'])}只"
        )

        return results[:top_n], graded_results

    def generate_report(self, results: List[Dict], graded: Dict) -> str:
        """生成选股报告"""
        lines = [
            "# 智能选股报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]

        # A级推荐
        if graded.get("A"):
            lines.append("## A级推荐（强烈推荐）")
            lines.append("")
            lines.append("| 股票 | 现价 | 涨幅 | 主力流入 | 综合得分 | 舆情评分 |")
            lines.append("|------|------|------|----------|----------|----------|")
            for r in graded["A"]:
                lines.append(
                    f"| {r['name']}({r['code']}) | {r['price']:.2f}元 | {r['change_pct']:.2f}% | "
                    f"{r['capital_flow'] / 10000:.1f}亿 | {r['total_score']:.1f} | {r['sentiment_score']} |"
                )
            lines.append("")

        # B级推荐
        if graded.get("B"):
            lines.append("## B级推荐（可以关注）")
            lines.append("")
            lines.append("| 股票 | 现价 | 涨幅 | 主力流入 | 综合得分 | 舆情评分 |")
            lines.append("|------|------|------|----------|----------|----------|")
            for r in graded["B"]:
                lines.append(
                    f"| {r['name']}({r['code']}) | {r['price']:.2f}元 | {r['change_pct']:.2f}% | "
                    f"{r['capital_flow'] / 10000:.1f}亿 | {r['total_score']:.1f} | {r['sentiment_score']} |"
                )
            lines.append("")

        # C级推荐
        if graded.get("C"):
            lines.append("## C级推荐（追高需谨慎）")
            lines.append("")
            lines.append("| 股票 | 现价 | 涨幅 | 主力流入 | 综合得分 | 舆情评分 |")
            lines.append("|------|------|------|----------|----------|----------|")
            for r in graded["C"]:
                lines.append(
                    f"| {r['name']}({r['code']}) | {r['price']:.2f}元 | {r['change_pct']:.2f}% | "
                    f"{r['capital_flow'] / 10000:.1f}亿 | {r['total_score']:.1f} | {r['sentiment_score']} |"
                )
            lines.append("")

        # 详细分析
        lines.append("---")
        lines.append("")
        lines.append("## 详细分析")
        lines.append("")

        for r in results[:5]:
            lines.append(f"### {r['name']}({r['code']})")
            lines.append("")
            lines.append(
                f"**综合得分**: {r['total_score']:.1f} | **等级**: {r['grade']}"
            )
            lines.append("")
            lines.append(f"| 维度 | 得分 |")
            lines.append(f"|------|------|")
            lines.append(f"| 资金流向 | {r['capital_score']:.1f} |")
            lines.append(f"| 技术指标 | {r['technical_score']:.1f} |")
            lines.append(f"| 基本面 | {r['fundamental_score']:.1f} |")
            lines.append(f"| 舆情评分 | {r['sentiment_score']} |")
            lines.append("")

            if r.get("reasons"):
                lines.append("**优势**:")
                for reason in r["reasons"][:5]:
                    lines.append(f"- {reason}")
                lines.append("")

            if r.get("warnings"):
                lines.append("**风险**:")
                for warning in r["warnings"][:5]:
                    lines.append(f"- {warning}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="智能选股引擎 v2.0")
    parser.add_argument("--stock", "-s", type=str, help="分析单只股票")
    parser.add_argument("--stocks", type=str, help="多个股票代码，逗号分隔")
    parser.add_argument("--top", "-t", type=int, default=10, help="显示前N只")
    parser.add_argument("--output", "-o", type=str, help="输出报告文件")

    args = parser.parse_args()

    selector = SmartStockSelector()

    if args.stock:
        result = selector.analyze_stock(args.stock)
        print(f"\n{'=' * 60}")
        print(f"股票: {result['name']}({result['code']})")
        print(f"综合得分: {result['total_score']:.1f} | 等级: {result['grade']}")
        print(f"舆情评分: {result['sentiment_score']}")
        print(f"价格: {result['price']:.2f}元 | 涨幅: {result['change_pct']:.2f}%")
        print(f"主力流入: {result['capital_flow'] / 10000:.1f}亿")
        print(f"{'=' * 60}")

        if result.get("reasons"):
            print("\n优势:")
            for r in result["reasons"]:
                print(f"  + {r}")

        if result.get("warnings"):
            print("\n风险:")
            for w in result["warnings"]:
                print(f"  - {w}")

    elif args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(",")]
        results, graded = selector.screen_stocks(stock_list, args.top)

        print(f"\n{'=' * 60}")
        print(f"筛选完成: 共{len(results)}只股票")
        print(f"  A级（强烈推荐）: {len(graded['A'])}只")
        print(f"  B级（可以关注）: {len(graded['B'])}只")
        print(f"  C级（追高需谨慎）: {len(graded['C'])}只")
        print(f"{'=' * 60}")

        # 生成报告
        report = selector.generate_report(results, graded)
        print("\n" + report)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"报告已保存到 {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
