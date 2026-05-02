# -*- coding: utf-8 -*-
"""
风险预算模块 - 幻方量化三层策略池顶层
- CVaR风险模型
- 熔断机制
- 风险预算分配
- 回撤控制
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class CVaRModel:
    """CVaR（条件风险价值）模型"""

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level

    def calculate_var(self, returns: pd.Series) -> float:
        """计算VaR"""
        var = np.percentile(returns.dropna(), (1 - self.confidence_level) * 100)
        return var

    def calculate_cvar(self, returns: pd.Series) -> float:
        """计算CVaR（期望短缺）"""
        var = self.calculate_var(returns)
        cvar = returns[returns <= var].mean()
        return cvar

    def calculate_portfolio_cvar(
        self, weights: np.ndarray, returns_matrix: pd.DataFrame
    ) -> float:
        """计算组合CVaR"""
        portfolio_returns = (returns_matrix * weights).sum(axis=1)
        return self.calculate_cvar(portfolio_returns)

    def optimize_weights_by_cvar(
        self, returns_matrix: pd.DataFrame, max_cvar: float = -0.02
    ) -> np.ndarray:
        """
        基于CVaR优化权重

        返回:
            最优权重数组
        """
        n_assets = returns_matrix.shape[1]

        # 简化版：等权重 + CVaR调整
        equal_weights = np.ones(n_assets) / n_assets

        # 计算各资产CVaR
        asset_cvars = []
        for col in returns_matrix.columns:
            cvar = self.calculate_cvar(returns_matrix[col])
            asset_cvars.append(abs(cvar))

        asset_cvars = np.array(asset_cvars)

        # 根据CVaR调整权重（风险低的权重大）
        if asset_cvars.sum() > 0:
            risk_adjusted_weights = (1 / asset_cvars) / (1 / asset_cvars).sum()
            # 平滑调整
            final_weights = 0.5 * equal_weights + 0.5 * risk_adjusted_weights
        else:
            final_weights = equal_weights

        return final_weights


class CircuitBreaker:
    """熔断机制 - 幻方量化风控体系"""

    def __init__(self):
        # 熔断参数（参考幻方量化）
        self.max_drawdown = 0.05  # 单策略最大回撤5%（原2%）
        self.consecutive_loss_days = 3  # 连续亏损天数
        self.daily_loss_threshold = -0.03  # 单日亏损阈值3%
        self.total_loss_threshold = -0.05  # 总亏损阈值5%
        self.daily_drawdown_threshold = 0.05  # 日回撤5%熔断（新增）

        # 单笔止损参数（新增）
        self.single_trade_stop_loss = 0.05  # 单笔止损5%（原20%）
        self.single_trade_max_position = 0.20  # 单股最大仓位20%

        # 状态
        self.loss_days = 0
        self.triggered = False
        self.trigger_reason = ""
        self.trigger_time = None
        self.cooldown_days = 0
        self.cooldown_period = 5  # 冷却期5天

        # 日回撤跟踪（新增）
        self.daily_start_value = 0  # 日初账户价值
        self.current_value = 0  # 当前账户价值
        self.daily_drawdown = 0  # 当日回撤

    def check(self, daily_pnl: float, current_drawdown: float) -> Dict:
        """
        检查是否触发熔断

        返回:
            {
                'can_trade': 是否可以交易,
                'triggered': 是否触发熔断,
                'reason': 原因,
                'action': 行动建议
            }
        """
        # 如果在冷却期
        if self.cooldown_days > 0:
            self.cooldown_days -= 1
            return {
                "can_trade": False,
                "triggered": True,
                "reason": f"熔断冷却期，剩余{self.cooldown_days}天",
                "action": "暂停交易，观察市场",
            }

        # 1. 日回撤熔断（新增）
        if self.daily_drawdown >= self.daily_drawdown_threshold:
            self.triggered = True
            self.trigger_reason = f"日回撤熔断：{self.daily_drawdown * 100:.2f}% >= 5%"
            self.trigger_time = datetime.now()
            self.cooldown_days = self.cooldown_period

            return {
                "can_trade": False,
                "triggered": True,
                "reason": self.trigger_reason,
                "action": "立即停止交易，当日不再开新仓",
            }

        # 2. 总回撤熔断
        if current_drawdown < -self.max_drawdown:
            self.triggered = True
            self.trigger_reason = f"总回撤熔断：{current_drawdown * 100:.2f}% < -5%"
            self.trigger_time = datetime.now()
            self.cooldown_days = self.cooldown_period

            return {
                "can_trade": False,
                "triggered": True,
                "reason": self.trigger_reason,
                "action": "立即停止交易，重新评估策略",
            }

        # 3. 连续亏损熔断
        if daily_pnl < self.daily_loss_threshold:
            self.loss_days += 1
            if self.loss_days >= self.consecutive_loss_days:
                self.triggered = True
                self.trigger_reason = f"连续亏损熔断：{self.loss_days}天亏损>{abs(self.daily_loss_threshold) * 100}%"
                self.trigger_time = datetime.now()
                self.cooldown_days = self.cooldown_period

                return {
                    "can_trade": False,
                    "triggered": True,
                    "reason": self.trigger_reason,
                    "action": "暂停交易，检查策略有效性",
                }
        else:
            self.loss_days = 0  # 重置

        # 4. 单日大幅亏损熔断
        if daily_pnl < self.total_loss_threshold:
            self.triggered = True
            self.trigger_reason = f"单日亏损熔断：{daily_pnl * 100:.2f}% < -5%"
            self.trigger_time = datetime.now()
            self.cooldown_days = self.cooldown_period

            return {
                "can_trade": False,
                "triggered": True,
                "reason": self.trigger_reason,
                "action": "立即止损，暂停交易",
            }

        return {
            "can_trade": True,
            "triggered": False,
            "reason": "正常交易",
            "action": "继续执行策略",
        }

    def check_single_trade(
        self, entry_price: float, current_price: float, position_value: float
    ) -> Dict:
        """
        检查单笔交易是否触发止损（新增）

        参数:
            entry_price: 买入价
            current_price: 当前价
            position_value: 持仓市值

        返回:
            {
                'should_stop': 是否止损,
                'loss_pct': 亏损百分比,
                'action': 行动建议
            }
        """
        if entry_price <= 0:
            return {"should_stop": False, "loss_pct": 0, "action": "持仓正常"}

        # 计算亏损百分比
        loss_pct = (current_price - entry_price) / entry_price

        # 检查是否触发止损
        if loss_pct <= -self.single_trade_stop_loss:
            return {
                "should_stop": True,
                "loss_pct": loss_pct,
                "action": f"触发止损：亏损{abs(loss_pct) * 100:.2f}% >= 5%，立即卖出",
            }

        return {
            "should_stop": False,
            "loss_pct": loss_pct,
            "action": f"持仓正常，当前{'盈利' if loss_pct > 0 else '亏损'}{abs(loss_pct) * 100:.2f}%",
        }

    def update_daily_drawdown(self, start_value: float, current_value: float):
        """
        更新日回撤（新增）

        参数:
            start_value: 日初账户价值
            current_value: 当前账户价值
        """
        self.daily_start_value = start_value
        self.current_value = current_value

        if start_value > 0:
            self.daily_drawdown = (start_value - current_value) / start_value
        else:
            self.daily_drawdown = 0

    def reset_daily(self):
        """重置日回撤（每日开盘调用）"""
        self.daily_drawdown = 0

    def reset(self):
        """重置熔断状态"""
        self.triggered = False
        self.trigger_reason = ""
        self.loss_days = 0
        self.cooldown_days = 0

    def get_status(self) -> Dict:
        """获取熔断状态"""
        return {
            "triggered": self.triggered,
            "trigger_reason": self.trigger_reason,
            "trigger_time": self.trigger_time,
            "loss_days": self.loss_days,
            "cooldown_days": self.cooldown_days,
        }


class RiskBudgetAllocator:
    """风险预算分配器"""

    def __init__(self, total_capital: float = 1000000):
        self.total_capital = total_capital
        self.max_single_position = 0.20  # 单股最大仓位20%
        self.max_sector_exposure = 0.40  # 单行业最大暴露40%
        self.max_total_exposure = 0.80  # 总暴露80%

    def allocate(self, strategies: List[Dict], risk_budget: float = 0.02) -> Dict:
        """
        分配风险预算

        参数:
            strategies: 策略列表
            risk_budget: 总风险预算（默认2%）

        返回:
            {
                'strategy_allocations': 策略分配,
                'position_limits': 仓位限制,
                'risk_budget_used': 已用风险预算
            }
        """
        n_strategies = len(strategies)

        # 等风险分配
        strategy_risk_budget = risk_budget / n_strategies

        allocations = {}
        total_risk = 0

        for strategy in strategies:
            name = strategy["name"]
            expected_return = strategy.get("expected_return", 0.05)
            volatility = strategy.get("volatility", 0.20)

            # 根据风险预算计算仓位
            # 仓位 = 风险预算 / 波动率
            position_size = min(
                strategy_risk_budget / volatility, self.max_single_position
            )

            # 计算预期风险
            strategy_risk = position_size * volatility

            allocations[name] = {
                "position_size": position_size,
                "capital": position_size * self.total_capital,
                "risk_budget": strategy_risk,
                "expected_return": position_size * expected_return,
            }

            total_risk += strategy_risk

        return {
            "strategy_allocations": allocations,
            "position_limits": {
                "max_single": self.max_single_position,
                "max_sector": self.max_sector_exposure,
                "max_total": self.max_total_exposure,
            },
            "risk_budget_used": total_risk,
            "risk_budget_remaining": risk_budget - total_risk,
        }


class DrawdownController:
    """回撤控制器"""

    def __init__(self, max_drawdown: float = 0.02):
        self.max_drawdown = max_drawdown
        self.peak_value = None
        self.current_drawdown = 0
        self.drawdown_history = []

    def update(self, current_value: float) -> Dict:
        """
        更新回撤状态

        返回:
            {
                'drawdown': 当前回撤,
                'peak': 峰值,
                'is_warning': 是否警告,
                'action': 行动建议
            }
        """
        # 更新峰值
        if self.peak_value is None or current_value > self.peak_value:
            self.peak_value = current_value

        # 计算回撤
        self.current_drawdown = (current_value - self.peak_value) / self.peak_value

        # 记录历史
        self.drawdown_history.append(
            {
                "time": datetime.now(),
                "value": current_value,
                "drawdown": self.current_drawdown,
            }
        )

        # 判断是否警告
        is_warning = self.current_drawdown < -self.max_drawdown * 0.8

        # 行动建议
        if self.current_drawdown < -self.max_drawdown:
            action = "触发回撤限制，立即减仓"
        elif self.current_drawdown < -self.max_drawdown * 0.8:
            action = "接近回撤限制，准备减仓"
        else:
            action = "正常交易"

        return {
            "drawdown": self.current_drawdown,
            "peak": self.peak_value,
            "is_warning": is_warning,
            "action": action,
        }

    def get_statistics(self) -> Dict:
        """获取回撤统计"""
        if len(self.drawdown_history) == 0:
            return {}

        drawdowns = [d["drawdown"] for d in self.drawdown_history]

        return {
            "max_drawdown": min(drawdowns),
            "avg_drawdown": np.mean(drawdowns),
            "current_drawdown": self.current_drawdown,
            "recovery_count": sum(1 for d in drawdowns if d > -0.01),
        }


class RiskBudgetSystem:
    """风险预算系统 - 整合所有风控模块"""

    def __init__(self, total_capital: float = 1000000):
        self.cvar_model = CVaRModel()
        self.circuit_breaker = CircuitBreaker()
        self.budget_allocator = RiskBudgetAllocator(total_capital)
        self.drawdown_controller = DrawdownController()

        self.total_capital = total_capital
        self.current_value = total_capital

    def check_before_trade(self, daily_pnl: float = 0) -> Dict:
        """交易前检查"""
        # 更新净值
        self.current_value += daily_pnl * self.total_capital

        # 1. 回撤检查
        drawdown_status = self.drawdown_controller.update(self.current_value)

        # 2. 熔断检查
        circuit_status = self.circuit_breaker.check(
            daily_pnl, drawdown_status["drawdown"]
        )

        return {
            "can_trade": circuit_status["can_trade"],
            "drawdown": drawdown_status,
            "circuit_breaker": circuit_status,
            "current_value": self.current_value,
        }

    def allocate_risk(self, strategies: List[Dict]) -> Dict:
        """分配风险预算"""
        return self.budget_allocator.allocate(strategies)

    def calculate_portfolio_risk(
        self, positions: Dict, returns_matrix: pd.DataFrame
    ) -> Dict:
        """计算组合风险"""
        weights = np.array([p["weight"] for p in positions.values()])

        portfolio_cvar = self.cvar_model.calculate_portfolio_cvar(
            weights, returns_matrix
        )

        return {
            "portfolio_cvar": portfolio_cvar,
            "risk_level": "high"
            if portfolio_cvar < -0.03
            else "medium"
            if portfolio_cvar < -0.02
            else "low",
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("风险预算模块测试 - 幻方量化三层策略池顶层")
    print("=" * 80)

    # 测试CVaR模型
    print("\n1. CVaR模型测试")
    print("-" * 80)

    np.random.seed(42)
    returns = pd.Series(np.random.randn(100) * 0.02)

    cvar_model = CVaRModel()
    var = cvar_model.calculate_var(returns)
    cvar = cvar_model.calculate_cvar(returns)

    print(f"VaR(95%): {var * 100:.2f}%")
    print(f"CVaR(95%): {cvar * 100:.2f}%")

    # 测试熔断机制
    print("\n2. 熔断机制测试")
    print("-" * 80)

    circuit_breaker = CircuitBreaker()

    # 模拟连续亏损
    test_cases = [
        (-0.02, -0.01),  # 正常
        (-0.04, -0.015),  # 接近熔断
        (-0.04, -0.025),  # 触发回撤熔断
    ]

    for daily_pnl, drawdown in test_cases:
        result = circuit_breaker.check(daily_pnl, drawdown)
        print(f"日盈亏: {daily_pnl * 100:.1f}%, 回撤: {drawdown * 100:.1f}%")
        print(f"  可交易: {result['can_trade']}, 原因: {result['reason']}")

    # 测试风险预算分配
    print("\n3. 风险预算分配测试")
    print("-" * 80)

    allocator = RiskBudgetAllocator(total_capital=1000000)

    strategies = [
        {"name": "趋势策略", "expected_return": 0.08, "volatility": 0.25},
        {"name": "震荡策略", "expected_return": 0.05, "volatility": 0.15},
        {"name": "动量策略", "expected_return": 0.06, "volatility": 0.20},
    ]

    allocation = allocator.allocate(strategies, risk_budget=0.02)

    print(f"总风险预算: 2%")
    print(f"已用风险预算: {allocation['risk_budget_used'] * 100:.2f}%")
    print("\n策略分配:")
    for name, alloc in allocation["strategy_allocations"].items():
        print(f"  {name}:")
        print(f"    仓位: {alloc['position_size'] * 100:.1f}%")
        print(f"    资金: {alloc['capital']:.0f}元")
        print(f"    风险预算: {alloc['risk_budget'] * 100:.2f}%")

    # 测试回撤控制
    print("\n4. 回撤控制测试")
    print("-" * 80)

    controller = DrawdownController(max_drawdown=0.02)

    # 模拟净值变化
    values = [1000000, 990000, 980000, 970000, 975000, 980000]

    for value in values:
        status = controller.update(value)
        print(
            f"净值: {value:.0f}, 回撤: {status['drawdown'] * 100:.2f}%, 建议: {status['action']}"
        )

    # 测试完整系统
    print("\n5. 完整风险预算系统测试")
    print("-" * 80)

    system = RiskBudgetSystem(total_capital=1000000)

    # 检查交易
    check_result = system.check_before_trade(daily_pnl=-0.02)
    print(f"可交易: {check_result['can_trade']}")
    print(f"当前回撤: {check_result['drawdown']['drawdown'] * 100:.2f}%")
    print(f"熔断状态: {check_result['circuit_breaker']['reason']}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
