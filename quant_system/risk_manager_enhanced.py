#!/usr/bin/env python3
"""
风控加强系统
- 自动止损止盈
- 仓位管理
- 风险预警
- 回撤控制
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class RiskLevel(Enum):
    """风险等级"""

    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


class AlertType(Enum):
    """预警类型"""

    STOP_LOSS = "止损"
    STOP_PROFIT = "止盈"
    POSITION_LIMIT = "仓位超限"
    DRAWDOWN = "回撤预警"
    VOLATILITY = "波动预警"


@dataclass
class RiskAlert:
    """风险预警"""

    code: str
    name: str
    alert_type: AlertType
    risk_level: RiskLevel
    message: str
    current_value: float
    threshold: float
    action: str
    timestamp: str


@dataclass
class PositionRisk:
    """持仓风险"""

    code: str
    name: str
    shares: int
    cost_price: float
    current_price: float
    profit_loss_pct: float
    position_value: float
    position_pct: float  # 占总资产比例
    days_held: int
    max_drawdown: float
    volatility: float
    risk_level: RiskLevel


class RiskManager:
    """风控管理器"""

    def __init__(self, total_capital: float = 270000):
        self.total_capital = total_capital

        # 风控参数
        self.stop_loss_pct = -0.05  # 止损线 -5%
        self.stop_profit_pct = 0.10  # 止盈线 +10%
        self.max_position_pct = 0.20  # 单股最大仓位 20%
        self.max_total_position_pct = 0.80  # 总仓位上限 80%
        self.max_drawdown_pct = -0.10  # 最大回撤 -10%
        self.max_volatility = 0.05  # 最大波动率 5%

        # 止盈分批
        self.profit_levels = [
            (0.10, 0.33),  # 盈利10%，卖出1/3
            (0.20, 0.50),  # 盈利20%，卖出剩余的一半
            (0.30, 1.00),  # 盈利30%，全部卖出
        ]

    def check_position_risk(
        self,
        code: str,
        name: str,
        shares: int,
        cost_price: float,
        current_price: float,
        buy_date: str,
        historical_prices: List[float] = None,
    ) -> PositionRisk:
        """
        检查持仓风险

        参数:
            code: 股票代码
            name: 股票名称
            shares: 持股数量
            cost_price: 成本价
            current_price: 现价
            buy_date: 买入日期
            historical_prices: 历史价格列表（用于计算波动率）

        返回:
            持仓风险评估
        """
        # 计算盈亏
        profit_loss_pct = (current_price - cost_price) / cost_price

        # 计算持仓市值
        position_value = shares * current_price

        # 计算仓位占比
        position_pct = position_value / self.total_capital

        # 计算持有天数
        buy_datetime = datetime.strptime(buy_date, "%Y-%m-%d")
        days_held = (datetime.now() - buy_datetime).days

        # 计算最大回撤
        max_drawdown = 0.0
        if historical_prices and len(historical_prices) > 0:
            peak = cost_price
            for price in historical_prices:
                if price > peak:
                    peak = price
                drawdown = (price - peak) / peak
                if drawdown < max_drawdown:
                    max_drawdown = drawdown

        # 计算波动率
        volatility = 0.0
        if historical_prices and len(historical_prices) > 1:
            returns = pd.Series(historical_prices).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波动率

        # 确定风险等级
        if profit_loss_pct < self.stop_loss_pct:
            risk_level = RiskLevel.CRITICAL
        elif position_pct > self.max_position_pct:
            risk_level = RiskLevel.HIGH
        elif max_drawdown < self.max_drawdown_pct:
            risk_level = RiskLevel.HIGH
        elif volatility > self.max_volatility:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return PositionRisk(
            code=code,
            name=name,
            shares=shares,
            cost_price=cost_price,
            current_price=current_price,
            profit_loss_pct=profit_loss_pct,
            position_value=position_value,
            position_pct=position_pct,
            days_held=days_held,
            max_drawdown=max_drawdown,
            volatility=volatility,
            risk_level=risk_level,
        )

    def generate_alerts(self, position_risk: PositionRisk) -> List[RiskAlert]:
        """生成风险预警"""
        alerts = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 止损预警
        if position_risk.profit_loss_pct <= self.stop_loss_pct:
            alerts.append(
                RiskAlert(
                    code=position_risk.code,
                    name=position_risk.name,
                    alert_type=AlertType.STOP_LOSS,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"触发止损线：亏损{position_risk.profit_loss_pct:.2%}",
                    current_value=position_risk.profit_loss_pct,
                    threshold=self.stop_loss_pct,
                    action="立即卖出",
                    timestamp=timestamp,
                )
            )

        # 止盈预警
        if position_risk.profit_loss_pct >= self.stop_profit_pct:
            # 判断止盈级别
            for profit_level, sell_ratio in self.profit_levels:
                if position_risk.profit_loss_pct >= profit_level:
                    alerts.append(
                        RiskAlert(
                            code=position_risk.code,
                            name=position_risk.name,
                            alert_type=AlertType.STOP_PROFIT,
                            risk_level=RiskLevel.LOW,
                            message=f"触发止盈线：盈利{position_risk.profit_loss_pct:.2%}，建议卖出{sell_ratio:.0%}",
                            current_value=position_risk.profit_loss_pct,
                            threshold=profit_level,
                            action=f"卖出{sell_ratio:.0%}仓位",
                            timestamp=timestamp,
                        )
                    )
                    break

        # 仓位超限预警
        if position_risk.position_pct > self.max_position_pct:
            alerts.append(
                RiskAlert(
                    code=position_risk.code,
                    name=position_risk.name,
                    alert_type=AlertType.POSITION_LIMIT,
                    risk_level=RiskLevel.HIGH,
                    message=f"仓位超限：{position_risk.position_pct:.1%} > {self.max_position_pct:.1%}",
                    current_value=position_risk.position_pct,
                    threshold=self.max_position_pct,
                    action="减仓至合规水平",
                    timestamp=timestamp,
                )
            )

        # 回撤预警
        if position_risk.max_drawdown < self.max_drawdown_pct:
            alerts.append(
                RiskAlert(
                    code=position_risk.code,
                    name=position_risk.name,
                    alert_type=AlertType.DRAWDOWN,
                    risk_level=RiskLevel.HIGH,
                    message=f"回撤过大：{position_risk.max_drawdown:.2%}",
                    current_value=position_risk.max_drawdown,
                    threshold=self.max_drawdown_pct,
                    action="考虑止损或减仓",
                    timestamp=timestamp,
                )
            )

        # 波动预警
        if position_risk.volatility > self.max_volatility:
            alerts.append(
                RiskAlert(
                    code=position_risk.code,
                    name=position_risk.name,
                    alert_type=AlertType.VOLATILITY,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"波动率过高：{position_risk.volatility:.2%}",
                    current_value=position_risk.volatility,
                    threshold=self.max_volatility,
                    action="密切关注，考虑减仓",
                    timestamp=timestamp,
                )
            )

        return alerts

    def calculate_position_size(
        self, code: str, price: float, volatility: float = 0.03, confidence: float = 0.5
    ) -> int:
        """
        计算建议仓位

        参数:
            code: 股票代码
            price: 当前价格
            volatility: 波动率
            confidence: 信号置信度

        返回:
            建议买入股数
        """
        # 基础仓位（根据置信度）
        base_position_pct = min(confidence * 0.2, self.max_position_pct)

        # 波动率调整（波动越大，仓位越小）
        volatility_adjustment = max(1 - volatility / self.max_volatility, 0.5)
        adjusted_position_pct = base_position_pct * volatility_adjustment

        # 计算股数
        position_value = self.total_capital * adjusted_position_pct
        shares = int(position_value / price)

        return shares

    def check_total_risk(
        self, positions: List[PositionRisk]
    ) -> Tuple[RiskLevel, List[RiskAlert]]:
        """
        检查整体风险

        返回:
            (整体风险等级, 预警列表)
        """
        alerts = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 计算总仓位
        total_position_pct = sum(p.position_pct for p in positions)

        # 总仓位超限
        if total_position_pct > self.max_total_position_pct:
            alerts.append(
                RiskAlert(
                    code="TOTAL",
                    name="整体仓位",
                    alert_type=AlertType.POSITION_LIMIT,
                    risk_level=RiskLevel.HIGH,
                    message=f"总仓位超限：{total_position_pct:.1%} > {self.max_total_position_pct:.1%}",
                    current_value=total_position_pct,
                    threshold=self.max_total_position_pct,
                    action="降低整体仓位",
                    timestamp=timestamp,
                )
            )

        # 计算总盈亏
        total_profit_loss = sum(p.position_value * p.profit_loss_pct for p in positions)
        total_profit_loss_pct = total_profit_loss / self.total_capital

        # 整体止损
        if total_profit_loss_pct < self.stop_loss_pct:
            alerts.append(
                RiskAlert(
                    code="TOTAL",
                    name="整体盈亏",
                    alert_type=AlertType.STOP_LOSS,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"整体亏损触发止损：{total_profit_loss_pct:.2%}",
                    current_value=total_profit_loss_pct,
                    threshold=self.stop_loss_pct,
                    action="清仓止损",
                    timestamp=timestamp,
                )
            )

        # 确定整体风险等级
        critical_count = sum(1 for p in positions if p.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for p in positions if p.risk_level == RiskLevel.HIGH)

        if critical_count > 0:
            overall_risk = RiskLevel.CRITICAL
        elif high_count >= 2:
            overall_risk = RiskLevel.HIGH
        elif high_count >= 1:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        return overall_risk, alerts

    def generate_risk_report(self, positions: List[PositionRisk]) -> str:
        """生成风险报告"""
        overall_risk, alerts = self.check_total_risk(positions)

        lines = []
        lines.append("# 风控报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**总资金**: {self.total_capital:,.0f}元\n")
        lines.append(f"**整体风险**: {overall_risk.value}\n\n")

        # 风控参数
        lines.append("## 风控参数\n\n")
        lines.append(f"- **止损线**: {self.stop_loss_pct:.1%}\n")
        lines.append(f"- **止盈线**: {self.stop_profit_pct:.1%}\n")
        lines.append(f"- **单股最大仓位**: {self.max_position_pct:.1%}\n")
        lines.append(f"- **总仓位上限**: {self.max_total_position_pct:.1%}\n")
        lines.append(f"- **最大回撤**: {self.max_drawdown_pct:.1%}\n\n")

        # 持仓风险
        lines.append("## 持仓风险\n\n")
        lines.append(
            "| 股票 | 代码 | 盈亏 | 仓位 | 持有天数 | 最大回撤 | 波动率 | 风险等级 |\n"
        )
        lines.append(
            "|------|------|------|------|----------|----------|--------|----------|\n"
        )

        for p in positions:
            lines.append(
                f"| {p.name} | {p.code} | {p.profit_loss_pct:.2%} | "
                f"{p.position_pct:.1%} | {p.days_held}天 | "
                f"{p.max_drawdown:.2%} | {p.volatility:.2%} | {p.risk_level.value} |\n"
            )

        # 风险预警
        if alerts:
            lines.append("\n## 风险预警\n\n")
            lines.append("| 股票 | 类型 | 风险等级 | 消息 | 建议操作 |\n")
            lines.append("|------|------|----------|------|----------|\n")

            for alert in alerts:
                lines.append(
                    f"| {alert.name} | {alert.alert_type.value} | "
                    f"{alert.risk_level.value} | {alert.message} | {alert.action} |\n"
                )

        # 止盈建议
        lines.append("\n## 止盈策略\n\n")
        lines.append("| 盈利水平 | 操作 |\n")
        lines.append("|----------|------|\n")
        for profit_level, sell_ratio in self.profit_levels:
            lines.append(f"| {profit_level:.0%} | 卖出{sell_ratio:.0%}仓位 |\n")

        return "".join(lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="风控加强系统")
    parser.add_argument("--capital", type=float, default=270000, help="总资金")

    args = parser.parse_args()

    # 创建风控管理器
    manager = RiskManager(total_capital=args.capital)

    print("风控加强系统已创建")
    print(f"总资金: {args.capital:,.0f}元")
    print(f"\n风控参数:")
    print(f"  止损线: {manager.stop_loss_pct:.1%}")
    print(f"  止盈线: {manager.stop_profit_pct:.1%}")
    print(f"  单股最大仓位: {manager.max_position_pct:.1%}")
    print(f"  总仓位上限: {manager.max_total_position_pct:.1%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
