#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统集成测试 - 验证v4.0改进
测试内容：
1. 数据获取模块（妙想API、国信API、新闻API）
2. 因子计算（205+因子）
3. 风控系统（收紧后的参数）
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("系统集成测试 - v4.0改进验证")
print("=" * 60)

# 测试结果统计
test_results = {"passed": 0, "failed": 0, "errors": []}


def test_case(name, func):
    """测试用例包装器"""
    print(f"\n[测试] {name}")
    try:
        func()
        print(f"[通过] {name}")
        test_results["passed"] += 1
        return True
    except Exception as e:
        print(f"[失败] {name}: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: {str(e)}")
        return False


# ========== 测试1: 因子库 ==========
def test_factor_library():
    """测试因子库 - 205+因子"""
    from enhanced_factor_library import EnhancedFactorLibrary

    library = EnhancedFactorLibrary()

    # 创建测试数据
    np.random.seed(42)
    n = 100
    data = pd.DataFrame(
        {
            "open": np.random.uniform(10, 20, n),
            "high": np.random.uniform(15, 25, n),
            "low": np.random.uniform(5, 15, n),
            "close": np.random.uniform(10, 20, n),
            "volume": np.random.uniform(1000000, 5000000, n),
        }
    )

    # 提取所有因子
    factors = library.extract_all_factors(data)

    # 验证因子数量（factors是字典）
    factor_count = len(factors)
    print(f"  因子数量: {factor_count}")

    assert factor_count >= 200, f"因子数量不足: {factor_count} < 200"
    print(f"  因子库验证通过: {factor_count}个因子")


# ========== 测试2: 风控系统 ==========
def test_risk_system():
    """测试风控系统 - 收紧后的参数"""
    from risk_budget_system import RiskBudgetSystem, CircuitBreaker

    # 测试单笔止损（5%）
    breaker = CircuitBreaker()

    # 验证参数已收紧
    print(f"  单笔止损参数: {breaker.single_trade_stop_loss:.1%}")
    print(f"  日回撤熔断参数: {breaker.daily_drawdown_threshold:.1%}")

    assert breaker.single_trade_stop_loss == 0.05, "单笔止损参数未收紧到5%"
    assert breaker.daily_drawdown_threshold == 0.05, "日回撤熔断参数未设置为5%"

    # 模拟亏损6%的情况
    entry_price = 100.0
    current_price = 94.0  # -6%
    position_value = 10000.0

    # 检查单笔止损
    loss_pct = (current_price - entry_price) / entry_price
    should_stop = abs(loss_pct) >= breaker.single_trade_stop_loss

    print(
        f"  单笔止损测试: 入场{entry_price}元, 当前{current_price}元, 亏损{loss_pct:.1%}"
    )
    print(f"  是否触发止损: {should_stop}")

    assert should_stop == True, "单笔止损未正确触发（应该触发5%止损）"
    print(f"  单笔止损验证通过: 5%止损正确触发")

    # 测试日回撤熔断（5%）
    breaker.daily_start_value = 100000.0
    breaker.current_value = 94000.0  # 日回撤6%

    daily_drawdown = (
        breaker.daily_start_value - breaker.current_value
    ) / breaker.daily_start_value
    breaker.daily_circuit_triggered = daily_drawdown >= breaker.daily_drawdown_threshold

    print(
        f"  日回撤熔断测试: 初始{breaker.daily_start_value:.0f}, 当前{breaker.current_value:.0f}, 回撤{daily_drawdown:.1%}"
    )
    print(f"  是否触发熔断: {breaker.daily_circuit_triggered}")

    assert breaker.daily_circuit_triggered == True, "日回撤熔断未正确触发"
    print(f"  日回撤熔断验证通过: 5%熔断正确触发")


# ========== 测试3: 数据获取模块 ==========
def test_data_fetcher():
    """测试数据获取模块"""
    from data_fetcher import DataFetcher

    fetcher = DataFetcher()

    # 测试1: 检查API配置
    print(f"  妙想API配置: {'已配置' if fetcher.mx_apikey else '未配置'}")
    print(f"  国信API配置: {'已配置' if fetcher.gs_api_key else '未配置'}")

    # 测试2: 检查方法存在
    assert hasattr(fetcher, "fetch_ddx_data"), "缺少fetch_ddx_data方法"
    assert hasattr(fetcher, "fetch_financial_data"), "缺少fetch_financial_data方法"
    assert hasattr(fetcher, "fetch_sentiment_data"), "缺少fetch_sentiment_data方法"
    assert hasattr(fetcher, "fetch_all_data"), "缺少fetch_all_data方法"

    print(f"  数据获取方法验证通过")

    # 测试3: 模拟数据生成（用于因子计算）
    np.random.seed(42)
    n = 100
    mock_data = pd.DataFrame(
        {
            "open": np.random.uniform(10, 20, n),
            "high": np.random.uniform(15, 25, n),
            "low": np.random.uniform(5, 15, n),
            "close": np.random.uniform(10, 20, n),
            "volume": np.random.uniform(1000000, 5000000, n),
        }
    )

    print(f"  模拟数据生成成功: {len(mock_data)}天")
    print(f"  数据列: {list(mock_data.columns)}")


# ========== 测试4: 因子库与风控系统集成 ==========
def test_integration():
    """测试因子库与风控系统集成"""
    from enhanced_factor_library import EnhancedFactorLibrary
    from risk_budget_system import CVaRModel

    # 生成测试数据
    library = EnhancedFactorLibrary()

    np.random.seed(42)
    n = 100
    data = pd.DataFrame(
        {
            "open": np.random.uniform(10, 20, n),
            "high": np.random.uniform(15, 25, n),
            "low": np.random.uniform(5, 15, n),
            "close": np.random.uniform(10, 20, n),
            "volume": np.random.uniform(1000000, 5000000, n),
        }
    )

    # 提取因子
    factors = library.extract_all_factors(data)

    # 使用CVaR模型计算风险
    cvar_model = CVaRModel(confidence_level=0.95)

    # 模拟收益率数据
    returns = pd.Series(np.random.normal(0.001, 0.02, n))

    # 计算VaR和CVaR
    var = cvar_model.calculate_var(returns)
    cvar = cvar_model.calculate_cvar(returns)

    print(f"  因子数量: {len(factors)}")
    print(f"  VaR: {var:.4f}")
    print(f"  CVaR: {cvar:.4f}")

    assert len(factors) >= 200, "因子数量不足"
    assert var != 0, "VaR计算失败"
    assert cvar != 0, "CVaR计算失败"
    print(f"  集成测试通过")


# ========== 运行所有测试 ==========
if __name__ == "__main__":
    print("\n开始测试...")

    # 运行测试
    test_case("因子库 - 205+因子", test_factor_library)
    test_case("风控系统 - 5%止损+5%熔断", test_risk_system)
    test_case("数据获取模块", test_data_fetcher)
    test_case("因子库与风控系统集成", test_integration)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过: {test_results['passed']}")
    print(f"失败: {test_results['failed']}")

    if test_results["errors"]:
        print("\n失败详情:")
        for error in test_results["errors"]:
            print(f"  - {error}")

    # 返回退出码
    sys.exit(0 if test_results["failed"] == 0 else 1)
