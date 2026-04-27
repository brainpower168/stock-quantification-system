#!/usr/bin/env python3
"""
AI Trading Council Engine
Multi-AI decision system for stock trading
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import concurrent.futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Model adapters
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import dashscope
    from dashscope import Generation
except ImportError:
    dashscope = None

try:
    import anthropic
except ImportError:
    anthropic = None


class AIModelAdapter:
    """Base adapter for AI models"""

    def __init__(self, model_name: str, api_key: str, role: str):
        self.model_name = model_name
        self.api_key = api_key
        self.role = role

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        raise NotImplementedError


class LongCatAdapter(AIModelAdapter):
    """LongCat adapter - 量化专家 (OpenAI 兼容 API)"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.longcat.chat/openai",
        model: str = "LongCat-Flash-Lite",
    ):
        super().__init__("longcat", api_key, "quant_expert")
        self.base_url = base_url
        self.model = model
        if OpenAI:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = f"""
你是量化交易专家，专注于技术指标、量化因子、市场情绪分析。

股票代码: {stock_data.get("code", "")}
股票名称: {stock_data.get("name", "")}
当前价格: {stock_data.get("price", 0)}
涨跌幅: {stock_data.get("change_pct", 0)}%
成交量: {stock_data.get("volume", 0)}
主力资金流向: {stock_data.get("capital_flow", 0)}亿

【重要】决策权重：
- 资金流向：30%（主力流入>5亿看多，流出>5亿看空）
- 技术指标：25%
- 基本面：20%
- 板块联动：15%
- 市场情绪：10%

请分析该股票，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
简要说明你的分析逻辑，重点说明资金流向的影响。
"""

        try:
            if self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的量化交易专家，擅长技术分析和量化因子分析。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
            else:
                # Fallback to requests
                import requests

                url = f"{self.base_url}/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                data = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位专业的量化交易专家，擅长技术分析和量化因子分析。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                }
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                content = result["choices"][0]["message"]["content"]

            return self._parse_response(content, stock_data)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str, stock_data: Dict = None) -> Dict:
        """Parse AI response into structured decision with data-driven confidence"""
        vote = "HOLD"
        base_confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            base_confidence = 0.75
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            base_confidence = 0.65
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            base_confidence = 0.65
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            base_confidence = 0.75

        # Data-driven confidence adjustment
        confidence = base_confidence
        if stock_data:
            confidence = self._adjust_confidence_by_data(
                vote, base_confidence, stock_data
            )

        return {
            "model": "longcat",
            "role": "量化专家",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _adjust_confidence_by_data(
        self, vote: str, base_confidence: float, stock_data: Dict
    ) -> float:
        """Adjust confidence based on actual market data"""
        confidence = base_confidence
        adjustments = []

        # 1. Capital flow adjustment (most important)
        capital_flow = stock_data.get("capital_flow", 0)
        if vote in ["STRONG_BUY", "BUY"]:
            if capital_flow > 10:
                adjustments.append(0.15)  # 大额流入，提高置信度
            elif capital_flow > 5:
                adjustments.append(0.10)
            elif capital_flow > 0:
                adjustments.append(0.05)
            elif capital_flow < -5:
                adjustments.append(-0.10)  # 流出，降低置信度
        elif vote in ["SELL", "STRONG_SELL"]:
            if capital_flow < -10:
                adjustments.append(0.15)  # 大额流出，提高卖出置信度
            elif capital_flow < -5:
                adjustments.append(0.10)
            elif capital_flow > 5:
                adjustments.append(-0.10)  # 流入，降低卖出置信度

        # 2. Technical indicators adjustment
        kdj = stock_data.get("kdj", 50)
        rsi = stock_data.get("rsi", 50)

        if vote in ["STRONG_BUY", "BUY"]:
            if kdj < 20:
                adjustments.append(0.10)  # 超卖，提高买入置信度
            elif kdj > 80:
                adjustments.append(-0.15)  # 超买，降低买入置信度
            if rsi < 30:
                adjustments.append(0.10)
            elif rsi > 70:
                adjustments.append(-0.15)
        elif vote in ["SELL", "STRONG_SELL"]:
            if kdj > 80:
                adjustments.append(0.10)  # 超买，提高卖出置信度
            elif kdj < 20:
                adjustments.append(-0.10)  # 超卖，降低卖出置信度
            if rsi > 70:
                adjustments.append(0.10)
            elif rsi < 30:
                adjustments.append(-0.10)

        # 3. Recent trend adjustment
        change_5d = stock_data.get("change_5d", 0)
        if vote in ["STRONG_BUY", "BUY"]:
            if change_5d > 15:
                adjustments.append(-0.10)  # 近期涨幅过大，降低买入置信度
            elif change_5d < -10:
                adjustments.append(0.05)  # 近期跌幅大，提高买入置信度
        elif vote in ["SELL", "STRONG_SELL"]:
            if change_5d < -15:
                adjustments.append(-0.10)  # 近期跌幅过大，降低卖出置信度

        # Apply adjustments
        total_adjustment = sum(adjustments)
        confidence = max(0.3, min(0.95, base_confidence + total_adjustment))

        return round(confidence, 2)


class GLMAdapter(AIModelAdapter):
    """智谱 GLM adapter - 技术分析师"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        model: str = "glm-4-flash",
    ):
        super().__init__("glm", api_key, "technical_analyst")
        self.base_url = base_url
        self.model = model
        if OpenAI:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = f"""
你是技术分析师，专注于K线形态、趋势分析、支撑阻力位。

股票代码: {stock_data.get("code", "")}
股票名称: {stock_data.get("name", "")}
当前价格: {stock_data.get("price", 0)}
涨跌幅: {stock_data.get("change_pct", 0)}%
成交量: {stock_data.get("volume", 0)}
主力资金流向: {stock_data.get("capital_flow", 0)}亿

【重要】决策权重：
- 资金流向：35%（主力流入>5亿看多，流出>5亿看空）
- 技术指标：30%
- 基本面：15%
- 板块联动：12%
- 市场情绪：8%

请分析该股票的技术面，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
简要说明你的分析逻辑，重点说明技术形态和资金流向的影响。
"""

        try:
            if self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的技术分析师，擅长K线形态和趋势分析。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
            else:
                # Fallback to requests
                import requests

                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                data = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位专业的技术分析师，擅长K线形态和趋势分析。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                }
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                content = result["choices"][0]["message"]["content"]

            return self._parse_response(content, stock_data)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str, stock_data: Dict = None) -> Dict:
        """Parse AI response into structured decision with data-driven confidence"""
        vote = "HOLD"
        base_confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            base_confidence = 0.75
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            base_confidence = 0.65
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            base_confidence = 0.65
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            base_confidence = 0.75

        # Data-driven confidence adjustment (same as LongCat)
        confidence = base_confidence
        if stock_data:
            confidence = self._adjust_confidence_by_data(
                vote, base_confidence, stock_data
            )

        return {
            "model": "glm",
            "role": "技术分析师",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _adjust_confidence_by_data(
        self, vote: str, base_confidence: float, stock_data: Dict
    ) -> float:
        """Adjust confidence based on actual market data"""
        confidence = base_confidence
        adjustments = []

        # Capital flow adjustment
        capital_flow = stock_data.get("capital_flow", 0)
        if vote in ["STRONG_BUY", "BUY"]:
            if capital_flow > 10:
                adjustments.append(0.15)
            elif capital_flow > 5:
                adjustments.append(0.10)
            elif capital_flow > 0:
                adjustments.append(0.05)
            elif capital_flow < -5:
                adjustments.append(-0.10)
        elif vote in ["SELL", "STRONG_SELL"]:
            if capital_flow < -10:
                adjustments.append(0.15)
            elif capital_flow < -5:
                adjustments.append(0.10)
            elif capital_flow > 5:
                adjustments.append(-0.10)

        # Technical indicators adjustment
        kdj = stock_data.get("kdj", 50)
        rsi = stock_data.get("rsi", 50)

        if vote in ["STRONG_BUY", "BUY"]:
            if kdj < 20:
                adjustments.append(0.10)
            elif kdj > 80:
                adjustments.append(-0.15)
            if rsi < 30:
                adjustments.append(0.10)
            elif rsi > 70:
                adjustments.append(-0.15)
        elif vote in ["SELL", "STRONG_SELL"]:
            if kdj > 80:
                adjustments.append(0.10)
            elif kdj < 20:
                adjustments.append(-0.10)
            if rsi > 70:
                adjustments.append(0.10)
            elif rsi < 30:
                adjustments.append(-0.10)

        # Apply adjustments
        total_adjustment = sum(adjustments)
        confidence = max(0.3, min(0.95, base_confidence + total_adjustment))

        return round(confidence, 2)


class XunfeiAdapter(AIModelAdapter):
    """讯飞星火 adapter - 基本面分析师"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
        model: str = "astron-code-latest",
    ):
        super().__init__("xunfei", api_key, "fundamental_analyst")
        self.base_url = base_url
        self.model = model
        if OpenAI:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = f"""
你是基本面分析师，专注于财务数据、估值、行业分析。

股票代码: {stock_data.get("code", "")}
股票名称: {stock_data.get("name", "")}
当前价格: {stock_data.get("price", 0)}
涨跌幅: {stock_data.get("change_pct", 0)}%
成交量: {stock_data.get("volume", 0)}
主力资金流向: {stock_data.get("capital_flow", 0)}亿
市盈率: {stock_data.get("pe", 0)}
市净率: {stock_data.get("pb", 0)}
ROE: {stock_data.get("roe", 0)}%
净利润增长: {stock_data.get("profit_growth", 0)}%

请分析该股票的基本面和估值，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
简要说明你的分析逻辑，重点关注：
1. 资金流向是否支持买入
2. 估值是否合理
3. 业绩增长是否可持续
"""

        try:
            if self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的基本面分析师，擅长财务分析和估值。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
            else:
                # Fallback to requests
                import requests

                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                data = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位专业的基本面分析师，擅长财务分析和估值。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                }
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                content = result["choices"][0]["message"]["content"]

            return self._parse_response(content)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response into structured decision"""
        vote = "HOLD"
        confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            confidence = 0.85
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            confidence = 0.7
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            confidence = 0.7
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            confidence = 0.85

        return {
            "model": "xunfei",
            "role": "基本面分析师",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class DeepSeekAdapter(AIModelAdapter):
    """DeepSeek adapter - 量化专家"""

    def __init__(self, api_key: str):
        super().__init__("deepseek", api_key, "quant_expert")
        self.client = (
            OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            if OpenAI
            else None
        )

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = prompt_template.format(
            role="量化专家",
            focus="技术指标、量化因子、市场情绪",
            stock_code=stock_data.get("code", ""),
            stock_name=stock_data.get("name", ""),
            price=stock_data.get("price", 0),
            change_pct=stock_data.get("change_pct", 0),
            volume=stock_data.get("volume", 0),
            ma5=stock_data.get("ma5", 0),
            ma10=stock_data.get("ma10", 0),
            ma20=stock_data.get("ma20", 0),
            rsi=stock_data.get("rsi", 50),
            macd=stock_data.get("macd", {}),
            kdj=stock_data.get("kdj", {}),
            financial=stock_data.get("financial", {}),
        )

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的量化交易专家，擅长技术分析和量化因子分析。请给出简洁、数据驱动的分析。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response into structured decision"""
        vote = "HOLD"
        confidence = 0.5
        reasoning = content

        # Simple parsing logic
        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            confidence = 0.85
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            confidence = 0.7
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            confidence = 0.7
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            confidence = 0.85

        return {
            "model": "deepseek",
            "role": "量化专家",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class QwenAdapter(AIModelAdapter):
    """Qwen adapter - 基本面分析师"""

    def __init__(self, api_key: str):
        super().__init__("qwen", api_key, "fundamental_analyst")
        self.api_key = api_key

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = prompt_template.format(
            role="基本面分析师",
            focus="财务数据、估值、行业分析",
            stock_code=stock_data.get("code", ""),
            stock_name=stock_data.get("name", ""),
            pe=stock_data.get("pe", 0),
            pb=stock_data.get("pb", 0),
            roe=stock_data.get("roe", 0),
            revenue_growth=stock_data.get("revenue_growth", 0),
            profit_growth=stock_data.get("profit_growth", 0),
            debt_ratio=stock_data.get("debt_ratio", 0),
            financial=stock_data.get("financial", {}),
        )

        try:
            if dashscope:
                dashscope.api_key = self.api_key
                response = Generation.call(
                    model="qwen-max", prompt=prompt, temperature=0.3, max_tokens=1000
                )
                content = response.output.text
            else:
                # Fallback to OpenAI-compatible API
                client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                )
                response = client.chat.completions.create(
                    model="qwen-max",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的基本面分析师，擅长财务分析和估值。请给出简洁、数据驱动的分析。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
                content = response.choices[0].message.content

            return self._parse_response(content)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response into structured decision"""
        vote = "HOLD"
        confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            confidence = 0.85
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            confidence = 0.7
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            confidence = 0.7
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            confidence = 0.85

        return {
            "model": "qwen",
            "role": "基本面分析师",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class GPTAdapter(AIModelAdapter):
    """GPT adapter - 技术分析师"""

    def __init__(self, api_key: str):
        super().__init__("gpt", api_key, "technical_analyst")
        self.client = OpenAI(api_key=api_key)

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = prompt_template.format(
            role="技术分析师",
            focus="K线形态、趋势、支撑阻力",
            stock_code=stock_data.get("code", ""),
            stock_name=stock_data.get("name", ""),
            price=stock_data.get("price", 0),
            high=stock_data.get("high", 0),
            low=stock_data.get("low", 0),
            volume=stock_data.get("volume", 0),
            trend=stock_data.get("trend", "震荡"),
            support=stock_data.get("support", 0),
            resistance=stock_data.get("resistance", 0),
            pattern=stock_data.get("pattern", "无明显形态"),
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional technical analyst specializing in chart patterns and trend analysis. Provide concise, data-driven analysis.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response into structured decision"""
        vote = "HOLD"
        confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "strong buy" in content_lower or "强烈买入" in content:
            vote = "STRONG_BUY"
            confidence = 0.85
        elif "buy" in content_lower or "买入" in content:
            vote = "BUY"
            confidence = 0.7
        elif "sell" in content_lower or "卖出" in content:
            vote = "SELL"
            confidence = 0.7
        elif "strong sell" in content_lower or "强烈卖出" in content:
            vote = "STRONG_SELL"
            confidence = 0.85

        return {
            "model": "gpt",
            "role": "技术分析师",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class ClaudeAdapter(AIModelAdapter):
    """Claude adapter - 风控专家"""

    def __init__(self, api_key: str):
        super().__init__("claude", api_key, "risk_manager")
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, stock_data: Dict, prompt_template: str) -> Dict:
        prompt = prompt_template.format(
            role="风控专家",
            focus="风险评估、仓位管理、止损策略",
            stock_code=stock_data.get("code", ""),
            stock_name=stock_data.get("name", ""),
            price=stock_data.get("price", 0),
            volatility=stock_data.get("volatility", 0),
            beta=stock_data.get("beta", 1),
            max_drawdown=stock_data.get("max_drawdown", 0),
            sharpe=stock_data.get("sharpe", 0),
            position_size=stock_data.get("position_size", 0),
            portfolio_risk=stock_data.get("portfolio_risk", 0),
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                system="你是一位专业的风险管理专家，擅长风险评估和仓位管理。请给出简洁、谨慎的分析。",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            return self._parse_response(content)
        except Exception as e:
            return {
                "vote": "HOLD",
                "confidence": 0.5,
                "reasoning": f"分析失败: {str(e)}",
                "error": True,
            }

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response into structured decision"""
        vote = "HOLD"
        confidence = 0.5
        reasoning = content

        content_lower = content.lower()
        if "强烈买入" in content or "strong buy" in content_lower:
            vote = "STRONG_BUY"
            confidence = 0.85
        elif "买入" in content or "buy" in content_lower:
            vote = "BUY"
            confidence = 0.7
        elif "卖出" in content or "sell" in content_lower:
            vote = "SELL"
            confidence = 0.7
        elif "强烈卖出" in content or "strong sell" in content_lower:
            vote = "STRONG_SELL"
            confidence = 0.85

        return {
            "model": "claude",
            "role": "风控专家",
            "vote": vote,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class TradingCouncil:
    """AI Trading Council - Multi-model decision system with memory"""

    def __init__(self, config_path: Optional[str] = None, enable_memory: bool = True):
        self.config = self._load_config(config_path)
        self.models = self._init_models()
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Initialize memory system
        self.memory = None
        self.enable_memory = enable_memory
        if enable_memory:
            try:
                from hindsight_memory import get_trading_memory

                self.memory = get_trading_memory(enabled=False)  # Use local fallback
                print("✓ Trading memory initialized")
            except ImportError:
                print("✗ Memory system not available")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load council configuration"""
        default_config = {
            "models": {
                "longcat": {
                    "enabled": True,
                    "api_key_env": "LONGCAT_API_KEY",
                    "base_url": "https://api.longcat.chat/openai",
                    "model": "LongCat-Flash-Lite",
                    "role": "quant_expert",
                    "weight": 1.0,
                },
                "deepseek": {
                    "enabled": False,
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "role": "quant_expert",
                    "weight": 1.0,
                },
                "qwen": {
                    "enabled": False,
                    "api_key_env": "QWEN_API_KEY",
                    "role": "fundamental_analyst",
                    "weight": 1.0,
                },
                "gpt": {
                    "enabled": False,
                    "api_key_env": "OPENAI_API_KEY",
                    "role": "technical_analyst",
                    "weight": 1.0,
                },
                "claude": {
                    "enabled": False,
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "role": "risk_manager",
                    "weight": 1.2,
                },
            },
            "consensus_threshold": 0.6,
            "min_confidence": 0.5,
        }

        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def _init_models(self) -> Dict[str, AIModelAdapter]:
        """Initialize AI model adapters"""
        models = {}

        for model_name, model_config in self.config["models"].items():
            if not model_config.get("enabled", False):
                continue

            # 支持直接配置 api_key 或从环境变量读取
            api_key = model_config.get("api_key", "")
            if not api_key:
                api_key_env = model_config.get("api_key_env", "")
                if api_key_env:
                    api_key = os.environ.get(api_key_env, "")

            if not api_key:
                print(f"Warning: {model_name} API key not set, skipping")
                continue

            if model_name == "longcat":
                base_url = model_config.get(
                    "base_url", "https://api.longcat.chat/openai"
                )
                model = model_config.get("model", "LongCat-Flash-Lite")
                models[model_name] = LongCatAdapter(api_key, base_url, model)
            elif model_name == "xunfei":
                base_url = model_config.get(
                    "base_url", "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
                )
                model = model_config.get("model", "astron-code-latest")
                models[model_name] = XunfeiAdapter(api_key, base_url, model)
            elif model_name == "glm":
                base_url = model_config.get(
                    "base_url", "https://open.bigmodel.cn/api/paas/v4"
                )
                model = model_config.get("model", "glm-4-flash")
                models[model_name] = GLMAdapter(api_key, base_url, model)
            elif model_name == "deepseek":
                models[model_name] = DeepSeekAdapter(api_key)
            elif model_name == "qwen":
                models[model_name] = QwenAdapter(api_key)
            elif model_name == "gpt":
                models[model_name] = GPTAdapter(api_key)
            elif model_name == "claude":
                models[model_name] = ClaudeAdapter(api_key)

        return models

    def _get_prompt_template(self, role: str) -> str:
        """Get role-specific prompt template"""
        templates = {
            "quant_expert": """
你是{role}，专注于{focus}。

股票代码: {stock_code}
股票名称: {stock_name}
当前价格: {price}
涨跌幅: {change_pct}%
成交量: {volume}
MA5: {ma5}
MA10: {ma10}
MA20: {ma20}
RSI: {rsi}
MACD: {macd}
KDJ: {kdj}

请分析该股票的技术面和量化因子，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
简要说明你的分析逻辑。
""",
            "fundamental_analyst": """
你是{role}，专注于{focus}。

股票代码: {stock_code}
股票名称: {stock_name}
当前价格: {price}
PE: {pe}
PB: {pb}
ROE: {roe}%
营收增长: {revenue_growth}%
利润增长: {profit_growth}%
负债率: {debt_ratio}%

请分析该股票的基本面和估值，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
简要说明你的分析逻辑。
""",
            "technical_analyst": """
You are a {role}, focusing on {focus}.

Stock Code: {stock_code}
Stock Name: {stock_name}
Current Price: {price}
High: {high}
Low: {low}
Volume: {volume}
Trend: {trend}
Support: {support}
Resistance: {resistance}
Pattern: {pattern}

Please analyze the technical aspects and provide your trading recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell) with confidence (0-1).
Briefly explain your analysis logic.
""",
            "risk_manager": """
你是{role}，专注于{focus}。

股票代码: {stock_code}
股票名称: {stock_name}
当前价格: {price}
波动率: {volatility}%
Beta: {beta}
最大回撤: {max_drawdown}%
夏普比率: {sharpe}
建议仓位: {position_size}%
组合风险: {portfolio_risk}%

请评估该股票的风险，给出你的交易建议（强烈买入/买入/持有/卖出/强烈卖出）和置信度（0-1）。
重点说明风险点和止损建议。
""",
        }
        return templates.get(role, templates["quant_expert"])

    def run_council_analysis(
        self, stock_code: str, stock_data: Optional[Dict] = None
    ) -> Dict:
        """Run full council analysis on a single stock"""

        # Default stock data if not provided
        if stock_data is None:
            stock_data = {
                "code": stock_code,
                "name": stock_code,
                "price": 0,
                "change_pct": 0,
                "volume": 0,
            }

        # Collect votes from all models
        votes = {}

        for model_name, model in self.models.items():
            role = model.role
            prompt_template = self._get_prompt_template(role)

            print(f"  正在咨询 {model_name} ({role})...")
            result = model.analyze(stock_data, prompt_template)
            votes[model_name] = result

        # Calculate consensus
        consensus = self._calculate_consensus(votes)

        # Build final result
        result = {
            "stock_code": stock_code,
            "stock_name": stock_data.get("name", stock_code),
            "timestamp": datetime.now().isoformat(),
            "consensus": consensus["decision"],
            "confidence": consensus["confidence"],
            "council_votes": votes,
            "vote_summary": consensus["summary"],
            "key_points": self._extract_key_points(votes),
            "risk_warnings": self._extract_risk_warnings(votes),
            "data_source": stock_data.get("data_source", "unknown"),
        }

        # Save decision
        self._save_decision(result)

        # Store in memory system
        if self.memory:
            self._store_decision_memory(result, stock_data)

        return result

    def _calculate_consensus(self, votes: Dict) -> Dict:
        """Calculate consensus from model votes"""

        vote_weights = {
            "STRONG_BUY": 2,
            "BUY": 1,
            "HOLD": 0,
            "SELL": -1,
            "STRONG_SELL": -2,
        }

        weighted_sum = 0
        total_weight = 0
        vote_counts = {
            "STRONG_BUY": 0,
            "BUY": 0,
            "HOLD": 0,
            "SELL": 0,
            "STRONG_SELL": 0,
        }

        for model_name, vote in votes.items():
            if vote.get("error"):
                continue

            model_weight = self.config["models"].get(model_name, {}).get("weight", 1.0)
            vote_value = vote_weights.get(vote["vote"], 0)
            confidence = vote["confidence"]

            weighted_sum += vote_value * confidence * model_weight
            total_weight += model_weight
            vote_counts[vote["vote"]] += 1

        if total_weight == 0:
            return {"decision": "HOLD", "confidence": 0.5, "summary": vote_counts}

        avg_score = weighted_sum / total_weight

        # Determine consensus
        if avg_score >= 1.5:
            decision = "STRONG_BUY"
            confidence = min(0.95, 0.85 + (avg_score - 1.5) * 0.1)
        elif avg_score >= 0.5:
            decision = "BUY"
            confidence = min(0.85, 0.65 + (avg_score - 0.5) * 0.2)
        elif avg_score <= -1.5:
            decision = "STRONG_SELL"
            confidence = min(0.95, 0.85 + (abs(avg_score) - 1.5) * 0.1)
        elif avg_score <= -0.5:
            decision = "SELL"
            confidence = min(0.85, 0.65 + (abs(avg_score) - 0.5) * 0.2)
        else:
            decision = "HOLD"
            confidence = 0.5 + abs(avg_score) * 0.1

        return {
            "decision": decision,
            "confidence": round(confidence, 2),
            "summary": vote_counts,
        }

    def _extract_key_points(self, votes: Dict) -> List[str]:
        """Extract key points from model analyses"""
        points = []
        for model_name, vote in votes.items():
            if vote.get("error"):
                continue
            reasoning = vote.get("reasoning", "")
            # Extract first 100 chars as key point
            key_point = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
            points.append(f"[{vote['role']}] {key_point}")
        return points

    def _extract_risk_warnings(self, votes: Dict) -> List[str]:
        """Extract risk warnings from model analyses"""
        warnings = []
        risk_keywords = [
            "风险",
            "下跌",
            "止损",
            "警告",
            "谨慎",
            "风险",
            "risk",
            "warning",
            "caution",
        ]

        for model_name, vote in votes.items():
            if vote.get("error"):
                continue
            reasoning = vote.get("reasoning", "").lower()
            for keyword in risk_keywords:
                if keyword in reasoning:
                    warnings.append(f"[{vote['role']}] 检测到风险信号")
                    break

        return warnings

    def _save_decision(self, result: Dict):
        """Save decision to log file"""
        log_file = self.data_dir / "council_decisions.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def _store_decision_memory(self, result: Dict, stock_data: Dict):
        """Store decision in memory system for learning"""
        if not self.memory:
            return

        try:
            self.memory.retain_trade_decision(
                stock_code=result["stock_code"],
                stock_name=result["stock_name"],
                decision=result["consensus"],
                confidence=result["confidence"],
                council_votes=result["council_votes"],
                market_data={
                    "price": stock_data.get("price", 0),
                    "change_pct": stock_data.get("change_pct", 0),
                    "capital_flow": stock_data.get("capital_flow", 0),
                    "ddx_10d": stock_data.get("ddx_10d", 0),
                    "roe": stock_data.get("roe", 0),
                    "pe": stock_data.get("pe", 0),
                    "kdj": stock_data.get("kdj", 50),
                    "rsi": stock_data.get("rsi", 50),
                },
            )
        except Exception as e:
            print(f"Memory store failed: {e}")

    def get_stock_memory(self, stock_code: str) -> Dict:
        """Get memory context for a stock before analysis"""
        if not self.memory:
            return {"experiences": [], "rules": [], "lessons": []}

        return self.memory.get_stock_memory(stock_code)

    def reflect_on_performance(self, days: int = 30) -> Dict:
        """Reflect on trading performance using memory"""
        if not self.memory:
            return {"insights": "Memory system not available", "source": "none"}

        return self.memory.reflect_on_performance(period_days=days)

    def run_batch_council(
        self, stock_list: List[str], parallel: bool = True
    ) -> List[Dict]:
        """Run council analysis on multiple stocks"""
        results = []

        if parallel and len(self.models) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self.run_council_analysis, stock): stock
                    for stock in stock_list
                }
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
        else:
            for stock in stock_list:
                print(f"\n分析 {stock}...")
                results.append(self.run_council_analysis(stock))

        return results

    def get_council_history(self, days: int = 7) -> List[Dict]:
        """Get historical council decisions"""
        log_file = self.data_dir / "council_decisions.jsonl"

        if not log_file.exists():
            return []

        decisions = []
        cutoff = datetime.now().timestamp() - days * 86400

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    decision = json.loads(line)
                    timestamp = datetime.fromisoformat(
                        decision["timestamp"]
                    ).timestamp()
                    if timestamp >= cutoff:
                        decisions.append(decision)
                except:
                    continue

        return decisions


def main():
    parser = argparse.ArgumentParser(description="AI Trading Council Engine")
    parser.add_argument("--stock", type=str, help="Single stock code to analyze")
    parser.add_argument(
        "--stocks", type=str, help="Comma-separated list of stock codes"
    )
    parser.add_argument(
        "--type",
        type=str,
        default="full",
        choices=["full", "quick", "deep"],
        help="Analysis type",
    )
    parser.add_argument(
        "--parallel", action="store_true", default=True, help="Run in parallel"
    )
    parser.add_argument("--history", action="store_true", help="Show decision history")
    parser.add_argument(
        "--days", type=int, default=7, help="Days to look back for history"
    )
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--memory", action="store_true", help="Show stock memory")
    parser.add_argument("--reflect", action="store_true", help="Reflect on performance")

    args = parser.parse_args()

    council = TradingCouncil(args.config)

    # Memory commands
    if args.memory and args.stock:
        print(f"\n获取 {args.stock} 的记忆...")
        memory = council.get_stock_memory(args.stock)
        print(f"历史经验: {len(memory.get('experiences', []))} 条")
        print(f"交易规则: {len(memory.get('rules', []))} 条")
        for exp in memory.get("experiences", [])[:3]:
            print(f"  - {exp.get('content', '')[:100]}...")
        return

    if args.reflect:
        print(f"\n反思过去 {args.days} 天的交易表现...")
        insights = council.reflect_on_performance(days=args.days)
        print(insights.get("insights", "无分析结果"))
        if "stats" in insights:
            print(f"\n统计数据:")
            for k, v in insights["stats"].items():
                print(f"  {k}: {v}")
        return

    if args.history:
        history = council.get_council_history(args.days)
        print(f"\n过去 {args.days} 天的决策记录:")
        for decision in history:
            print(
                f"  {decision['stock_code']}: {decision['consensus']} (置信度: {decision['confidence']:.2f})"
            )
        return

    # 尝试导入数据获取器
    try:
        from selector_integration import StockDataFetcher

        fetcher = StockDataFetcher()
    except ImportError:
        fetcher = None

    if args.stock:
        print(f"\n分析 {args.stock}...")

        # 获取股票数据
        stock_data = None
        if fetcher:
            stock_data = fetcher.fetch_stock_data(args.stock)
            print(f"  数据来源: {stock_data.get('data_source', 'unknown')}")
            print(f"  主力资金: {stock_data.get('capital_flow', 0):.2f}亿")
            print(
                f"  KDJ: {stock_data.get('kdj', 50)}, RSI: {stock_data.get('rsi', 50)}"
            )

        result = council.run_council_analysis(args.stock, stock_data)

        print(f"\n{'=' * 50}")
        print(f"股票: {result['stock_code']} ({result['stock_name']})")
        print(f"共识决策: {result['consensus']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"\n各模型投票:")
        for model, vote in result["council_votes"].items():
            print(
                f"  {model} ({vote['role']}): {vote['vote']} (置信度: {vote['confidence']:.2f})"
            )
        print(f"{'=' * 50}")

    elif args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(",")]

        # 获取所有股票数据
        stocks_data = {}
        if fetcher:
            for stock in stock_list:
                stocks_data[stock] = fetcher.fetch_stock_data(stock)

        results = []
        for stock in stock_list:
            print(f"\n分析 {stock}...")
            data = stocks_data.get(stock)
            results.append(council.run_council_analysis(stock, data))

        print(f"\n批量分析结果:")
        for result in results:
            print(
                f"  {result['stock_code']}: {result['consensus']} (置信度: {result['confidence']:.2f})"
            )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
