#!/usr/bin/env python3
"""
Trading Orchestrator - 统一交易编排器

串联完整交易流程：
选股 → AI决策 → 风控检查 → 执行交易

使用方式：
    python trading_orchestrator.py --mode daily          # 每日运行
    python trading_orchestrator.py --mode analyze        # 仅分析不交易
    python trading_orchestrator.py --mode trade          # 执行交易
    python trading_orchestrator.py --stocks 600519,000001  # 指定股票
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading_orchestrator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


class TradingMode(Enum):
    ANALYZE = "analyze"  # 仅分析，不交易
    DAILY = "daily"  # 每日运行（分析+建议）
    TRADE = "trade"  # 执行交易（需确认）


@dataclass
class TradingSignal:
    """交易信号"""

    stock_code: str
    stock_name: str
    action: str  # BUY / SELL / HOLD
    confidence: float
    price: float
    capital_flow: float
    ddx_10d: float
    reasoning: str
    risk_level: str  # LOW / MEDIUM / HIGH


@dataclass
class RiskCheckResult:
    """风控检查结果"""

    passed: bool
    warnings: List[str]
    position_limit: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]


class TradingOrchestrator:
    """统一交易编排器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.data_dir = SCRIPT_DIR.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        # 初始化各模块
        self.council = None
        self.risk_manager = None
        self.cache = None
        self.position_monitor = None
        self.performance_tracker = None

        self._init_modules()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        default_config = {
            "mode": "daily",
            "max_position_pct": 0.3,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.15,
            "min_confidence": 0.6,
            "red_lines": {
                "ddx_10d_positive": True,
                "capital_flow_positive": True,
                "price_change_under_3pct": True,
            },
            "watchlist": [
                "601138",  # 工业富联
                "002475",  # 立讯精密
                "002460",  # 赣锋锂业
                "002281",  # 光迅科技
                "002463",  # 沪电股份
                "300750",  # 宁德时代
                "300476",  # 胜宏科技
                "000988",  # 华工科技
            ],
            "notification": {"enabled": True, "channels": ["console"]},
        }

        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def _init_modules(self):
        """初始化各模块"""
        # 初始化 AI Council
        try:
            from council_engine import TradingCouncil

            self.council = TradingCouncil()
            logger.info("✓ AI Trading Council 已初始化")
        except Exception as e:
            logger.warning(f"✗ AI Council 初始化失败: {e}")

        # 初始化数据缓存
        try:
            from data_cache import DataCache

            self.cache = DataCache()
            logger.info("✓ 数据缓存已初始化")
        except Exception as e:
            logger.warning(f"✗ 数据缓存初始化失败: {e}")

        # 初始化持仓监控
        try:
            from position_monitor import PositionMonitor

            self.position_monitor = PositionMonitor()
            logger.info("✓ 持仓监控已初始化")
        except Exception as e:
            logger.warning(f"✗ 持仓监控初始化失败: {e}")

        # 初始化表现跟踪
        try:
            from performance_tracker import PerformanceTracker

            self.performance_tracker = PerformanceTracker()
            logger.info("✓ 表现跟踪已初始化")
        except Exception as e:
            logger.warning(f"✗ 表现跟踪初始化失败: {e}")

    def run(self, mode: TradingMode, stocks: Optional[List[str]] = None) -> Dict:
        """
        运行完整交易流程

        Args:
            mode: 运行模式
            stocks: 指定股票列表（可选）

        Returns:
            执行结果
        """
        logger.info(f"{'=' * 60}")
        logger.info(f"Trading Orchestrator 启动 - 模式: {mode.value}")
        logger.info(f"{'=' * 60}")

        result = {
            "mode": mode.value,
            "timestamp": datetime.now().isoformat(),
            "signals": [],
            "trades": [],
            "errors": [],
        }

        # 1. 获取股票列表
        target_stocks = stocks or self.config.get("watchlist", [])
        if not target_stocks:
            logger.error("没有指定股票列表")
            return result

        logger.info(f"目标股票: {', '.join(target_stocks)}")

        # 2. 获取市场数据
        market_data = self._fetch_market_data(target_stocks)

        # 3. AI 分析
        signals = self._analyze_stocks(target_stocks, market_data)
        result["signals"] = [self._signal_to_dict(s) for s in signals]

        # 4. 风控检查
        checked_signals = []
        for signal in signals:
            risk_result = self._risk_check(signal)
            if risk_result.passed:
                checked_signals.append(signal)
            else:
                logger.warning(
                    f"{signal.stock_code} 风控未通过: {risk_result.warnings}"
                )

        # 5. 执行交易（如果模式允许）
        if mode == TradingMode.TRADE and checked_signals:
            trades = self._execute_trades(checked_signals)
            result["trades"] = trades

        # 6. 生成报告
        report = self._generate_report(result)
        self._save_report(report)

        # 7. 发送通知
        self._send_notification(result)

        logger.info(f"{'=' * 60}")
        logger.info(f"执行完成 - 信号: {len(signals)}, 可交易: {len(checked_signals)}")
        logger.info(f"{'=' * 60}")

        return result

    def _fetch_market_data(self, stocks: List[str]) -> Dict[str, Dict]:
        """获取市场数据"""
        logger.info("获取市场数据...")

        market_data = {}

        # 优先使用缓存
        if self.cache:
            for stock in stocks:
                cached = self.cache.get_stock_data(stock)
                if cached:
                    market_data[stock] = cached
                    continue

                # 缓存未命中，从API获取
                data = self._fetch_from_api(stock)
                if data:
                    market_data[stock] = data
                    self.cache.set_stock_data(stock, data)
        else:
            # 无缓存，直接从API获取
            for stock in stocks:
                data = self._fetch_from_api(stock)
                if data:
                    market_data[stock] = data

        logger.info(f"获取到 {len(market_data)} 只股票数据")
        return market_data

    def _fetch_from_api(self, stock_code: str) -> Optional[Dict]:
        """从API获取股票数据"""
        try:
            import urllib.request
            import json
            import os

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {os.environ.get('IWENCAI_API_KEY', '')}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": f"{stock_code}最新价、涨跌幅、主力资金流向、10日DDX、ROE、市盈率",
                "page": "1",
                "limit": "1",
                "is_cache": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") == 0 and result.get("datas"):
                item = result["datas"][0]
                return {
                    "code": stock_code,
                    "name": item.get("股票简称", stock_code),
                    "price": float(item.get("最新价", 0)),
                    "change_pct": float(item.get("涨跌幅", "0").replace("%", "")),
                    "capital_flow": float(item.get("主力净流入", 0)),
                    "ddx_10d": float(item.get("10日DDX", 0)),
                    "roe": float(item.get("ROE", "0").replace("%", "")),
                    "pe": float(item.get("市盈率", 0)),
                    "data_source": "iwencai",
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"获取 {stock_code} 数据失败: {e}")

        return None

    def _analyze_stocks(
        self, stocks: List[str], market_data: Dict
    ) -> List[TradingSignal]:
        """AI分析股票"""
        logger.info("AI分析中...")

        signals = []

        for stock in stocks:
            data = market_data.get(stock)
            if not data:
                logger.warning(f"{stock} 无数据，跳过")
                continue

            # 使用 AI Council 分析
            if self.council:
                try:
                    result = self.council.run_council_analysis(stock, data)

                    signal = TradingSignal(
                        stock_code=stock,
                        stock_name=data.get("name", stock),
                        action=result["consensus"],
                        confidence=result["confidence"],
                        price=data.get("price", 0),
                        capital_flow=data.get("capital_flow", 0),
                        ddx_10d=data.get("ddx_10d", 0),
                        reasoning=self._extract_reasoning(result),
                        risk_level=self._assess_risk(data),
                    )
                    signals.append(signal)

                    logger.info(
                        f"  {stock} ({data.get('name', '')}): {signal.action} (置信度: {signal.confidence:.2f})"
                    )
                except Exception as e:
                    logger.error(f"  {stock} 分析失败: {e}")
            else:
                # 无 AI Council，使用规则判断
                signal = self._rule_based_analysis(stock, data)
                if signal:
                    signals.append(signal)

        return signals

    def _rule_based_analysis(
        self, stock_code: str, data: Dict
    ) -> Optional[TradingSignal]:
        """规则分析（无AI时的fallback）"""
        red_lines = self.config.get("red_lines", {})

        # 检查红线规则
        if red_lines.get("ddx_10d_positive") and data.get("ddx_10d", 0) <= 0:
            return TradingSignal(
                stock_code=stock_code,
                stock_name=data.get("name", stock_code),
                action="HOLD",
                confidence=0.3,
                price=data.get("price", 0),
                capital_flow=data.get("capital_flow", 0),
                ddx_10d=data.get("ddx_10d", 0),
                reasoning="10日DDX < 0，不符合买入条件",
                risk_level="HIGH",
            )

        if red_lines.get("capital_flow_positive") and data.get("capital_flow", 0) <= 0:
            return TradingSignal(
                stock_code=stock_code,
                stock_name=data.get("name", stock_code),
                action="HOLD",
                confidence=0.4,
                price=data.get("price", 0),
                capital_flow=data.get("capital_flow", 0),
                ddx_10d=data.get("ddx_10d", 0),
                reasoning="主力资金流出，不符合买入条件",
                risk_level="MEDIUM",
            )

        # 符合条件
        if data.get("capital_flow", 0) > 5 and data.get("ddx_10d", 0) > 0:
            return TradingSignal(
                stock_code=stock_code,
                stock_name=data.get("name", stock_code),
                action="BUY",
                confidence=0.7,
                price=data.get("price", 0),
                capital_flow=data.get("capital_flow", 0),
                ddx_10d=data.get("ddx_10d", 0),
                reasoning="主力资金流入>5亿，10日DDX>0，符合买入条件",
                risk_level="LOW",
            )

        return TradingSignal(
            stock_code=stock_code,
            stock_name=data.get("name", stock_code),
            action="HOLD",
            confidence=0.5,
            price=data.get("price", 0),
            capital_flow=data.get("capital_flow", 0),
            ddx_10d=data.get("ddx_10d", 0),
            reasoning="条件不明确，建议观望",
            risk_level="MEDIUM",
        )

    def _risk_check(self, signal: TradingSignal) -> RiskCheckResult:
        """风控检查"""
        warnings = []
        passed = True

        # 1. 置信度检查
        if signal.confidence < self.config.get("min_confidence", 0.6):
            warnings.append(f"置信度过低: {signal.confidence:.2f}")
            passed = False

        # 2. 红线检查
        red_lines = self.config.get("red_lines", {})

        if red_lines.get("ddx_10d_positive") and signal.ddx_10d <= 0:
            warnings.append(f"10日DDX < 0: {signal.ddx_10d}")
            passed = False

        if red_lines.get("capital_flow_positive") and signal.capital_flow <= 0:
            warnings.append(f"主力资金流出: {signal.capital_flow:.2f}亿")
            passed = False

        # 3. 风险等级检查
        if signal.risk_level == "HIGH":
            warnings.append("风险等级过高")
            passed = False

        # 4. 计算止损止盈价
        stop_loss_price = None
        take_profit_price = None

        if signal.action == "BUY":
            stop_loss_price = signal.price * (
                1 - self.config.get("stop_loss_pct", 0.05)
            )
            take_profit_price = signal.price * (
                1 + self.config.get("take_profit_pct", 0.15)
            )

        return RiskCheckResult(
            passed=passed,
            warnings=warnings,
            position_limit=self.config.get("max_position_pct", 0.3),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )

    def _execute_trades(self, signals: List[TradingSignal]) -> List[Dict]:
        """执行交易"""
        logger.info("执行交易...")

        trades = []

        for signal in signals:
            if signal.action not in ["BUY", "STRONG_BUY"]:
                continue

            trade = {
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "action": "BUY",
                "price": signal.price,
                "timestamp": datetime.now().isoformat(),
                "status": "PENDING",
            }

            # 这里可以对接 live_trading 模块
            # 目前仅记录，不实际执行
            logger.info(f"  建议买入: {signal.stock_code} @ {signal.price}")
            trade["status"] = "SIMULATED"

            trades.append(trade)

        return trades

    def _generate_report(self, result: Dict) -> str:
        """生成报告"""
        report = f"""
# Trading Orchestrator 报告

生成时间: {result["timestamp"]}
运行模式: {result["mode"]}

## 分析结果

| 股票 | 决策 | 置信度 | 主力资金 | 10日DDX | 风险等级 |
|------|------|--------|---------|---------|----------|
"""

        for signal in result["signals"]:
            report += f"| {signal['stock_code']} | {signal['action']} | {signal['confidence']:.2f} | {signal['capital_flow']:.2f}亿 | {signal['ddx_10d']} | {signal['risk_level']} |\n"

        if result["trades"]:
            report += f"""
## 交易执行

"""
            for trade in result["trades"]:
                report += (
                    f"- {trade['stock_code']} @ {trade['price']} ({trade['status']})\n"
                )

        report += f"""
## 统计

- 分析股票数: {len(result["signals"])}
- 可交易信号: {len([s for s in result["signals"] if s["action"] in ["BUY", "STRONG_BUY"]])}
- 执行交易数: {len(result["trades"])}

---
*报告由 Trading Orchestrator 自动生成*
"""

        return report

    def _save_report(self, report: str):
        """保存报告"""
        report_file = (
            self.data_dir
            / f"orchestrator_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存: {report_file}")

    def _send_notification(self, result: Dict):
        """发送通知"""
        if not self.config.get("notification", {}).get("enabled", False):
            return

        # 控制台通知
        print("\n" + "=" * 60)
        print("交易信号汇总")
        print("=" * 60)

        buy_signals = [
            s for s in result["signals"] if s["action"] in ["BUY", "STRONG_BUY"]
        ]
        if buy_signals:
            print("\n建议买入:")
            for s in buy_signals:
                print(
                    f"  {s['stock_code']} ({s['stock_name']}): {s['action']} @ {s['price']}"
                )
                print(
                    f"    主力资金: {s['capital_flow']:.2f}亿, 10日DDX: {s['ddx_10d']}"
                )
        else:
            print("\n暂无买入信号")

        print("\n" + "=" * 60)

    def _extract_reasoning(self, result: Dict) -> str:
        """提取分析理由"""
        votes = result.get("council_votes", {})
        if votes:
            for model, vote in votes.items():
                if vote.get("reasoning"):
                    return vote["reasoning"][:200]
        return "AI分析完成"

    def _assess_risk(self, data: Dict) -> str:
        """评估风险等级"""
        if data.get("ddx_10d", 0) < 0:
            return "HIGH"
        if data.get("capital_flow", 0) < 0:
            return "HIGH"
        if data.get("capital_flow", 0) > 10:
            return "LOW"
        return "MEDIUM"

    def _signal_to_dict(self, signal: TradingSignal) -> Dict:
        """信号转字典"""
        return {
            "stock_code": signal.stock_code,
            "stock_name": signal.stock_name,
            "action": signal.action,
            "confidence": signal.confidence,
            "price": signal.price,
            "capital_flow": signal.capital_flow,
            "ddx_10d": signal.ddx_10d,
            "reasoning": signal.reasoning,
            "risk_level": signal.risk_level,
        }


def main():
    parser = argparse.ArgumentParser(description="Trading Orchestrator")
    parser.add_argument(
        "--mode",
        type=str,
        default="daily",
        choices=["analyze", "daily", "trade"],
        help="运行模式: analyze(仅分析), daily(每日运行), trade(执行交易)",
    )
    parser.add_argument("--stocks", type=str, help="指定股票列表，逗号分隔")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    # 解析股票列表
    stocks = None
    if args.stocks:
        stocks = [s.strip() for s in args.stocks.split(",")]

    # 创建编排器
    orchestrator = TradingOrchestrator(args.config)

    # 运行
    mode = TradingMode(args.mode)
    result = orchestrator.run(mode, stocks)

    print(f"\n完成! 分析 {len(result['signals'])} 只股票")


if __name__ == "__main__":
    main()
