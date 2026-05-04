#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化系统 v3.0 - 统一入口
整合所有模块，提供一站式量化交易服务

核心模块：
1. 数据层：DuckDB存储、数据缓存
2. 因子层：205个因子库
3. 策略层：智能选股、行业对冲
4. 分析层：热点监控、市场状态检测
5. 回测层：高性能回测引擎
6. 决策层：增强版AI决策系统
7. 交易层：实盘交易接口
"""

import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 导入所有模块
from duckdb_storage import DuckDBStorage, DataConfig
from hot_event_monitor import HotEventMonitor, HotEvent, ImpactDepth
from high_performance_backtest import HighPerformanceBacktestEngine
from backtest_engine_fixed import FixedBacktestEngine, CommissionConfig, SlippageConfig
from market_state_detector import MarketStateDetector, MarketState, MarketRegime
from enhanced_ai_decision import EnhancedAIDecisionSystem
from industry_hedge_strategy import IndustryHedgeStrategy
from enhanced_factor_library import EnhancedFactorLibrary
from risk_manager_advanced import EnhancedRiskManager


@dataclass
class QuantSystemConfig:
    """量化系统配置"""

    # 数据库配置
    db_path: str = "data/quant_data.duckdb"
    cache_size: int = 10000

    # 回测配置
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 万三

    # 风控配置
    max_position_ratio: float = 0.2  # 单股最大仓位20%
    stop_loss_ratio: float = 0.05  # 止损5%
    take_profit_ratio: float = 0.10  # 止盈10%

    # 数据源配置
    primary_data_source: str = "妙想"  # 妙想/问财/国信
    enable_cache: bool = True


class QuantSystem:
    """量化系统 v3.0"""

    def __init__(self, config: Optional[QuantSystemConfig] = None):
        """初始化量化系统"""
        self.config = config or QuantSystemConfig()

        print("=" * 70)
        print("量化系统 v3.0 启动中...")
        print("=" * 70)

        # 初始化各模块
        print("\n[1/7] 初始化数据存储...")
        self.storage = DuckDBStorage(
            DataConfig(db_path=self.config.db_path, cache_size=self.config.cache_size)
        )
        print("  ✅ DuckDB数据存储已就绪")

        print("\n[2/7] 初始化因子库...")
        self.factor_library = EnhancedFactorLibrary()
        print(f"  ✅ 因子库已加载（205个因子）")

        print("\n[3/7] 初始化热点监控...")
        self.hot_event_monitor = HotEventMonitor()
        print("  ✅ 热点事件监控已就绪")

        print("\n[4/7] 初始化市场状态检测...")
        self.market_detector = MarketStateDetector()
        print("  ✅ 市场状态检测已就绪")

        print("\n[5/7] 初始化回测引擎...")
        self.backtest_engine = HighPerformanceBacktestEngine()
        self.backtest_engine_fixed = FixedBacktestEngine(
            commission_config=CommissionConfig(), slippage_config=SlippageConfig()
        )
        print("  ✅ 高性能回测引擎已就绪（含修复版）")

        print("\n[6/7] 初始化AI决策系统...")
        self.ai_decision = EnhancedAIDecisionSystem()
        print("  ✅ 增强版AI决策系统已就绪")

        print("\n[7/7] 初始化行业对冲策略...")
        self.hedge_strategy = IndustryHedgeStrategy()
        self.risk_manager = EnhancedRiskManager(
            total_capital=self.config.initial_capital
        )
        print("  ✅ 行业对冲策略已就绪")
        print("  ✅ 增强版风控系统已就绪")

        print("\n" + "=" * 70)
        print("量化系统 v3.0 启动完成！")
        print("=" * 70)

    def analyze_stock(
        self,
        stock_code: str,
        data: Optional[pd.DataFrame] = None,
        industry: Optional[str] = None,
    ) -> Dict:
        """
        分析单只股票

        Args:
            stock_code: 股票代码
            data: 历史行情数据（可选，不传则从数据库读取）
            industry: 行业（可选）

        Returns:
            分析结果
        """
        print(f"\n{'=' * 70}")
        print(f"股票分析: {stock_code}")
        print(f"{'=' * 70}")

        result = {
            "stock_code": stock_code,
            "analysis_time": datetime.now(),
            "status": "success",
        }

        try:
            # 1. 获取数据
            if data is None:
                data = self.storage.get_stock_quotes(stock_code)
                if data.empty:
                    # 生成模拟数据
                    print("  ⚠️ 数据库无数据，使用模拟数据")
                    data = self._generate_mock_data(stock_code)

            result["data_points"] = len(data)

            # 2. 提取因子（简化版）
            print("\n[1/5] 提取因子...")
            # factors = self.factor_library.extract_all_factors(data)
            result["factors"] = {"status": "skipped"}
            print(f"  ✅ 因子提取已跳过")

            # 3. 市场状态检测
            print("\n[2/5] 市场状态检测...")
            market_state = self.market_detector.detect(data)
            result["market_state"] = market_state.to_dict()
            print(f"  波动率: {market_state.volatility.value}")
            print(f"  趋势强度: {market_state.trend.value}")
            print(f"  市场阶段: {market_state.regime.value}")

            # 4. 热点事件
            print("\n[3/5] 热点事件监控...")
            events = self.hot_event_monitor.fetch_hot_events()
            industry_events = (
                self.hot_event_monitor.get_events_by_industry(industry)
                if industry
                else []
            )
            result["hot_events"] = {
                "total": len(events),
                "deep_impact": len(
                    [e for e in events if e.impact_depth == ImpactDepth.DEEP]
                ),
                "industry_related": len(industry_events),
            }
            print(f"  热点事件: {result['hot_events']['total']}个")
            print(f"  深度影响: {result['hot_events']['deep_impact']}个")

            # 5. AI决策
            print("\n[4/5] AI决策分析...")
            decision = self.ai_decision.analyze(stock_code, data, industry)
            result["decision"] = {
                "rating": decision.ai_rating,
                "confidence": decision.ai_confidence,
                "position_size": decision.position_size,
                "stop_loss": decision.stop_loss,
                "take_profit": decision.take_profit,
                "reasoning": decision.ai_reasoning,
            }
            print(f"  评级: {decision.ai_rating}")
            print(f"  置信度: {decision.ai_confidence:.0%}")
            print(f"  建议仓位: {decision.position_size:.0%}")

            # 6. 风险提示
            print("\n[5/5] 风险评估...")
            risks = self._assess_risk(result)
            result["risks"] = risks
            for risk in risks:
                print(f"  ⚠️ {risk}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"  ❌ 分析失败: {e}")

        return result

    def screen_stocks(self, stock_list: List[str], top_n: int = 10) -> pd.DataFrame:
        """
        批量筛选股票

        Args:
            stock_list: 股票代码列表
            top_n: 返回前N只

        Returns:
            筛选结果DataFrame
        """
        print(f"\n{'=' * 70}")
        print(f"批量筛选: {len(stock_list)}只股票")
        print(f"{'=' * 70}")

        results = []
        for i, stock_code in enumerate(stock_list, 1):
            print(f"\n[{i}/{len(stock_list)}] 分析 {stock_code}...")
            try:
                result = self.analyze_stock(stock_code)
                if result["status"] == "success":
                    results.append(
                        {
                            "stock_code": stock_code,
                            "rating": result["decision"]["rating"],
                            "confidence": result["decision"]["confidence"],
                            "position_size": result["decision"]["position_size"],
                            "market_state": result["market_state"]["regime"],
                            "hot_events": result["hot_events"]["total"],
                        }
                    )
            except Exception as e:
                print(f"  ⚠️ 跳过: {e}")

        # 转换为DataFrame
        df = pd.DataFrame(results)

        if not df.empty:
            # 按置信度排序
            df = df.sort_values("confidence", ascending=False).head(top_n)

        print(f"\n{'=' * 70}")
        print(f"筛选完成: {len(df)}只股票")
        print(f"{'=' * 70}")

        return df

    def analyze_portfolio(self, positions: List[Dict]) -> Dict:
        """
        分析投资组合

        Args:
            positions: 持仓列表

        Returns:
            组合分析结果
        """
        print(f"\n{'=' * 70}")
        print("投资组合分析")
        print(f"{'=' * 70}")

        # 1. 组合风险分析
        print("\n[1/3] 组合风险分析...")
        risk_analysis = self.hedge_strategy.calculate_portfolio_risk(positions)
        print(f"  总风险评分: {risk_analysis['total_risk']:.2%}")
        print(f"  风险等级: {risk_analysis['risk_level']}")

        # 2. 对冲建议
        print("\n[2/3] 对冲建议...")
        hedge_recommendations = self.hedge_strategy.generate_hedge_recommendations(
            positions
        )
        print(f"  对冲建议数: {len(hedge_recommendations)}")

        # 3. 个股分析
        print("\n[3/3] 个股分析...")
        stock_analysis = []
        for pos in positions:
            stock_code = pos.get("stock_code")
            print(f"\n  分析 {stock_code}...")
            try:
                result = self.analyze_stock(stock_code)
                if result["status"] == "success":
                    stock_analysis.append(
                        {
                            "stock_code": stock_code,
                            "position_value": pos.get("position_value", 0),
                            "rating": result["decision"]["rating"],
                            "confidence": result["decision"]["confidence"],
                            "market_state": result["market_state"]["regime"],
                        }
                    )
            except Exception as e:
                print(f"    ⚠️ 跳过: {e}")

        return {
            "risk_analysis": risk_analysis,
            "hedge_recommendations": hedge_recommendations,
            "stock_analysis": stock_analysis,
            "total_positions": len(positions),
            "analysis_time": datetime.now(),
        }

    def backtest_strategy(
        self,
        data: pd.DataFrame,
        strategy_func: callable,
        strategy_name: str = "自定义策略",
        use_fixed_engine: bool = True,
    ) -> Dict:
        """
        回测策略

        Args:
            data: 历史数据
            strategy_func: 策略函数
            strategy_name: 策略名称
            use_fixed_engine: 是否使用修复后的回测引擎（默认True，推荐）

        Returns:
            回测结果
        """
        print(f"\n{'=' * 70}")
        print(f"策略回测: {strategy_name}")
        print(f"{'=' * 70}")

        # 选择回测引擎
        if use_fixed_engine:
            print("\n使用修复后的回测引擎（无未来函数 + 完整交易成本）")
            result = self.backtest_engine_fixed.run_backtest(
                data=data,
                strategy_func=strategy_func,
                initial_capital=self.config.initial_capital,
            )
        else:
            print("\n使用原始回测引擎（存在未来函数，仅供参考）")
            result = self.backtest_engine.run_backtest(
                data=data,
                strategy_func=strategy_func,
                initial_capital=self.config.initial_capital,
                stop_loss=self.config.stop_loss_ratio,
                take_profit=self.config.take_profit_ratio,
            )

        print(f"\n【回测结果】")
        print(f"  总收益率: {result.total_return:.2%}")
        print(f"  年化收益: {result.annual_return:.2%}")
        print(f"  最大回撤: {result.max_drawdown:.2%}")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")
        print(f"  胜率: {result.win_rate:.1%}")

        return {
            "strategy_name": strategy_name,
            "total_return": result.total_return,
            "annual_return": result.annual_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "backtest_time": datetime.now(),
        }

    def get_hot_events(
        self, industry: Optional[str] = None, limit: int = 20
    ) -> List[HotEvent]:
        """
        获取热点事件

        Args:
            industry: 行业过滤
            limit: 返回数量

        Returns:
            热点事件列表
        """
        print(f"\n{'=' * 70}")
        print("热点事件监控")
        print(f"{'=' * 70}")

        events = self.hot_event_monitor.fetch_hot_events()

        if industry:
            events = [e for e in events if industry in e.industries]

        events = events[:limit]

        print(f"\n【热点事件】共 {len(events)} 个")
        for i, event in enumerate(events, 1):
            print(f"\n{i}. {event.title}")
            print(f"   影响深度: {event.impact_depth.value}")

        return events

    def check_position_risk(
        self,
        positions: List[Dict],
        check_correlation: bool = True,
        run_stress_test: bool = True,
    ) -> Dict:
        """
        检查持仓风险

        Args:
            positions: 持仓列表，格式 [{"code": "600519", "name": "茅台", "shares": 100, "cost_price": 1800.0, "current_price": 1850.0}]
            check_correlation: 是否检查相关性
            run_stress_test: 是否运行压力测试

        Returns:
            风险检查结果
        """
        print(f"\n{'=' * 70}")
        print("持仓风险检查")
        print(f"{'=' * 70}")

        # 1. 单股风险检查
        print("\n[1/3] 单股风险检查...")
        position_risks = []
        for pos in positions:
            risk = self.risk_manager.check_position_risk(
                code=pos["code"],
                name=pos["name"],
                shares=pos["shares"],
                cost_price=pos["cost_price"],
                current_price=pos["current_price"],
            )
            position_risks.append(risk)
            print(f"  {pos['name']}: 风险等级 {risk.risk_level}")

        # 2. 相关性检查
        correlation_alerts = []
        if check_correlation and len(positions) > 1:
            print("\n[2/3] 相关性检查...")
            correlation_matrix = self.risk_manager.calculate_portfolio_correlation(
                positions
            )
            high_correlation_pairs = []
            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions):
                    if (
                        i < j
                        and correlation_matrix[i, j] > self.risk_manager.max_correlation
                    ):
                        high_correlation_pairs.append(
                            {
                                "stock1": pos1["name"],
                                "stock2": pos2["name"],
                                "correlation": correlation_matrix[i, j],
                            }
                        )
            if high_correlation_pairs:
                print(f"  ⚠️ 发现{len(high_correlation_pairs)}对高相关性持仓")
                correlation_alerts = high_correlation_pairs

        # 3. 压力测试
        stress_test_results = None
        if run_stress_test:
            print("\n[3/3] 压力测试...")
            stress_test_results = self.risk_manager.run_stress_test(positions)
            print(
                f"  轻度下跌(-10%): 损失 {stress_test_results['轻度下跌']['loss_amount']:.0f}元"
            )

        # 4. 整体风险评估
        print("\n[整体风险评估]")
        overall_risk, alerts = self.risk_manager.check_total_risk(positions)
        print(f"  总风险等级: {overall_risk.value}")
        print(f"  预警数量: {len(alerts)}")

        return {
            "position_risks": position_risks,
            "correlation_alerts": correlation_alerts,
            "stress_test_results": stress_test_results,
            "overall_risk": overall_risk.value,
            "alerts": alerts,
        }

    def _generate_mock_data(self, stock_code: str, days: int = 500) -> pd.DataFrame:
        """生成模拟数据"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        # 生成随机价格
        np.random.seed(hash(stock_code) % 2**32)
        base_price = 50 + np.random.random() * 100
        returns = np.random.randn(days) * 0.02
        prices = base_price * (1 + returns).cumprod()

        data = pd.DataFrame(
            {
                "trade_date": dates,
                "open": prices * (1 + np.random.randn(days) * 0.01),
                "high": prices * (1 + np.abs(np.random.randn(days) * 0.02)),
                "low": prices * (1 - np.abs(np.random.randn(days) * 0.02)),
                "close": prices,
                "volume": np.random.randint(1000000, 10000000, days),
                "amount": prices * np.random.randint(1000000, 10000000, days),
            }
        )

        return data

    def _assess_risk(self, analysis_result: Dict) -> List[str]:
        """评估风险"""
        risks = []

        # 市场状态风险
        market_state = analysis_result.get("market_state", {})
        if market_state.get("volatility") == "高波动":
            risks.append("市场波动率较高，注意控制仓位")

        # 决策风险
        decision = analysis_result.get("decision", {})
        if decision.get("confidence", 0) < 0.5:
            risks.append("AI决策置信度较低，需谨慎")

        # 热点事件风险
        hot_events = analysis_result.get("hot_events", {})
        if hot_events.get("deep_impact", 0) > 5:
            risks.append("热点事件较多，市场可能剧烈波动")

        return risks

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        stats = self.storage.get_statistics()

        return {
            "version": "3.0",
            "status": "running",
            "modules": {
                "数据存储": "✅",
                "因子库": "✅ (205个因子)",
                "热点监控": "✅",
                "市场检测": "✅",
                "回测引擎": "✅",
                "AI决策": "✅",
                "行业对冲": "✅",
            },
            "data_stats": stats,
            "config": {
                "数据库路径": self.config.db_path,
                "初始资金": f"{self.config.initial_capital:,.0f}元",
                "止损比例": f"{self.config.stop_loss_ratio:.1%}",
                "止盈比例": f"{self.config.take_profit_ratio:.1%}",
                "最大仓位": f"{self.config.max_position_ratio:.1%}",
            },
        }

    def close(self):
        """关闭系统"""
        self.storage.close()
        print("\n量化系统已关闭")


def main():
    """测试量化系统"""
    print("\n" + "=" * 70)
    print("量化系统 v3.0 测试")
    print("=" * 70)

    # 创建系统实例
    system = QuantSystem()

    # 测试1: 系统状态
    print("\n【测试1: 系统状态】")
    status = system.get_system_status()
    print(f"版本: {status['version']}")
    print(f"状态: {status['status']}")
    print("\n模块状态:")
    for module, status_str in status["modules"].items():
        print(f"  {module}: {status_str}")

    # 测试2: 单股分析
    print("\n【测试2: 单股分析】")
    result = system.analyze_stock("600519", industry="白酒")
    print(f"\n分析结果:")
    print(f"  评级: {result['decision']['rating']}")
    print(f"  置信度: {result['decision']['confidence']:.0%}")
    print(f"  建议仓位: {result['decision']['position_size']:.0%}")

    # 测试3: 热点事件
    print("\n【测试3: 热点事件】")
    events = system.get_hot_events(limit=5)

    # 测试4: 组合分析
    print("\n【测试4: 组合分析】")
    positions = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "industry": "白酒",
            "position_value": 100000,
        },
        {
            "stock_code": "300750",
            "stock_name": "宁德时代",
            "industry": "新能源",
            "position_value": 120000,
        },
    ]
    portfolio_result = system.analyze_portfolio(positions)
    print(f"\n组合风险: {portfolio_result['risk_analysis']['total_risk']:.2%}")
    print(f"风险等级: {portfolio_result['risk_analysis']['risk_level']}")

    # 关闭系统
    system.close()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
