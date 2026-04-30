#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票舆情分析主程序
整合多数据源的股票新闻舆情分析系统
"""

import os
import sys
import json
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SentimentEngine:
    """情绪分析引擎"""

    # 正面关键词
    POSITIVE_KEYWORDS = [
        "涨停",
        "大涨",
        "利好",
        "业绩大增",
        "中标",
        "签约",
        "突破",
        "创新高",
        "翻倍",
        "暴涨",
        "强势",
        "看好",
        "增持",
        "回购",
        "分红",
        "并购",
        "重组",
        "获批",
        "订单",
        "合作",
        "扩张",
    ]

    # 负面关键词
    NEGATIVE_KEYWORDS = [
        "跌停",
        "大跌",
        "利空",
        "亏损",
        "减持",
        "处罚",
        "调查",
        "诉讼",
        "违规",
        "造假",
        "退市",
        "破产",
        "清算",
        "质押",
        "冻结",
        "下滑",
        "下降",
        "减少",
        "关闭",
        "裁员",
        "违约",
        "风险",
    ]

    # 重大负面关键词（高风险）
    SEVERE_NEGATIVE_KEYWORDS = [
        "立案调查",
        "行政处罚",
        "退市风险",
        "财务造假",
        "重大违规",
        "涉嫌犯罪",
        "被查",
        "冻结",
        "强制",
        "禁入",
    ]

    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Any]:
        """
        分析文本情绪

        Args:
            text: 待分析文本

        Returns:
            情绪分析结果
        """
        if not text:
            return {"sentiment": "neutral", "score": 50, "keywords": []}

        text = text.lower()

        # 检测重大负面
        severe_negative = [kw for kw in cls.SEVERE_NEGATIVE_KEYWORDS if kw in text]
        if severe_negative:
            return {
                "sentiment": "severe_negative",
                "score": 10,
                "keywords": severe_negative,
                "alert": True,
            }

        # 统计正负面关键词
        positive_found = [kw for kw in cls.POSITIVE_KEYWORDS if kw in text]
        negative_found = [kw for kw in cls.NEGATIVE_KEYWORDS if kw in text]

        # 计算情绪评分
        positive_count = len(positive_found)
        negative_count = len(negative_found)

        # 基础分50分
        base_score = 50
        # 正面每个+5分，负面每个-8分
        score = base_score + (positive_count * 5) - (negative_count * 8)
        # 限制在0-100
        score = max(0, min(100, score))

        # 判断情绪
        if score >= 70:
            sentiment = "positive"
        elif score >= 40:
            sentiment = "neutral"
        else:
            sentiment = "negative"

        return {
            "sentiment": sentiment,
            "score": score,
            "positive_keywords": positive_found,
            "negative_keywords": negative_found,
            "alert": score < 30,
        }

    @classmethod
    def get_risk_level(cls, score: int) -> Dict[str, str]:
        """
        根据评分获取风险等级

        Args:
            score: 情绪评分

        Returns:
            风险等级信息
        """
        if score < 30:
            return {"level": "high", "label": "高风险", "emoji": "🔴"}
        elif score < 50:
            return {"level": "medium", "label": "中风险", "emoji": "🟡"}
        else:
            return {"level": "low", "label": "低风险", "emoji": "🟢"}


class NewsSourceManager:
    """多源新闻管理器"""

    def __init__(self):
        self.iwencai_key = os.getenv("IWENCAI_API_KEY")
        self.mx_apikey = os.getenv("MX_APIKEY")

    def search_iwencai(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        问财新闻搜索

        Args:
            query: 搜索关键词
            limit: 返回数量

        Returns:
            新闻列表
        """
        if not self.iwencai_key:
            logger.warning("问财API Key未配置")
            return []

        try:
            # 使用问财正确的API地址
            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.iwencai_key}",
            }
            # 构造新闻查询
            payload = {
                "query": f"{query} 相关新闻",
                "page": "1",
                "limit": str(limit),
                "is_cache": "1",
                "expand_index": "true",
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # 检查状态码
                if data.get("status_code", 0) != 0:
                    logger.error(f"问财API返回错误: {data.get('status_msg', '')}")
                    return []

                # 解析返回数据
                articles = []
                datas = data.get("datas", [])

                for item in datas[:limit]:
                    # 问财返回的数据结构可能不同，需要适配
                    articles.append(
                        {
                            "title": item.get("title", item.get("新闻标题", "")),
                            "summary": item.get("summary", item.get("内容", ""))[:200]
                            if item.get("summary") or item.get("内容")
                            else "",
                            "url": item.get("url", item.get("链接", "")),
                            "publish_date": item.get(
                                "publish_date", item.get("发布时间", "")
                            ),
                            "source": "问财",
                        }
                    )
                return articles
            else:
                logger.error(f"问财API请求失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"问财搜索异常: {str(e)}")
            return []

    def search_mx(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        妙想新闻搜索

        Args:
            query: 搜索关键词
            limit: 返回数量

        Returns:
            新闻列表
        """
        if not self.mx_apikey:
            logger.warning("妙想API Key未配置")
            return []

        try:
            # 使用正确的妙想API地址
            url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
            headers = {
                "Content-Type": "application/json",
                "apikey": self.mx_apikey,
            }
            payload = {"query": query}

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # 解析妙想返回的数据结构: data.data.llmSearchResponse.data
                articles = []
                result_data = data.get("data", {})
                inner_data = result_data.get("data", {})
                search_response = inner_data.get("llmSearchResponse", {})
                items = search_response.get("data", [])

                for item in items[:limit]:
                    articles.append(
                        {
                            "title": item.get("title", ""),
                            "summary": item.get("content", "")[:200]
                            if item.get("content")
                            else "",
                            "url": item.get("url", ""),
                            "publish_date": item.get("date", "").split()[0]
                            if item.get("date")
                            else "",
                            "source": "妙想",
                            "type": item.get("informationType", ""),
                            "entity": item.get("entityFullName", ""),
                        }
                    )
                logger.info(f"妙想搜索成功: {len(articles)}条")
                return articles
            else:
                logger.error(f"妙想API请求失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"妙想搜索异常: {str(e)}")
            return []

        try:
            # 使用正确的妙想API地址
            url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
            headers = {
                "Content-Type": "application/json",
                "apikey": self.mx_apikey,
            }
            payload = {"query": query}

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # 解析妙想返回的数据结构
                articles = []
                result_data = data.get("data", data.get("result", {}))

                # 尝试从不同字段提取新闻列表
                if isinstance(result_data, dict):
                    news_list = result_data.get(
                        "newsList", result_data.get("articles", [])
                    )
                elif isinstance(result_data, list):
                    news_list = result_data
                else:
                    news_list = []

                for article in news_list[:limit]:
                    articles.append(
                        {
                            "title": article.get("title", ""),
                            "summary": article.get(
                                "summary", article.get("content", "")
                            )[:200]
                            if article.get("summary") or article.get("content")
                            else "",
                            "url": article.get("url", ""),
                            "publish_date": article.get(
                                "publishDate", article.get("publish_time", "")
                            ),
                            "source": "妙想",
                        }
                    )
                return articles
            else:
                logger.error(f"妙想API请求失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"妙想搜索异常: {str(e)}")
            return []

    def search_all(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        多源搜索并去重

        Args:
            query: 搜索关键词
            limit: 每个源返回数量

        Returns:
            合并去重后的新闻列表
        """
        all_news = []

        # 问财搜索
        iwencai_news = self.search_iwencai(query, limit)
        all_news.extend(iwencai_news)

        # 妙想搜索
        mx_news = self.search_mx(query, limit)
        all_news.extend(mx_news)

        # 去重（按标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)

        logger.info(
            f"多源搜索完成: 问财{len(iwencai_news)}篇, 妙想{len(mx_news)}篇, 去重后{len(unique_news)}篇"
        )
        return unique_news


class StockSentimentAnalyzer:
    """股票舆情分析器"""

    def __init__(self):
        self.news_manager = NewsSourceManager()
        self.sentiment_engine = SentimentEngine()

    def analyze(
        self, stock_code: str, stock_name: str = None, days: int = 7
    ) -> Dict[str, Any]:
        """
        分析股票舆情

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            days: 搜索最近多少天的新闻

        Returns:
            舆情分析报告
        """
        logger.info(f"开始分析股票舆情: {stock_code}")

        # 构建搜索关键词 - 优化为股票相关
        if stock_name:
            query = f"{stock_name}股票 {stock_code}"
        else:
            query = f"{stock_code}股票"

        # 搜索新闻
        news_list = self.news_manager.search_all(query, limit=15)

        if not news_list:
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "news_count": 0,
                "sentiment_score": 50,
                "sentiment": "neutral",
                "risk_level": {"level": "unknown", "label": "无数据", "emoji": "⚪"},
                "news": [],
                "alerts": [],
                "positives": [],
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # 分析每条新闻的情绪
        analyzed_news = []
        total_score = 0
        alerts = []
        positives = []

        for news in news_list:
            # 合并标题和摘要进行分析
            text = f"{news.get('title', '')} {news.get('summary', '')}"
            sentiment_result = self.sentiment_engine.analyze_text(text)

            analyzed_news.append(
                {
                    **news,
                    "sentiment": sentiment_result["sentiment"],
                    "sentiment_score": sentiment_result["score"],
                    "alert": sentiment_result.get("alert", False),
                }
            )

            total_score += sentiment_result["score"]

            # 收集警报
            if sentiment_result.get("alert"):
                alerts.append(
                    {
                        "title": news.get("title", ""),
                        "keywords": sentiment_result.get("negative_keywords", []),
                    }
                )

            # 收集利好
            if sentiment_result["sentiment"] == "positive":
                positives.append(
                    {
                        "title": news.get("title", ""),
                        "keywords": sentiment_result.get("positive_keywords", []),
                    }
                )

        # 计算综合评分
        avg_score = total_score / len(news_list) if news_list else 50
        overall_sentiment = (
            "positive"
            if avg_score >= 70
            else ("negative" if avg_score < 40 else "neutral")
        )
        risk_level = self.sentiment_engine.get_risk_level(int(avg_score))

        # 生成报告
        report = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "news_count": len(news_list),
            "sentiment_score": int(avg_score),
            "sentiment": overall_sentiment,
            "risk_level": risk_level,
            "news": analyzed_news[:10],  # 只返回前10条
            "alerts": alerts[:5],
            "positives": positives[:5],
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        logger.info(
            f"舆情分析完成: {stock_code}, 评分{int(avg_score)}, {risk_level['label']}"
        )
        return report

    def format_report(self, report: Dict[str, Any]) -> str:
        """
        格式化报告为文本

        Args:
            report: 舆情分析报告

        Returns:
            格式化后的文本
        """
        lines = []
        lines.append(
            f"📊 股票舆情报告 - {report.get('stock_name', '')}({report.get('stock_code', '')})"
        )
        lines.append("")
        lines.append(f"📅 分析时间：{report.get('analysis_time', '')}")
        lines.append(f"📰 新闻数量：{report.get('news_count', 0)}篇")

        risk = report.get("risk_level", {})
        lines.append(
            f"📈 舆情评分：{report.get('sentiment_score', 50)}分 {risk.get('emoji', '')} {risk.get('label', '')}"
        )
        lines.append("")

        # 重要新闻
        news_list = report.get("news", [])
        if news_list:
            lines.append("📰 重要新闻摘要")
            for i, news in enumerate(news_list[:5], 1):
                sentiment_label = {
                    "positive": "✅正面",
                    "negative": "❌负面",
                    "neutral": "⚪中性",
                }.get(news.get("sentiment"), "⚪中性")
                lines.append(f"{i}. {news.get('title', '')} - {sentiment_label}")
                if news.get("summary"):
                    lines.append(f"   {news.get('summary', '')[:100]}...")
                lines.append("")

        # 风险警报
        alerts = report.get("alerts", [])
        if alerts:
            lines.append("🚨 风险警报")
            for alert in alerts:
                lines.append(f"- {alert.get('title', '')}")
                if alert.get("keywords"):
                    lines.append(f"  关键词: {', '.join(alert.get('keywords', []))}")
            lines.append("")

        # 利好因素
        positives = report.get("positives", [])
        if positives:
            lines.append("✨ 利好因素")
            for pos in positives:
                lines.append(f"- {pos.get('title', '')}")
                if pos.get("keywords"):
                    lines.append(f"  关键词: {', '.join(pos.get('keywords', []))}")
            lines.append("")

        # 分析建议
        lines.append("💡 分析建议")
        if report.get("sentiment_score", 50) >= 70:
            lines.append("- 舆情整体正面，可关注相关利好消息")
        elif report.get("sentiment_score", 50) >= 40:
            lines.append("- 舆情中性，建议综合其他指标判断")
        else:
            lines.append("- 舆情偏负面，注意风险控制")

        lines.append("")
        lines.append("数据来源：问财 + 妙想")

        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="股票舆情分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--stock", "-s", help="股票代码")
    parser.add_argument("--name", "-n", help="股票名称")
    parser.add_argument("--stocks", help="多个股票代码，逗号分隔")
    parser.add_argument(
        "--days", "-d", type=int, default=7, help="搜索最近多少天的新闻 (默认: 7)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()

    if not args.stock and not args.stocks:
        parser.print_help()
        sys.exit(1)

    analyzer = StockSentimentAnalyzer()

    # 处理股票列表
    stocks = []
    if args.stocks:
        stocks = [s.strip() for s in args.stocks.split(",")]
    elif args.stock:
        stocks = [args.stock]

    results = []
    for stock_code in stocks:
        report = analyzer.analyze(stock_code, args.name, args.days)
        results.append(report)

        if args.format == "text":
            print(analyzer.format_report(report))
            print("\n" + "=" * 60 + "\n")

    if args.format == "json":
        output = json.dumps(results, ensure_ascii=False, indent=2)
        print(output)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"结果已保存到 {args.output}")


if __name__ == "__main__":
    main()
