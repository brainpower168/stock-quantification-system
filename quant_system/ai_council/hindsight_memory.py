#!/usr/bin/env python3
"""
Hindsight Memory Integration for AI Trading Council

Integrates Hindsight agent memory system to enable learning from trading decisions.
Memory Types:
- World: Market facts, trading rules, sector knowledge
- Experiences: Past trades, decisions, outcomes
- Mental Models: Learned patterns, strategies, risk insights
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Hindsight client
try:
    from hindsight_client import Hindsight

    HINDSIGHT_AVAILABLE = True
except ImportError:
    HINDSIGHT_AVAILABLE = False
    print("Warning: hindsight-client not installed. Run: pip install hindsight-client")


class TradingMemory:
    """
    Trading Memory System powered by Hindsight

    Three memory banks:
    - trading_world: Market facts, rules, sector knowledge
    - trading_experiences: Past trades, decisions, outcomes
    - trading_models: Learned patterns, strategies
    """

    def __init__(self, base_url: str = "http://localhost:8888", enabled: bool = True):
        self.enabled = enabled and HINDSIGHT_AVAILABLE
        self.client = None

        if self.enabled:
            try:
                self.client = Hindsight(base_url=base_url)
                print(f"✓ Hindsight memory connected: {base_url}")
            except Exception as e:
                print(f"✗ Hindsight connection failed: {e}")
                self.enabled = False

        # Fallback to local file storage
        self.local_memory_dir = Path(__file__).parent.parent / "data" / "memory"
        self.local_memory_dir.mkdir(parents=True, exist_ok=True)

        # Memory banks
        self.WORLD_BANK = "trading_world"
        self.EXPERIENCES_BANK = "trading_experiences"
        self.MODELS_BANK = "trading_models"

    def retain_trade_decision(
        self,
        stock_code: str,
        stock_name: str,
        decision: str,
        confidence: float,
        council_votes: Dict,
        market_data: Dict,
        outcome: Optional[str] = None,
    ) -> bool:
        """
        Store a trading decision as an experience

        Args:
            stock_code: Stock code (e.g., "600519")
            stock_name: Stock name (e.g., "贵州茅台")
            decision: Council decision (BUY/SELL/HOLD)
            confidence: Decision confidence (0-1)
            council_votes: Individual model votes
            market_data: Market data at decision time
            outcome: Actual outcome (profit/loss) - optional, can be updated later
        """
        content = f"""
交易决策记录
股票: {stock_name} ({stock_code})
时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
决策: {decision}
置信度: {confidence:.2f}

市场数据:
- 价格: {market_data.get("price", 0)}
- 涨跌幅: {market_data.get("change_pct", 0)}%
- 主力资金: {market_data.get("capital_flow", 0)}亿
- 10日DDX: {market_data.get("ddx_10d", "N/A")}
- ROE: {market_data.get("roe", 0)}%
- PE: {market_data.get("pe", 0)}

委员会投票:
{self._format_votes(council_votes)}

{f"实际结果: {outcome}" if outcome else "待跟踪结果"}
"""

        metadata = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "decision": decision,
            "confidence": confidence,
            "capital_flow": market_data.get("capital_flow", 0),
            "ddx_10d": market_data.get("ddx_10d", 0),
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
        }

        return self._retain(self.EXPERIENCES_BANK, content, metadata)

    def retain_trade_outcome(
        self,
        stock_code: str,
        entry_price: float,
        exit_price: float,
        profit_pct: float,
        hold_days: int,
        decision_quality: str,  # "good" / "bad" / "neutral"
    ) -> bool:
        """
        Store trade outcome for learning
        """
        content = f"""
交易结果记录
股票: {stock_code}
买入价: {entry_price:.2f}
卖出价: {exit_price:.2f}
盈亏: {profit_pct:.2f}%
持有天数: {hold_days}
决策质量: {decision_quality}

{"盈利交易 - 分析成功因素" if profit_pct > 0 else "亏损交易 - 分析失败原因"}
"""

        metadata = {
            "stock_code": stock_code,
            "profit_pct": profit_pct,
            "hold_days": hold_days,
            "decision_quality": decision_quality,
            "timestamp": datetime.now().isoformat(),
        }

        return self._retain(self.EXPERIENCES_BANK, content, metadata)

    def retain_trading_rule(
        self,
        rule_type: str,  # "buy" / "sell" / "risk"
        rule: str,
        description: str,
        priority: int = 1,
    ) -> bool:
        """
        Store a trading rule as world knowledge
        """
        content = f"""
交易规则 [{rule_type.upper()}]
规则: {rule}
说明: {description}
优先级: {priority}
"""

        metadata = {
            "rule_type": rule_type,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        }

        return self._retain(self.WORLD_BANK, content, metadata)

    def retain_lesson_learned(
        self, lesson: str, context: str, related_stocks: List[str] = None
    ) -> bool:
        """
        Store a lesson learned as a mental model
        """
        content = f"""
经验教训
教训: {lesson}
背景: {context}
相关股票: {", ".join(related_stocks) if related_stocks else "N/A"}
时间: {datetime.now().strftime("%Y-%m-%d")}
"""

        metadata = {
            "lesson": lesson,
            "related_stocks": related_stocks or [],
            "timestamp": datetime.now().isoformat(),
        }

        return self._retain(self.MODELS_BANK, content, metadata)

    def recall_similar_situations(
        self,
        stock_code: str = None,
        capital_flow_range: tuple = None,
        decision_type: str = None,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Recall similar trading situations from memory
        """
        query_parts = []

        if stock_code:
            query_parts.append(f"股票 {stock_code}")
        if capital_flow_range:
            query_parts.append(
                f"主力资金 {capital_flow_range[0]}到{capital_flow_range[1]}亿"
            )
        if decision_type:
            query_parts.append(f"决策 {decision_type}")

        query = " ".join(query_parts) if query_parts else "交易决策"

        return self._recall(self.EXPERIENCES_BANK, query, limit)

    def recall_trading_rules(
        self, rule_type: str = None, limit: int = 10
    ) -> List[Dict]:
        """
        Recall trading rules from memory
        """
        query = f"{rule_type}规则" if rule_type else "交易规则"
        return self._recall(self.WORLD_BANK, query, limit)

    def reflect_on_performance(
        self, period_days: int = 30, focus: str = "profitability"
    ) -> Dict:
        """
        Reflect on trading performance and generate insights
        """
        query = f"""
请分析过去{period_days}天的交易记录，重点关注{focus}：
1. 哪些决策是正确的？为什么？
2. 哪些决策是错误的？原因是什么？
3. 有什么规律可以总结？
4. 需要改进的地方有哪些？
"""

        if self.enabled and self.client:
            try:
                result = self.client.reflect(bank_id=self.EXPERIENCES_BANK, query=query)
                return {"insights": result, "source": "hindsight"}
            except Exception as e:
                print(f"Reflect failed: {e}")

        # Fallback: analyze local decisions
        return self._local_reflect(period_days, focus)

    def get_stock_memory(
        self,
        stock_code: str,
        include_experiences: bool = True,
        include_rules: bool = True,
    ) -> Dict:
        """
        Get all memory related to a specific stock
        """
        result = {
            "stock_code": stock_code,
            "experiences": [],
            "rules": [],
            "lessons": [],
        }

        if include_experiences:
            result["experiences"] = self._recall(
                self.EXPERIENCES_BANK, f"股票 {stock_code}", limit=10
            )

        if include_rules:
            result["rules"] = self._recall(self.WORLD_BANK, "交易规则", limit=10)

        return result

    def _retain(self, bank_id: str, content: str, metadata: Dict = None) -> bool:
        """Internal retain method"""
        if self.enabled and self.client:
            try:
                self.client.retain(bank_id=bank_id, content=content, metadata=metadata)
                return True
            except Exception as e:
                print(f"Retain failed: {e}")

        # Fallback: save to local file
        return self._local_retain(bank_id, content, metadata)

    def _recall(self, bank_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Internal recall method"""
        if self.enabled and self.client:
            try:
                results = self.client.recall(bank_id=bank_id, query=query, limit=limit)
                return results
            except Exception as e:
                print(f"Recall failed: {e}")

        # Fallback: search local files
        return self._local_recall(bank_id, query, limit)

    def _local_retain(self, bank_id: str, content: str, metadata: Dict = None) -> bool:
        """Save to local file as fallback"""
        memory_file = self.local_memory_dir / f"{bank_id}.jsonl"

        entry = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return True

    def _local_recall(self, bank_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Search local files as fallback"""
        memory_file = self.local_memory_dir / f"{bank_id}.jsonl"

        if not memory_file.exists():
            return []

        results = []
        query_lower = query.lower()

        with open(memory_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    content = entry.get("content", "").lower()

                    # Simple keyword matching
                    if any(kw in content for kw in query_lower.split()):
                        results.append(entry)

                        if len(results) >= limit:
                            break
                except:
                    continue

        return results

    def _local_reflect(self, period_days: int, focus: str) -> Dict:
        """Local reflection as fallback"""
        # Load recent decisions
        decisions_file = (
            Path(__file__).parent.parent / "data" / "council_decisions.jsonl"
        )

        if not decisions_file.exists():
            return {"insights": "无历史决策记录", "source": "local"}

        recent_decisions = []
        cutoff = datetime.now().timestamp() - period_days * 86400

        with open(decisions_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    decision = json.loads(line)
                    timestamp = datetime.fromisoformat(
                        decision["timestamp"]
                    ).timestamp()
                    if timestamp >= cutoff:
                        recent_decisions.append(decision)
                except:
                    continue

        # Simple statistics
        buy_count = sum(
            1 for d in recent_decisions if d.get("consensus") in ["BUY", "STRONG_BUY"]
        )
        sell_count = sum(
            1 for d in recent_decisions if d.get("consensus") in ["SELL", "STRONG_SELL"]
        )
        hold_count = sum(1 for d in recent_decisions if d.get("consensus") == "HOLD")

        avg_confidence = (
            sum(d.get("confidence", 0) for d in recent_decisions)
            / len(recent_decisions)
            if recent_decisions
            else 0
        )

        insights = f"""
过去{period_days}天交易分析:
- 总决策数: {len(recent_decisions)}
- 买入: {buy_count}次
- 卖出: {sell_count}次
- 持有: {hold_count}次
- 平均置信度: {avg_confidence:.2f}

建议:
1. 保持交易纪律，严格执行止损止盈
2. 关注资金流向，10日DDX < 0 不买
3. 不追高，涨幅超过3%等回调
"""

        return {
            "insights": insights,
            "source": "local",
            "stats": {
                "total": len(recent_decisions),
                "buy": buy_count,
                "sell": sell_count,
                "hold": hold_count,
                "avg_confidence": avg_confidence,
            },
        }

    def _format_votes(self, votes: Dict) -> str:
        """Format council votes for storage"""
        lines = []
        for model, vote in votes.items():
            lines.append(
                f"- {model} ({vote.get('role', 'N/A')}): {vote.get('vote', 'N/A')} (置信度: {vote.get('confidence', 0):.2f})"
            )
        return "\n".join(lines)


# Singleton instance
_memory_instance = None


def get_trading_memory(
    base_url: str = "http://localhost:8888", enabled: bool = True
) -> TradingMemory:
    """Get or create TradingMemory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = TradingMemory(base_url=base_url, enabled=enabled)
    return _memory_instance


if __name__ == "__main__":
    # Test the memory system
    memory = get_trading_memory(enabled=False)  # Use local fallback

    # Test retain
    memory.retain_trade_decision(
        stock_code="600519",
        stock_name="贵州茅台",
        decision="BUY",
        confidence=0.75,
        council_votes={
            "longcat": {"vote": "BUY", "confidence": 0.8, "role": "量化专家"},
            "xunfei": {"vote": "BUY", "confidence": 0.7, "role": "基本面分析师"},
        },
        market_data={
            "price": 1800,
            "change_pct": 1.5,
            "capital_flow": 5.2,
            "ddx_10d": 0.45,
            "roe": 25,
            "pe": 35,
        },
    )

    # Test recall
    results = memory.recall_similar_situations(stock_code="600519")
    print(f"Found {len(results)} similar situations")

    # Test reflect
    insights = memory.reflect_on_performance(period_days=7)
    print(insights["insights"])
