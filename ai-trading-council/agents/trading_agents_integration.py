"""
TradingAgents 集成脚本
将多空辩论机制整合到现有AI Trading Council
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
from langchain_openai import ChatOpenAI


class TradingAgentsIntegration:
    """TradingAgents与现有系统的集成"""

    def __init__(self):
        # 初始化LLM（使用讯飞API）
        # 讯飞API Key格式: appid:api_key:api_secret
        xunfei_key = os.getenv("XUNFEI_API_KEY", "")
        if not xunfei_key:
            raise ValueError("XUNFEI_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="generalv3.5",
            openai_api_key=xunfei_key,
            openai_api_base="https://spark-api-open.xf-yun.com/v1",
            temperature=0.7,
        )

        self.system = TradingAgentsSystem(self.llm)

    def prepare_analyst_reports(self, stock_data: dict) -> dict:
        """准备分析师报告"""
        return {
            "market_report": self._generate_market_report(stock_data),
            "fundamentals_report": self._generate_fundamentals_report(stock_data),
            "sentiment_report": self._generate_sentiment_report(stock_data),
            "news_report": self._generate_news_report(stock_data),
        }

    def _generate_market_report(self, data: dict) -> str:
        """生成市场报告"""
        price = data.get("price", 0)
        change_pct = data.get("change_pct", 0)
        volume = data.get("volume", 0)
        turnover_rate = data.get("turnover_rate", 0)

        report = f"""市场分析报告

当前价格: {price}元
涨跌幅: {change_pct}%
成交量: {volume}手
换手率: {turnover_rate}%

技术指标:
- 5日均线: {data.get("ma5", "N/A")}
- 10日均线: {data.get("ma10", "N/A")}
- 20日均线: {data.get("ma20", "N/A")}
- RSI: {data.get("rsi", "N/A")}
- MACD: {data.get("macd", "N/A")}
"""
        return report

    def _generate_fundamentals_report(self, data: dict) -> str:
        """生成基本面报告"""
        report = f"""基本面分析报告

财务指标:
- 市盈率PE: {data.get("pe", "N/A")}
- 市净率PB: {data.get("pb", "N/A")}
- ROE: {data.get("roe", "N/A")}%
- 净利润增长率: {data.get("profit_growth", "N/A")}%

资金流向:
- 主力净流入: {data.get("main_inflow", 0)}万元
- DDX: {data.get("ddx", 0)}
- 5日DDX: {data.get("ddx_5d", 0)}
- 10日DDX: {data.get("ddx_10d", 0)}
"""
        return report

    def _generate_sentiment_report(self, data: dict) -> str:
        """生成情绪报告"""
        report = f"""情绪分析报告

市场情绪:
- 涨停基因: {data.get("limit_gene", "N/A")}
- 机构评级: {data.get("rating", "N/A")}
- 社交媒体情绪: {data.get("social_sentiment", "中性")}

资金情绪:
- 主力资金趋势: {"流入" if data.get("main_inflow", 0) > 0 else "流出"}
- 散户情绪: {data.get("retail_sentiment", "中性")}
"""
        return report

    def _generate_news_report(self, data: dict) -> str:
        """生成新闻报告"""
        news_list = data.get("news", [])
        report = "新闻分析报告\n\n"
        if news_list:
            for i, news in enumerate(news_list[:5], 1):
                report += f"{i}. {news}\n"
        else:
            report += "暂无重要新闻\n"
        return report

    def analyze_stock(self, stock_code: str, stock_data: dict) -> dict:
        """分析股票"""
        # 准备分析师报告
        analyst_reports = self.prepare_analyst_reports(stock_data)

        # 运行TradingAgents系统
        result = self.system.run_full_analysis(stock_code, analyst_reports)

        # 生成报告
        report = render_decision_report(result)

        return {
            "result": result,
            "report": report,
            "final_decision": result["final_decision"].model_dump(),
        }


def main():
    """测试集成"""
    integration = TradingAgentsIntegration()

    # 模拟股票数据
    stock_data = {
        "price": 1850.0,
        "change_pct": 2.5,
        "volume": 15000,
        "turnover_rate": 3.2,
        "ma5": 1830,
        "ma10": 1810,
        "ma20": 1780,
        "rsi": 65,
        "macd": "金叉",
        "pe": 35,
        "pb": 12,
        "roe": 18,
        "profit_growth": 15,
        "main_inflow": 50000,
        "ddx": 2.5,
        "ddx_5d": 3.2,
        "ddx_10d": 4.1,
        "limit_gene": 45,
        "rating": "买入",
        "social_sentiment": "偏正面",
        "retail_sentiment": "乐观",
        "news": [
            "公司发布新产品，市场反响良好",
            "机构上调评级至买入",
            "北向资金连续3日净流入",
        ],
    }

    result = integration.analyze_stock("600519", stock_data)
    print(result["report"])

    # 保存报告
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, "trading_agents_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["report"])

    print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
