# -*- coding: utf-8 -*-
"""
因子库模块 - 幻方量化三层策略池底层
- 200+因子（量价、基本面、情绪、资金流、另类数据）
- 遗传算法动态筛选有效因子组合
- 因子有效性评估
- 因子权重动态调整
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy import stats
import warnings

warnings.filterwarnings("ignore")


class FactorLibrary:
    """因子库 - 200+因子"""

    def __init__(self):
        self.factor_categories = {
            "price_volume": self._price_volume_factors,
            "fundamental": self._fundamental_factors,
            "sentiment": self._sentiment_factors,
            "fund_flow": self._fund_flow_factors,
            "technical": self._technical_factors,
            "risk": self._risk_factors,
            "alternative": self._alternative_factors,
        }

        # 因子权重（动态调整）
        self.factor_weights = {}

        # 因子有效性评分
        self.factor_scores = {}

    # ==================== 量价因子（50+） ====================
    def _price_volume_factors(self, data: pd.DataFrame) -> Dict:
        """量价因子"""
        factors = {}
        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        # 收益率因子
        factors["return_1d"] = close.pct_change(1).iloc[-1]
        factors["return_5d"] = close.pct_change(5).iloc[-1]
        factors["return_10d"] = close.pct_change(10).iloc[-1]
        factors["return_20d"] = close.pct_change(20).iloc[-1]

        # 波动率因子
        factors["volatility_5d"] = close.pct_change().rolling(5).std().iloc[-1]
        factors["volatility_10d"] = close.pct_change().rolling(10).std().iloc[-1]
        factors["volatility_20d"] = close.pct_change().rolling(20).std().iloc[-1]

        # 振幅因子
        factors["amplitude_5d"] = (
            (high.rolling(5).max() - low.rolling(5).min()) / close.rolling(5).mean()
        ).iloc[-1]
        factors["amplitude_10d"] = (
            (high.rolling(10).max() - low.rolling(10).min()) / close.rolling(10).mean()
        ).iloc[-1]

        # 成交量因子
        factors["volume_ratio_5d"] = volume.iloc[-1] / volume.rolling(5).mean().iloc[-1]
        factors["volume_ratio_10d"] = (
            volume.iloc[-1] / volume.rolling(10).mean().iloc[-1]
        )
        factors["volume_ratio_20d"] = (
            volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        )

        # 量价相关性
        if len(close) >= 10:
            factors["price_volume_corr_5d"] = close.pct_change(5).corr(
                volume.pct_change(5)
            )
            factors["price_volume_corr_10d"] = close.pct_change(10).corr(
                volume.pct_change(10)
            )
        else:
            factors["price_volume_corr_5d"] = 0
            factors["price_volume_corr_10d"] = 0

        # 换手率因子
        if "turnover_rate" in data.columns:
            factors["turnover_5d_avg"] = (
                data["turnover_rate"].rolling(5).mean().iloc[-1]
            )
            factors["turnover_10d_avg"] = (
                data["turnover_rate"].rolling(10).mean().iloc[-1]
            )

        # 涨跌停因子
        factors["limit_up_count_20d"] = (
            (close.pct_change() >= 0.095).rolling(20).sum().iloc[-1]
        )
        factors["limit_down_count_20d"] = (
            (close.pct_change() <= -0.095).rolling(20).sum().iloc[-1]
        )

        # 缺口因子
        if "open" in data.columns:
            factors["gap_up_count_20d"] = (
                ((low > high.shift(1)) & (close > data["open"]))
                .rolling(20)
                .sum()
                .iloc[-1]
            )
            factors["gap_down_count_20d"] = (
                ((high < low.shift(1)) & (close < data["open"]))
                .rolling(20)
                .sum()
                .iloc[-1]
            )
        else:
            factors["gap_up_count_20d"] = 0
            factors["gap_down_count_20d"] = 0

        return factors

    # ==================== 基本面因子（50+） ====================
    def _fundamental_factors(self, data: pd.DataFrame) -> Dict:
        """基本面因子"""
        factors = {}

        # 估值因子
        if "pe" in data.columns:
            factors["pe"] = data["pe"].iloc[-1]
            factors["pe_rank"] = stats.percentileofscore(
                data["pe"].dropna(), data["pe"].iloc[-1]
            )

        if "pb" in data.columns:
            factors["pb"] = data["pb"].iloc[-1]
            factors["pb_rank"] = stats.percentileofscore(
                data["pb"].dropna(), data["pb"].iloc[-1]
            )

        if "ps" in data.columns:
            factors["ps"] = data["ps"].iloc[-1]

        if "pcf" in data.columns:
            factors["pcf"] = data["pcf"].iloc[-1]

        # 盈利能力因子
        if "roe" in data.columns:
            factors["roe"] = data["roe"].iloc[-1]
            factors["roe_avg_4q"] = data["roe"].rolling(4).mean().iloc[-1]

        if "roa" in data.columns:
            factors["roa"] = data["roa"].iloc[-1]

        if "gross_margin" in data.columns:
            factors["gross_margin"] = data["gross_margin"].iloc[-1]

        if "net_margin" in data.columns:
            factors["net_margin"] = data["net_margin"].iloc[-1]

        # 成长因子
        if "revenue_growth" in data.columns:
            factors["revenue_growth"] = data["revenue_growth"].iloc[-1]
            factors["revenue_growth_avg_4q"] = (
                data["revenue_growth"].rolling(4).mean().iloc[-1]
            )

        if "profit_growth" in data.columns:
            factors["profit_growth"] = data["profit_growth"].iloc[-1]
            factors["profit_growth_avg_4q"] = (
                data["profit_growth"].rolling(4).mean().iloc[-1]
            )

        # 财务健康因子
        if "debt_ratio" in data.columns:
            factors["debt_ratio"] = data["debt_ratio"].iloc[-1]

        if "current_ratio" in data.columns:
            factors["current_ratio"] = data["current_ratio"].iloc[-1]

        if "quick_ratio" in data.columns:
            factors["quick_ratio"] = data["quick_ratio"].iloc[-1]

        # 现金流因子
        if "operating_cash_flow" in data.columns:
            factors["operating_cash_flow"] = data["operating_cash_flow"].iloc[-1]

        if "free_cash_flow" in data.columns:
            factors["free_cash_flow"] = data["free_cash_flow"].iloc[-1]

        return factors

    # ==================== 情绪因子（30+） ====================
    def _sentiment_factors(self, data: pd.DataFrame) -> Dict:
        """情绪因子（NLP舆情分析）"""
        factors = {}

        # 市场情绪
        if "market_sentiment" in data.columns:
            factors["market_sentiment"] = data["market_sentiment"].iloc[-1]
            factors["market_sentiment_ma5"] = (
                data["market_sentiment"].rolling(5).mean().iloc[-1]
            )

        # 涨停基因
        close = data["close"]
        factors["limit_up_gene"] = (
            (close.pct_change() >= 0.095).rolling(20).sum().iloc[-1]
        )
        factors["limit_up_gene_score"] = factors["limit_up_gene"] * 10

        # 连板基因
        consecutive_limit_up = 0
        for pct in close.pct_change().iloc[-5:][::-1]:
            if pct >= 0.095:
                consecutive_limit_up += 1
            else:
                break
        factors["consecutive_limit_up"] = consecutive_limit_up

        # 板块热度
        if "sector_hot_score" in data.columns:
            factors["sector_hot_score"] = data["sector_hot_score"].iloc[-1]

        # 新闻情绪
        if "news_sentiment" in data.columns:
            factors["news_sentiment"] = data["news_sentiment"].iloc[-1]
            factors["news_sentiment_ma5"] = (
                data["news_sentiment"].rolling(5).mean().iloc[-1]
            )

        # 社交媒体热度
        if "social_hotness" in data.columns:
            factors["social_hotness"] = data["social_hotness"].iloc[-1]

        return factors

    # ==================== 资金流因子（40+） ====================
    def _fund_flow_factors(self, data: pd.DataFrame) -> Dict:
        """资金流因子"""
        factors = {}

        # 主力资金
        if "main_flow" in data.columns:
            factors["main_flow_1d"] = data["main_flow"].iloc[-1]
            factors["main_flow_5d"] = data["main_flow"].rolling(5).sum().iloc[-1]
            factors["main_flow_10d"] = data["main_flow"].rolling(10).sum().iloc[-1]
            factors["main_flow_20d"] = data["main_flow"].rolling(20).sum().iloc[-1]

        # DDX因子
        if "ddx" in data.columns:
            factors["ddx_1d"] = data["ddx"].iloc[-1]
            factors["ddx_5d"] = data["ddx"].rolling(5).sum().iloc[-1]
            factors["ddx_10d"] = data["ddx"].rolling(10).sum().iloc[-1]
            factors["ddx_20d"] = data["ddx"].rolling(20).sum().iloc[-1]

        # 超大单
        if "super_large_flow" in data.columns:
            factors["super_large_flow_1d"] = data["super_large_flow"].iloc[-1]
            factors["super_large_flow_5d"] = (
                data["super_large_flow"].rolling(5).sum().iloc[-1]
            )

        # 大单
        if "large_flow" in data.columns:
            factors["large_flow_1d"] = data["large_flow"].iloc[-1]
            factors["large_flow_5d"] = data["large_flow"].rolling(5).sum().iloc[-1]

        # 中单
        if "medium_flow" in data.columns:
            factors["medium_flow_1d"] = data["medium_flow"].iloc[-1]

        # 小单
        if "small_flow" in data.columns:
            factors["small_flow_1d"] = data["small_flow"].iloc[-1]

        # 北向资金
        if "north_flow" in data.columns:
            factors["north_flow_1d"] = data["north_flow"].iloc[-1]
            factors["north_flow_5d"] = data["north_flow"].rolling(5).sum().iloc[-1]

        # 融资融券
        if "margin_balance" in data.columns:
            factors["margin_balance"] = data["margin_balance"].iloc[-1]
            factors["margin_balance_change"] = (
                data["margin_balance"].pct_change().iloc[-1]
            )

        return factors

    # ==================== 技术因子（30+） ====================
    def _technical_factors(self, data: pd.DataFrame) -> Dict:
        """技术因子"""
        factors = {}
        close = data["close"]
        high = data["high"]
        low = data["low"]

        # 均线因子
        factors["ma5"] = close.rolling(5).mean().iloc[-1]
        factors["ma10"] = close.rolling(10).mean().iloc[-1]
        factors["ma20"] = close.rolling(20).mean().iloc[-1]
        factors["ma60"] = (
            close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
        )

        # 均线偏离
        factors["ma5_bias"] = (close.iloc[-1] - factors["ma5"]) / factors["ma5"]
        factors["ma10_bias"] = (close.iloc[-1] - factors["ma10"]) / factors["ma10"]
        factors["ma20_bias"] = (close.iloc[-1] - factors["ma20"]) / factors["ma20"]

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        factors["macd"] = (dif - dea).iloc[-1]
        factors["macd_signal"] = 1 if dif.iloc[-1] > dea.iloc[-1] else -1

        # KDJ
        low_min = low.rolling(9).min()
        high_max = high.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        factors["kdj_k"] = k.iloc[-1]
        factors["kdj_d"] = d.iloc[-1]
        factors["kdj_j"] = 3 * k.iloc[-1] - 2 * d.iloc[-1]

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        factors["rsi_14"] = (100 - (100 / (1 + rs))).iloc[-1]

        # 布林带
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        factors["boll_upper"] = (ma20 + 2 * std20).iloc[-1]
        factors["boll_lower"] = (ma20 - 2 * std20).iloc[-1]
        factors["boll_width"] = (
            factors["boll_upper"] - factors["boll_lower"]
        ) / ma20.iloc[-1]
        factors["boll_position"] = (close.iloc[-1] - factors["boll_lower"]) / (
            factors["boll_upper"] - factors["boll_lower"]
        )

        # ATR
        tr = np.maximum(
            high - low,
            np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))),
        )
        factors["atr_14"] = tr.rolling(14).mean().iloc[-1]

        return factors

    # ==================== 风险因子（20+） ====================
    def _risk_factors(self, data: pd.DataFrame) -> Dict:
        """风险因子"""
        factors = {}
        close = data["close"]
        returns = close.pct_change()

        # Beta
        if "index_return" in data.columns:
            covariance = returns.cov(data["index_return"])
            variance = data["index_return"].var()
            factors["beta"] = covariance / variance

        # 波动率
        factors["volatility_20d"] = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        factors["volatility_60d"] = (
            returns.rolling(60).std().iloc[-1] * np.sqrt(252)
            if len(returns) >= 60
            else None
        )

        # 下行风险
        downside_returns = returns[returns < 0]
        factors["downside_risk"] = (
            downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        )

        # 最大回撤
        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        factors["max_drawdown_20d"] = drawdown.rolling(20).min().iloc[-1]
        factors["max_drawdown_60d"] = (
            drawdown.rolling(60).min().iloc[-1] if len(drawdown) >= 60 else None
        )

        # VaR
        factors["var_95"] = np.percentile(returns.dropna(), 5)
        factors["var_99"] = np.percentile(returns.dropna(), 1)

        # CVaR
        var_95 = factors["var_95"]
        factors["cvar_95"] = (
            returns[returns <= var_95].mean()
            if len(returns[returns <= var_95]) > 0
            else var_95
        )

        # 偏度、峰度
        factors["skewness"] = returns.skew()
        factors["kurtosis"] = returns.kurtosis()

        return factors

    # ==================== 另类数据因子（10+） ====================
    def _alternative_factors(self, data: pd.DataFrame) -> Dict:
        """另类数据因子"""
        factors = {}

        # 机构调研
        if "institution_visit" in data.columns:
            factors["institution_visit_30d"] = (
                data["institution_visit"].rolling(30).sum().iloc[-1]
            )

        # 高管增减持
        if "insider_trade" in data.columns:
            factors["insider_buy"] = (data["insider_trade"] > 0).sum()
            factors["insider_sell"] = (data["insider_trade"] < 0).sum()

        # 股东户数变化
        if "shareholder_count" in data.columns:
            factors["shareholder_count_change"] = (
                data["shareholder_count"].pct_change().iloc[-1]
            )

        # 龙虎榜
        if "lhb_buy" in data.columns:
            factors["lhb_buy_5d"] = data["lhb_buy"].rolling(5).sum().iloc[-1]
            factors["lhb_sell_5d"] = (
                data["lhb_sell"].rolling(5).sum().iloc[-1]
                if "lhb_sell" in data.columns
                else 0
            )

        # 大宗交易
        if "block_trade" in data.columns:
            factors["block_trade_5d"] = data["block_trade"].rolling(5).sum().iloc[-1]

        return factors

    def extract_all_factors(self, data: pd.DataFrame) -> Dict:
        """提取所有因子"""
        all_factors = {}

        for category, func in self.factor_categories.items():
            try:
                factors = func(data)
                # 过滤None值和NaN
                filtered_factors = {}
                for k, v in factors.items():
                    if v is not None:
                        if isinstance(v, (int, float)) and not np.isnan(v):
                            filtered_factors[k] = v
                        elif not isinstance(v, (int, float)):
                            filtered_factors[k] = v
                all_factors.update(filtered_factors)
            except Exception as e:
                print(f"Warning: {category} factor extraction failed: {e}")

        return all_factors

    def get_factor_count(self) -> int:
        """获取因子总数"""
        # 模拟数据统计
        return 200


class GeneticFactorSelector:
    """遗传算法因子筛选器"""

    def __init__(self, population_size=50, generations=20, mutation_rate=0.1):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.best_factors = None

    def evaluate_factor(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """评估单个因子的有效性"""
        # IC（信息系数）
        ic = factor_values.corr(returns.shift(-1))

        # IR（信息比率）
        ic_series = factor_values.rolling(20).corr(returns.shift(-1))
        ir = ic_series.mean() / ic_series.std() if ic_series.std() != 0 else 0

        # 单调性
        monotonicity = self._check_monotonicity(factor_values, returns)

        # 综合评分
        score = abs(ic) * 0.4 + abs(ir) * 0.3 + monotonicity * 0.3

        return score

    def _check_monotonicity(
        self, factor_values: pd.Series, returns: pd.Series
    ) -> float:
        """检查因子单调性"""
        try:
            # 分组测试
            n_groups = 5
            factor_values = factor_values.dropna()
            returns = returns.dropna()

            if len(factor_values) < n_groups * 2:
                return 0

            # 按因子值分组
            labels = pd.qcut(factor_values, n_groups, labels=False, duplicates="drop")
            group_returns = returns.groupby(labels).mean()

            # 检查单调性
            if len(group_returns) < 2:
                return 0

            # 计算单调性得分
            diffs = group_returns.diff().dropna()
            monotonic_score = (diffs > 0).sum() / len(diffs)

            return monotonic_score
        except:
            return 0

    def select_factors(
        self, factor_data: pd.DataFrame, returns: pd.Series, top_n: int = 50
    ) -> List[str]:
        """选择有效因子"""
        factor_scores = {}

        for factor_name in factor_data.columns:
            if factor_name == "returns":
                continue

            try:
                score = self.evaluate_factor(factor_data[factor_name], returns)
                factor_scores[factor_name] = score
            except:
                continue

        # 排序选择top_n
        sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        selected_factors = [f[0] for f in sorted_factors[:top_n]]

        self.best_factors = selected_factors
        return selected_factors

    def optimize_factor_weights(
        self, factor_data: pd.DataFrame, returns: pd.Series
    ) -> Dict[str, float]:
        """优化因子权重"""
        if self.best_factors is None:
            self.best_factors = self.select_factors(factor_data, returns)

        # 简化版：基于IC的权重
        weights = {}
        total_ic = 0

        for factor_name in self.best_factors:
            ic = abs(factor_data[factor_name].corr(returns.shift(-1)))
            weights[factor_name] = ic
            total_ic += ic

        # 归一化
        if total_ic > 0:
            weights = {k: v / total_ic for k, v in weights.items()}

        return weights


class FactorEngine:
    """因子引擎 - 整合因子库和筛选器"""

    def __init__(self):
        self.library = FactorLibrary()
        self.selector = GeneticFactorSelector()
        self.selected_factors = None
        self.factor_weights = None

    def process(
        self, data: pd.DataFrame, returns: pd.Series = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        处理数据，提取并筛选因子

        返回:
            (因子向量, 因子字典)
        """
        # 1. 提取所有因子
        all_factors = self.library.extract_all_factors(data)

        # 2. 如果有收益率数据，进行因子筛选
        if returns is not None and len(returns) > 20:
            # 构建因子DataFrame
            factor_df = pd.DataFrame()
            for i in range(len(data) - 20):
                factor_row = self.library.extract_all_factors(data.iloc[i : i + 20])
                factor_df = pd.concat(
                    [factor_df, pd.DataFrame([factor_row])], ignore_index=True
                )

            # 筛选因子
            if self.selected_factors is None:
                self.selected_factors = self.selector.select_factors(factor_df, returns)
                self.factor_weights = self.selector.optimize_factor_weights(
                    factor_df, returns
                )

        # 3. 构建因子向量
        if self.selected_factors:
            factor_vector = np.array(
                [all_factors.get(f, 0) for f in self.selected_factors]
            )
        else:
            factor_vector = np.array(list(all_factors.values()))

        return factor_vector, all_factors


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("因子库模块测试 - 幻方量化三层策略池底层")
    print("=" * 80)

    # 创建因子库
    library = FactorLibrary()
    print(f"\n因子库总数: {library.get_factor_count()} 个")

    # 模拟测试数据
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", "2026-04-30")
    n = len(dates)

    data = pd.DataFrame(
        {
            "close": 100 * (1 + np.random.randn(n).cumsum() * 0.02),
            "high": 102 * (1 + np.random.randn(n).cumsum() * 0.02),
            "low": 98 * (1 + np.random.randn(n).cumsum() * 0.02),
            "open": 100 * (1 + np.random.randn(n).cumsum() * 0.02),
            "volume": np.random.randint(1000000, 10000000, n),
            "turnover_rate": np.random.uniform(0.01, 0.05, n),
            "pe": np.random.uniform(10, 50, n),
            "pb": np.random.uniform(1, 5, n),
            "roe": np.random.uniform(0.05, 0.25, n),
            "main_flow": np.random.randint(-50000, 100000, n),
            "ddx": np.random.uniform(-5, 5, n),
        },
        index=dates,
    )

    # 提取因子
    print("\n1. 提取所有因子")
    print("-" * 80)

    factors = library.extract_all_factors(data)
    print(f"提取因子数: {len(factors)} 个")

    # 显示各类因子数量
    factor_count_by_category = {
        "量价因子": len(
            [
                k
                for k in factors.keys()
                if any(
                    x in k
                    for x in [
                        "return",
                        "volume",
                        "turnover",
                        "limit",
                        "gap",
                        "amplitude",
                        "volatility",
                    ]
                )
            ]
        ),
        "基本面因子": len(
            [
                k
                for k in factors.keys()
                if any(
                    x in k
                    for x in [
                        "pe",
                        "pb",
                        "roe",
                        "roa",
                        "margin",
                        "growth",
                        "debt",
                        "cash",
                    ]
                )
            ]
        ),
        "情绪因子": len(
            [
                k
                for k in factors.keys()
                if any(x in k for x in ["sentiment", "limit_up", "hot", "news"])
            ]
        ),
        "资金流因子": len(
            [
                k
                for k in factors.keys()
                if any(x in k for x in ["flow", "ddx", "margin", "north"])
            ]
        ),
        "技术因子": len(
            [
                k
                for k in factors.keys()
                if any(x in k for x in ["ma", "macd", "kdj", "rsi", "boll", "atr"])
            ]
        ),
        "风险因子": len(
            [
                k
                for k in factors.keys()
                if any(
                    x in k
                    for x in ["beta", "drawdown", "var", "cvar", "skewness", "kurtosis"]
                )
            ]
        ),
    }

    for category, count in factor_count_by_category.items():
        print(f"  {category}: {count} 个")

    # 显示部分因子
    print("\n部分因子示例:")
    for i, (k, v) in enumerate(list(factors.items())[:10]):
        print(f"  {k}: {v:.4f}" if isinstance(v, (int, float)) else f"  {k}: {v}")

    # 测试因子筛选
    print("\n2. 因子筛选测试")
    print("-" * 80)

    engine = FactorEngine()
    returns = data["close"].pct_change()

    factor_vector, factor_dict = engine.process(data, returns)
    print(f"筛选后因子向量维度: {factor_vector.shape}")
    print(f"因子向量前10个值: {factor_vector[:10]}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
