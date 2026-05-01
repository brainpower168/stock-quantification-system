# -*- coding: utf-8 -*-
"""
量化交易系统 - 组合优化模块 v2.0
升级：马科维茨优化 + 风险平价优化 + 相关性分析
作者：DuMate AI
日期：2026-05-01
功能：优化仓位配置，降低组合风险
"""

import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import minimize
import os
import json
import warnings

warnings.filterwarnings("ignore")


# ==================== 配置区 ====================
CONFIG = {
    "portfolio_params": {
        "risk_free_rate": 0.03,  # 无风险利率 3%
        "min_weight": 0.02,  # 最小权重 2%
        "max_weight": 0.30,  # 最大权重 30%
        "target_return": 0.15,  # 目标收益率 15%
        "max_volatility": 0.25,  # 最大波动率 25%
    }
}


# ==================== 数据生成器 ====================
class PortfolioDataGenerator:
    """组合数据生成器"""

    @staticmethod
    def generate_returns(n_stocks=10, n_days=252, random_state=42):
        """
        生成模拟收益率数据
        :param n_stocks: 股票数量
        :param n_days: 天数
        :param random_state: 随机种子
        :return: 收益率矩阵, 平均收益率, 标准差, 相关矩阵
        """
        np.random.seed(random_state)

        # 生成正定相关矩阵
        A = np.random.randn(n_stocks, n_stocks) * 0.3
        corr_matrix = np.dot(A, A.T) / n_stocks
        np.fill_diagonal(corr_matrix, 1.0)

        # Cholesky分解
        L = np.linalg.cholesky(corr_matrix)

        # 生成收益率
        returns = np.random.randn(n_days, n_stocks) @ L

        # 添加趋势和波动率
        for i in range(n_stocks):
            trend = np.random.uniform(-0.001, 0.001)
            volatility = np.random.uniform(0.15, 0.40)
            returns[:, i] += trend + volatility * np.random.randn(n_days)

        # 计算统计量
        mean_returns = np.mean(returns, axis=0)
        std_returns = np.std(returns, axis=0)

        return returns, mean_returns, std_returns, corr_matrix


# ==================== 马科维茨优化器 ====================
class MarkowitzOptimizer:
    """马科维茨均值-方差优化器"""

    def __init__(self, params=None):
        self.params = params or CONFIG["portfolio_params"]

    def optimize_max_sharpe(self, mean_returns, cov_matrix):
        """
        最大化夏普比率
        :param mean_returns: 平均收益率
        :param cov_matrix: 协方差矩阵
        :return: 最优权重, 优化结果
        """
        n_assets = len(mean_returns)
        risk_free_rate = self.params["risk_free_rate"] / 252

        def neg_sharpe(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_std = np.sqrt(portfolio_variance)

            if portfolio_std == 0:
                return 0

            sharpe = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe

        # 约束条件
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1}  # 权重和为1
        ]

        # 边界条件
        bounds = [
            (self.params["min_weight"], self.params["max_weight"])
            for _ in range(n_assets)
        ]

        # 初始权重
        x0 = np.ones(n_assets) / n_assets

        # 优化
        result = minimize(
            neg_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000},
        )

        if result.success:
            weights = result.x
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_std = np.sqrt(portfolio_variance)
            sharpe_ratio = (
                (portfolio_return - risk_free_rate) / portfolio_std
                if portfolio_std > 0
                else 0
            )

            return weights, {
                "success": True,
                "portfolio_return": portfolio_return * 252,  # 年化
                "portfolio_std": portfolio_std * np.sqrt(252),  # 年化
                "sharpe_ratio": sharpe_ratio * np.sqrt(252),  # 年化
                "var_95": portfolio_return - 1.645 * portfolio_std,
            }

        return None, {"success": False, "error": result.message}

    def optimize_min_volatility(self, mean_returns, cov_matrix):
        """
        最小化波动率
        :param mean_returns: 平均收益率
        :param cov_matrix: 协方差矩阵
        :return: 最优权重, 优化结果
        """
        n_assets = len(mean_returns)

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # 约束条件
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        # 边界条件
        bounds = [
            (self.params["min_weight"], self.params["max_weight"])
            for _ in range(n_assets)
        ]

        # 初始权重
        x0 = np.ones(n_assets) / n_assets

        # 优化
        result = minimize(
            portfolio_volatility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000},
        )

        if result.success:
            weights = result.x
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = result.fun

            return weights, {
                "success": True,
                "portfolio_return": portfolio_return * 252,
                "portfolio_std": portfolio_std * np.sqrt(252),
                "sharpe_ratio": (portfolio_return - self.params["risk_free_rate"] / 252)
                / portfolio_std
                * np.sqrt(252),
            }

        return None, {"success": False, "error": result.message}

    def optimize_target_return(self, mean_returns, cov_matrix, target_return):
        """
        给定目标收益率，最小化风险
        :param mean_returns: 平均收益率
        :param cov_matrix: 协方差矩阵
        :param target_return: 目标收益率（年化）
        :return: 最优权重, 优化结果
        """
        n_assets = len(mean_returns)
        target_daily = target_return / 252

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # 约束条件
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w: np.dot(w, mean_returns) - target_daily},
        ]

        # 边界条件
        bounds = [
            (self.params["min_weight"], self.params["max_weight"])
            for _ in range(n_assets)
        ]

        # 初始权重
        x0 = np.ones(n_assets) / n_assets

        # 优化
        result = minimize(
            portfolio_volatility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000},
        )

        if result.success:
            weights = result.x
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = result.fun

            return weights, {
                "success": True,
                "portfolio_return": portfolio_return * 252,
                "portfolio_std": portfolio_std * np.sqrt(252),
                "sharpe_ratio": (portfolio_return - self.params["risk_free_rate"] / 252)
                / portfolio_std
                * np.sqrt(252),
            }

        return None, {"success": False, "error": result.message}


# ==================== 风险平价优化器 ====================
class RiskParityOptimizer:
    """风险平价优化器"""

    def __init__(self, params=None):
        self.params = params or CONFIG["portfolio_params"]

    def optimize(self, mean_returns, cov_matrix):
        """
        风险平价优化 - 每个资产风险贡献相等
        :param mean_returns: 平均收益率
        :param cov_matrix: 协方差矩阵
        :return: 最优权重, 优化结果
        """
        n_assets = len(mean_returns)

        # 初始权重
        weights = np.ones(n_assets) / n_assets

        # 迭代优化
        for iteration in range(100):
            # 计算边际风险贡献
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_std = np.sqrt(portfolio_variance)

            # 每个资产的风险贡献
            marginal_risk = np.dot(cov_matrix, weights) / portfolio_std
            risk_contribution = weights * marginal_risk

            # 目标：每个资产风险贡献相等
            target_risk = portfolio_std / n_assets

            # 调整权重
            new_weights = weights * (target_risk / (risk_contribution + 1e-10))
            new_weights = new_weights / np.sum(new_weights)

            # 应用边界条件
            new_weights = np.clip(
                new_weights, self.params["min_weight"], self.params["max_weight"]
            )
            new_weights = new_weights / np.sum(new_weights)

            # 检查收敛
            if np.linalg.norm(new_weights - weights) < 1e-6:
                break

            weights = new_weights

        # 计算结果
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        portfolio_std = np.sqrt(portfolio_variance)

        # 计算风险贡献百分比
        marginal_risk = np.dot(cov_matrix, weights) / portfolio_std
        risk_contribution = weights * marginal_risk
        risk_contribution_pct = risk_contribution / portfolio_std * 100

        return weights, {
            "success": True,
            "portfolio_return": portfolio_return * 252,
            "portfolio_std": portfolio_std * np.sqrt(252),
            "sharpe_ratio": (portfolio_return - self.params["risk_free_rate"] / 252)
            / portfolio_std
            * np.sqrt(252),
            "risk_contributions": risk_contribution_pct.tolist(),
        }


# ==================== 相关性分析器 ====================
class CorrelationAnalyzer:
    """相关性分析器"""

    @staticmethod
    def analyze(corr_matrix, threshold=0.7):
        """
        分析相关矩阵
        :param corr_matrix: 相关矩阵
        :param threshold: 高相关性阈值
        :return: 分析结果
        """
        n_assets = len(corr_matrix)

        # 计算平均相关性
        upper_triangle = corr_matrix[np.triu_indices(n_assets, k=1)]
        avg_correlation = np.mean(np.abs(upper_triangle))

        # 找出高相关资产对
        high_corr_pairs = []
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                corr = abs(corr_matrix[i, j])
                if corr >= threshold:
                    high_corr_pairs.append(
                        {"asset_i": i, "asset_j": j, "correlation": corr}
                    )

        # 评估分散化质量
        if avg_correlation < 0.3:
            diversification = "excellent"
        elif avg_correlation < 0.5:
            diversification = "good"
        elif avg_correlation < 0.7:
            diversification = "moderate"
        else:
            diversification = "poor"

        return {
            "total_pairs": n_assets * (n_assets - 1) // 2,
            "high_correlation_pairs": len(high_corr_pairs),
            "average_correlation": avg_correlation,
            "diversification_quality": diversification,
            "high_corr_pairs": high_corr_pairs[:10],  # 只返回前10对
        }


# ==================== 组合优化器 ====================
class PortfolioOptimizer:
    """组合优化器 - 整合所有优化方法"""

    def __init__(self):
        self.markowitz = MarkowitzOptimizer()
        self.risk_parity = RiskParityOptimizer()
        self.correlation_analyzer = CorrelationAnalyzer()

    def optimize_portfolio(self, returns, stock_names=None):
        """
        执行组合优化
        :param returns: 收益率矩阵 (n_days, n_stocks)
        :param stock_names: 股票名称列表
        :return: 优化结果
        """
        if stock_names is None:
            stock_names = [f"Stock_{i}" for i in range(returns.shape[1])]

        # 计算统计量
        mean_returns = np.mean(returns, axis=0)
        std_returns = np.std(returns, axis=0)
        cov_matrix = np.cov(returns.T)
        corr_matrix = np.corrcoef(returns.T)

        print(f"[Portfolio Optimizer]")
        print(f"   Assets: {len(stock_names)}")
        print(f"   Days: {returns.shape[0]}")
        print()

        # 相关性分析
        print("[1. Correlation Analysis]")
        corr_result = self.correlation_analyzer.analyze(corr_matrix)
        print(f"   Average Correlation: {corr_result['average_correlation']:.3f}")
        print(f"   Diversification: {corr_result['diversification_quality']}")
        print(f"   High Correlation Pairs: {corr_result['high_correlation_pairs']}")
        print()

        # 马科维茨优化 - 最大夏普
        print("[2. Markowitz - Max Sharpe]")
        mv_weights, mv_result = self.markowitz.optimize_max_sharpe(
            mean_returns, cov_matrix
        )

        if mv_result["success"]:
            print(f"   Sharpe Ratio: {mv_result['sharpe_ratio']:.3f}")
            print(f"   Expected Return: {mv_result['portfolio_return'] * 100:.2f}%")
            print(f"   Volatility: {mv_result['portfolio_std'] * 100:.2f}%")
            print(f"   Top 3 Weights:")
            top3_idx = np.argsort(mv_weights)[::-1][:3]
            for idx in top3_idx:
                print(f"      {stock_names[idx]}: {mv_weights[idx] * 100:.1f}%")
        print()

        # 马科维茨优化 - 最小波动
        print("[3. Markowitz - Min Volatility]")
        min_vol_weights, min_vol_result = self.markowitz.optimize_min_volatility(
            mean_returns, cov_matrix
        )

        if min_vol_result["success"]:
            print(f"   Volatility: {min_vol_result['portfolio_std'] * 100:.2f}%")
            print(f"   Sharpe Ratio: {min_vol_result['sharpe_ratio']:.3f}")
        print()

        # 风险平价优化
        print("[4. Risk Parity]")
        rp_weights, rp_result = self.risk_parity.optimize(mean_returns, cov_matrix)

        if rp_result["success"]:
            print(f"   Sharpe Ratio: {rp_result['sharpe_ratio']:.3f}")
            print(f"   Risk Contributions:")
            for i, rc in enumerate(rp_result["risk_contributions"][:5]):
                print(f"      {stock_names[i]}: {rc:.1f}%")
        print()

        return {
            "correlation": corr_result,
            "markowitz_max_sharpe": {
                "weights": mv_weights.tolist() if mv_weights is not None else None,
                "result": mv_result,
            },
            "markowitz_min_vol": {
                "weights": min_vol_weights.tolist()
                if min_vol_weights is not None
                else None,
                "result": min_vol_result,
            },
            "risk_parity": {"weights": rp_weights.tolist(), "result": rp_result},
        }


# ==================== 主程序 ====================
def main():
    """主函数 - 组合优化演示"""
    print("=" * 70)
    print("[Portfolio Optimizer v2.0]")
    print("=" * 70)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 生成测试数据
    print("[Generating test data...]")
    dg = PortfolioDataGenerator()
    returns, mean_returns, std_returns, corr_matrix = dg.generate_returns(
        n_stocks=10, n_days=252
    )

    stock_names = [
        "Moutai",
        "Ping An Bank",
        "CATL",
        "Ping An",
        "Wuliangye",
        "China Tourism",
        "Luxshare",
        "Ganfeng Lithium",
        "Foxconn",
        "East Money",
    ]

    print(f"   Generated {len(stock_names)} stocks, {returns.shape[0]} days")
    print()

    # 执行优化
    optimizer = PortfolioOptimizer()
    results = optimizer.optimize_portfolio(returns, stock_names)

    print("=" * 70)
    print("[OPTIMIZATION RESULTS]")
    print("=" * 70)

    # 显示最优配置
    print("\n[Recommended Allocation - Max Sharpe]")
    if results["markowitz_max_sharpe"]["weights"]:
        weights = results["markowitz_max_sharpe"]["weights"]
        for i, (name, weight) in enumerate(zip(stock_names, weights)):
            if weight > 0.05:  # 只显示权重>5%的
                print(f"   {name}: {weight * 100:.1f}%")

    print("\n[OK] Portfolio optimization completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
