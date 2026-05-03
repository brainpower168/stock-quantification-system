#!/usr/bin/env python3
"""
多Agent辩论决策机制
====================
基于TradingAgents论文的多智能体辩论系统

核心架构：
1. 分析师层（Bull/Bear研究员）
2. 研究员层（基本面/技术面/消息面）
3. 决策层（多空辩论 → 投票决策）

使用方法：
    python council_debate.py --stock 600519
    python council_debate.py --stocks 600519,000001,300750
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Stance(Enum):
    """立场"""

    BULL = "看多"
    BEAR = "看空"
    NEUTRAL = "中性"


@dataclass
class AgentOpinion:
    """智能体观点"""

    agent_name: str
    agent_role: str
    stance: Stance
    confidence: float  # 0-1
    reasoning: str
    key_points: List[str]
    risks: List[str]


@dataclass
class DebateResult:
    """辩论结果"""

    topic: str
    bull_arguments: List[str]
    bear_arguments: List[str]
    consensus: Stance
    confidence: float
    final_decision: str


class AnalystAgent:
    """分析师智能体"""

    def __init__(self, name: str, role: str, stance: Stance):
        self.name = name
        self.role = role
        self.stance = stance

    def analyze(self, stock_data: Dict) -> AgentOpinion:
        """
        分析股票数据并生成观点

        Args:
            stock_data: 股票数据字典

        Returns:
            智能体观点
        """
        # 基于角色生成分析
        if self.role == "fundamental":
            return self._analyze_fundamental(stock_data)
        elif self.role == "technical":
            return self._analyze_technical(stock_data)
        elif self.role == "sentiment":
            return self._analyze_sentiment(stock_data)
        else:
            return self._analyze_general(stock_data)

    def _analyze_fundamental(self, data: Dict) -> AgentOpinion:
        """基本面分析"""
        points = []
        risks = []

        # PE分析
        pe = data.get("pe", 0)
        if pe > 0 and pe < 20:
            points.append(f"PE={pe}，估值合理偏低")
        elif pe > 50:
            risks.append(f"PE={pe}，估值偏高")

        # ROE分析
        roe = data.get("roe", 0)
        if roe > 15:
            points.append(f"ROE={roe}%，盈利能力强")
        elif roe < 10:
            risks.append(f"ROE={roe}%，盈利能力弱")

        # 净利润增长
        profit_growth = data.get("profit_growth", 0)
        if profit_growth > 20:
            points.append(f"净利润增长{profit_growth}%，成长性好")
        elif profit_growth < 0:
            risks.append(f"净利润增长{profit_growth}%，业绩下滑")

        # 主力资金
        ddx_10 = data.get("ddx_10", 0)
        if ddx_10 > 0:
            points.append(f"10日DDX={ddx_10}，中期资金流入")
        else:
            risks.append(f"10日DDX={ddx_10}，中期资金流出")

        reasoning = f"基本面分析：PE={pe}, ROE={roe}%, 净利润增长={profit_growth}%"

        # 判断立场
        score = len(points) - len(risks)
        stance = (
            Stance.BULL if score > 0 else Stance.BEAR if score < 0 else Stance.NEUTRAL
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_role=self.role,
            stance=stance,
            confidence=min(0.9, 0.5 + abs(score) * 0.1),
            reasoning=reasoning,
            key_points=points,
            risks=risks,
        )

    def _analyze_technical(self, data: Dict) -> AgentOpinion:
        """技术面分析"""
        points = []
        risks = []

        # 均线分析
        price = data.get("price", 0)
        ma5 = data.get("ma5", 0)
        ma10 = data.get("ma10", 0)
        ma20 = data.get("ma20", 0)

        if price > ma5 > ma10 > ma20:
            points.append("均线多头排列，趋势向上")
        elif price < ma5 < ma10 < ma20:
            risks.append("均线空头排列，趋势向下")

        # KDJ分析
        kdj_k = data.get("kdj_k", 50)
        kdj_d = data.get("kdj_d", 50)

        if kdj_k < 20 and kdj_d < 20:
            points.append(f"KDJ={kdj_k}/{kdj_d}，超卖区，可能反弹")
        elif kdj_k > 80 and kdj_d > 80:
            risks.append(f"KDJ={kdj_k}/{kdj_d}，超买区，注意回调")

        # RSI分析
        rsi = data.get("rsi", 50)
        if rsi < 30:
            points.append(f"RSI={rsi}，超卖")
        elif rsi > 70:
            risks.append(f"RSI={rsi}，超买")

        # 成交量
        volume_ratio = data.get("volume_ratio", 1)
        if volume_ratio > 2:
            points.append(f"量比={volume_ratio}，放量明显")
        elif volume_ratio < 0.5:
            risks.append(f"量比={volume_ratio}，缩量明显")

        reasoning = f"技术面分析：价格={price}, KDJ={kdj_k}/{kdj_d}, RSI={rsi}"

        score = len(points) - len(risks)
        stance = (
            Stance.BULL if score > 0 else Stance.BEAR if score < 0 else Stance.NEUTRAL
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_role=self.role,
            stance=stance,
            confidence=min(0.9, 0.5 + abs(score) * 0.1),
            reasoning=reasoning,
            key_points=points,
            risks=risks,
        )

    def _analyze_sentiment(self, data: Dict) -> AgentOpinion:
        """消息面/情绪分析"""
        points = []
        risks = []

        # 涨跌幅
        change_pct = data.get("change_pct", 0)
        if change_pct > 3:
            risks.append(f"今日涨幅{change_pct}%，注意追高风险")
        elif change_pct < -3:
            points.append(f"今日跌幅{change_pct}%，可能有反弹机会")

        # 主力净流入
        main_inflow = data.get("main_inflow", 0)
        if main_inflow > 0:
            points.append(f"主力净流入{main_inflow / 100000000:.2f}亿")
        else:
            risks.append(f"主力净流出{abs(main_inflow) / 100000000:.2f}亿")

        # 板块热度
        sector_trend = data.get("sector_trend", "neutral")
        if sector_trend == "hot":
            points.append("板块热度高，资金关注")
        elif sector_trend == "cold":
            risks.append("板块热度低，资金撤离")

        # 新闻情绪
        news_sentiment = data.get("news_sentiment", 0)
        if news_sentiment > 0.5:
            points.append("新闻情绪偏正面")
        elif news_sentiment < -0.5:
            risks.append("新闻情绪偏负面")

        reasoning = (
            f"情绪面分析：涨幅={change_pct}%, 主力流入={main_inflow / 100000000:.2f}亿"
        )

        score = len(points) - len(risks)
        stance = (
            Stance.BULL if score > 0 else Stance.BEAR if score < 0 else Stance.NEUTRAL
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_role=self.role,
            stance=stance,
            confidence=min(0.9, 0.5 + abs(score) * 0.1),
            reasoning=reasoning,
            key_points=points,
            risks=risks,
        )

    def _analyze_general(self, data: Dict) -> AgentOpinion:
        """综合分析"""
        return AgentOpinion(
            agent_name=self.name,
            agent_role=self.role,
            stance=self.stance,
            confidence=0.5,
            reasoning="综合分析",
            key_points=[],
            risks=[],
        )


class DebateOrchestrator:
    """辩论编排器"""

    def __init__(self):
        # 创建分析师团队
        self.analysts = [
            AnalystAgent("基本面分析师", "fundamental", Stance.NEUTRAL),
            AnalystAgent("技术面分析师", "technical", Stance.NEUTRAL),
            AnalystAgent("情绪面分析师", "sentiment", Stance.NEUTRAL),
        ]

        # 看多/看空研究员
        self.bull_researcher = AnalystAgent("看多研究员", "general", Stance.BULL)
        self.bear_researcher = AnalystAgent("看空研究员", "general", Stance.BEAR)

    def run_debate(self, stock_data: Dict, rounds: int = 3) -> DebateResult:
        """
        运行辩论流程

        Args:
            stock_data: 股票数据
            rounds: 辩论轮数

        Returns:
            辩论结果
        """
        # 第一阶段：分析师独立分析
        analyst_opinions = []
        for analyst in self.analysts:
            opinion = analyst.analyze(stock_data)
            analyst_opinions.append(opinion)

        # 第二阶段：汇总论点
        bull_arguments = []
        bear_arguments = []

        for opinion in analyst_opinions:
            if opinion.stance == Stance.BULL:
                bull_arguments.extend(opinion.key_points)
            elif opinion.stance == Stance.BEAR:
                bear_arguments.extend(opinion.risks)

        # 第三阶段：多轮辩论
        for round_num in range(rounds):
            # 看多方辩护
            bull_defense = self._defend_position(
                Stance.BULL, bull_arguments, bear_arguments, stock_data
            )
            bull_arguments.extend(bull_defense)

            # 看空方辩护
            bear_defense = self._defend_position(
                Stance.BEAR, bear_arguments, bull_arguments, stock_data
            )
            bear_arguments.extend(bear_defense)

        # 第四阶段：投票决策
        bull_votes = sum(1 for op in analyst_opinions if op.stance == Stance.BULL)
        bear_votes = sum(1 for op in analyst_opinions if op.stance == Stance.BEAR)

        if bull_votes > bear_votes:
            consensus = Stance.BULL
            confidence = bull_votes / len(analyst_opinions)
        elif bear_votes > bull_votes:
            consensus = Stance.BEAR
            confidence = bear_votes / len(analyst_opinions)
        else:
            consensus = Stance.NEUTRAL
            confidence = 0.5

        # 生成最终决策
        final_decision = self._generate_decision(
            consensus, confidence, bull_arguments, bear_arguments
        )

        return DebateResult(
            topic=f"股票{stock_data.get('code', 'UNKNOWN')}投资决策",
            bull_arguments=bull_arguments[:5],  # 取前5个论点
            bear_arguments=bear_arguments[:5],
            consensus=consensus,
            confidence=confidence,
            final_decision=final_decision,
        )

    def _defend_position(
        self, stance: Stance, own_args: List[str], opponent_args: List[str], data: Dict
    ) -> List[str]:
        """
        为立场辩护

        Args:
            stance: 立场
            own_args: 己方论点
            opponent_args: 对方论点
            data: 股票数据

        Returns:
            新增论点
        """
        new_args = []

        if stance == Stance.BULL:
            # 看多方反驳看空观点
            if "主力净流出" in str(opponent_args):
                ddx_10 = data.get("ddx_10", 0)
                if ddx_10 > 0:
                    new_args.append(f"虽然单日流出，但10日DDX={ddx_10}，中期趋势仍向上")

            if "估值偏高" in str(opponent_args):
                profit_growth = data.get("profit_growth", 0)
                if profit_growth > 30:
                    new_args.append(f"高估值匹配高成长，净利润增长{profit_growth}%")

        else:
            # 看空方反驳看多观点
            if "主力净流入" in str(opponent_args):
                ddx_10 = data.get("ddx_10", 0)
                if ddx_10 < 0:
                    new_args.append(
                        f"单日流入可能是诱多，10日DDX={ddx_10}，中期趋势向下"
                    )

            if "均线多头排列" in str(opponent_args):
                kdj_k = data.get("kdj_k", 50)
                if kdj_k > 80:
                    new_args.append(f"均线虽好但KDJ={kdj_k}超买，短期有回调风险")

        return new_args

    def _generate_decision(
        self,
        consensus: Stance,
        confidence: float,
        bull_args: List[str],
        bear_args: List[str],
    ) -> str:
        """生成最终决策文本"""
        decision = f"【辩论结论】{consensus.value}\n\n"
        decision += f"置信度: {confidence * 100:.0f}%\n\n"

        decision += "看多理由:\n"
        for i, arg in enumerate(bull_args[:3], 1):
            decision += f"  {i}. {arg}\n"

        decision += "\n看空理由:\n"
        for i, arg in enumerate(bear_args[:3], 1):
            decision += f"  {i}. {arg}\n"

        if consensus == Stance.BULL:
            decision += "\n建议: 可考虑建仓，设置止损"
        elif consensus == Stance.BEAR:
            decision += "\n建议: 观望或减仓，控制风险"
        else:
            decision += "\n建议: 暂时观望，等待明确信号"

        return decision


def fetch_stock_data(stock_code: str) -> Dict:
    """
    获取股票数据

    Args:
        stock_code: 股票代码

    Returns:
        股票数据字典
    """
    try:
        # 使用数据获取工具
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from data_fetcher import DataFetcher

        fetcher = DataFetcher()
        df = fetcher.get_stock_data(stock_code, days=30)
        quote = fetcher.get_realtime_quote(stock_code)

        if df is not None and not df.empty:
            latest = df.iloc[-1]

            # 计算技术指标
            data = {
                "code": stock_code,
                "price": latest.get("close", 0),
                "change_pct": quote.get("change_pct", 0),
                "volume_ratio": latest.get("volume", 0) / df["volume"].mean()
                if df["volume"].mean() > 0
                else 1,
                "main_inflow": quote.get("main_inflow", 0),
                "ddx_10": quote.get("ddx_10", 0),
                "pe": quote.get("pe", 20),
                "roe": quote.get("roe", 10),
                "profit_growth": quote.get("profit_growth", 10),
                "ma5": df["close"].rolling(5).mean().iloc[-1],
                "ma10": df["close"].rolling(10).mean().iloc[-1],
                "ma20": df["close"].rolling(20).mean().iloc[-1],
            }

            # 计算KDJ
            low_min = df["low"].rolling(9).min()
            high_max = df["high"].rolling(9).max()
            rsv = (df["close"] - low_min) / (high_max - low_min) * 100

            data["kdj_k"] = rsv.ewm(com=2).mean().iloc[-1]
            data["kdj_d"] = (
                data["kdj_k"] * 0.667 + rsv.iloc[-2] * 0.333 if len(rsv) > 1 else 50
            )

            # 计算RSI
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            data["rsi"] = (100 - 100 / (1 + rs)).iloc[-1] if loss.iloc[-1] != 0 else 50

            return data
    except Exception as e:
        print(f"获取数据失败: {e}")

    # 返回模拟数据
    return {
        "code": stock_code,
        "price": 100,
        "change_pct": 0,
        "volume_ratio": 1,
        "main_inflow": 0,
        "ddx_10": 0,
        "pe": 20,
        "roe": 10,
        "profit_growth": 10,
        "ma5": 100,
        "ma10": 100,
        "ma20": 100,
        "kdj_k": 50,
        "kdj_d": 50,
        "rsi": 50,
    }


def main():
    parser = argparse.ArgumentParser(description="多Agent辩论决策")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--stocks", type=str, help="多个股票代码（逗号分隔）")
    parser.add_argument("--rounds", type=int, default=3, help="辩论轮数")

    args = parser.parse_args()

    orchestrator = DebateOrchestrator()

    stocks = []
    if args.stock:
        stocks = [args.stock]
    elif args.stocks:
        stocks = args.stocks.split(",")
    else:
        print("请指定股票代码: --stock 600519 或 --stocks 600519,000001")
        return

    for stock_code in stocks:
        print(f"\n{'=' * 60}")
        print(f"多Agent辩论决策: {stock_code}")
        print(f"{'=' * 60}\n")

        # 获取数据
        stock_data = fetch_stock_data(stock_code)

        # 运行辩论
        result = orchestrator.run_debate(stock_data, args.rounds)

        # 输出结果
        print(f"辩论主题: {result.topic}")
        print(f"\n共识立场: {result.consensus.value}")
        print(f"置信度: {result.confidence * 100:.0f}%")

        print(f"\n看多论点:")
        for i, arg in enumerate(result.bull_arguments, 1):
            print(f"  {i}. {arg}")

        print(f"\n看空论点:")
        for i, arg in enumerate(result.bear_arguments, 1):
            print(f"  {i}. {arg}")

        print(f"\n{result.final_decision}")


if __name__ == "__main__":
    main()
