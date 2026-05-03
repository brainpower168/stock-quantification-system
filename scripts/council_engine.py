#!/usr/bin/env python3
"""
AI Trading Council - 多模型决策引擎
支持 LongCat、讯飞星火、智谱 GLM 三模型投票决策
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# 导入日志
try:
    from logger_config import get_logger

    logger = get_logger("council_engine")
except ImportError:
    import logging

    logger = logging.getLogger("council_engine")

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent / "config" / "council_config.json"
DATA_DIR = Path(__file__).parent.parent / "data"
MEMORY_DIR = DATA_DIR / "memory"
REPORT_DIR = DATA_DIR / "reports"


@dataclass
class ModelVote:
    """模型投票结果"""

    model_name: str
    role: str
    decision: str  # BUY, HOLD, SELL
    confidence: float  # 0-1
    reasoning: str
    key_factors: List[str]


@dataclass
class CouncilDecision:
    """委员会最终决策"""

    stock_code: str
    stock_name: str
    final_decision: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float
    votes: List[ModelVote]
    consensus_level: str  # UNANIMOUS, MAJORITY, SPLIT
    risk_warnings: List[str]
    timestamp: str


class AITradingCouncil:
    """AI交易委员会 - 多模型决策系统"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path or CONFIG_PATH)
        self._ensure_dirs()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _ensure_dirs(self):
        """确保目录存在"""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _get_api_key(self, model_key: str) -> str:
        """获取API Key"""
        model_config = self.config["models"].get(model_key, {})
        env_var = model_config.get("api_key_env")

        # 先从环境变量获取
        if env_var:
            key = os.environ.get(env_var)
            if key:
                return key

        # 回退到配置文件中的直接配置（如果有）
        return model_config.get("api_key", "")

    def _call_model(self, model_key: str, prompt: str) -> Optional[str]:
        """调用单个模型"""
        model_config = self.config["models"].get(model_key)
        if not model_config:
            return None

        api_key = self._get_api_key(model_key)
        if not api_key:
            logger.warning(f"{model_key} API Key 未配置")
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_config["name"],
            "messages": [
                {
                    "role": "system",
                    "content": f"你是一位专业的{model_config['role']}。请基于你的专业领域给出投资建议。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        try:
            response = requests.post(
                f"{model_config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"调用 {model_key} 失败: {e}")
            return None

    def _parse_vote(self, model_key: str, response: str, role: str) -> ModelVote:
        """解析模型响应为投票结果"""
        response_lower = response.lower()

        # 简单的决策解析
        if "买入" in response or "buy" in response_lower:
            decision = "BUY"
        elif "卖出" in response or "sell" in response_lower:
            decision = "SELL"
        else:
            decision = "HOLD"

        # 提取关键因素
        key_factors = []
        keywords = [
            "资金",
            "DDX",
            "主力",
            "估值",
            "业绩",
            "技术",
            "趋势",
            "支撑",
            "阻力",
        ]
        for kw in keywords:
            if kw in response:
                key_factors.append(kw)

        return ModelVote(
            model_name=model_key,
            role=role,
            decision=decision,
            confidence=0.7,  # 默认置信度
            reasoning=response[:500] if response else "无响应",
            key_factors=key_factors[:5],
        )

    def analyze_stock(
        self, stock_code: str, stock_name: str = None, market_data: dict = None
    ) -> CouncilDecision:
        """分析单只股票"""
        if not stock_name:
            stock_name = stock_code

        # 构建分析提示
        prompt = f"""
请分析股票 {stock_code} ({stock_name}) 的投资价值。

{"市场数据：" + json.dumps(market_data, ensure_ascii=False, indent=2) if market_data else ""}

请从你的专业角度给出：
1. 投资建议（买入/持有/卖出）
2. 主要理由（3-5点）
3. 风险提示

请用简洁的中文回答。
"""

        # 调用所有模型
        votes = []
        for model_key, model_config in self.config["models"].items():
            logger.info(f"正在咨询 {model_config['role']} ({model_key})...")
            response = self._call_model(model_key, prompt)
            if response:
                vote = self._parse_vote(model_key, response, model_config["role"])
                votes.append(vote)

        # 计算最终决策
        final_decision, confidence, consensus_level = self._calculate_decision(votes)

        # 生成风险警告
        risk_warnings = self._generate_risk_warnings(stock_code, market_data, votes)

        decision = CouncilDecision(
            stock_code=stock_code,
            stock_name=stock_name,
            final_decision=final_decision,
            confidence=confidence,
            votes=votes,
            consensus_level=consensus_level,
            risk_warnings=risk_warnings,
            timestamp=datetime.now().isoformat(),
        )

        # 保存决策报告
        self._save_report(decision)

        return decision

    def _calculate_decision(self, votes: List[ModelVote]) -> tuple:
        """计算最终决策"""
        if not votes:
            return "HOLD", 0.0, "SPLIT"

        # 投票计数
        buy_count = sum(1 for v in votes if v.decision == "BUY")
        sell_count = sum(1 for v in votes if v.decision == "SELL")
        hold_count = sum(1 for v in votes if v.decision == "HOLD")

        total = len(votes)

        # 计算加权分数
        score = (buy_count - sell_count) / total

        # 确定决策
        thresholds = self.config["decision_thresholds"]
        if score >= thresholds["strong_buy"]:
            decision = "STRONG_BUY"
        elif score >= thresholds["buy"]:
            decision = "BUY"
        elif score <= thresholds["sell"]:
            decision = "SELL"
        elif score <= thresholds["strong_buy"] * -1:
            decision = "STRONG_SELL"
        else:
            decision = "HOLD"

        # 计算置信度
        confidence = abs(score)

        # 确定共识程度
        max_count = max(buy_count, sell_count, hold_count)
        if max_count == total:
            consensus_level = "UNANIMOUS"
        elif max_count > total / 2:
            consensus_level = "MAJORITY"
        else:
            consensus_level = "SPLIT"

        return decision, confidence, consensus_level

    def _generate_risk_warnings(
        self, stock_code: str, market_data: dict, votes: List[ModelVote]
    ) -> List[str]:
        """生成风险警告"""
        warnings = []

        # 检查用户持仓
        positions = self.config.get("user_positions", {})
        if stock_code in positions:
            pos = positions[stock_code]
            warnings.append(f"您已持有 {pos['name']}，成本 {pos['cost']} 元")

        # 检查市场数据
        if market_data:
            # DDX 检查
            ddx_10d = market_data.get("ddx_10d", 0)
            if ddx_10d < 0:
                warnings.append(f"⚠️ 10日DDX为负({ddx_10d:.3f})，中期资金流出")

            # 涨幅检查
            change_pct = market_data.get("change_pct", 0)
            if change_pct > 3:
                warnings.append(f"⚠️ 涨幅过大({change_pct:.2f}%)，注意追高风险")

        return warnings

    def _save_report(self, decision: CouncilDecision):
        """保存决策报告"""
        report_path = (
            REPORT_DIR
            / f"council_{decision.stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# AI Trading Council 决策报告\n\n")
            f.write(f"**股票**: {decision.stock_code} ({decision.stock_name})\n")
            f.write(f"**时间**: {decision.timestamp}\n")
            f.write(f"**决策**: **{decision.final_decision}**\n")
            f.write(f"**置信度**: {decision.confidence:.2%}\n")
            f.write(f"**共识程度**: {decision.consensus_level}\n\n")

            f.write(f"## 模型投票\n\n")
            for vote in decision.votes:
                f.write(f"### {vote.role} ({vote.model_name})\n")
                f.write(f"- **决策**: {vote.decision}\n")
                f.write(f"- **置信度**: {vote.confidence:.2%}\n")
                f.write(f"- **关键因素**: {', '.join(vote.key_factors) or '无'}\n")
                f.write(f"- **理由**: {vote.reasoning[:200]}...\n\n")

            if decision.risk_warnings:
                f.write(f"## 风险警告\n\n")
                for w in decision.risk_warnings:
                    f.write(f"- {w}\n")

        logger.info(f"报告已保存: {report_path}")

    def analyze_with_strategies(self, stock_code: str, real_data: dict = None) -> dict:
        """
        使用多策略综合分析

        整合：
        1. AI Council 多模型投票
        2. 海龟法则进阶版
        3. 多Agent辩论机制
        4. DDX资金流向

        Args:
            stock_code: 股票代码
            real_data: 实盘数据（可选）

        Returns:
            综合分析结果
        """
        from strategies.turtle_strategy import TurtleStrategy
        from strategies.council_debate import DebateOrchestrator

        logger.info(f"\n{'=' * 60}")
        logger.info(f"多策略综合分析: {stock_code}")
        logger.info(f"{'=' * 60}\n")

        results = {
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
        }

        # 1. AI Council 分析
        logger.info("【AI Council 分析】")
        try:
            council_decision = self.analyze_stock(stock_code)
            results["council"] = {
                "decision": council_decision.final_decision,
                "confidence": council_decision.confidence,
                "consensus": council_decision.consensus_level,
            }
            logger.info(f"  决策: {council_decision.final_decision}")
            logger.info(f"  置信度: {council_decision.confidence:.2%}")
        except Exception as e:
            logger.error(f" {e}")
            results["council"] = None

        # 2. 海龟法则分析
        print("\n【海龟法则分析】")
        try:
            turtle = TurtleStrategy()
            if real_data and real_data.get("df") is not None:
                turtle_result = turtle.analyze(real_data["df"])
            else:
                # 使用模拟数据
                import pandas as pd
                import numpy as np

                dates = pd.date_range(end=datetime.now(), periods=100, freq="D")
                np.random.seed(hash(stock_code) % 2**32)
                base_price = 100 + np.random.rand() * 100
                returns = np.random.randn(100) * 0.02
                prices = base_price * (1 + returns).cumprod()
                df = pd.DataFrame(
                    {
                        "open": prices * (1 + np.random.randn(100) * 0.01),
                        "high": prices * (1 + np.abs(np.random.randn(100) * 0.02)),
                        "low": prices * (1 - np.abs(np.random.randn(100) * 0.02)),
                        "close": prices,
                        "volume": np.random.randint(1000000, 10000000, 100),
                    },
                    index=dates,
                )
                turtle_result = turtle.analyze(df)

            results["turtle"] = turtle_result
            logger.info(f"  信号: {turtle_result['signal']}")
            logger.info(f"  趋势: {turtle_result['trend']}")
        except Exception as e:
            logger.error(f" {e}")
            results["turtle"] = None

        # 3. 多Agent辩论
        print("\n【多Agent辩论】")
        try:
            debater = DebateOrchestrator()
            if real_data and real_data.get("quote"):
                debate_result = debater.run_debate(real_data["quote"], rounds=2)
            else:
                debate_result = debater.run_debate({"code": stock_code}, rounds=2)

            results["debate"] = {
                "consensus": debate_result.consensus.value,
                "confidence": debate_result.confidence,
            }
            logger.info(f"  共识: {debate_result.consensus.value}")
            logger.info(f"  置信度: {debate_result.confidence * 100:.0f}%")
        except Exception as e:
            logger.error(f" {e}")
            results["debate"] = None

        # 4. DDX资金流向
        print("\n【DDX资金流向】")
        if real_data and real_data.get("quote"):
            quote = real_data["quote"]
            ddx_10 = quote.get("ddx_10", 0)
            ddx_5 = quote.get("ddx_5", 0)
            main_inflow = quote.get("main_inflow", 0)

            results["ddx"] = {
                "ddx_10": ddx_10,
                "ddx_5": ddx_5,
                "main_inflow": main_inflow,
            }

            if ddx_10 > 0:
                logger.info(f"  10日DDX: {ddx_10} ✅ 中期资金流入")
            else:
                logger.info(f"  10日DDX: {ddx_10} ⚠️ 中期资金流出")

            if main_inflow > 0:
                print(f"  今日主力: {main_inflow / 100000000:.2f}亿 ✅ 流入")
            else:
                print(f"  今日主力: {abs(main_inflow) / 100000000:.2f}亿 ⚠️ 流出")
        else:
            print("  无实盘数据")
            results["ddx"] = None

        # 5. 综合决策
        print("\n【综合决策】")
        final_score = 0
        weights = {
            "council": 0.3,
            "turtle": 0.2,
            "debate": 0.2,
            "ddx": 0.3,
        }

        # Council得分
        if results.get("council"):
            decision_map = {
                "STRONG_BUY": 1,
                "BUY": 0.5,
                "HOLD": 0,
                "SELL": -0.5,
                "STRONG_SELL": -1,
            }
            score = decision_map.get(results["council"]["decision"], 0)
            final_score += score * results["council"]["confidence"] * weights["council"]

        # 海龟得分
        if results.get("turtle"):
            signal_map = {"BUY": 1, "HOLD": 0, "SELL": -1}
            score = signal_map.get(results["turtle"]["signal"], 0)
            final_score += score * weights["turtle"]

        # 辩论得分
        if results.get("debate"):
            stance_map = {"看多": 1, "中性": 0, "看空": -1}
            score = stance_map.get(results["debate"]["consensus"], 0)
            final_score += score * results["debate"]["confidence"] * weights["debate"]

        # DDX得分
        if results.get("ddx"):
            ddx = results["ddx"]
            score = 0
            if ddx["ddx_10"] > 0:
                score += 0.5
            if ddx["main_inflow"] > 0:
                score += 0.5
            final_score += score * weights["ddx"]

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

        results["final_decision"] = final_decision
        results["final_score"] = final_score

        print(f"  综合得分: {final_score:.2f}")
        print(f"  最终决策: {final_decision} ({action})")

        return results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Trading Council")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--stocks", type=str, help="股票代码列表，逗号分隔")
    args = parser.parse_args()

    council = AITradingCouncil()

    if args.stock:
        decision = council.analyze_stock(args.stock)
        print(f"\n最终决策: {decision.final_decision}")
        print(f"置信度: {decision.confidence:.2%}")
    elif args.stocks:
        stocks = args.stocks.split(",")
        for stock in stocks:
            decision = council.analyze_stock(stock.strip())
            print(f"{stock}: {decision.final_decision} ({decision.confidence:.2%})")
    else:
        print("请使用 --stock 或 --stocks 参数指定股票代码")


if __name__ == "__main__":
    main()
