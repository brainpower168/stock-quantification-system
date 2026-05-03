#!/usr/bin/env python3
"""
机器学习策略演示脚本
使用随机森林预测股票未来5日涨跌方向
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

# 导入数据获取工具
try:
    from mx_data import MXDataClient

    HAS_MX = True
except ImportError:
    HAS_MX = False
    print("[WARN] mx_data not available, will use mock data")


def validate_data(df: pd.DataFrame, min_rows: int = 300) -> bool:
    """检查数据是否符合ML训练要求"""
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return False
    if len(df) < min_rows:
        return False
    if df["close"].isnull().mean() > 0.2:
        return False
    return True


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """构建机器学习特征矩阵"""
    c = df["close"]
    v = df["volume"]
    ret = c.pct_change()

    features = pd.DataFrame(index=df.index)

    # 动量特征
    features["f_ret_5d"] = c.pct_change(5)
    features["f_ret_20d"] = c.pct_change(20)

    # 波动特征
    features["f_vol_20d"] = ret.rolling(20).std()

    # 均线偏离
    features["f_ma_ratio"] = c / c.rolling(20).mean()

    # 量比
    features["f_volume_ratio"] = v / v.rolling(20).mean()

    # RSI(14)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    features["f_rsi_14"] = 100 - (100 / (1 + rs))

    # 布林带位置
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    features["f_bb_position"] = (c - bb_lower) / bb_range

    # 日内特征
    features["f_high_low_ratio"] = (df["high"] - df["low"]) / c
    features["f_close_open_ratio"] = (c - df["open"]) / df["open"]
    features["f_skew_20d"] = ret.rolling(20).skew()

    # 清理inf
    features = features.replace([np.inf, -np.inf], np.nan)
    return features


def walk_forward_predict(
    features: pd.DataFrame,
    labels: pd.Series,
    min_train_size: int = 252,
    retrain_freq: int = 20,
    model_type: str = "random_forest",
) -> pd.Series:
    """Walk-Forward训练和预测"""
    predictions = pd.Series(0.0, index=features.index)
    model = None
    scaler = None

    for i in range(min_train_size, len(features)):
        # 每retrain_freq天重新训练
        if model is None or (i - min_train_size) % retrain_freq == 0:
            X_train = features.iloc[:i].values
            y_train = labels.iloc[:i].values

            # 去除NaN
            valid = ~(np.isnan(X_train).any(axis=1) | np.isnan(y_train))
            X_train = X_train[valid]
            y_train = y_train[valid]

            if len(X_train) < 50:
                continue

            # 标准化
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)

            # 构建模型
            if model_type == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=5,
                    random_state=42,
                )
            elif model_type == "gradient_boosting":
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.05,
                    random_state=42,
                )
            elif model_type == "ridge":
                model = LogisticRegression(penalty="l2", C=1.0, random_state=42)

            model.fit(X_train, y_train)

        # 预测今天
        X_today = features.iloc[i : i + 1].values
        if np.isnan(X_today).any():
            predictions.iloc[i] = 0.0
            continue

        X_today = scaler.transform(X_today)

        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(X_today)[0, 1]
            predictions.iloc[i] = prob * 2 - 1  # [0,1] -> [-1,1]
        else:
            predictions.iloc[i] = float(model.predict(X_today)[0])

    predictions = predictions.fillna(0.0).clip(-1.0, 1.0)
    return predictions


def get_stock_data(code: str, days: int = 500) -> pd.DataFrame:
    """获取股票历史数据"""
    if HAS_MX:
        try:
            client = MXDataClient()
            # 获取日K线数据
            df = client.get_daily_kline(code, days=days)
            if df is not None and len(df) > 0:
                return df
        except Exception as e:
            print(f"[WARN] Failed to get data from MX: {e}")

    # 如果没有真实数据，生成模拟数据
    print(f"[INFO] Using mock data for {code}")
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq="B")

    # 模拟价格走势
    returns = np.random.randn(days) * 0.02
    price = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "open": price * (1 + np.random.randn(days) * 0.01),
            "high": price * (1 + np.abs(np.random.randn(days) * 0.02)),
            "low": price * (1 - np.abs(np.random.randn(days) * 0.02)),
            "close": price,
            "volume": np.random.randint(1000000, 10000000, days),
        },
        index=dates,
    )

    return df


def analyze_stock(code: str, model_type: str = "random_forest"):
    """分析单只股票"""
    print(f"\n{'=' * 60}")
    print(f"分析股票: {code}")
    print(f"模型类型: {model_type}")
    print("=" * 60)

    # 获取数据
    df = get_stock_data(code)
    if df is None or len(df) < 300:
        print(f"[ERROR] 数据不足，需要至少300个交易日")
        return None

    print(f"数据范围: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"数据行数: {len(df)}")

    # 验证数据
    if not validate_data(df):
        print(f"[ERROR] 数据质量不符合要求")
        return None

    # 构建特征
    features = build_features(df)
    print(f"\n特征数量: {len(features.columns)}")
    print(f"特征列表: {list(features.columns)}")

    # 构建标签（未来5日涨跌）
    labels = (df["close"].pct_change(5).shift(-5) > 0).astype(int)

    # Walk-Forward预测
    print(f"\n开始Walk-Forward训练...")
    signals = walk_forward_predict(features, labels, model_type=model_type)

    # 分析结果
    latest_signal = signals.iloc[-1]
    latest_price = df["close"].iloc[-1]

    print(f"\n{'=' * 60}")
    print(f"预测结果")
    print("=" * 60)
    print(f"最新价格: {latest_price:.2f}")
    print(f"ML信号: {latest_signal:.3f}")

    if latest_signal > 0.3:
        signal_desc = "看多 (买入信号)"
    elif latest_signal < -0.3:
        signal_desc = "看空 (卖出信号)"
    else:
        signal_desc = "中性 (观望)"

    print(f"信号解读: {signal_desc}")

    # 计算历史准确率
    valid_signals = signals[signals != 0]
    valid_labels = labels.loc[valid_signals.index]
    correct = ((valid_signals > 0) == (valid_labels == 1)).sum()
    total = len(valid_signals)
    accuracy = correct / total if total > 0 else 0

    print(f"\n历史准确率: {accuracy:.1%} ({correct}/{total})")

    # 最近10日信号
    print(f"\n最近10日信号:")
    recent_signals = signals.tail(10)
    for date, sig in recent_signals.items():
        direction = "看多" if sig > 0.3 else ("看空" if sig < -0.3 else "中性")
        print(f"  {date.date()}: {sig:+.3f} ({direction})")

    return {
        "code": code,
        "price": latest_price,
        "signal": latest_signal,
        "accuracy": accuracy,
        "signals": signals,
    }


def compare_models(code: str):
    """对比不同模型"""
    print(f"\n{'=' * 60}")
    print(f"模型对比: {code}")
    print("=" * 60)

    results = {}
    for model_type in ["random_forest", "gradient_boosting", "ridge"]:
        print(f"\n--- {model_type} ---")
        result = analyze_stock(code, model_type=model_type)
        if result:
            results[model_type] = result

    # 对比结果
    print(f"\n{'=' * 60}")
    print(f"模型对比结果")
    print("=" * 60)
    print(f"{'模型':<20} {'信号':<10} {'准确率':<10}")
    print("-" * 40)
    for model_type, result in results.items():
        print(f"{model_type:<20} {result['signal']:+.3f}    {result['accuracy']:.1%}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="机器学习策略演示")
    parser.add_argument("--stock", type=str, default="600519", help="股票代码")
    parser.add_argument(
        "--model",
        type=str,
        default="random_forest",
        choices=["random_forest", "gradient_boosting", "ridge"],
        help="模型类型",
    )
    parser.add_argument("--compare", action="store_true", help="对比所有模型")

    args = parser.parse_args()

    if args.compare:
        compare_models(args.stock)
    else:
        analyze_stock(args.stock, args.model)
