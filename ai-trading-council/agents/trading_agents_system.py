"""
多空辩论系统 - 借鉴TradingAgents架构

核心机制：
1. 多头分析师 vs 空头分析师辩论
2. 风控辩论（激进/保守/中立）
3. 5级评级输出（Buy/Overweight/Hold/Underweight/Sell）
"""

from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# 评级类型
# ---------------------------------------------------------------------------


class PortfolioRating(str, Enum):
    """5级评级系统"""

    BUY = "Buy"  # 强烈买入
    OVERWEIGHT = "Overweight"  # 增加持仓
    HOLD = "Hold"  # 维持现状
    UNDERWEIGHT = "Underweight"  # 减少持仓
    SELL = "Sell"  # 卖出


class TraderAction(str, Enum):
    """3级交易动作"""

    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


# ---------------------------------------------------------------------------
# 结构化输出
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """研究员决策输出"""

    recommendation: PortfolioRating = Field(
        description="投资建议：Buy/Overweight/Hold/Underweight/Sell"
    )
    rationale: str = Field(description="决策理由，总结多空辩论的关键论点")
    strategic_actions: str = Field(description="具体操作建议，包括仓位管理")


class TraderProposal(BaseModel):
    """交易员提案"""

    action: TraderAction = Field(description="交易方向：Buy/Hold/Sell")
    reasoning: str = Field(description="交易理由，基于分析师报告")
    entry_price: Optional[float] = Field(default=None, description="建议入场价")
    stop_loss: Optional[float] = Field(default=None, description="止损价")
    position_sizing: Optional[str] = Field(
        default=None, description="仓位建议，如'5% of portfolio'"
    )


class PortfolioDecision(BaseModel):
    """投资组合经理最终决策"""

    rating: PortfolioRating = Field(
        description="最终评级：Buy/Overweight/Hold/Underweight/Sell"
    )
    executive_summary: str = Field(
        description="执行摘要：入场策略、仓位、风险水平、时间周期"
    )
    investment_thesis: str = Field(description="投资逻辑，基于分析师辩论的具体证据")
    price_target: Optional[float] = Field(default=None, description="目标价")
    time_horizon: Optional[str] = Field(
        default=None, description="建议持有周期，如'3-6 months'"
    )


# ---------------------------------------------------------------------------
# 多空辩论系统
# ---------------------------------------------------------------------------


class BullBearDebate:
    """多头 vs 空头辩论系统"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def bull_argument(self, state: Dict) -> str:
        """多头观点"""
        prompt = f"""你是一位多头分析师，负责为买入该股票构建强有力的论据。

关注要点：
- 成长潜力：市场机会、收入预期、可扩展性
- 竞争优势：独特产品、强大品牌、市场主导地位
- 积极指标：财务健康、行业趋势、近期利好消息
- 反驳空头：用具体数据和合理推理批判空头论点

可用资源：
- 市场研究报告：{state.get("market_report", "N/A")}
- 社交媒体情绪：{state.get("sentiment_report", "N/A")}
- 新闻报告：{state.get("news_report", "N/A")}
- 基本面报告：{state.get("fundamentals_report", "N/A")}
- 辩论历史：{state.get("debate_history", "")}
- 最近空头论点：{state.get("bear_response", "")}

请用对话风格呈现论点，直接回应空头分析师的观点，进行动态辩论。"""

        response = self.llm.invoke(prompt)
        return f"多头分析师：{response.content}"

    def bear_argument(self, state: Dict) -> str:
        """空头观点"""
        prompt = f"""你是一位空头分析师，负责为卖出/避免该股票构建强有力的论据。

关注要点：
- 风险因素：市场威胁、竞争压力、监管风险
- 财务担忧：高估值、盈利能力、债务水平
- 负面指标：行业衰退、负面新闻、管理层问题
- 反驳多头：用具体数据和合理推理批判多头论点

可用资源：
- 市场研究报告：{state.get("market_report", "N/A")}
- 社交媒体情绪：{state.get("sentiment_report", "N/A")}
- 新闻报告：{state.get("news_report", "N/A")}
- 基本面报告：{state.get("fundamentals_report", "N/A")}
- 辩论历史：{state.get("debate_history", "")}
- 最近多头论点：{state.get("bull_response", "")}

请用对话风格呈现论点，直接回应多头分析师的观点，进行动态辩论。"""

        response = self.llm.invoke(prompt)
        return f"空头分析师：{response.content}"

    def run_debate(self, state: Dict, rounds: int = 3) -> Dict:
        """运行多空辩论"""
        debate_history = []
        bull_history = []
        bear_history = []

        for i in range(rounds):
            # 多头发言
            bull_arg = self.bull_argument(
                {
                    **state,
                    "debate_history": "\n".join(debate_history),
                    "bear_response": bear_history[-1] if bear_history else "",
                }
            )
            debate_history.append(bull_arg)
            bull_history.append(bull_arg)

            # 空头发言
            bear_arg = self.bear_argument(
                {
                    **state,
                    "debate_history": "\n".join(debate_history),
                    "bull_response": bull_history[-1],
                }
            )
            debate_history.append(bear_arg)
            bear_history.append(bear_arg)

        return {
            "debate_history": debate_history,
            "bull_history": bull_history,
            "bear_history": bear_history,
        }


# ---------------------------------------------------------------------------
# 风控辩论系统
# ---------------------------------------------------------------------------


class RiskDebate:
    """风控辩论系统：激进 vs 保守 vs 中立"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def aggressive_argument(self, state: Dict) -> str:
        """激进观点"""
        prompt = f"""你是一位激进型风险分析师，主张积极交易。

关注要点：
- 机会成本：错过机会的风险
- 市场动能：趋势延续的可能性
- 收益潜力：最大化收益的策略
- 反驳保守：为什么保守策略会错失机会

可用资源：
- 投资计划：{state.get("investment_plan", "N/A")}
- 交易员提案：{state.get("trader_proposal", "N/A")}
- 辩论历史：{state.get("risk_debate_history", "")}
- 最近保守观点：{state.get("conservative_response", "")}

请用对话风格呈现论点。"""

        response = self.llm.invoke(prompt)
        return f"激进分析师：{response.content}"

    def conservative_argument(self, state: Dict) -> str:
        """保守观点"""
        prompt = f"""你是一位保守型风险分析师，主张谨慎交易。

关注要点：
- 下行风险：潜在损失的可能性
- 市场不确定性：波动性和不可预测因素
- 资金保护：保本优先的策略
- 反驳激进：为什么激进策略风险过高

可用资源：
- 投资计划：{state.get("investment_plan", "N/A")}
- 交易员提案：{state.get("trader_proposal", "N/A")}
- 辩论历史：{state.get("risk_debate_history", "")}
- 最近激进观点：{state.get("aggressive_response", "")}

请用对话风格呈现论点。"""

        response = self.llm.invoke(prompt)
        return f"保守分析师：{response.content}"

    def neutral_argument(self, state: Dict) -> str:
        """中立观点"""
        prompt = f"""你是一位中立型风险分析师，平衡风险与收益。

关注要点：
- 平衡观点：权衡激进和保守的论点
- 条件分析：在不同情况下哪种策略更优
- 风险管理：如何平衡收益与风险
- 综合建议：基于辩论的最佳行动方案

可用资源：
- 投资计划：{state.get("investment_plan", "N/A")}
- 交易员提案：{state.get("trader_proposal", "N/A")}
- 辩论历史：{state.get("risk_debate_history", "")}
- 最近激进观点：{state.get("aggressive_response", "")}
- 最近保守观点：{state.get("conservative_response", "")}

请用对话风格呈现论点。"""

        response = self.llm.invoke(prompt)
        return f"中立分析师：{response.content}"

    def run_debate(self, state: Dict, rounds: int = 2) -> Dict:
        """运行风控辩论"""
        debate_history = []
        aggressive_history = []
        conservative_history = []
        neutral_history = []

        for i in range(rounds):
            # 激进发言
            agg_arg = self.aggressive_argument(
                {
                    **state,
                    "risk_debate_history": "\n".join(debate_history),
                    "conservative_response": conservative_history[-1]
                    if conservative_history
                    else "",
                }
            )
            debate_history.append(agg_arg)
            aggressive_history.append(agg_arg)

            # 保守发言
            con_arg = self.conservative_argument(
                {
                    **state,
                    "risk_debate_history": "\n".join(debate_history),
                    "aggressive_response": aggressive_history[-1],
                }
            )
            debate_history.append(con_arg)
            conservative_history.append(con_arg)

            # 中立发言
            neu_arg = self.neutral_argument(
                {
                    **state,
                    "risk_debate_history": "\n".join(debate_history),
                    "aggressive_response": aggressive_history[-1],
                    "conservative_response": conservative_history[-1],
                }
            )
            debate_history.append(neu_arg)
            neutral_history.append(neu_arg)

        return {
            "risk_debate_history": debate_history,
            "aggressive_history": aggressive_history,
            "conservative_history": conservative_history,
            "neutral_history": neutral_history,
        }


# ---------------------------------------------------------------------------
# 完整决策流程
# ---------------------------------------------------------------------------


class TradingAgentsSystem:
    """完整的TradingAgents决策系统"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.bull_bear_debate = BullBearDebate(llm_client)
        self.risk_debate = RiskDebate(llm_client)

    def research_manager(self, debate_result: Dict) -> ResearchPlan:
        """研究经理：综合多空辩论，形成投资计划"""
        prompt = f"""作为研究经理，综合多空辩论，形成投资计划。

多空辩论历史：
{chr(10).join(debate_result["debate_history"])}

请输出JSON格式：
{{
  "recommendation": "Buy/Overweight/Hold/Underweight/Sell",
  "rationale": "决策理由（2-4句）",
  "strategic_actions": "具体操作建议"
}}"""

        response = self.llm.invoke(prompt)

        # 解析响应
        try:
            content = response.content
            # 尝试提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                # 尝试直接解析
                import re

                json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content

            data = json.loads(json_str)
            return ResearchPlan(**data)
        except Exception as e:
            print(f"研究经理解析错误: {e}")
            print(f"响应内容: {response.content[:200]}")
            # 默认返回Hold
            return ResearchPlan(
                recommendation=PortfolioRating.HOLD,
                rationale="无法解析辩论结果",
                strategic_actions="建议观望",
            )

    def trader(
        self, research_plan: ResearchPlan, analyst_reports: Dict
    ) -> TraderProposal:
        """交易员：将投资计划转化为交易提案"""
        prompt = f"""作为交易员，基于投资计划形成交易提案。

投资计划：
- 建议：{research_plan.recommendation.value}
- 理由：{research_plan.rationale}
- 操作：{research_plan.strategic_actions}

分析师报告：
- 市场报告：{analyst_reports.get("market_report", "N/A")[:500]}
- 基本面报告：{analyst_reports.get("fundamentals_report", "N/A")[:500]}

请输出：
1. action: Buy/Hold/Sell
2. reasoning: 交易理由（2-4句）
3. entry_price: 建议入场价（可选）
4. stop_loss: 止损价（可选）
5. position_sizing: 仓位建议（可选）

以JSON格式输出。"""

        response = self.llm.invoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            data = json.loads(json_str)
            return TraderProposal(**data)
        except:
            return TraderProposal(
                action=TraderAction.HOLD, reasoning="无法解析投资计划"
            )

    def portfolio_manager(
        self, risk_debate: Dict, trader_proposal: TraderProposal
    ) -> PortfolioDecision:
        """投资组合经理：最终决策"""
        prompt = f"""作为投资组合经理，综合风控辩论，做出最终决策。

风控辩论历史：
{chr(10).join(risk_debate["risk_debate_history"][-6:])}

交易员提案：
- 动作：{trader_proposal.action.value}
- 理由：{trader_proposal.reasoning}

请输出：
1. rating: Buy/Overweight/Hold/Underweight/Sell
2. executive_summary: 执行摘要（2-4句）
3. investment_thesis: 投资逻辑
4. price_target: 目标价（可选）
5. time_horizon: 持有周期（可选）

以JSON格式输出。"""

        response = self.llm.invoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            data = json.loads(json_str)
            return PortfolioDecision(**data)
        except:
            return PortfolioDecision(
                rating=PortfolioRating.HOLD,
                executive_summary="无法解析风控辩论",
                investment_thesis="建议观望",
            )

    def run_full_analysis(self, stock_code: str, analyst_reports: Dict) -> Dict:
        """运行完整分析流程"""
        print(f"\n{'=' * 60}")
        print(f"TradingAgents 多智能体决策系统")
        print(f"股票代码: {stock_code}")
        print(f"{'=' * 60}\n")

        # Step 1: 多空辩论
        print("【Step 1】多空辩论...")
        debate_result = self.bull_bear_debate.run_debate(analyst_reports, rounds=2)
        print(f"  - 多头发言次数: {len(debate_result['bull_history'])}")
        print(f"  - 空头发言次数: {len(debate_result['bear_history'])}")

        # Step 2: 研究经理决策
        print("\n【Step 2】研究经理综合决策...")
        research_plan = self.research_manager(debate_result)
        print(f"  - 建议: {research_plan.recommendation.value}")
        print(f"  - 理由: {research_plan.rationale[:100]}...")

        # Step 3: 交易员提案
        print("\n【Step 3】交易员形成提案...")
        trader_proposal = self.trader(research_plan, analyst_reports)
        print(f"  - 动作: {trader_proposal.action.value}")
        print(f"  - 理由: {trader_proposal.reasoning[:100]}...")

        # Step 4: 风控辩论
        print("\n【Step 4】风控辩论...")
        risk_debate = self.risk_debate.run_debate(
            {
                "investment_plan": research_plan.model_dump(),
                "trader_proposal": trader_proposal.model_dump(),
            },
            rounds=1,
        )
        print(f"  - 激进发言次数: {len(risk_debate['aggressive_history'])}")
        print(f"  - 保守发言次数: {len(risk_debate['conservative_history'])}")
        print(f"  - 中立发言次数: {len(risk_debate['neutral_history'])}")

        # Step 5: 投资组合经理最终决策
        print("\n【Step 5】投资组合经理最终决策...")
        final_decision = self.portfolio_manager(risk_debate, trader_proposal)
        print(f"  - 最终评级: {final_decision.rating.value}")
        print(f"  - 执行摘要: {final_decision.executive_summary[:100]}...")

        return {
            "stock_code": stock_code,
            "debate_result": debate_result,
            "research_plan": research_plan,
            "trader_proposal": trader_proposal,
            "risk_debate": risk_debate,
            "final_decision": final_decision,
            "timestamp": datetime.now().isoformat(),
        }


def render_decision_report(result: Dict) -> str:
    """渲染决策报告"""
    decision = result["final_decision"]

    report = f"""# TradingAgents 决策报告

**股票代码**: {result["stock_code"]}
**时间**: {result["timestamp"]}

---

## 最终决策

**评级**: {decision.rating.value}

**执行摘要**: {decision.executive_summary}

**投资逻辑**: {decision.investment_thesis}
"""

    if decision.price_target:
        report += f"\n**目标价**: {decision.price_target}"

    if decision.time_horizon:
        report += f"\n**持有周期**: {decision.time_horizon}"

    # 多空辩论摘要
    debate = result["debate_result"]
    report += f"\n\n---\n\n## 多空辩论摘要\n\n"
    report += f"**多头观点**:\n{debate['bull_history'][-1] if debate['bull_history'] else 'N/A'}\n\n"
    report += f"**空头观点**:\n{debate['bear_history'][-1] if debate['bear_history'] else 'N/A'}\n\n"

    # 风控辩论摘要
    risk = result["risk_debate"]
    report += f"---\n\n## 风控辩论摘要\n\n"
    report += f"**激进观点**:\n{risk['aggressive_history'][-1] if risk['aggressive_history'] else 'N/A'}\n\n"
    report += f"**保守观点**:\n{risk['conservative_history'][-1] if risk['conservative_history'] else 'N/A'}\n\n"
    report += f"**中立观点**:\n{risk['neutral_history'][-1] if risk['neutral_history'] else 'N/A'}\n\n"

    return report


if __name__ == "__main__":
    # 测试代码
    from langchain_openai import ChatOpenAI

    # 使用LongCat API
    llm = ChatOpenAI(
        model="LongCat-Flash-Lite",
        openai_api_key=os.getenv("LONGCAT_API_KEY"),
        openai_api_base="https://api.longcat.chat/openai",
    )

    system = TradingAgentsSystem(llm)

    # 模拟分析师报告
    analyst_reports = {
        "market_report": "股价近期上涨，成交量放大，技术指标向好。",
        "fundamentals_report": "营收增长20%，净利润增长15%，ROE为18%。",
        "sentiment_report": "社交媒体情绪偏正面，机构评级买入。",
        "news_report": "公司发布新产品，市场反响良好。",
    }

    result = system.run_full_analysis("600519", analyst_reports)
    report = render_decision_report(result)
    print("\n" + report)
