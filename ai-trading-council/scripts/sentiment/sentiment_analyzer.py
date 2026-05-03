#!/usr/bin/env python3
"""
舆情分析模块
============
整合Tavily API + 妙想搜索 + LongCat AI情感分析

功能：
1. 股票新闻搜索（Tavily + 妙想）
2. 情感分析（LongCat AI）
3. 舆情评分（-10 到 +10）
4. 风险预警

使用方法：
    python sentiment_analyzer.py --stock 600519
    python sentiment_analyzer.py --stocks 600519,000001,300750
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import requests


class SentimentLevel(Enum):
    """情感等级"""

    VERY_BEARISH = "极度看空"  # -10 to -7
    BEARISH = "看空"  # -7 to -3
    NEUTRAL = "中性"  # -3 to +3
    BULLISH = "看多"  # +3 to +7
    VERY_BULLISH = "极度看多"  # +7 to +10


@dataclass
class NewsItem:
    """新闻条目"""

    title: str
    source: str
    url: str
    published_date: str
    summary: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str


@dataclass
class SentimentReport:
    """舆情报告"""

    stock_code: str
    stock_name: str
    overall_sentiment: float  # -10 to +10
    sentiment_level: SentimentLevel
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    key_topics: List[str]
    risk_warnings: List[str]
    opportunities: List[str]
    news_items: List[NewsItem]
    analysis_time: str


class MiaoXiangClient:
    """妙想搜索客户端（中文新闻源）"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        搜索中文新闻

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            新闻列表
        """
        try:
            headers = {"Content-Type": "application/json", "apikey": self.api_key}
            data = {"query": query}

            response = requests.post(
                self.base_url, headers=headers, json=data, timeout=30
            )
            response.raise_for_status()

            result = response.json()

            # 解析结果
            items = (
                result.get("data", {})
                .get("data", {})
                .get("llmSearchResponse", {})
                .get("data", [])
            )

            news_list = []
            for item in items[:max_results]:
                news_list.append(
                    {
                        "title": item.get("title", ""),
                        "source": item.get("insName", "东方财富"),
                        "url": "",
                        "published_date": item.get("date", ""),
                        "content": item.get("content", ""),
                        "info_type": item.get("informationType", "NEWS"),
                    }
                )

            return news_list

        except Exception as e:
            print(f"妙想搜索失败: {e}")
            return []


class TavilyClient:
    """Tavily API客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"

    def search(self, query: str, days: int = 7, max_results: int = 10) -> List[Dict]:
        """
        搜索新闻

        Args:
            query: 搜索关键词
            days: 搜索天数
            max_results: 最大结果数

        Returns:
            新闻列表
        """
        try:
            url = f"{self.base_url}/search"

            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "include_raw_content": False,
                "max_results": max_results,
                "include_domains": [],
                "exclude_domains": [],
                "include_answer": True,
                "days": days,
                "topic": "news",
            }

            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            news_list = []
            for item in results:
                news_list.append(
                    {
                        "title": item.get("title", ""),
                        "source": item.get("url", "").split("/")[2]
                        if item.get("url")
                        else "Unknown",
                        "url": item.get("url", ""),
                        "published_date": item.get("published_date", ""),
                        "content": item.get("content", ""),
                    }
                )

            return news_list

        except Exception as e:
            print(f"Tavily搜索失败: {e}")
            return []


class LongCatClient:
    """LongCat AI客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.longcat.chat/openai"
        self.model = "LongCat-Flash-Lite"

    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            (情感分数, 情感标签)
        """
        try:
            url = f"{self.base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            prompt = f"""分析以下财经新闻的情感倾向，返回JSON格式：

新闻内容：
{text}

请返回：
{{
    "sentiment_score": < -1到1之间的数值，-1表示极度看空，1表示极度看多，0表示中性 >,
    "sentiment_label": "<看空/中性/看多>",
    "key_points": ["关键点1", "关键点2"],
    "risk_factors": ["风险因素1"],
    "opportunities": ["机会1"]
}}

只返回JSON，不要其他内容。"""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的财经分析师，擅长分析新闻情感。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            )

            # 解析JSON
            try:
                result = json.loads(content)
                score = float(result.get("sentiment_score", 0))
                label = result.get("sentiment_label", "中性")
                return score, label
            except:
                return 0.0, "中性"

        except Exception as e:
            print(f"LongCat分析失败: {e}")
            return 0.0, "中性"

    def analyze_batch_sentiment(self, news_list: List[Dict], stock_name: str) -> Dict:
        """
        批量分析新闻情感

        Args:
            news_list: 新闻列表
            stock_name: 股票名称

        Returns:
            综合分析结果
        """
        try:
            url = f"{self.base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # 拼接新闻标题
            news_text = "\n".join(
                [f"{i + 1}. {n.get('title', '')}" for i, n in enumerate(news_list[:10])]
            )

            prompt = f"""分析以下关于{stock_name}的新闻，给出综合舆情评估：

{news_text}

请返回JSON格式：
{{
    "overall_sentiment": <-10到10之间的数值，-10表示极度看空，10表示极度看多>,
    "sentiment_level": "<极度看空/看空/中性/看多/极度看多>",
    "key_topics": ["关键主题1", "关键主题2"],
    "risk_warnings": ["风险预警1"],
    "opportunities": ["投资机会1"],
    "summary": "一句话总结"
}}

只返回JSON，不要其他内容。"""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的财经分析师，擅长舆情分析。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 800,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            )

            try:
                result = json.loads(content)
                return result
            except:
                return {
                    "overall_sentiment": 0,
                    "sentiment_level": "中性",
                    "key_topics": [],
                    "risk_warnings": [],
                    "opportunities": [],
                    "summary": "分析失败",
                }

        except Exception as e:
            print(f"批量分析失败: {e}")
            return {
                "overall_sentiment": 0,
                "sentiment_level": "中性",
                "key_topics": [],
                "risk_warnings": [],
                "opportunities": [],
                "summary": str(e),
            }


class SentimentAnalyzer:
    """舆情分析器"""

    def __init__(self, tavily_key: str, longcat_key: str, miao_key: str = None):
        self.tavily = TavilyClient(tavily_key)
        self.longcat = LongCatClient(longcat_key)
        self.miao = MiaoXiangClient(miao_key) if miao_key else None

    # 股票代码到名称和行业的映射
    STOCK_INFO_MAP = {
        "600519": {
            "name": "Kweichow Moutai",
            "industry": "liquor baijiu",
            "cn_name": "贵州茅台",
        },
        "300750": {"name": "CATL", "industry": "battery EV", "cn_name": "宁德时代"},
        "002594": {"name": "BYD", "industry": "EV auto", "cn_name": "比亚迪"},
        "002460": {
            "name": "Ganfeng Lithium",
            "industry": "lithium battery",
            "cn_name": "赣锋锂业",
        },
        "002475": {
            "name": "Luxshare Precision",
            "industry": "electronics connector",
            "cn_name": "立讯精密",
        },
        "601138": {
            "name": "Foxconn Industrial Internet",
            "industry": "manufacturing",
            "cn_name": "工业富联",
        },
        "002281": {
            "name": "Accelink Technologies",
            "industry": "optical communication",
            "cn_name": "光迅科技",
        },
        "002463": {
            "name": "Shanghai Electric",
            "industry": "PCB electronics",
            "cn_name": "沪电股份",
        },
        "000988": {
            "name": "Hgtech",
            "industry": "laser equipment",
            "cn_name": "华工科技",
        },
        "300476": {
            "name": "Shenghong Technology",
            "industry": "PCB electronics",
            "cn_name": "胜宏科技",
        },
        "002916": {
            "name": "Shennan Circuits",
            "industry": "PCB semiconductor",
            "cn_name": "深南电路",
        },
        "603019": {
            "name": "Sugon",
            "industry": "server computing",
            "cn_name": "中科曙光",
        },
        "603931": {
            "name": "Grenland",
            "industry": "chemical materials",
            "cn_name": "格林达",
        },
        "000001": {
            "name": "Ping An Bank",
            "industry": "banking finance",
            "cn_name": "平安银行",
        },
        "000858": {
            "name": "Wuliangye",
            "industry": "liquor baijiu",
            "cn_name": "五粮液",
        },
        "601318": {
            "name": "Ping An Insurance",
            "industry": "insurance finance",
            "cn_name": "中国平安",
        },
        "002415": {
            "name": "Hikvision",
            "industry": "security AI",
            "cn_name": "海康威视",
        },
        "300059": {"name": "East Money", "industry": "fintech", "cn_name": "东方财富"},
        "002304": {
            "name": "Yanghe Brewery",
            "industry": "liquor",
            "cn_name": "洋河股份",
        },
        "000568": {
            "name": "Luzhou Laojiao",
            "industry": "liquor baijiu",
            "cn_name": "泸州老窖",
        },
    }

    # 行业关键词映射（用于搜索优化）
    INDUSTRY_KEYWORDS = {
        "liquor": ["baijiu", "wine", "alcohol", "beverage"],
        "battery": ["lithium", "EV", "electric vehicle", "energy storage"],
        "EV": ["electric vehicle", "NEV", "new energy", "BYD", "Tesla"],
        "electronics": ["semiconductor", "chip", "PCB", "connector"],
        "finance": ["bank", "insurance", "fintech", "investment"],
    }

    def analyze_stock(
        self, stock_code: str, stock_name: str, days: int = 7
    ) -> SentimentReport:
        """
        分析单只股票舆情

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            days: 分析天数

        Returns:
            舆情报告
        """
        print(f"正在分析 {stock_name}({stock_code}) 舆情...")

        # 1. 获取股票信息
        stock_info = self.STOCK_INFO_MAP.get(stock_code, {})
        english_name = stock_info.get("name", stock_name)
        industry = stock_info.get("industry", "")
        cn_name = stock_info.get("cn_name", stock_name)

        # 2. 搜索新闻（双源）
        news_list = []

        # 2.1 妙想搜索（中文新闻，优先）
        if self.miao:
            print(f"  [妙想] 搜索中文新闻...")
            cn_query = f"{cn_name} 最新新闻"
            miao_news = self.miao.search(cn_query, max_results=10)
            if miao_news:
                print(f"  [妙想] 找到 {len(miao_news)} 条新闻")
                news_list.extend(miao_news)

        # 2.2 Tavily搜索（英文新闻，补充）
        if industry:
            en_query = f"{english_name} {industry} stock China"
        else:
            en_query = f"{english_name} stock China"

        print(f"  [Tavily] 搜索英文新闻: {en_query}")
        tavily_news = self.tavily.search(en_query, days=days, max_results=10)
        if tavily_news:
            print(f"  [Tavily] 找到 {len(tavily_news)} 条新闻")
            news_list.extend(tavily_news)

        # 去重（按标题）
        seen_titles = set()
        unique_news = []
        for news in news_list:
            title = news.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)

        news_list = unique_news[:15]  # 最多15条

        if not news_list:
            print(f"  未找到相关新闻")
            return SentimentReport(
                stock_code=stock_code,
                stock_name=stock_name,
                overall_sentiment=0,
                sentiment_level=SentimentLevel.NEUTRAL,
                news_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                key_topics=[],
                risk_warnings=["无新闻数据"],
                opportunities=[],
                news_items=[],
                analysis_time=datetime.now().isoformat(),
            )

        print(f"  合计找到 {len(news_list)} 条新闻（去重后）")

        # 2. 批量情感分析
        batch_result = self.longcat.analyze_batch_sentiment(news_list, stock_name)

        # 3. 单条新闻情感分析
        news_items = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for news in news_list[:10]:
            score, label = self.longcat.analyze_sentiment(news.get("title", ""))

            if score > 0.3:
                positive_count += 1
            elif score < -0.3:
                negative_count += 1
            else:
                neutral_count += 1

            news_items.append(
                NewsItem(
                    title=news.get("title", ""),
                    source=news.get("source", ""),
                    url=news.get("url", ""),
                    published_date=news.get("published_date", ""),
                    summary=news.get("content", "")[:200],
                    sentiment_score=score,
                    sentiment_label=label,
                )
            )

        # 4. 确定情感等级
        overall = batch_result.get("overall_sentiment", 0)
        if overall >= 7:
            level = SentimentLevel.VERY_BULLISH
        elif overall >= 3:
            level = SentimentLevel.BULLISH
        elif overall <= -7:
            level = SentimentLevel.VERY_BEARISH
        elif overall <= -3:
            level = SentimentLevel.BEARISH
        else:
            level = SentimentLevel.NEUTRAL

        return SentimentReport(
            stock_code=stock_code,
            stock_name=stock_name,
            overall_sentiment=overall,
            sentiment_level=level,
            news_count=len(news_list),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            key_topics=batch_result.get("key_topics", []),
            risk_warnings=batch_result.get("risk_warnings", []),
            opportunities=batch_result.get("opportunities", []),
            news_items=news_items,
            analysis_time=datetime.now().isoformat(),
        )

    def generate_report(self, report: SentimentReport) -> str:
        """生成报告文本"""
        lines = []
        lines.append(f"# {report.stock_name}({report.stock_code}) 舆情分析报告")
        lines.append(f"\n**分析时间**: {report.analysis_time}")
        lines.append(f"\n---")

        lines.append(f"\n## 舆情概览")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 综合评分 | {report.overall_sentiment:.1f} |")
        lines.append(f"| 情感等级 | {report.sentiment_level.value} |")
        lines.append(f"| 新闻数量 | {report.news_count} |")
        lines.append(f"| 正面新闻 | {report.positive_count} |")
        lines.append(f"| 负面新闻 | {report.negative_count} |")
        lines.append(f"| 中性新闻 | {report.neutral_count} |")

        if report.key_topics:
            lines.append(f"\n## 关键主题")
            for topic in report.key_topics[:5]:
                lines.append(f"- {topic}")

        if report.risk_warnings:
            lines.append(f"\n## ⚠️ 风险预警")
            for risk in report.risk_warnings[:3]:
                lines.append(f"- {risk}")

        if report.opportunities:
            lines.append(f"\n## ✅ 投资机会")
            for opp in report.opportunities[:3]:
                lines.append(f"- {opp}")

        if report.news_items:
            lines.append(f"\n## 新闻详情")
            lines.append(f"\n| 标题 | 来源 | 情感 |")
            lines.append(f"|------|------|------|")
            for news in report.news_items[:10]:
                sentiment_emoji = (
                    "🔴"
                    if news.sentiment_score < -0.3
                    else "🟢"
                    if news.sentiment_score > 0.3
                    else "⚪"
                )
                lines.append(
                    f"| {news.title[:30]}... | {news.source} | {sentiment_emoji} {news.sentiment_label} |"
                )

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="舆情分析")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--stocks", type=str, help="多个股票代码（逗号分隔）")
    parser.add_argument("--days", type=int, default=7, help="分析天数")
    parser.add_argument("--save", action="store_true", help="保存报告")

    args = parser.parse_args()

    # API Keys
    tavily_key = os.environ.get(
        "TAVILY_API_KEY", "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"
    )
    longcat_key = os.environ.get("LONGCAT_API_KEY", "ak_2hA4hD5K28mC0Vd6PL1mu1qk3dX6r")
    miao_key = os.environ.get(
        "MX_APIKEY", "mkt_TWs49QJsDQJn-tVRHqPwmdWmTFO5_vqSpwUPfN-Ti6M"
    )

    analyzer = SentimentAnalyzer(tavily_key, longcat_key, miao_key)

    stocks = []
    if args.stock:
        stocks = [(args.stock, args.stock)]
    elif args.stocks:
        for code in args.stocks.split(","):
            stocks.append((code.strip(), code.strip()))
    else:
        print("请指定股票代码: --stock 600519 或 --stocks 600519,000001")
        return

    for stock_code, stock_name in stocks:
        print(f"\n{'=' * 60}")
        print(f"舆情分析: {stock_name}({stock_code})")
        print(f"{'=' * 60}\n")

        report = analyzer.analyze_stock(stock_code, stock_name, args.days)

        # 输出报告
        report_text = analyzer.generate_report(report)
        print(report_text)

        # 保存报告
        if args.save:
            filename = f"sentiment_{stock_code}_{datetime.now().strftime('%Y%m%d')}.md"
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                filename,
            )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"\n报告已保存: {filepath}")


if __name__ == "__main__":
    main()
