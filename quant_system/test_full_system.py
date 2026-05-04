#!/usr/bin/env python3
"""
完整系统测试
整合实盘验证、组合策略、风控加强三个系统
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from quant_system.live_trading_validator import LiveTradingValidator, SignalType
from quant_system.portfolio_strategy import PortfolioManager, MultiStrategyVoting
from quant_system.risk_manager_enhanced import RiskManager, PositionRisk


def generate_test_data(days: int = 250, seed: int = 42) -> pd.DataFrame:
    """生成测试数据"""
    np.random.seed(seed)

    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    returns = np.random.randn(days) * 0.02
    trend = np.linspace(0, 0.3, days)
    prices = 100 * np.exp(np.cumsum(returns + trend / days))

    data = pd.DataFrame(
        {
            "date": dates,
            "open": prices * (1 + np.random.randn(days) * 0.01),
            "high": prices * (1 + np.abs(np.random.randn(days) * 0.02)),
            "low": prices * (1 - np.abs(np.random.randn(days) * 0.02)),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, days),
        }
    )
    data.set_index("date", inplace=True)

    return data


def test_live_trading_validator():
    """测试实盘验证系统"""
    print("\n" + "=" * 60)
    print("测试实盘验证系统")
    print("=" * 60)

    # 创建验证系统
    validator = LiveTradingValidator(initial_capital=270000)

    # 生成测试数据
    data = generate_test_data(days=250, seed=42)

    # 分析股票
    signals = validator.analyze_stock("600519", "茅台", data)

    print("\n各策略信号:")
    for signal in signals:
        print(
            f"  {signal.strategy}: {signal.signal_type.value} "
            f"(置信度: {signal.confidence:.2%}) - {signal.reason}"
        )

    # 获取组合信号
    final_signal, confidence, reason = validator.get_combined_signal(signals)
    print(f"\n组合决策: {final_signal.value} (置信度: {confidence:.2%})")
    print(f"原因: {reason}")

    return validator, signals


def test_portfolio_strategy():
    """测试组合策略系统"""
    print("\n" + "=" * 60)
    print("测试组合策略系统")
    print("=" * 60)

    # 创建组合管理器
    manager = PortfolioManager(total_capital=270000)

    # 准备股票列表
    stock_list = [
        {"code": "600519", "name": "茅台", "data": generate_test_data(250, seed=42)},
        {
            "code": "300750",
            "name": "宁德时代",
            "data": generate_test_data(250, seed=43),
        },
        {
            "code": "000001",
            "name": "平安银行",
            "data": generate_test_data(250, seed=44),
        },
    ]

    # 分析组合
    decisions = manager.analyze_portfolio(stock_list)

    print("\n组合决策:")
    for d in decisions:
        print(f"\n{d.name}({d.code}):")
        print(f"  最终决策: {d.final_signal.value}")
        print(f"  置信度: {d.confidence:.2%}")
        print(
            f"  投票: 买入{d.buy_votes}票, 卖出{d.sell_votes}票, 持有{d.hold_votes}票"
        )
        print(f"  风险等级: {d.risk_level}")
        print(f"  建议仓位: {d.position_size:.1%}")

    # 资金分配
    allocations = manager.allocate_capital(decisions)
    print("\n资金分配:")
    for code, amount in allocations.items():
        print(f"  {code}: {amount:,.0f}元")

    return manager, decisions


def test_risk_manager():
    """测试风控加强系统"""
    print("\n" + "=" * 60)
    print("测试风控加强系统")
    print("=" * 60)

    # 创建风控管理器
    manager = RiskManager(total_capital=270000)

    # 模拟持仓
    positions = [
        {
            "code": "600519",
            "name": "茅台",
            "shares": 100,
            "cost_price": 1800.0,
            "current_price": 1850.0,
            "buy_date": "2026-04-01",
        },
        {
            "code": "300750",
            "name": "宁德时代",
            "shares": 200,
            "cost_price": 200.0,
            "current_price": 210.0,
            "buy_date": "2026-04-15",
        },
    ]

    # 检查风险
    position_risks = []
    all_alerts = []

    for pos in positions:
        risk = manager.check_position_risk(
            code=pos["code"],
            name=pos["name"],
            shares=pos["shares"],
            cost_price=pos["cost_price"],
            current_price=pos["current_price"],
            buy_date=pos["buy_date"],
            historical_prices=[
                pos["cost_price"] * (1 + np.random.randn() * 0.02) for _ in range(20)
            ],
        )
        position_risks.append(risk)

        # 生成预警
        alerts = manager.generate_alerts(risk)
        all_alerts.extend(alerts)

        print(f"\n{pos['name']}({pos['code']})风险:")
        print(f"  盈亏: {risk.profit_loss_pct:.2%}")
        print(f"  仓位: {risk.position_pct:.1%}")
        print(f"  持有天数: {risk.days_held}天")
        print(f"  风险等级: {risk.risk_level.value}")

        if alerts:
            print(f"  预警:")
            for alert in alerts:
                print(f"    - {alert.alert_type.value}: {alert.message}")

    # 整体风险
    overall_risk, total_alerts = manager.check_total_risk(position_risks)
    print(f"\n整体风险等级: {overall_risk.value}")

    return manager, position_risks


def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 60)
    print("测试完整工作流")
    print("=" * 60)

    # 1. 实盘验证
    validator, signals = test_live_trading_validator()

    # 2. 组合策略
    portfolio_manager, decisions = test_portfolio_strategy()

    # 3. 风控加强
    risk_manager, position_risks = test_risk_manager()

    # 4. 生成综合报告
    print("\n" + "=" * 60)
    print("生成综合报告")
    print("=" * 60)

    lines = []
    lines.append("# 量化交易系统综合报告\n\n")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # 实盘验证摘要
    summary = validator.get_portfolio_summary()
    lines.append("## 实盘验证摘要\n\n")
    lines.append(f"- **初始资金**: {summary['initial_capital']:,.0f}元\n")
    lines.append(f"- **现金余额**: {summary['cash']:,.0f}元\n")
    lines.append(f"- **总资产**: {summary['total_value']:,.0f}元\n")
    lines.append(f"- **总收益率**: {summary['total_return']:.2%}\n\n")

    # 组合策略摘要
    buy_count = sum(1 for d in decisions if d.final_signal == SignalType.BUY)
    lines.append("## 组合策略摘要\n\n")
    lines.append(f"- **买入信号**: {buy_count}只\n")
    lines.append(f"- **总资金**: {portfolio_manager.total_capital:,.0f}元\n\n")

    # 风控摘要
    overall_risk, _ = risk_manager.check_total_risk(position_risks)
    lines.append("## 风控摘要\n\n")
    lines.append(f"- **整体风险**: {overall_risk.value}\n")
    lines.append(f"- **持仓数量**: {len(position_risks)}只\n\n")

    report = "".join(lines)

    # 保存报告
    output_path = PROJECT_ROOT / "data" / "full_system_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存到: {output_path}")
    print("\n" + report)

    return {
        "validator": validator,
        "portfolio_manager": portfolio_manager,
        "risk_manager": risk_manager,
        "decisions": decisions,
        "position_risks": position_risks,
    }


def main():
    """主函数"""
    print("=" * 60)
    print("量化交易系统完整测试")
    print("=" * 60)

    # 运行完整测试
    results = test_full_workflow()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n系统功能:")
    print("  1. 实盘验证: 使用优化参数进行模拟交易")
    print("  2. 组合策略: 多策略投票，动态资金分配")
    print("  3. 风控加强: 自动止损止盈，风险预警")

    return 0


if __name__ == "__main__":
    main()
