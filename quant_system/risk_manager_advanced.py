#!/usr/bin/env python3
"""
增强版风控系统
- 凯利公式仓位管理
- 相关性风控
- 杠杆率控制
- 压力测试
- VaR计算
- 动态止损止盈

修复内容：
1. 实现凯利公式动态仓位管理
2. 持仓相关性分析与风控
3. 杠杆率监控与限制
4. 压力测试与极端情况模拟
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings

warnings.filterwarnings("ignore")


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
    CORRELATION = "相关性预警"
    LEVERAGE = "杠杆率预警"
    KELLY = "凯利仓位预警"


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
    position_pct: float
    days_held: int
    max_drawdown: float
    volatility: float
    risk_level: RiskLevel
    kelly_position: float = 0.0  # 凯利建议仓位
    correlation_risk: float = 0.0  # 相关性风险


class EnhancedRiskManager:
    """增强版风控管理器"""

    def __init__(self, total_capital: float = 270000):
        self.total_capital = total_capital

        # 基础风控参数
        self.stop_loss_pct = -0.05
        self.stop_profit_pct = 0.10
        self.max_position_pct = 0.20
        self.max_total_position_pct = 0.80
        self.max_drawdown_pct = -0.10
        self.max_volatility = 0.05

        # 凯利公式参数
        self.kelly_fraction = 0.25  # 使用1/4凯利（保守）
        self.min_win_rate = 0.40  # 最低胜率要求
        self.min_win_loss_ratio = 1.0  # 最低盈亏比要求

        # 相关性风控参数
        self.max_correlation = 0.70  # 最大持仓相关性
        self.correlation_lookback = 60  # 相关性计算周期

        # 杠杆率参数
        self.max_leverage = 1.0  # 最大杠杆率（1.0 = 无杠杆）
        self.current_leverage = 1.0

        # 压力测试参数
        self.stress_scenarios = {
            "轻度下跌": -0.10,
            "中度下跌": -0.20,
            "重度下跌": -0.30,
            "极端下跌": -0.50,
            "闪崩": -0.70,
        }

        # 止盈分批
        self.profit_levels = [
            (0.10, 0.33),
            (0.20, 0.50),
            (0.30, 1.00),
        ]

        # 历史交易记录（用于凯利公式）
        self.trade_history: List[Dict] = []

    def calculate_kelly_position(
        self,
        win_rate: float,
        win_loss_ratio: float,
        volatility: float = 0.03,
    ) -> float:
        """
        凯利公式计算最优仓位

        公式: f* = (p * b - q) / b
        其中: p = 胜率, q = 1-p, b = 盈亏比

        Args:
            win_rate: 胜率（0-1）
            win_loss_ratio: 盈亏比（平均盈利/平均亏损）
            volatility: 波动率（用于调整）

        Returns:
            建议仓位比例（0-1）
        """
        # 检查最低要求
        if win_rate < self.min_win_rate:
            return 0.0

        if win_loss_ratio < self.min_win_loss_ratio:
            return 0.0

        # 凯利公式
        q = 1 - win_rate
        kelly = (win_rate * win_loss_ratio - q) / win_loss_ratio

        # 使用部分凯利（降低风险）
        kelly = kelly * self.kelly_fraction

        # 波动率调整（波动越大，仓位越小）
        if volatility > 0.03:
            volatility_adj = max(0.5, 1 - (volatility - 0.03) / 0.05)
            kelly *= volatility_adj

        # 限制最大仓位
        kelly = min(kelly, self.max_position_pct)
        kelly = max(kelly, 0.0)

        return kelly

    def calculate_portfolio_correlation(
        self,
        positions: List[PositionRisk],
        price_data: Dict[str, pd.DataFrame],
    ) -> Tuple[np.ndarray, List[str]]:
        """
        计算持仓相关性矩阵

        Args:
            positions: 持仓列表
            price_data: 价格数据字典 {code: DataFrame}

        Returns:
            (相关性矩阵, 股票代码列表)
        """
        if len(positions) < 2:
            return np.array([]), []

        codes = [p.code for p in positions]
        returns_dict = {}

        for code in codes:
            if code in price_data and len(price_data[code]) > 0:
                # 计算收益率
                closes = price_data[code]["close"]
                returns = closes.pct_change().dropna()

                # 取最近N天
                if len(returns) > self.correlation_lookback:
                    returns = returns.tail(self.correlation_lookback)

                returns_dict[code] = returns

        if len(returns_dict) < 2:
            return np.array([]), []

        # 构建收益率DataFrame
        returns_df = pd.DataFrame(returns_dict)

        # 计算相关性矩阵
        corr_matrix = returns_df.corr().values

        return corr_matrix, codes

    def check_correlation_risk(
        self,
        positions: List[PositionRisk],
        price_data: Dict[str, pd.DataFrame],
    ) -> List[RiskAlert]:
        """
        检查相关性风险

        高相关性持仓会放大风险，需要降低仓位
        """
        alerts = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if len(positions) < 2:
            return alerts

        corr_matrix, codes = self.calculate_portfolio_correlation(positions, price_data)

        if len(corr_matrix) == 0:
            return alerts

        # 检查每对股票的相关性
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                corr = corr_matrix[i, j]

                if corr > self.max_correlation:
                    alerts.append(
                        RiskAlert(
                            code=f"{codes[i]}-{codes[j]}",
                            name="持仓相关性",
                            alert_type=AlertType.CORRELATION,
                            risk_level=RiskLevel.HIGH,
                            message=f"持仓相关性过高: {corr:.2f} > {self.max_correlation:.2f}",
                            current_value=corr,
                            threshold=self.max_correlation,
                            action="降低其中一只股票的仓位",
                            timestamp=timestamp,
                        )
                    )

        return alerts

    def calculate_leverage(
        self,
        positions: List[PositionRisk],
        margin_used: float = 0.0,
    ) -> float:
        """
        计算当前杠杆率

        Args:
            positions: 持仓列表
            margin_used: 已使用保证金

        Returns:
            杠杆率（1.0 = 无杠杆）
        """
        total_position_value = sum(p.position_value for p in positions)

        if self.total_capital <= 0:
            return 1.0

        # 杠杆率 = 总持仓市值 / 净资产
        leverage = total_position_value / (self.total_capital - margin_used)

        return leverage

    def check_leverage_risk(
        self,
        positions: List[PositionRisk],
        margin_used: float = 0.0,
    ) -> List[RiskAlert]:
        """检查杠杆率风险"""
        alerts = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        leverage = self.calculate_leverage(positions, margin_used)
        self.current_leverage = leverage

        if leverage > self.max_leverage:
            alerts.append(
                RiskAlert(
                    code="TOTAL",
                    name="整体杠杆",
                    alert_type=AlertType.LEVERAGE,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"杠杆率过高: {leverage:.2f}x > {self.max_leverage:.2f}x",
                    current_value=leverage,
                    threshold=self.max_leverage,
                    action="降低仓位或增加保证金",
                    timestamp=timestamp,
                )
            )

        return alerts

    def run_stress_test(
        self,
        positions: List[PositionRisk],
    ) -> Dict[str, Dict]:
        """
        压力测试

        模拟不同市场情况下的损失
        """
        results = {}
        total_position_value = sum(p.position_value for p in positions)

        for scenario_name, drop_pct in self.stress_scenarios.items():
            # 计算该场景下的损失
            loss = total_position_value * drop_pct
            loss_pct = loss / self.total_capital

            # 计算剩余资金
            remaining_capital = self.total_capital + loss

            # 判断是否触发清盘
            is_liquidation = remaining_capital < self.total_capital * 0.3

            results[scenario_name] = {
                "drop_pct": drop_pct,
                "loss_amount": loss,
                "loss_pct": loss_pct,
                "remaining_capital": remaining_capital,
                "is_liquidation": is_liquidation,
                "risk_level": RiskLevel.CRITICAL
                if is_liquidation
                else (RiskLevel.HIGH if loss_pct < -0.20 else RiskLevel.MEDIUM),
            }

        return results

    def calculate_var(
        self,
        positions: List[PositionRisk],
        confidence_level: float = 0.95,
        time_horizon: int = 1,
    ) -> Dict[str, float]:
        """
        计算VaR（风险价值）

        Args:
            positions: 持仓列表
            confidence_level: 置信水平（0.95 = 95%）
            time_horizon: 时间跨度（天）

        Returns:
            VaR计算结果
        """
        if len(positions) == 0:
            return {"var": 0, "var_pct": 0}

        # 计算组合波动率
        total_value = sum(p.position_value for p in positions)
        weighted_volatility = sum(
            p.position_value / total_value * p.volatility
            for p in positions
            if p.volatility > 0
        )

        if weighted_volatility == 0:
            weighted_volatility = 0.20  # 默认20%年化波动率

        # 日波动率
        daily_vol = weighted_volatility / np.sqrt(252)

        # VaR计算（正态分布假设）
        from scipy.stats import norm

        z_score = norm.ppf(1 - confidence_level)

        var = total_value * daily_vol * z_score * np.sqrt(time_horizon)
        var_pct = var / self.total_capital

        return {
            "var": abs(var),
            "var_pct": abs(var_pct),
            "confidence_level": confidence_level,
            "time_horizon": time_horizon,
        }

    def update_trade_history(
        self,
        code: str,
        profit_pct: float,
        hold_days: int,
    ):
        """更新交易历史（用于凯利公式）"""
        self.trade_history.append(
            {
                "code": code,
                "profit_pct": profit_pct,
                "hold_days": hold_days,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
        )

    def get_statistics(self) -> Dict[str, float]:
        """计算交易统计（用于凯利公式）"""
        if len(self.trade_history) < 10:
            return {
                "win_rate": 0.5,
                "win_loss_ratio": 1.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
            }

        profits = [t["profit_pct"] for t in self.trade_history]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]

        win_rate = len(wins) / len(profits) if len(profits) > 0 else 0.5
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

        return {
            "win_rate": win_rate,
            "win_loss_ratio": win_loss_ratio,
            "avg_profit": avg_win,
            "avg_loss": avg_loss,
            "total_trades": len(profits),
        }

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
        """检查持仓风险（增强版）"""
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
            volatility = returns.std() * np.sqrt(252)

        # 凯利仓位
        stats = self.get_statistics()
        kelly_position = self.calculate_kelly_position(
            stats["win_rate"],
            stats["win_loss_ratio"],
            volatility,
        )

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
            kelly_position=kelly_position,
        )

    def generate_alerts(self, position_risk: PositionRisk) -> List[RiskAlert]:
        """生成风险预警（增强版）"""
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

        # 凯利仓位预警
        if (
            position_risk.kelly_position > 0
            and position_risk.position_pct > position_risk.kelly_position
        ):
            alerts.append(
                RiskAlert(
                    code=position_risk.code,
                    name=position_risk.name,
                    alert_type=AlertType.KELLY,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"超过凯利建议仓位：{position_risk.position_pct:.1%} > {position_risk.kelly_position:.1%}",
                    current_value=position_risk.position_pct,
                    threshold=position_risk.kelly_position,
                    action="考虑减仓至凯利建议水平",
                    timestamp=timestamp,
                )
            )

        return alerts

    def calculate_position_size(
        self, code: str, price: float, volatility: float = 0.03, confidence: float = 0.5
    ) -> int:
        """计算建议仓位（增强版 - 使用凯利公式）"""
        stats = self.get_statistics()

        # 凯利仓位
        kelly_pct = self.calculate_kelly_position(
            stats["win_rate"],
            stats["win_loss_ratio"],
            volatility,
        )

        # 如果凯利仓位为0，使用置信度计算
        if kelly_pct == 0:
            kelly_pct = min(confidence * 0.15, self.max_position_pct)

        # 计算股数
        position_value = self.total_capital * kelly_pct
        shares = int(position_value / price)

        return shares

    def generate_risk_report(
        self,
        positions: List[PositionRisk],
        price_data: Dict[str, pd.DataFrame] = None,
    ) -> str:
        """生成风险报告（增强版）"""
        lines = []
        lines.append("# 增强版风控报告\n\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**总资金**: {self.total_capital:,.0f}元\n\n")

        # 风控参数
        lines.append("## 风控参数\n\n")
        lines.append(f"- **止损线**: {self.stop_loss_pct:.1%}\n")
        lines.append(f"- **止盈线**: {self.stop_profit_pct:.1%}\n")
        lines.append(f"- **单股最大仓位**: {self.max_position_pct:.1%}\n")
        lines.append(f"- **总仓位上限**: {self.max_total_position_pct:.1%}\n")
        lines.append(f"- **最大回撤**: {self.max_drawdown_pct:.1%}\n")
        lines.append(f"- **最大杠杆率**: {self.max_leverage:.2f}x\n")
        lines.append(f"- **凯利系数**: {self.kelly_fraction:.2f}\n\n")

        # 凯利统计
        stats = self.get_statistics()
        lines.append("## 凯利公式统计\n\n")
        lines.append(f"- **历史胜率**: {stats['win_rate']:.2%}\n")
        lines.append(f"- **盈亏比**: {stats['win_loss_ratio']:.2f}\n")
        lines.append(f"- **历史交易次数**: {stats.get('total_trades', 0)}\n\n")

        # 持仓风险
        lines.append("## 持仓风险\n\n")
        lines.append("| 股票 | 代码 | 盈亏 | 仓位 | 凯利仓位 | 持有天数 | 风险等级 |\n")
        lines.append("|------|------|------|------|----------|----------|----------|\n")

        for p in positions:
            lines.append(
                f"| {p.name} | {p.code} | {p.profit_loss_pct:.2%} | "
                f"{p.position_pct:.1%} | {p.kelly_position:.1%} | "
                f"{p.days_held}天 | {p.risk_level.value} |\n"
            )

        # 相关性分析
        if price_data and len(positions) >= 2:
            lines.append("\n## 相关性分析\n\n")
            corr_alerts = self.check_correlation_risk(positions, price_data)

            if corr_alerts:
                lines.append("| 股票对 | 相关性 | 阈值 | 建议操作 |\n")
                lines.append("|--------|--------|------|----------|\n")
                for alert in corr_alerts:
                    lines.append(
                        f"| {alert.code} | {alert.current_value:.2f} | "
                        f"{alert.threshold:.2f} | {alert.action} |\n"
                    )
            else:
                lines.append("持仓相关性正常，无高风险相关性。\n")

        # 杠杆率分析
        lines.append("\n## 杠杆率分析\n\n")
        leverage = self.calculate_leverage(positions)
        lines.append(f"- **当前杠杆率**: {leverage:.2f}x\n")
        lines.append(f"- **最大杠杆率**: {self.max_leverage:.2f}x\n")

        if leverage > self.max_leverage:
            lines.append(f"- **警告**: 杠杆率超标！\n")

        # 压力测试
        lines.append("\n## 压力测试\n\n")
        stress_results = self.run_stress_test(positions)

        lines.append("| 场景 | 跌幅 | 损失金额 | 损失比例 | 是否清盘 |\n")
        lines.append("|------|------|----------|----------|----------|\n")

        for scenario, result in stress_results.items():
            lines.append(
                f"| {scenario} | {result['drop_pct']:.0%} | "
                f"{result['loss_amount']:,.0f}元 | {result['loss_pct']:.2%} | "
                f"{'是' if result['is_liquidation'] else '否'} |\n"
            )

        # VaR分析
        lines.append("\n## VaR分析\n\n")
        var_result = self.calculate_var(positions)
        lines.append(
            f"- **95% VaR（1天）**: {var_result['var']:,.0f}元 ({var_result['var_pct']:.2%})\n"
        )

        return "".join(lines)


def main():
    """测试增强版风控系统"""
    print("=" * 70)
    print("测试增强版风控系统")
    print("=" * 70)

    # 创建风控管理器
    manager = EnhancedRiskManager(total_capital=270000)

    # 模拟交易历史
    manager.update_trade_history("600519", 0.05, 10)
    manager.update_trade_history("600519", -0.03, 5)
    manager.update_trade_history("600519", 0.08, 15)
    manager.update_trade_history("600519", 0.02, 8)
    manager.update_trade_history("600519", -0.02, 3)

    # 获取统计
    stats = manager.get_statistics()
    print(f"\n交易统计:")
    print(f"  胜率: {stats['win_rate']:.2%}")
    print(f"  盈亏比: {stats['win_loss_ratio']:.2f}")

    # 计算凯利仓位
    kelly = manager.calculate_kelly_position(
        win_rate=stats["win_rate"],
        win_loss_ratio=stats["win_loss_ratio"],
        volatility=0.03,
    )
    print(f"\n凯利建议仓位: {kelly:.1%}")

    # 模拟持仓
    positions = [
        manager.check_position_risk(
            code="600519",
            name="贵州茅台",
            shares=100,
            cost_price=1800.0,
            current_price=1850.0,
            buy_date="2026-04-01",
        ),
        manager.check_position_risk(
            code="300750",
            name="宁德时代",
            shares=200,
            cost_price=200.0,
            current_price=210.0,
            buy_date="2026-04-15",
        ),
    ]

    # 生成报告
    print("\n" + manager.generate_risk_report(positions))


if __name__ == "__main__":
    main()
