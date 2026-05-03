#!/usr/bin/env python3
"""
Trading Orchestrator - 统一交易编排器
串联完整交易流程：选股 → AI决策 → 风控检查 → 执行交易
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# 导入其他模块
try:
    from council_engine import AITradingCouncil, CouncilDecision
except ImportError:
    pass

CONFIG_PATH = Path(__file__).parent.parent / "config" / "council_config.json"
DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class TradingSignal:
    """交易信号"""

    stock_code: str
    stock_name: str
    action: str  # BUY, SELL, HOLD
    quantity: int
    price: float
    reason: str
    confidence: float
    risk_level: str  # LOW, MEDIUM, HIGH


@dataclass
class OrchestratorResult:
    """编排器执行结果"""

    timestamp: str
    mode: str
    signals: List[TradingSignal]
    decisions: List[dict]
    risk_warnings: List[str]
    execution_results: List[dict]


class TradingOrchestrator:
    """统一交易编排器"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path or CONFIG_PATH)
        self.council = None
        self._init_council()

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_council(self):
        """初始化 AI Council"""
        try:
            self.council = AITradingCouncil()
        except Exception as e:
            print(f"警告: AI Council 初始化失败: {e}")

    def run_daily_workflow(self, mode: str = "analyze") -> OrchestratorResult:
        """运行每日工作流

        Args:
            mode: analyze（仅分析）, trade（执行交易）, daily（完整流程）
        """
        print(f"\n{'=' * 50}")
        print(f"Trading Orchestrator - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"模式: {mode}")
        print(f"{'=' * 50}\n")

        signals = []
        decisions = []
        risk_warnings = []
        execution_results = []

        # Step 1: 获取自选股/持仓
        print("Step 1: 获取股票列表...")
        stocks = self._get_stock_list()
        print(f"  共 {len(stocks)} 只股票\n")

        # Step 2: AI 决策分析
        print("Step 2: AI 决策分析...")
        for stock in stocks[:5]:  # 限制数量避免 API 过载
            try:
                if self.council:
                    decision = self.council.analyze_stock(
                        stock["code"], stock.get("name"), stock.get("market_data")
                    )
                    decisions.append(
                        {
                            "stock_code": decision.stock_code,
                            "stock_name": decision.stock_name,
                            "decision": decision.final_decision,
                            "confidence": decision.confidence,
                            "consensus": decision.consensus_level,
                        }
                    )

                    # 生成交易信号
                    signal = self._decision_to_signal(decision, stock)
                    if signal:
                        signals.append(signal)
            except Exception as e:
                print(f"  分析 {stock['code']} 失败: {e}")

        # Step 3: 风控检查
        print("\nStep 3: 风控检查...")
        risk_warnings = self._risk_check(signals)
        for w in risk_warnings:
            print(f"  ⚠️ {w}")

        # Step 4: 执行交易（如果模式允许）
        if mode in ["trade", "daily"]:
            print("\nStep 4: 执行交易...")
            execution_results = self._execute_trades(signals, risk_warnings)
        else:
            print("\nStep 4: 跳过交易执行（分析模式）")

        # 生成结果
        result = OrchestratorResult(
            timestamp=datetime.now().isoformat(),
            mode=mode,
            signals=signals,
            decisions=decisions,
            risk_warnings=risk_warnings,
            execution_results=execution_results,
        )

        # 保存结果
        self._save_result(result)

        return result

    def _get_stock_list(self) -> List[dict]:
        """获取股票列表（自选股 + 持仓）"""
        stocks = []

        # 持仓
        positions = self.config.get("user_positions", {})
        for code, pos in positions.items():
            stocks.append(
                {
                    "code": code,
                    "name": pos.get("name", code),
                    "type": "position",
                    "cost": pos.get("cost", 0),
                    "shares": pos.get("shares", 0),
                }
            )

        # 这里可以添加自选股获取逻辑
        # 暂时返回持仓

        return stocks

    def _decision_to_signal(
        self, decision: CouncilDecision, stock: dict
    ) -> Optional[TradingSignal]:
        """将决策转换为交易信号"""
        action = "HOLD"

        if decision.final_decision in ["STRONG_BUY", "BUY"]:
            action = "BUY"
        elif decision.final_decision in ["STRONG_SELL", "SELL"]:
            action = "SELL"

        if action == "HOLD":
            return None

        # 计算数量（简单逻辑）
        quantity = 100  # 默认100股

        # 风险等级
        risk_level = "MEDIUM"
        if decision.confidence > 0.7:
            risk_level = "LOW"
        elif decision.confidence < 0.3:
            risk_level = "HIGH"

        return TradingSignal(
            stock_code=decision.stock_code,
            stock_name=decision.stock_name,
            action=action,
            quantity=quantity,
            price=stock.get("cost", 0),  # 需要实时价格
            reason=f"AI Council 决策: {decision.final_decision}",
            confidence=decision.confidence,
            risk_level=risk_level,
        )

    def _risk_check(self, signals: List[TradingSignal]) -> List[str]:
        """风控检查"""
        warnings = []
        limits = self.config.get("risk_limits", {})

        for signal in signals:
            # 检查单只股票仓位限制
            max_position = limits.get("max_position_pct", 20)

            # 检查止损限制
            if signal.action == "BUY":
                # 买入检查
                if signal.risk_level == "HIGH":
                    warnings.append(f"{signal.stock_name}: 置信度过低，建议观望")

            # 检查是否已有持仓
            positions = self.config.get("user_positions", {})
            if signal.stock_code in positions and signal.action == "BUY":
                warnings.append(f"{signal.stock_name}: 已有持仓，注意仓位控制")

        return warnings

    def _execute_trades(
        self, signals: List[TradingSignal], risk_warnings: List[str]
    ) -> List[dict]:
        """执行交易（模拟）"""
        results = []

        for signal in signals:
            # 检查是否有阻止交易的风险警告
            blocked = any(
                signal.stock_name in w for w in risk_warnings if "置信度过低" in w
            )

            result = {
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "action": signal.action,
                "quantity": signal.quantity,
                "status": "BLOCKED" if blocked else "SIMULATED",
                "message": "风险检查未通过" if blocked else "模拟执行成功",
            }
            results.append(result)
            print(f"  {signal.stock_name}: {result['status']} - {result['message']}")

        return results

    def _save_result(self, result: OrchestratorResult):
        """保存执行结果"""
        result_path = (
            DATA_DIR
            / "reports"
            / f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": result.timestamp,
                    "mode": result.mode,
                    "signals": [
                        {
                            "stock_code": s.stock_code,
                            "stock_name": s.stock_name,
                            "action": s.action,
                            "quantity": s.quantity,
                            "confidence": s.confidence,
                            "risk_level": s.risk_level,
                        }
                        for s in result.signals
                    ],
                    "decisions": result.decisions,
                    "risk_warnings": result.risk_warnings,
                    "execution_results": result.execution_results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"\n结果已保存: {result_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Trading Orchestrator")
    parser.add_argument(
        "--mode",
        type=str,
        default="analyze",
        choices=["analyze", "trade", "daily"],
        help="运行模式",
    )
    args = parser.parse_args()

    orchestrator = TradingOrchestrator()
    result = orchestrator.run_daily_workflow(mode=args.mode)

    print(f"\n{'=' * 50}")
    print("执行摘要")
    print(f"{'=' * 50}")
    print(f"决策数: {len(result.decisions)}")
    print(f"信号数: {len(result.signals)}")
    print(f"风险警告: {len(result.risk_warnings)}")
    print(f"执行结果: {len(result.execution_results)}")


if __name__ == "__main__":
    main()
