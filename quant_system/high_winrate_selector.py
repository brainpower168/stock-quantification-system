# -*- coding: utf-8 -*-
"""
高胜率选股模式 - 宁缺毋滥，多重确认
目标：在降低亏损的同时提高胜率

核心原则：
1. 提高选股门槛：评分≥70才推荐
2. 多重确认机制：DDX+资金+技术+基本面+情绪，5重验证
3. 等待最佳买点：不追高，等回调
4. 从历史学习：持续优化因子权重
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

from enhanced_factor_library import EnhancedFactorLibrary
from risk_budget_system import CircuitBreaker
from data_fetcher import DataFetcher
from trade_journal import TradeJournal

warnings.filterwarnings("ignore")


class HighWinrateSelector:
    """高胜率选股模式"""

    def __init__(self, config: Dict = None):
        """
        初始化高胜率选股模式

        参数:
            config: 配置字典
                - min_score: 最低推荐评分（默认70）
                - min_ddx_10d: 最低10日DDX（默认2）
                - min_main_flow_5d: 最低5日主力流入（默认1亿）
                - max_price_change: 最大涨幅（默认3%）
                - require_all_confirmations: 是否需要全部确认（默认True）
        """
        self.config = config or {
            "min_score": 70,  # 最低评分
            "min_ddx_10d": 2.0,  # 最低10日DDX
            "min_main_flow_5d": 100000000,  # 最低5日主力流入1亿
            "max_price_change": 0.03,  # 最大涨幅3%
            "require_all_confirmations": True,  # 需要5重确认
        }

        # 初始化模块
        self.factor_library = EnhancedFactorLibrary()
        self.circuit_breaker = CircuitBreaker()
        self.data_fetcher = DataFetcher()
        self.trade_journal = TradeJournal()

        # 加载历史学习数据
        self.learned_weights = self._load_learned_weights()
        self.learned_patterns = self._load_learned_patterns()

        print("[高胜率选股模式] 初始化完成")
        print(f"  最低评分: {self.config['min_score']}")
        print(f"  最低10日DDX: {self.config['min_ddx_10d']}")
        print(f"  最低5日主力流入: {self.config['min_main_flow_5d'] / 100000000:.1f}亿")
        print(f"  最大涨幅: {self.config['max_price_change'] * 100:.0f}%")
        print(
            f"  5重确认: {'必须' if self.config['require_all_confirmations'] else '可选'}"
        )

    def _load_learned_weights(self) -> Dict:
        """加载从历史交易中学到的因子权重"""
        weights_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "factor_weights.json"
        )

        if os.path.exists(weights_file):
            with open(weights_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def _load_learned_patterns(self) -> Dict:
        """加载从历史交易中学到的模式"""
        patterns_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "learned_patterns.json"
        )

        if os.path.exists(patterns_file):
            with open(patterns_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "win_patterns": [],  # 盈利模式
            "loss_patterns": [],  # 亏损模式
            "best_strategies": {},  # 最佳策略
            "avoid_conditions": [],  # 避免的情况
        }

    def analyze_stock(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float = None,
        price_change_pct: float = None,
    ) -> Dict:
        """
        分析单只股票（高胜率模式）

        参数:
            stock_code: 股票代码
            stock_name: 股票名称
            current_price: 当前价格（可选）
            price_change_pct: 今日涨幅（可选）

        返回:
            分析结果
        """
        print(f"\n[高胜率分析] {stock_name}({stock_code})")
        print("=" * 60)

        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "passed": False,
            "score": 0,
            "confirmations": {},
            "buy_signal": False,
            "buy_point_quality": "none",  # none/poor/good/excellent
            "recommendation": "avoid",
            "reasons": [],
            "risks": [],
            "stop_loss": None,
            "target_price": None,
            "position_size": None,
            "factors": {},
        }

        # ========== 1. 数据获取 ==========
        print("\n[1/6] 获取数据...")

        try:
            # 获取DDX数据
            ddx_data = self.data_fetcher.fetch_ddx_data(stock_code, days=10)

            # 获取资金流向
            fund_flow = self.data_fetcher.fetch_fund_flow(stock_code, days=5)

            # 获取财务数据
            financial_data = self.data_fetcher.fetch_financial_data(stock_code)

            # 获取舆情数据
            sentiment_data = self.data_fetcher.fetch_sentiment_data(stock_code, days=7)

        except Exception as e:
            print(f"  数据获取失败: {e}")
            result["risks"].append("数据获取失败")
            return result

        # 模拟行情数据（实际应从API获取）
        np.random.seed(hash(stock_code) % 1000)
        n = 100
        market_data = pd.DataFrame(
            {
                "open": np.random.uniform(10, 20, n),
                "high": np.random.uniform(15, 25, n),
                "low": np.random.uniform(5, 15, n),
                "close": np.random.uniform(10, 20, n),
                "volume": np.random.uniform(1000000, 5000000, n),
            }
        )

        if current_price is None:
            current_price = market_data["close"].iloc[-1]

        if price_change_pct is None:
            price_change_pct = np.random.uniform(-0.05, 0.08)

        print(f"  当前价格: {current_price:.2f}元")
        print(f"  今日涨幅: {price_change_pct * 100:+.2f}%")

        # ========== 2. 提取因子 ==========
        print("\n[2/6] 提取因子...")

        factors = self.factor_library.extract_all_factors(market_data)

        # 添加DDX因子
        if ddx_data:
            factors.update(
                {
                    "ddx_10d": ddx_data.get("ddx_10d_avg", 0),
                    "ddx_trend": ddx_data.get("ddx_trend", 0),
                    "ddx_positive_days": ddx_data.get("ddx_positive_days", 0),
                }
            )

        # 添加资金流向因子
        if fund_flow:
            factors.update(
                {
                    "main_flow": fund_flow.get("main_flow", 0),
                    "main_flow_5d": fund_flow.get("main_flow_5d_sum", 0),
                    "super_large_flow": fund_flow.get("super_large_flow", 0),
                }
            )

        # 添加基本面因子
        if financial_data:
            factors.update(
                {
                    "pe": financial_data.get("pe", 0),
                    "pb": financial_data.get("pb", 0),
                    "roe": financial_data.get("roe", 0),
                }
            )

        # 添加情绪因子
        if sentiment_data:
            factors.update(
                {
                    "sentiment_score": sentiment_data.get("sentiment_score", 50),
                }
            )

        result["factors"] = factors
        print(f"  提取因子: {len(factors)}个")

        # ========== 3. 5重确认检查 ==========
        print("\n[3/6] 5重确认检查...")

        confirmations = {}

        # 确认1: DDX确认
        ddx_10d = factors.get("ddx_10d", 0)
        ddx_positive_days = factors.get("ddx_positive_days", 0)

        ddx_confirmed = ddx_10d >= self.config["min_ddx_10d"] and ddx_positive_days >= 3

        confirmations["ddx"] = {
            "passed": ddx_confirmed,
            "ddx_10d": ddx_10d,
            "ddx_positive_days": ddx_positive_days,
            "reason": f"10日DDX={ddx_10d:.2f}, 连续{ddx_positive_days}天流入"
            if ddx_confirmed
            else "DDX不满足条件",
        }

        print(
            f"  [确认1] DDX: {'[通过]' if ddx_confirmed else '[未通过]'} - {confirmations['ddx']['reason']}"
        )

        # 确认2: 资金确认
        main_flow_5d = factors.get("main_flow_5d", 0)
        main_flow_today = factors.get("main_flow", 0)

        fund_confirmed = (
            main_flow_5d >= self.config["min_main_flow_5d"] and main_flow_today > 0
        )

        confirmations["fund"] = {
            "passed": fund_confirmed,
            "main_flow_5d": main_flow_5d,
            "main_flow_today": main_flow_today,
            "reason": f"5日主力流入{main_flow_5d / 100000000:.2f}亿, 今日{main_flow_today / 100000000:.2f}亿"
            if fund_confirmed
            else "资金流向不满足条件",
        }

        print(
            f"  [确认2] 资金: {'[通过]' if fund_confirmed else '[未通过]'} - {confirmations['fund']['reason']}"
        )

        # 确认3: 技术确认
        tech_confirmed = abs(price_change_pct) <= self.config["max_price_change"]

        confirmations["technical"] = {
            "passed": tech_confirmed,
            "price_change_pct": price_change_pct,
            "reason": f"涨幅{price_change_pct * 100:+.2f}%"
            if tech_confirmed
            else f"涨幅过高{price_change_pct * 100:+.2f}%",
        }

        print(
            f"  [确认3] 技术: {'[通过]' if tech_confirmed else '[未通过]'} - {confirmations['technical']['reason']}"
        )

        # 确认4: 基本面确认
        pe = factors.get("pe", 999)
        roe = factors.get("roe", 0)

        fundamental_confirmed = pe < 50 and roe > 10

        confirmations["fundamental"] = {
            "passed": fundamental_confirmed,
            "pe": pe,
            "roe": roe,
            "reason": f"PE={pe:.1f}, ROE={roe:.1f}%"
            if fundamental_confirmed
            else "基本面不满足条件",
        }

        print(
            f"  [确认4] 基本面: {'[通过]' if fundamental_confirmed else '[未通过]'} - {confirmations['fundamental']['reason']}"
        )

        # 确认5: 情绪确认
        sentiment_score = factors.get("sentiment_score", 50)

        # 检查是否有重大负面新闻
        has_negative_news = sentiment_score < 30

        sentiment_confirmed = not has_negative_news

        confirmations["sentiment"] = {
            "passed": sentiment_confirmed,
            "sentiment_score": sentiment_score,
            "reason": f"情绪评分{sentiment_score:.0f}"
            if sentiment_confirmed
            else "有重大负面新闻",
        }

        print(
            f"  [确认5] 情绪: {'[通过]' if sentiment_confirmed else '[未通过]'} - {confirmations['sentiment']['reason']}"
        )

        result["confirmations"] = confirmations

        # ========== 4. 计算综合评分 ==========
        print("\n[4/6] 计算综合评分...")

        score = self._calculate_high_winrate_score(factors, confirmations)
        result["score"] = score

        print(f"  综合评分: {score:.1f}")

        # ========== 5. 判断买点质量 ==========
        print("\n[5/6] 判断买点质量...")

        buy_point_quality = self._evaluate_buy_point(
            price_change_pct, factors, confirmations
        )

        result["buy_point_quality"] = buy_point_quality

        print(f"  买点质量: {buy_point_quality}")

        # ========== 6. 生成推荐 ==========
        print("\n[6/6] 生成推荐...")

        # 判断是否通过
        all_confirmed = all(c["passed"] for c in confirmations.values())

        if self.config["require_all_confirmations"]:
            result["passed"] = all_confirmed and score >= self.config["min_score"]
        else:
            # 至少4个确认通过
            passed_count = sum(1 for c in confirmations.values() if c["passed"])
            result["passed"] = passed_count >= 4 and score >= self.config["min_score"]

        # 生成推荐
        if result["passed"] and buy_point_quality in ["good", "excellent"]:
            result["buy_signal"] = True
            result["recommendation"] = "strong_buy"
            result["reasons"].append("5重确认全部通过")
            result["reasons"].append(f"综合评分{score:.1f}分")
            result["reasons"].append(f"买点质量: {buy_point_quality}")

        elif result["passed"] and buy_point_quality == "poor":
            result["recommendation"] = "wait"
            result["reasons"].append("确认通过但买点不佳")
            result["reasons"].append("建议等回调后再买")

        elif score >= self.config["min_score"] and not all_confirmed:
            result["recommendation"] = "watch"
            result["reasons"].append(f"评分达标但确认未全部通过")
            result["reasons"].append("可以关注，等待更好时机")

        else:
            result["recommendation"] = "avoid"
            result["reasons"].append("不满足高胜率条件")

        # 计算止损价、目标价、仓位
        result["stop_loss"] = current_price * 0.95
        result["target_price"] = current_price * 1.10
        result["position_size"] = self._calculate_position_size(
            score, buy_point_quality
        )

        # 添加风险提示
        if not ddx_confirmed:
            result["risks"].append("DDX未确认，资金趋势不稳定")
        if not fund_confirmed:
            result["risks"].append("资金流向未确认，缺乏资金支持")
        if not tech_confirmed:
            result["risks"].append(
                f"涨幅过高{price_change_pct * 100:+.1f}%，追高风险大"
            )

        # 输出结果
        print(f"\n[推荐结果]")
        print(f"  推荐等级: {result['recommendation']}")
        print(f"  综合评分: {result['score']:.1f}")
        print(f"  买点质量: {result['buy_point_quality']}")
        print(f"  买入信号: {'是' if result['buy_signal'] else '否'}")

        if result["reasons"]:
            print(f"\n[推荐理由]")
            for reason in result["reasons"]:
                print(f"  - {reason}")

        if result["risks"]:
            print(f"\n[风险提示]")
            for risk in result["risks"]:
                print(f"  - {risk}")

        return result

    def _calculate_high_winrate_score(
        self, factors: Dict, confirmations: Dict
    ) -> float:
        """
        计算高胜率评分

        参数:
            factors: 因子字典
            confirmations: 确认结果

        返回:
            评分（0-100）
        """
        score = 50  # 基础分

        # 1. 确认通过加分（每个确认+5分）
        for name, conf in confirmations.items():
            if conf["passed"]:
                score += 5

        # 2. DDX强度加分
        ddx_10d = factors.get("ddx_10d", 0)
        if ddx_10d > 5:
            score += 10
        elif ddx_10d > 2:
            score += 5

        # 3. 资金强度加分
        main_flow_5d = factors.get("main_flow_5d", 0)
        if main_flow_5d > 500000000:  # 5亿
            score += 10
        elif main_flow_5d > 200000000:  # 2亿
            score += 5

        # 4. 参考历史学习权重
        for factor_name, factor_value in factors.items():
            if factor_name in self.learned_weights:
                weight = self.learned_weights[factor_name]
                if factor_value > 0 and weight > 0:
                    score += weight * 3
                elif factor_value < 0 and weight < 0:
                    score += abs(weight) * 3

        # 5. 避免已知的亏损模式
        for pattern in self.learned_patterns.get("avoid_conditions", []):
            # 简单的模式匹配
            if self._match_pattern(factors, pattern):
                score -= 10

        return max(0, min(100, score))

    def _evaluate_buy_point(
        self, price_change_pct: float, factors: Dict, confirmations: Dict
    ) -> str:
        """
        评估买点质量

        返回:
            "excellent" - 最佳买点
            "good" - 好买点
            "poor" - 差买点
            "none" - 无买点
        """
        # 涨幅判断
        if price_change_pct > 0.05:
            return "none"  # 涨幅>5%，不追

        if price_change_pct > 0.03:
            return "poor"  # 涨幅3-5%，买点不佳

        # 资金确认
        if not confirmations.get("fund", {}).get("passed", False):
            return "none"

        # DDX确认
        if not confirmations.get("ddx", {}).get("passed", False):
            return "poor"

        # 最佳买点：涨幅<1% + 资金流入 + DDX确认
        if (
            abs(price_change_pct) < 0.01
            and confirmations["fund"]["passed"]
            and confirmations["ddx"]["passed"]
        ):
            return "excellent"

        # 好买点：涨幅1-3% + 资金流入
        if abs(price_change_pct) < 0.03 and confirmations["fund"]["passed"]:
            return "good"

        return "poor"

    def _match_pattern(self, factors: Dict, pattern: Dict) -> bool:
        """匹配模式"""
        # 简单实现：检查关键因子是否符合模式
        for key, value in pattern.items():
            if key in factors:
                if isinstance(value, dict):
                    if "min" in value and factors[key] < value["min"]:
                        return False
                    if "max" in value and factors[key] > value["max"]:
                        return False
        return True

    def _calculate_position_size(self, score: float, buy_point_quality: str) -> float:
        """计算建议仓位"""
        base_position = 54000  # 基础仓位（20% of 27万）

        # 根据评分调整
        if score >= 80:
            score_multiplier = 1.0
        elif score >= 70:
            score_multiplier = 0.8
        else:
            score_multiplier = 0.6

        # 根据买点质量调整
        quality_multiplier = {"excellent": 1.0, "good": 0.8, "poor": 0.5, "none": 0.0}

        return (
            base_position
            * score_multiplier
            * quality_multiplier.get(buy_point_quality, 0)
        )

    def batch_analyze(self, stock_list: List[Dict]) -> List[Dict]:
        """
        批量分析股票

        参数:
            stock_list: 股票列表 [{"code": "600519", "name": "贵州茅台", "price": 1800, "change": 0.02}, ...]

        返回:
            分析结果列表（按评分排序）
        """
        print(f"\n[批量分析] {len(stock_list)}只股票")
        print("=" * 60)

        results = []

        for stock in stock_list:
            result = self.analyze_stock(
                stock_code=stock["code"],
                stock_name=stock["name"],
                current_price=stock.get("price"),
                price_change_pct=stock.get("change"),
            )
            results.append(result)

        # 按评分排序
        results.sort(key=lambda x: x["score"], reverse=True)

        # 输出汇总
        print(f"\n[分析汇总]")
        print("=" * 60)

        strong_buys = [r for r in results if r["recommendation"] == "strong_buy"]
        waits = [r for r in results if r["recommendation"] == "wait"]
        watches = [r for r in results if r["recommendation"] == "watch"]

        print(f"  强烈推荐: {len(strong_buys)}只")
        for r in strong_buys:
            print(
                f"    - {r['stock_name']}({r['stock_code']}) 评分{r['score']:.0f} 买点{r['buy_point_quality']}"
            )

        print(f"  等待回调: {len(waits)}只")
        for r in waits:
            print(f"    - {r['stock_name']}({r['stock_code']}) 评分{r['score']:.0f}")

        print(f"  可以关注: {len(watches)}只")
        for r in watches:
            print(f"    - {r['stock_name']}({r['stock_code']}) 评分{r['score']:.0f}")

        return results

    def learn_from_trade(self, trade_result: Dict):
        """
        从交易中学习

        参数:
            trade_result: 交易结果
                - stock_code: 股票代码
                - pnl_pct: 盈亏比例
                - factors: 因子数据
                - confirmations: 确认结果
        """
        pnl_pct = trade_result.get("pnl_pct", 0)
        factors = trade_result.get("factors", {})
        confirmations = trade_result.get("confirmations", {})

        print(f"\n[学习] 从交易中学习...")

        # 1. 更新因子权重
        for factor_name, factor_value in factors.items():
            if factor_name not in self.learned_weights:
                self.learned_weights[factor_name] = 0

            # 盈利：正向因子增加权重
            # 亏损：负向因子增加权重
            if pnl_pct > 0:
                if factor_value > 0:
                    self.learned_weights[factor_name] += 0.02
                else:
                    self.learned_weights[factor_name] -= 0.02
            else:
                if factor_value > 0:
                    self.learned_weights[factor_name] -= 0.02
                else:
                    self.learned_weights[factor_name] += 0.02

        # 2. 记录盈利/亏损模式
        if pnl_pct > 5:
            # 盈利>5%，记录为盈利模式
            pattern = {
                "factors": factors,
                "confirmations": confirmations,
                "pnl_pct": pnl_pct,
            }
            self.learned_patterns["win_patterns"].append(pattern)
            print(f"  记录盈利模式: 盈利{pnl_pct:+.1f}%")

        elif pnl_pct < -3:
            # 亏损>3%，记录为亏损模式
            pattern = {
                "factors": factors,
                "confirmations": confirmations,
                "pnl_pct": pnl_pct,
            }
            self.learned_patterns["loss_patterns"].append(pattern)
            print(f"  记录亏损模式: 亏损{pnl_pct:+.1f}%")

        # 3. 保存学习结果
        self._save_learned_data()

        print(f"  学习完成，因子权重已更新")

    def _save_learned_data(self):
        """保存学习数据"""
        # 保存因子权重
        weights_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "factor_weights.json"
        )
        with open(weights_file, "w", encoding="utf-8") as f:
            json.dump(self.learned_weights, f, ensure_ascii=False, indent=2)

        # 保存学习模式
        patterns_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "learned_patterns.json"
        )
        with open(patterns_file, "w", encoding="utf-8") as f:
            json.dump(
                self.learned_patterns, f, ensure_ascii=False, indent=2, default=str
            )


def test_high_winrate_selector():
    """测试高胜率选股模式"""
    print("\n" + "=" * 60)
    print("高胜率选股模式测试")
    print("=" * 60)

    # 初始化
    selector = HighWinrateSelector()

    # 测试1: 单股分析
    print("\n" + "=" * 60)
    print("测试1: 单股分析")
    print("=" * 60)

    result = selector.analyze_stock(
        stock_code="600519",
        stock_name="贵州茅台",
        current_price=1800.0,
        price_change_pct=0.02,  # 涨幅2%
    )

    # 测试2: 批量分析
    print("\n" + "=" * 60)
    print("测试2: 批量分析")
    print("=" * 60)

    stock_list = [
        {"code": "600519", "name": "贵州茅台", "price": 1800, "change": 0.02},
        {"code": "000001", "name": "平安银行", "price": 15, "change": 0.01},
        {"code": "300750", "name": "宁德时代", "price": 200, "change": 0.04},
    ]

    results = selector.batch_analyze(stock_list)

    # 测试3: 从交易中学习
    print("\n" + "=" * 60)
    print("测试3: 从交易中学习")
    print("=" * 60)

    trade_result = {
        "stock_code": "600519",
        "pnl_pct": 5.2,  # 盈利5.2%
        "factors": result["factors"],
        "confirmations": result["confirmations"],
    }

    selector.learn_from_trade(trade_result)


if __name__ == "__main__":
    test_high_winrate_selector()
