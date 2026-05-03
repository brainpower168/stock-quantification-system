"""
TradingAgents 系统测试（模拟版本）
验证多空辩论机制和决策流程
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agents_system import (
    TradingAgentsSystem,
    PortfolioRating,
    TraderAction,
    render_decision_report,
)


class MockLLM:
    """模拟LLM响应"""

    def invoke(self, prompt):
        """模拟调用 - 使用精确匹配避免冲突"""

        # 匹配优先级：投资组合经理 > 研究经理 > 其他
        # 因为投资组合经理的prompt可能包含"研究经理"这个词

        # 1. 投资组合经理（最高优先级，因为prompt可能包含其他角色名）
        if "投资组合经理" in prompt and "最终决策" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """```json
{
  "rating": "Overweight",
  "executive_summary": "建议增持，首次买入5-10%，等回调加仓。止损-5%，止盈分批。关注主力资金流向变化。",
  "investment_thesis": "基本面强劲（ROE 18%，净利润增长15%），技术面向好（均线多头排列，MACD金叉），资金持续流入（主力+5亿，DDX连续5日为正）。主要风险是估值偏高（PE 35），建议分批建仓降低风险。",
  "price_target": 1950,
  "time_horizon": "1-3个月"
}
```"""
                },
            )()

        # 2. 多空辩论
        if "多头分析师" in prompt and "为买入" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """基于以下理由，我强烈建议买入该股票：

1. **成长潜力**：公司营收增长20%，净利润增长15%，ROE达18%，显示强劲增长动力
2. **技术面向好**：股价站上5日、10日、20日均线，MACD金叉，RSI为65，处于健康区间
3. **资金流入**：主力资金净流入5亿元，DDX连续5日为正，10日DDX达4.1，资金趋势稳定
4. **市场情绪**：机构评级买入，社交媒体情绪偏正面，北向资金连续流入

**反驳空头观点**：空头担心的风险确实存在，但当前市场环境和技术面都支持继续上涨，建议积极买入。"""
                },
            )()

        elif "空头分析师" in prompt and "卖出" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """基于以下风险，我建议谨慎操作：

1. **估值风险**：PE为35，PB为12，估值已不便宜，存在回调压力
2. **市场波动**：换手率3.2%，成交量放大，可能存在短期获利盘
3. **外部风险**：宏观经济不确定性，行业竞争加剧
4. **技术指标**：RSI接近超买区间，短期可能面临调整

**反驳多头观点**：虽然基本面良好，但估值偏高，建议等回调后再买入，不要追高。"""
                },
            )()

        # 3. 风控辩论（精确匹配角色）
        elif "激进型风险分析师" in prompt and "积极交易" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """建议积极买入：

1. 当前市场动能强劲，错过机会成本更高
2. 资金持续流入，趋势延续概率大
3. 建议仓位可提高到15-20%
4. 止损设在-5%，风险可控"""
                },
            )()

        elif "保守型风险分析师" in prompt and "谨慎交易" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """建议谨慎操作：

1. 估值偏高，存在回调风险
2. 建议仓位控制在10%以内
3. 等回调到均线支撑再买入
4. 严格止损-3%"""
                },
            )()

        elif "中立型风险分析师" in prompt and "平衡风险" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """综合分析：

1. 基本面良好，但估值偏高
2. 建议分批建仓，首次5%，回调加仓
3. 止损-5%，止盈分批（10%、20%）
4. 关注主力资金流向变化"""
                },
            )()

        # 4. 研究经理（综合多空辩论）
        elif "研究经理" in prompt and "综合多空辩论" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """```json
{
  "recommendation": "Overweight",
  "rationale": "多空辩论显示，多头观点基于强劲的基本面和资金流向，空头主要担心估值风险。综合判断，建议增持但控制仓位。",
  "strategic_actions": "建议分批建仓，首次买入5-10%，等回调到均线支撑加仓。止损-5%，止盈分批（10%卖一半，20%再卖一半）。"
}
```"""
                },
            )()

        # 5. 交易员（形成交易提案）
        elif "交易员" in prompt and "交易提案" in prompt:
            return type(
                "Response",
                (),
                {
                    "content": """```json
{
  "action": "Buy",
  "reasoning": "基于研究经理的增持建议，结合技术面和资金流向，建议买入。当前价格处于均线之上，MACD金叉，主力资金持续流入。",
  "entry_price": 1840,
  "stop_loss": 1750,
  "position_sizing": "首次5-10%仓位"
}
```"""
                },
            )()

        else:
            return type("Response", (), {"content": "分析完成，建议持有观望。"})()


def test_trading_agents_system():
    """测试TradingAgents系统"""
    print("\n" + "=" * 60)
    print("TradingAgents 多智能体决策系统测试")
    print("=" * 60 + "\n")

    # 创建模拟LLM
    mock_llm = MockLLM()

    # 创建系统
    system = TradingAgentsSystem(mock_llm)

    # 准备分析师报告
    analyst_reports = {
        "market_report": """市场分析报告

当前价格: 1850元
涨跌幅: +2.5%
成交量: 15000手
换手率: 3.2%

技术指标:
- 5日均线: 1830元
- 10日均线: 1810元
- 20日均线: 1780元
- RSI: 65
- MACD: 金叉""",
        "fundamentals_report": """基本面分析报告

财务指标:
- 市盈率PE: 35
- 市净率PB: 12
- ROE: 18%
- 净利润增长率: 15%

资金流向:
- 主力净流入: 50000万元
- DDX: 2.5
- 5日DDX: 3.2
- 10日DDX: 4.1""",
        "sentiment_report": """情绪分析报告

市场情绪:
- 涨停基因: 45
- 机构评级: 买入
- 社交媒体情绪: 偏正面

资金情绪:
- 主力资金趋势: 流入
- 散户情绪: 乐观""",
        "news_report": """新闻分析报告

1. 公司发布新产品，市场反响良好
2. 机构上调评级至买入
3. 北向资金连续3日净流入""",
    }

    # 运行完整分析
    result = system.run_full_analysis("600519", analyst_reports)

    # 生成报告
    report = render_decision_report(result)
    print("\n" + report)

    # 验证结果
    print("\n" + "=" * 60)
    print("测试结果验证")
    print("=" * 60)

    decision = result["final_decision"]
    print(f"\n最终评级: {decision.rating.value}")
    print(f"评级类型: {type(decision.rating).__name__}")
    print(f"执行摘要长度: {len(decision.executive_summary)} 字符")
    print(f"投资逻辑长度: {len(decision.investment_thesis)} 字符")

    if decision.price_target:
        print(f"目标价: {decision.price_target}元")

    if decision.time_horizon:
        print(f"持有周期: {decision.time_horizon}")

    # 验证辩论历史
    debate = result["debate_result"]
    print(f"\n多空辩论:")
    print(f"  - 多头发言次数: {len(debate['bull_history'])}")
    print(f"  - 空头发言次数: {len(debate['bear_history'])}")

    risk = result["risk_debate"]
    print(f"\n风控辩论:")
    print(f"  - 激进发言次数: {len(risk['aggressive_history'])}")
    print(f"  - 保守发言次数: {len(risk['conservative_history'])}")
    print(f"  - 中立发言次数: {len(risk['neutral_history'])}")

    # 保存报告
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, "trading_agents_test_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存到: {report_path}")

    return result


if __name__ == "__main__":
    result = test_trading_agents_system()

    print("\n" + "=" * 60)
    print("✅ TradingAgents系统测试完成")
    print("=" * 60)
