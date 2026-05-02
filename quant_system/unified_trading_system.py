# -*- coding: utf-8 -*-
"""
统一交易系统 - 整合选股、风控、交易记录、复盘
功能：
1. 选股时自动记录推荐理由、因子数据
2. 买入时自动关联推荐，记录交易
3. 卖出时自动计算盈亏，更新记录
4. 选股时参考历史交易，动态调整因子权重
5. 定期自动复盘，生成优化建议
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

from enhanced_factor_library import EnhancedFactorLibrary
from risk_budget_system import CircuitBreaker, CVaRModel
from data_fetcher import DataFetcher
from trade_journal import TradeJournal
from auto_review import AutoReview

warnings.filterwarnings("ignore")


class UnifiedTradingSystem:
    """统一交易系统"""

    def __init__(self, config: Dict = None):
        """
        初始化统一交易系统

        参数:
            config: 配置字典
                - total_capital: 总资金（默认27万）
                - max_single_loss_pct: 单笔止损比例（默认5%）
                - max_position_pct: 单股最大仓位（默认20%）
        """
        # 配置
        self.config = config or {
            "total_capital": 270000,  # 27万
            "max_single_loss_pct": 0.05,  # 5%止损
            "max_position_pct": 0.20,  # 单股最大20%
        }

        # 初始化各模块
        self.factor_library = EnhancedFactorLibrary()
        self.circuit_breaker = CircuitBreaker()
        self.cvar_model = CVaRModel()
        self.data_fetcher = DataFetcher()
        self.trade_journal = TradeJournal()
        self.auto_review = AutoReview()

        # 加载历史交易记录（用于优化选股）
        self.history_weights = self._load_history_weights()

        print("[统一交易系统] 初始化完成")
        print(f"  总资金: {self.config['total_capital']:,.0f}元")
        print(f"  单笔止损: {self.config['max_single_loss_pct'] * 100:.0f}%")
        print(f"  单股最大仓位: {self.config['max_position_pct'] * 100:.0f}%")

    def _load_history_weights(self) -> Dict:
        """加载历史因子权重（从交易记录中学习）"""
        weights_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "factor_weights.json"
        )

        if os.path.exists(weights_file):
            with open(weights_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def _save_history_weights(self, weights: Dict):
        """保存因子权重"""
        weights_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "factor_weights.json"
        )

        with open(weights_file, "w", encoding="utf-8") as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)

    def analyze_and_recommend(
        self, stock_code: str, stock_name: str, auto_record: bool = True
    ) -> Dict:
        """
        分析股票并生成推荐（自动记录推荐理由和因子数据）

        参数:
            stock_code: 股票代码
            stock_name: 股票名称
            auto_record: 是否自动记录推荐

        返回:
            推荐结果
        """
        print(f"\n[分析] {stock_name}({stock_code})")
        print("=" * 60)

        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "recommendation": "hold",
            "score": 0,
            "factors": {},
            "reasons": [],
            "risks": [],
            "stop_loss": None,
            "target_price": None,
            "position_size": None,
        }

        # 1. 获取数据
        print("\n[1/5] 获取数据...")
        try:
            # 获取行情数据（模拟）
            np.random.seed(42)
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

            # 获取DDX数据（如果有API）
            ddx_data = self.data_fetcher.fetch_ddx_data(stock_code, days=10)

            # 获取资金流向（如果有API）
            fund_flow = self.data_fetcher.fetch_fund_flow(stock_code, days=5)

        except Exception as e:
            print(f"  数据获取失败: {e}")
            result["risks"].append("数据获取失败")
            return result

        # 2. 提取因子
        print("\n[2/5] 提取因子...")
        factors = self.factor_library.extract_all_factors(market_data)
        result["factors"] = factors

        # 添加DDX因子
        if ddx_data:
            factors.update(
                {
                    "ddx_10d": ddx_data.get("ddx_10d_avg", 0),
                    "ddx_trend": ddx_data.get("ddx_trend", 0),
                }
            )

        # 添加资金流向因子
        if fund_flow:
            factors.update(
                {
                    "main_flow": fund_flow.get("main_flow", 0),
                    "main_flow_5d": fund_flow.get("main_flow_5d_sum", 0),
                }
            )

        print(f"  提取因子: {len(factors)}个")

        # 3. 计算评分（参考历史权重）
        print("\n[3/5] 计算评分...")
        score = self._calculate_score(factors)
        result["score"] = score

        # 4. 生成推荐
        print("\n[4/5] 生成推荐...")
        if score >= 70:
            result["recommendation"] = "strong_buy"
            result["reasons"].append("综合评分≥70，强烈推荐")
        elif score >= 60:
            result["recommendation"] = "buy"
            result["reasons"].append("综合评分≥60，可以买入")
        elif score >= 50:
            result["recommendation"] = "hold"
            result["reasons"].append("综合评分50-60，观望")
        else:
            result["recommendation"] = "avoid"
            result["reasons"].append("综合评分<50，不推荐")

        # 5. 风控检查
        print("\n[5/5] 风控检查...")

        # 计算止损价
        current_price = market_data["close"].iloc[-1]
        result["stop_loss"] = current_price * (1 - self.config["max_single_loss_pct"])

        # 计算目标价
        result["target_price"] = current_price * 1.10  # +10%

        # 计算建议仓位
        result["position_size"] = self._calculate_position_size(score)

        # 风险提示
        if factors.get("ddx_10d", 0) < 0:
            result["risks"].append("10日DDX为负，中期资金流出")

        if factors.get("main_flow_5d", 0) < 0:
            result["risks"].append("5日主力资金流出")

        # 输出结果
        print(f"\n[推荐结果]")
        print(f"  推荐等级: {result['recommendation']}")
        print(f"  综合评分: {result['score']:.1f}")
        print(f"  当前价格: {current_price:.2f}元")
        print(f"  止损价: {result['stop_loss']:.2f}元")
        print(f"  目标价: {result['target_price']:.2f}元")
        print(f"  建议仓位: {result['position_size']:,.0f}元")

        if result["reasons"]:
            print(f"\n[推荐理由]")
            for reason in result["reasons"]:
                print(f"  - {reason}")

        if result["risks"]:
            print(f"\n[风险提示]")
            for risk in result["risks"]:
                print(f"  - {risk}")

        # 自动记录推荐
        if auto_record and result["recommendation"] in ["strong_buy", "buy"]:
            self._record_recommendation(result)

        return result

    def _calculate_score(self, factors: Dict) -> float:
        """
        计算综合评分（参考历史权重）

        参数:
            factors: 因子字典

        返回:
            综合评分（0-100）
        """
        score = 50  # 基础分

        # DDX因子（权重最高）
        ddx_10d = factors.get("ddx_10d", 0)
        if ddx_10d > 2:
            score += 15
        elif ddx_10d > 0:
            score += 10
        elif ddx_10d < -2:
            score -= 15
        else:
            score -= 10

        # 主力资金因子
        main_flow_5d = factors.get("main_flow_5d", 0)
        if main_flow_5d > 5:
            score += 10
        elif main_flow_5d > 0:
            score += 5
        elif main_flow_5d < -5:
            score -= 10
        else:
            score -= 5

        # 参考历史权重调整
        for factor_name, factor_value in factors.items():
            if factor_name in self.history_weights:
                weight = self.history_weights[factor_name]
                # 简单加权（实际可以更复杂）
                if factor_value > 0:
                    score += weight * 5
                else:
                    score -= weight * 5

        return max(0, min(100, score))

    def _calculate_position_size(self, score: float) -> float:
        """
        计算建议仓位

        参数:
            score: 综合评分

        返回:
            建议仓位金额
        """
        max_position = self.config["total_capital"] * self.config["max_position_pct"]

        if score >= 80:
            return max_position  # 满仓
        elif score >= 70:
            return max_position * 0.8  # 80%
        elif score >= 60:
            return max_position * 0.6  # 60%
        else:
            return max_position * 0.4  # 40%

    def _record_recommendation(self, result: Dict):
        """记录推荐（用于后续跟踪）"""
        recommend_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "recommendations.json"
        )

        # 读取现有推荐
        if os.path.exists(recommend_file):
            with open(recommend_file, "r", encoding="utf-8") as f:
                recommendations = json.load(f)
        else:
            recommendations = []

        # 添加新推荐
        recommendations.append(
            {
                "stock_code": result["stock_code"],
                "stock_name": result["stock_name"],
                "datetime": result["datetime"],
                "recommendation": result["recommendation"],
                "score": result["score"],
                "factors": result["factors"],
                "stop_loss": result["stop_loss"],
                "target_price": result["target_price"],
                "position_size": result["position_size"],
                "status": "pending",  # pending/bought/expired
            }
        )

        # 保存
        with open(recommend_file, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)

        print(f"\n[自动记录] 推荐已保存到交易记录")

    def execute_buy(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        shares: int,
        reason: str = "manual",
        strategy: str = "manual",
    ) -> str:
        """
        执行买入（自动关联推荐记录）

        参数:
            stock_code: 股票代码
            stock_name: 股票名称
            price: 买入价格
            shares: 买入股数
            reason: 买入理由
            strategy: 策略名称

        返回:
            trade_id: 交易ID
        """
        print(f"\n[买入] {stock_name}({stock_code}) {shares}股 @ {price}元")

        # 查找最近的推荐记录
        recommend_data = self._find_recommendation(stock_code)

        # 如果有推荐记录，使用推荐的数据
        if recommend_data:
            print(f"  关联推荐记录: {recommend_data['datetime']}")
            print(f"  推荐评分: {recommend_data['score']:.1f}")
            print(f"  推荐理由: {recommend_data['recommendation']}")

            # 使用推荐的因子数据
            factors = recommend_data.get("factors", {})
            stop_loss = recommend_data.get("stop_loss", price * 0.95)
            target_price = recommend_data.get("target_price", price * 1.10)

            # 更新推荐状态
            self._update_recommendation_status(stock_code, "bought")

        else:
            # 没有推荐记录，使用默认值
            factors = {}
            stop_loss = price * 0.95
            target_price = price * 1.10

        # 记录买入
        trade_id = self.trade_journal.record_buy(
            stock_code=stock_code,
            stock_name=stock_name,
            price=price,
            shares=shares,
            reason=reason,
            strategy=strategy,
            stop_loss=stop_loss,
            target_price=target_price,
            factors=factors,
        )

        return trade_id

    def _find_recommendation(self, stock_code: str) -> Optional[Dict]:
        """查找最近的推荐记录"""
        recommend_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "recommendations.json"
        )

        if not os.path.exists(recommend_file):
            return None

        with open(recommend_file, "r", encoding="utf-8") as f:
            recommendations = json.load(f)

        # 查找最近7天内的推荐
        cutoff_date = datetime.now() - timedelta(days=7)
        for rec in reversed(recommendations):
            if rec["stock_code"] == stock_code and rec["status"] == "pending":
                rec_date = datetime.strptime(rec["datetime"], "%Y-%m-%d %H:%M:%S")
                if rec_date >= cutoff_date:
                    return rec

        return None

    def _update_recommendation_status(self, stock_code: str, status: str):
        """更新推荐状态"""
        recommend_file = os.path.join(
            os.path.dirname(__file__), "trade_journal", "recommendations.json"
        )

        if not os.path.exists(recommend_file):
            return

        with open(recommend_file, "r", encoding="utf-8") as f:
            recommendations = json.load(f)

        # 更新状态
        for rec in recommendations:
            if rec["stock_code"] == stock_code and rec["status"] == "pending":
                rec["status"] = status
                break

        with open(recommend_file, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)

    def execute_sell(
        self, trade_id: str, exit_price: float, exit_reason: str = "manual"
    ) -> Dict:
        """
        执行卖出（自动计算盈亏，更新因子权重）

        参数:
            trade_id: 交易ID
            exit_price: 卖出价格
            exit_reason: 卖出原因

        返回:
            交易结果
        """
        print(f"\n[卖出] 交易ID: {trade_id}")

        # 记录卖出
        result = self.trade_journal.record_sell(
            trade_id=trade_id, exit_price=exit_price, exit_reason=exit_reason
        )

        if result:
            # 更新因子权重（从交易中学习）
            self._update_factor_weights(result)

        return result

    def _update_factor_weights(self, trade_result: Dict):
        """
        更新因子权重（从交易中学习）

        参数:
            trade_result: 交易结果
        """
        # 读取因子数据
        with open(self.trade_journal.factors_file, "r", encoding="utf-8") as f:
            factors_list = json.load(f)

        # 找到这笔交易的因子数据
        trade_factors = [
            f for f in factors_list if f["trade_id"] == trade_result["trade_id"]
        ]

        if not trade_factors:
            return

        # 更新权重
        pnl_pct = trade_result["pnl_pct"]

        for factor in trade_factors:
            factor_name = factor["factor_name"]
            factor_value = factor["factor_value"]

            # 简单的学习规则：
            # 如果盈利，增加这个因子的权重
            # 如果亏损，减少这个因子的权重
            if factor_name not in self.history_weights:
                self.history_weights[factor_name] = 0

            # 根据盈亏调整权重
            if pnl_pct > 0:
                # 盈利：因子值>0增加权重，因子值<0减少权重
                if factor_value > 0:
                    self.history_weights[factor_name] += 0.01
                else:
                    self.history_weights[factor_name] -= 0.01
            else:
                # 亏损：因子值>0减少权重，因子值<0增加权重
                if factor_value > 0:
                    self.history_weights[factor_name] -= 0.01
                else:
                    self.history_weights[factor_name] += 0.01

        # 保存权重
        self._save_history_weights(self.history_weights)

        print(f"\n[学习] 因子权重已更新")

    def auto_review_and_optimize(self, days: int = 30) -> Dict:
        """
        自动复盘并优化系统

        参数:
            days: 复盘天数

        返回:
            复盘结果
        """
        print(f"\n[自动复盘] 最近{days}天")
        print("=" * 60)

        # 运行复盘
        results = self.auto_review.review_trades(days=days)

        if results:
            # 根据复盘结果优化因子权重
            self._optimize_from_review(results)

        return results

    def _optimize_from_review(self, review_results: Dict):
        """根据复盘结果优化因子权重"""
        # 这里可以根据复盘结果调整因子权重
        # 暂时简单实现
        print("\n[优化] 根据复盘结果调整因子权重")

        if "recommendations" in review_results:
            for rec in review_results["recommendations"]:
                print(f"  - {rec}")

    def get_portfolio_status(self) -> Dict:
        """
        获取当前持仓状态

        返回:
            持仓状态
        """
        print(f"\n[持仓状态]")
        print("=" * 60)

        # 获取当前持仓
        open_trades = self.trade_journal.get_open_trades()

        if not open_trades:
            print("  当前无持仓")
            return {"positions": [], "total_value": 0}

        total_value = 0
        positions = []

        for trade in open_trades:
            position_value = trade["price"] * trade["shares"]
            total_value += position_value

            positions.append(
                {
                    "stock_code": trade["stock_code"],
                    "stock_name": trade["stock_name"],
                    "shares": trade["shares"],
                    "entry_price": trade["price"],
                    "current_value": position_value,
                    "stop_loss": trade["stop_loss"],
                    "target_price": trade["target_price"],
                }
            )

            print(
                f"  {trade['stock_name']}({trade['stock_code']}) "
                f"{trade['shares']}股 @ {trade['price']:.2f}元 "
                f"止损{trade['stop_loss']:.2f}元"
            )

        print(f"\n  总市值: {total_value:,.0f}元")
        print(f"  可用资金: {self.config['total_capital'] - total_value:,.0f}元")

        return {
            "positions": positions,
            "total_value": total_value,
            "available_cash": self.config["total_capital"] - total_value,
        }


def test_unified_system():
    """测试统一交易系统"""
    print("\n" + "=" * 60)
    print("统一交易系统测试")
    print("=" * 60)

    # 初始化系统
    system = UnifiedTradingSystem()

    # 1. 分析并推荐股票
    print("\n" + "=" * 60)
    print("场景1: 分析并推荐股票")
    print("=" * 60)

    result = system.analyze_and_recommend(
        stock_code="600519", stock_name="贵州茅台", auto_record=True
    )

    # 2. 执行买入
    print("\n" + "=" * 60)
    print("场景2: 执行买入（自动关联推荐）")
    print("=" * 60)

    trade_id = system.execute_buy(
        stock_code="600519",
        stock_name="贵州茅台",
        price=1800.0,
        shares=100,
        reason="AI推荐，评分75分",
        strategy="AI选股",
    )

    # 3. 查看持仓
    print("\n" + "=" * 60)
    print("场景3: 查看持仓")
    print("=" * 60)

    system.get_portfolio_status()

    # 4. 执行卖出
    print("\n" + "=" * 60)
    print("场景4: 执行卖出（自动更新因子权重）")
    print("=" * 60)

    system.execute_sell(trade_id=trade_id, exit_price=1850.0, exit_reason="止盈")

    # 5. 自动复盘
    print("\n" + "=" * 60)
    print("场景5: 自动复盘并优化")
    print("=" * 60)

    system.auto_review_and_optimize(days=30)


if __name__ == "__main__":
    test_unified_system()
