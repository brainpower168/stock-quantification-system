"""测试投资组合经理解析"""

import sys
import json

sys.path.insert(0, ".")

from agents.test_trading_agents import MockLLM
from agents.trading_agents_system import (
    TradingAgentsSystem,
    TraderProposal,
    TraderAction,
)

llm = MockLLM()
system = TradingAgentsSystem(llm)

# 构建prompt
risk_debate = {
    "risk_debate_history": [
        "激进分析师：建议积极买入",
        "保守分析师：建议谨慎操作",
        "中立分析师：综合分析",
    ]
}

trader_proposal = TraderProposal(
    action=TraderAction.BUY, reasoning="基于研究经理的增持建议"
)

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

print("=== Prompt ===")
print(prompt)
print()

response = llm.invoke(prompt)
print("=== Response ===")
print(response.content)
print()

# 解析
try:
    content = response.content
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        json_str = content.split("```")[1].split("```")[0].strip()
    else:
        json_str = content

    print("=== JSON String ===")
    print(json_str)
    print()

    data = json.loads(json_str)
    print("=== Parsed Data ===")
    print(data)
except Exception as e:
    print(f"解析错误: {e}")
    import traceback

    traceback.print_exc()
