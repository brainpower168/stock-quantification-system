# -*- coding: utf-8 -*-
"""
量化交易系统 - ML特征工程模块 v2.0
升级：从28个特征 → 50+特征，7大类
作者：DuMate AI
日期：2026-05-01
功能：提取50+个特征，分类管理，归一化处理
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")


class FeatureEngineer:
    """特征工程器 - 提取50+个特征，7大类"""

    def __init__(self):
        # 定义7大类特征
        self.feature_categories = {
            "price_momentum": [
                "rsi_6",
                "rsi_12",
                "rsi_24",
                "macd",
                "macd_signal",
                "macd_hist",
                "kdj_k",
                "kdj_d",
                "kdj_j",
                "cci",
                "wr",
            ],
            "volume_analysis": [
                "volume_ratio",
                "obv_trend",
                "volume_ma_5",
                "volume_ma_10",
                "volume_ma_20",
                "turnover_rate",
                "amount_ratio",
            ],
            "fundamental_quality": [
                "pe_ratio",
                "pb_ratio",
                "ps_ratio",
                "roe",
                "roa",
                "net_profit_margin",
                "gross_profit_margin",
                "debt_ratio",
            ],
            "financial_health": [
                "current_ratio",
                "quick_ratio",
                "inventory_turnover",
                "receivable_turnover",
                "cash_flow_ratio",
                "operating_cash_flow",
            ],
            "market_sentiment": [
                "news_positive_rate",
                "news_negative_rate",
                "analyst_rating",
                "analyst_target_price",
                "institutional_holding_change",
                "fund_holding_ratio",
            ],
            "technical_patterns": [
                "bollinger_upper",
                "bollinger_middle",
                "bollinger_lower",
                "bollinger_width",
                "adx",
                "adx_trend",
                "ma_5",
                "ma_10",
                "ma_20",
                "ma_60",
                "price_above_ma5",
                "price_above_ma20",
            ],
            "risk_metrics": [
                "beta",
                "volatility_20d",
                "volatility_60d",
                "max_drawdown_20d",
                "max_drawdown_60d",
                "sharpe_ratio",
                "sortino_ratio",
                "var_95",
                "cvar_95",
            ],
        }

        # 计算总特征数
        self.total_features = sum(len(v) for v in self.feature_categories.values())
        self.feature_names = []
        for category, names in self.feature_categories.items():
            self.feature_names.extend(names)

    def extract_features(self, stock_data, market_data=None):
        """
        从股票数据中提取特征
        :param stock_data: 单只股票的数据字典
        :param market_data: 市场整体数据（用于计算相对表现）
        :return: 特征向量（numpy array）+ 特征名称列表
        """
        features = []
        feature_dict = {}

        # ========== 1. 价格动量特征（11个）==========
        price_momentum = self._extract_price_momentum(stock_data)
        features.extend(price_momentum.values())
        feature_dict.update(price_momentum)

        # ========== 2. 成交量分析特征（7个）==========
        volume_analysis = self._extract_volume_analysis(stock_data)
        features.extend(volume_analysis.values())
        feature_dict.update(volume_analysis)

        # ========== 3. 基本面质量特征（8个）==========
        fundamental_quality = self._extract_fundamental_quality(stock_data)
        features.extend(fundamental_quality.values())
        feature_dict.update(fundamental_quality)

        # ========== 4. 财务健康特征（6个）==========
        financial_health = self._extract_financial_health(stock_data)
        features.extend(financial_health.values())
        feature_dict.update(financial_health)

        # ========== 5. 市场情绪特征（6个）==========
        market_sentiment = self._extract_market_sentiment(stock_data)
        features.extend(market_sentiment.values())
        feature_dict.update(market_sentiment)

        # ========== 6. 技术形态特征（12个）==========
        technical_patterns = self._extract_technical_patterns(stock_data)
        features.extend(technical_patterns.values())
        feature_dict.update(technical_patterns)

        # ========== 7. 风险指标特征（9个）==========
        risk_metrics = self._extract_risk_metrics(stock_data, market_data)
        features.extend(risk_metrics.values())
        feature_dict.update(risk_metrics)

        # ========== 标准化处理 ==========
        feature_vector = np.array(features, dtype=np.float32)

        # 处理NaN和Inf
        feature_vector = np.nan_to_num(feature_vector, nan=0.5, posinf=1.0, neginf=0.0)

        # 裁剪到[0, 1]范围
        feature_vector = np.clip(feature_vector, 0.0, 1.0)

        return feature_vector, feature_dict

    def _extract_price_momentum(self, data):
        """提取价格动量特征"""
        features = {}

        # RSI指标（归一化到0-1）
        features["rsi_6"] = self._safe_normalize(data.get("rsi_6", 50), 0, 100)
        features["rsi_12"] = self._safe_normalize(data.get("rsi_12", 50), 0, 100)
        features["rsi_24"] = self._safe_normalize(data.get("rsi_24", 50), 0, 100)

        # MACD指标
        macd = data.get("macd", 0)
        macd_signal = data.get("macd_signal", 0)
        macd_hist = data.get("macd_hist", macd - macd_signal)

        features["macd"] = self._safe_normalize(macd, -2, 2)
        features["macd_signal"] = self._safe_normalize(macd_signal, -2, 2)
        features["macd_hist"] = self._safe_normalize(macd_hist, -1, 1)

        # KDJ指标
        features["kdj_k"] = self._safe_normalize(data.get("kdj_k", 50), 0, 100)
        features["kdj_d"] = self._safe_normalize(data.get("kdj_d", 50), 0, 100)
        features["kdj_j"] = self._safe_normalize(data.get("kdj_j", 50), -20, 120)

        # CCI指标
        features["cci"] = self._safe_normalize(data.get("cci", 0), -200, 200)

        # WR指标（威廉指标）
        features["wr"] = self._safe_normalize(data.get("wr", 50), 0, 100)

        return features

    def _extract_volume_analysis(self, data):
        """提取成交量分析特征"""
        features = {}

        # 量比
        features["volume_ratio"] = self._safe_normalize(
            data.get("volume_ratio", 1), 0, 5
        )

        # OBV趋势
        obv_trend = data.get("obv_trend", 0)
        features["obv_trend"] = self._safe_normalize(obv_trend, -1, 1)

        # 成交量均线
        volume = data.get("volume", 1)
        volume_ma_5 = data.get("volume_ma_5", volume)
        volume_ma_10 = data.get("volume_ma_10", volume)
        volume_ma_20 = data.get("volume_ma_20", volume)

        features["volume_ma_5"] = self._safe_normalize(
            volume / max(volume_ma_5, 1), 0, 3
        )
        features["volume_ma_10"] = self._safe_normalize(
            volume / max(volume_ma_10, 1), 0, 3
        )
        features["volume_ma_20"] = self._safe_normalize(
            volume / max(volume_ma_20, 1), 0, 3
        )

        # 换手率
        features["turnover_rate"] = self._safe_normalize(
            data.get("turnover_rate", 0), 0, 20
        )

        # 金额比
        features["amount_ratio"] = self._safe_normalize(
            data.get("amount_ratio", 1), 0, 5
        )

        return features

    def _extract_fundamental_quality(self, data):
        """提取基本面质量特征"""
        features = {}

        # PE估值（越低越好，归一化后越高越好）
        pe = data.get("pe_ratio", 50)
        features["pe_ratio"] = max(0, min(1, (50 - pe) / 50))

        # PB估值
        pb = data.get("pb_ratio", 3)
        features["pb_ratio"] = max(0, min(1, (5 - pb) / 5))

        # PS估值
        ps = data.get("ps_ratio", 3)
        features["ps_ratio"] = max(0, min(1, (5 - ps) / 5))

        # ROE（越高越好）
        features["roe"] = self._safe_normalize(data.get("roe", 0.1), 0, 0.3)

        # ROA
        features["roa"] = self._safe_normalize(data.get("roa", 0.05), 0, 0.15)

        # 净利率
        features["net_profit_margin"] = self._safe_normalize(
            data.get("net_profit_margin", 0.1), 0, 0.3
        )

        # 毛利率
        features["gross_profit_margin"] = self._safe_normalize(
            data.get("gross_profit_margin", 0.2), 0, 0.5
        )

        # 负债率（越低越好）
        debt_ratio = data.get("debt_ratio", 0.5)
        features["debt_ratio"] = max(0, min(1, (0.7 - debt_ratio) / 0.7))

        return features

    def _extract_financial_health(self, data):
        """提取财务健康特征"""
        features = {}

        # 流动比率
        features["current_ratio"] = self._safe_normalize(
            data.get("current_ratio", 1.5), 0, 3
        )

        # 速动比率
        features["quick_ratio"] = self._safe_normalize(data.get("quick_ratio", 1), 0, 2)

        # 存货周转率
        features["inventory_turnover"] = self._safe_normalize(
            data.get("inventory_turnover", 5), 0, 15
        )

        # 应收账款周转率
        features["receivable_turnover"] = self._safe_normalize(
            data.get("receivable_turnover", 5), 0, 20
        )

        # 现金流比率
        features["cash_flow_ratio"] = self._safe_normalize(
            data.get("cash_flow_ratio", 0.5), 0, 2
        )

        # 经营现金流
        operating_cash_flow = data.get("operating_cash_flow", 0)
        features["operating_cash_flow"] = 1.0 if operating_cash_flow > 0 else 0.0

        return features

    def _extract_market_sentiment(self, data):
        """提取市场情绪特征"""
        features = {}

        # 新闻正面率
        features["news_positive_rate"] = self._safe_normalize(
            data.get("news_positive_rate", 0.5), 0, 1
        )

        # 新闻负面率
        features["news_negative_rate"] = self._safe_normalize(
            data.get("news_negative_rate", 0.3), 0, 1
        )

        # 分析师评级（1-5，归一化到0-1）
        analyst_rating = data.get("analyst_rating", 3)
        features["analyst_rating"] = self._safe_normalize(analyst_rating, 1, 5)

        # 分析师目标价相对当前价的涨幅
        target_price = data.get("analyst_target_price", data.get("price", 100))
        current_price = data.get("price", 100)
        target_upside = (target_price - current_price) / max(current_price, 1)
        features["analyst_target_price"] = self._safe_normalize(
            target_upside, -0.3, 0.5
        )

        # 机构持仓变化
        institutional_change = data.get("institutional_holding_change", 0)
        features["institutional_holding_change"] = self._safe_normalize(
            institutional_change, -0.1, 0.1
        )

        # 基金持仓比例
        features["fund_holding_ratio"] = self._safe_normalize(
            data.get("fund_holding_ratio", 0.1), 0, 0.3
        )

        return features

    def _extract_technical_patterns(self, data):
        """提取技术形态特征"""
        features = {}

        # 布林带
        price = data.get("price", 100)
        bollinger_upper = data.get("bollinger_upper", price * 1.02)
        bollinger_middle = data.get("bollinger_middle", price)
        bollinger_lower = data.get("bollinger_lower", price * 0.98)

        features["bollinger_upper"] = self._safe_normalize(
            price / max(bollinger_upper, 1), 0.9, 1.1
        )
        features["bollinger_middle"] = self._safe_normalize(
            price / max(bollinger_middle, 1), 0.9, 1.1
        )
        features["bollinger_lower"] = self._safe_normalize(
            price / max(bollinger_lower, 1), 0.9, 1.1
        )

        # 布林带宽度
        bb_width = (bollinger_upper - bollinger_lower) / max(bollinger_middle, 1)
        features["bollinger_width"] = self._safe_normalize(bb_width, 0, 0.2)

        # ADX趋势强度
        features["adx"] = self._safe_normalize(data.get("adx", 25), 0, 60)

        # ADX趋势方向
        adx_trend = data.get("adx_trend", 0)
        features["adx_trend"] = self._safe_normalize(adx_trend, -1, 1)

        # 均线
        ma_5 = data.get("ma_5", price)
        ma_10 = data.get("ma_10", price)
        ma_20 = data.get("ma_20", price)
        ma_60 = data.get("ma_60", price)

        features["ma_5"] = self._safe_normalize(price / max(ma_5, 1), 0.9, 1.1)
        features["ma_10"] = self._safe_normalize(price / max(ma_10, 1), 0.9, 1.1)
        features["ma_20"] = self._safe_normalize(price / max(ma_20, 1), 0.9, 1.1)
        features["ma_60"] = self._safe_normalize(price / max(ma_60, 1), 0.9, 1.1)

        # 价格在均线上方
        features["price_above_ma5"] = 1.0 if price > ma_5 else 0.0
        features["price_above_ma20"] = 1.0 if price > ma_20 else 0.0

        return features

    def _extract_risk_metrics(self, data, market_data=None):
        """提取风险指标特征"""
        features = {}

        # Beta系数
        features["beta"] = self._safe_normalize(data.get("beta", 1), 0, 2)

        # 波动率
        features["volatility_20d"] = self._safe_normalize(
            data.get("volatility_20d", 0.25), 0, 0.5
        )
        features["volatility_60d"] = self._safe_normalize(
            data.get("volatility_60d", 0.30), 0, 0.6
        )

        # 最大回撤（越小越好，归一化后越高越好）
        max_dd_20d = data.get("max_drawdown_20d", 0.1)
        features["max_drawdown_20d"] = max(0, min(1, (0.3 - abs(max_dd_20d)) / 0.3))

        max_dd_60d = data.get("max_drawdown_60d", 0.15)
        features["max_drawdown_60d"] = max(0, min(1, (0.4 - abs(max_dd_60d)) / 0.4))

        # 夏普比率
        features["sharpe_ratio"] = self._safe_normalize(
            data.get("sharpe_ratio", 1), -1, 3
        )

        # 索提诺比率
        features["sortino_ratio"] = self._safe_normalize(
            data.get("sortino_ratio", 1.5), -1, 4
        )

        # VaR和CVaR
        features["var_95"] = self._safe_normalize(data.get("var_95", 0.05), 0, 0.15)
        features["cvar_95"] = self._safe_normalize(data.get("cvar_95", 0.08), 0, 0.2)

        return features

    def _safe_normalize(self, value, min_val, max_val):
        """安全归一化到[0, 1]"""
        try:
            if pd.isna(value) or np.isinf(value):
                return 0.5
            normalized = (value - min_val) / (max_val - min_val)
            return max(0.0, min(1.0, normalized))
        except:
            return 0.5

    def get_feature_names(self):
        """获取所有特征名称"""
        return self.feature_names

    def get_feature_categories(self):
        """获取特征分类"""
        return self.feature_categories

    def get_total_features(self):
        """获取总特征数"""
        return self.total_features


# ==================== 数据生成器（用于演示）====================
class DataGenerator:
    """模拟数据生成器"""

    @staticmethod
    def generate_stock_data(code, random_state=None):
        """生成单只股票的模拟数据"""
        if random_state is not None:
            np.random.seed(random_state)

        # 基础价格
        base_price = np.random.uniform(10, 200)

        # 生成完整数据
        data = {
            "code": code,
            "price": base_price,
            # 价格动量
            "rsi_6": np.random.uniform(30, 70),
            "rsi_12": np.random.uniform(35, 65),
            "rsi_24": np.random.uniform(40, 60),
            "macd": np.random.uniform(-1, 1),
            "macd_signal": np.random.uniform(-1, 1),
            "macd_hist": np.random.uniform(-0.5, 0.5),
            "kdj_k": np.random.uniform(20, 80),
            "kdj_d": np.random.uniform(20, 80),
            "kdj_j": np.random.uniform(0, 100),
            "cci": np.random.uniform(-100, 100),
            "wr": np.random.uniform(20, 80),
            # 成交量
            "volume": np.random.uniform(100000, 10000000),
            "volume_ratio": np.random.uniform(0.5, 2.5),
            "obv_trend": np.random.uniform(-0.5, 0.5),
            "volume_ma_5": np.random.uniform(100000, 10000000),
            "volume_ma_10": np.random.uniform(100000, 10000000),
            "volume_ma_20": np.random.uniform(100000, 10000000),
            "turnover_rate": np.random.uniform(1, 10),
            "amount_ratio": np.random.uniform(0.5, 2),
            # 基本面
            "pe_ratio": np.random.uniform(10, 50),
            "pb_ratio": np.random.uniform(1, 5),
            "ps_ratio": np.random.uniform(1, 5),
            "roe": np.random.uniform(0.05, 0.25),
            "roa": np.random.uniform(0.02, 0.12),
            "net_profit_margin": np.random.uniform(0.05, 0.25),
            "gross_profit_margin": np.random.uniform(0.15, 0.45),
            "debt_ratio": np.random.uniform(0.2, 0.6),
            # 财务健康
            "current_ratio": np.random.uniform(1, 3),
            "quick_ratio": np.random.uniform(0.5, 2),
            "inventory_turnover": np.random.uniform(2, 12),
            "receivable_turnover": np.random.uniform(3, 15),
            "cash_flow_ratio": np.random.uniform(0.3, 1.5),
            "operating_cash_flow": np.random.uniform(-1e8, 1e9),
            # 市场情绪
            "news_positive_rate": np.random.uniform(0.3, 0.7),
            "news_negative_rate": np.random.uniform(0.1, 0.4),
            "analyst_rating": np.random.uniform(2, 5),
            "analyst_target_price": base_price * np.random.uniform(0.9, 1.3),
            "institutional_holding_change": np.random.uniform(-0.05, 0.05),
            "fund_holding_ratio": np.random.uniform(0.05, 0.25),
            # 技术形态
            "bollinger_upper": base_price * np.random.uniform(1.01, 1.10),
            "bollinger_middle": base_price,
            "bollinger_lower": base_price * np.random.uniform(0.90, 0.99),
            "adx": np.random.uniform(15, 45),
            "adx_trend": np.random.uniform(-0.5, 0.5),
            "ma_5": base_price * np.random.uniform(0.95, 1.05),
            "ma_10": base_price * np.random.uniform(0.93, 1.07),
            "ma_20": base_price * np.random.uniform(0.90, 1.10),
            "ma_60": base_price * np.random.uniform(0.85, 1.15),
            # 风险指标
            "beta": np.random.uniform(0.5, 1.5),
            "volatility_20d": np.random.uniform(0.15, 0.35),
            "volatility_60d": np.random.uniform(0.20, 0.40),
            "max_drawdown_20d": np.random.uniform(-0.15, -0.05),
            "max_drawdown_60d": np.random.uniform(-0.25, -0.08),
            "sharpe_ratio": np.random.uniform(0.5, 2.5),
            "sortino_ratio": np.random.uniform(0.8, 3),
            "var_95": np.random.uniform(0.02, 0.10),
            "cvar_95": np.random.uniform(0.03, 0.12),
        }

        return data


# ==================== 主程序 ====================
def main():
    """主函数 - 特征工程演示"""
    print("=" * 70)
    print("[ML Feature Engineer v2.0]")
    print("=" * 70)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 初始化特征工程器
    fe = FeatureEngineer()

    print(f"[OK] Feature Engineer initialized")
    print(f"   Total features: {fe.get_total_features()}")
    print(f"   Feature categories: {len(fe.get_feature_categories())}")
    print()

    # 显示特征分类
    print("[Feature Categories]:")
    for category, names in fe.get_feature_categories().items():
        print(f"   {category}: {len(names)} features")
        print(f"      {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")
    print()

    # 生成测试数据
    print("[Generating test data...]")
    dg = DataGenerator()
    test_stocks = ["600519", "000001", "300750", "601318", "000858"]

    features_list = []
    for code in test_stocks:
        stock_data = dg.generate_stock_data(code, random_state=hash(code) % 2**32)
        feature_vector, feature_dict = fe.extract_features(stock_data)
        features_list.append(feature_vector)
        print(
            f"   {code}: shape {feature_vector.shape}, range [{feature_vector.min():.3f}, {feature_vector.max():.3f}]"
        )

    print()

    # 转换为矩阵
    features_matrix = np.array(features_list)
    print(f"[OK] Feature matrix shape: {features_matrix.shape}")
    print(f"   Samples: {features_matrix.shape[0]}")
    print(f"   Features: {features_matrix.shape[1]}")
    print()

    # 显示示例特征
    print("[Sample Features (first stock)]:")
    sample_features = list(feature_dict.items())[:10]
    for name, value in sample_features:
        print(f"   {name}: {value:.4f}")
    print()

    print("=" * 70)
    print("[OK] Feature Engineer test completed!")
    print("=" * 70)
    print("📈 量化交易系统 - ML特征工程模块 v2.0")
    print("=" * 70)
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 初始化特征工程器
    fe = FeatureEngineer()

    print(f"✅ 特征工程器初始化完成")
    print(f"   总特征数：{fe.get_total_features()}")
    print(f"   特征类别：{len(fe.get_feature_categories())}")
    print()

    # 显示特征分类
    print("📊 特征分类明细：")
    for category, names in fe.get_feature_categories().items():
        print(f"   {category}: {len(names)}个")
        print(f"      {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")
    print()

    # 生成测试数据
    print("🔍 生成测试数据...")
    dg = DataGenerator()
    test_stocks = ["600519", "000001", "300750", "601318", "000858"]

    features_list = []
    for code in test_stocks:
        stock_data = dg.generate_stock_data(code, random_state=hash(code) % 2**32)
        feature_vector, feature_dict = fe.extract_features(stock_data)
        features_list.append(feature_vector)
        print(
            f"   {code}: 特征向量形状 {feature_vector.shape}, 范围 [{feature_vector.min():.3f}, {feature_vector.max():.3f}]"
        )

    print()

    # 转换为矩阵
    features_matrix = np.array(features_list)
    print(f"✅ 特征矩阵形状：{features_matrix.shape}")
    print(f"   样本数：{features_matrix.shape[0]}")
    print(f"   特征数：{features_matrix.shape[1]}")
    print()

    # 显示示例特征
    print("📊 示例特征（第一只股票）：")
    sample_features = list(feature_dict.items())[:10]
    for name, value in sample_features:
        print(f"   {name}: {value:.4f}")
    print()

    print("=" * 70)
    print("✅ 特征工程模块测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
