#!/usr/bin/env python3
"""
增强版机器学习策略 - XGBoost + PyTorch LSTM
对比sklearn、XGBoost、LSTM的预测效果
"""

import sys
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
from datetime import datetime, timedelta

# XGBoost
import xgboost as xgb

# PyTorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# 检查GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")


def validate_data(df: pd.DataFrame, min_rows: int = 300) -> bool:
    """检查数据质量"""
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return False
    if len(df) < min_rows:
        return False
    if df["close"].isnull().mean() > 0.2:
        return False
    return True


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """构建特征矩阵（包含技术指标）"""
    c = df["close"]
    v = df["volume"]
    ret = c.pct_change()

    features = pd.DataFrame(index=df.index)

    # 动量特征
    features["f_ret_1d"] = ret
    features["f_ret_5d"] = c.pct_change(5)
    features["f_ret_10d"] = c.pct_change(10)
    features["f_ret_20d"] = c.pct_change(20)

    # 波动特征
    features["f_vol_5d"] = ret.rolling(5).std()
    features["f_vol_10d"] = ret.rolling(10).std()
    features["f_vol_20d"] = ret.rolling(20).std()

    # 均线系统
    features["f_ma5_ratio"] = c / c.rolling(5).mean()
    features["f_ma10_ratio"] = c / c.rolling(10).mean()
    features["f_ma20_ratio"] = c / c.rolling(20).mean()
    features["f_ma60_ratio"] = c / c.rolling(60).mean()

    # 量价关系
    features["f_volume_ratio"] = v / v.rolling(20).mean()
    features["f_obv"] = (np.sign(ret) * v).cumsum()
    features["f_vwap"] = (c * v).rolling(20).sum() / v.rolling(20).sum()

    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    features["f_rsi_14"] = 100 - (100 / (1 + rs))

    # KDJ
    low_min = df["low"].rolling(9).min()
    high_max = df["high"].rolling(9).max()
    rsv = (c - low_min) / (high_max - low_min).replace(0, np.nan) * 100
    features["f_k"] = rsv.ewm(com=2).mean()
    features["f_d"] = features["f_k"].ewm(com=2).mean()

    # 布林带
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    features["f_bb_position"] = (c - bb_lower) / bb_range
    features["f_bb_width"] = bb_range / ma20

    # MACD
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    features["f_macd"] = ema12 - ema26
    features["f_macd_signal"] = features["f_macd"].ewm(span=9).mean()
    features["f_macd_hist"] = features["f_macd"] - features["f_macd_signal"]

    # 日内特征
    features["f_high_low_ratio"] = (df["high"] - df["low"]) / c
    features["f_close_open_ratio"] = (c - df["open"]) / df["open"]
    features["f_upper_shadow"] = (df["high"] - c.clip(upper=df["close"])) / c
    features["f_lower_shadow"] = (c.clip(lower=df["close"]) - df["low"]) / c

    # 统计特征
    features["f_skew_20d"] = ret.rolling(20).skew()
    features["f_kurt_20d"] = ret.rolling(20).kurt()

    # 清理inf
    features = features.replace([np.inf, -np.inf], np.nan)
    return features


def walk_forward_sklearn(features, labels, model_type="random_forest"):
    """sklearn模型Walk-Forward训练"""
    predictions = pd.Series(0.0, index=features.index)
    min_train_size = 252
    retrain_freq = 20
    model = None
    scaler = None

    for i in range(min_train_size, len(features)):
        if model is None or (i - min_train_size) % retrain_freq == 0:
            X_train = features.iloc[:i].values
            y_train = labels.iloc[:i].values

            valid = ~(np.isnan(X_train).any(axis=1) | np.isnan(y_train))
            X_train = X_train[valid]
            y_train = y_train[valid]

            if len(X_train) < 50:
                continue

            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)

            if model_type == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=100, max_depth=5, random_state=42, n_jobs=-1
                )
            elif model_type == "gradient_boosting":
                model = GradientBoostingClassifier(
                    n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42
                )
            elif model_type == "ridge":
                model = LogisticRegression(C=1.0, random_state=42, max_iter=1000)

            model.fit(X_train, y_train)

        X_today = features.iloc[i : i + 1].values
        if np.isnan(X_today).any():
            continue

        X_today = scaler.transform(X_today)
        prob = model.predict_proba(X_today)[0, 1]
        predictions.iloc[i] = prob * 2 - 1

    return predictions.fillna(0.0).clip(-1.0, 1.0)


def walk_forward_xgboost(features, labels):
    """XGBoost Walk-Forward训练"""
    predictions = pd.Series(0.0, index=features.index)
    min_train_size = 252
    retrain_freq = 20
    model = None
    scaler = None

    for i in range(min_train_size, len(features)):
        if model is None or (i - min_train_size) % retrain_freq == 0:
            X_train = features.iloc[:i].values
            y_train = labels.iloc[:i].values

            valid = ~(np.isnan(X_train).any(axis=1) | np.isnan(y_train))
            X_train = X_train[valid]
            y_train = y_train[valid]

            if len(X_train) < 50:
                continue

            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)

            # XGBoost参数（防止过拟合）
            model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=-1,
                verbosity=0,
            )
            model.fit(X_train, y_train)

        X_today = features.iloc[i : i + 1].values
        if np.isnan(X_today).any():
            continue

        X_today = scaler.transform(X_today)
        prob = model.predict_proba(X_today)[0, 1]
        predictions.iloc[i] = prob * 2 - 1

    return predictions.fillna(0.0).clip(-1.0, 1.0)


class LSTMModel(nn.Module):
    """LSTM模型"""

    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: (batch, seq_len, features)
        lstm_out, _ = self.lstm(x)
        # 取最后一个时间步
        out = lstm_out[:, -1, :]
        out = self.fc(out)
        return out.squeeze()


def walk_forward_lstm(features, labels, seq_len=20):
    """LSTM Walk-Forward训练"""
    predictions = pd.Series(0.0, index=features.index)
    min_train_size = 252 + seq_len
    retrain_freq = 20

    # 标准化
    scaler = StandardScaler()
    features_scaled = pd.DataFrame(
        scaler.fit_transform(features), index=features.index, columns=features.columns
    )
    features_scaled = features_scaled.fillna(0)

    model = None

    for i in range(min_train_size, len(features)):
        if model is None or (i - min_train_size) % retrain_freq == 0:
            # 构建训练数据
            X_train = []
            y_train = []

            for j in range(seq_len, i):
                X_train.append(features_scaled.iloc[j - seq_len : j].values)
                y_train.append(labels.iloc[j])

            X_train = np.array(X_train)
            y_train = np.array(y_train)

            if len(X_train) < 50:
                continue

            # 转为Tensor
            X_tensor = torch.FloatTensor(X_train).to(device)
            y_tensor = torch.FloatTensor(y_train).to(device)

            # 构建模型
            model = LSTMModel(
                input_size=features.shape[1],
                hidden_size=64,
                num_layers=2,
                dropout=0.2,
            ).to(device)

            optimizer = optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.BCELoss()

            # 训练
            model.train()
            dataset = TensorDataset(X_tensor, y_tensor)
            loader = DataLoader(dataset, batch_size=32, shuffle=True)

            for epoch in range(10):  # 快速训练
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()

        # 预测
        X_today = features_scaled.iloc[i - seq_len : i].values
        if np.isnan(X_today).any():
            continue

        X_tensor = torch.FloatTensor(X_today).unsqueeze(0).to(device)

        model.eval()
        with torch.no_grad():
            prob = model(X_tensor).item()

        predictions.iloc[i] = prob * 2 - 1

    return predictions.fillna(0.0).clip(-1.0, 1.0)


def calculate_metrics(signals, labels):
    """计算评估指标"""
    valid = signals != 0
    if valid.sum() == 0:
        return {"accuracy": 0, "precision": 0, "recall": 0, "sharpe": 0}

    pred = (signals[valid] > 0).astype(int)
    true = labels[valid].astype(int)

    # 计算收益（简化版）
    returns = signals * labels.shift(-5)  # 5日收益

    return {
        "accuracy": accuracy_score(true, pred),
        "precision": precision_score(true, pred, zero_division=0),
        "recall": recall_score(true, pred, zero_division=0),
        "sharpe": returns.mean() / returns.std() * np.sqrt(252)
        if returns.std() > 0
        else 0,
    }


def get_stock_data(code: str, days: int = 500) -> pd.DataFrame:
    """获取股票数据（模拟）"""
    np.random.seed(hash(code) % 2**32)
    dates = pd.date_range(end=datetime.now(), periods=days, freq="B")

    # 模拟价格走势（带趋势）
    trend = np.linspace(0, 0.3, days)  # 上涨趋势
    noise = np.random.randn(days) * 0.02
    returns = trend / days + noise
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


def analyze_stock(code: str):
    """分析单只股票，对比所有模型"""
    print(f"\n{'=' * 70}")
    print(f"股票代码: {code}")
    print("=" * 70)

    # 获取数据
    df = get_stock_data(code)
    print(f"数据范围: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"数据行数: {len(df)}")

    # 构建特征和标签
    features = build_features(df)
    labels = (df["close"].pct_change(5).shift(-5) > 0).astype(int)

    print(f"\n特征数量: {len(features.columns)}")

    # 测试所有模型
    results = {}

    models = [
        ("随机森林 (sklearn)", "random_forest", walk_forward_sklearn),
        ("梯度提升 (sklearn)", "gradient_boosting", walk_forward_sklearn),
        ("逻辑回归 (sklearn)", "ridge", walk_forward_sklearn),
        ("XGBoost", "xgboost", walk_forward_xgboost),
        ("LSTM (PyTorch)", "lstm", walk_forward_lstm),
    ]

    for name, model_type, func in models:
        print(f"\n训练 {name}...")

        try:
            if model_type == "lstm":
                signals = func(features, labels)
            elif model_type == "xgboost":
                signals = func(features, labels)
            else:
                signals = func(features, labels, model_type)

            metrics = calculate_metrics(signals, labels)
            results[name] = {
                "signal": signals.iloc[-1],
                "metrics": metrics,
                "signals": signals,
            }

            print(f"  准确率: {metrics['accuracy']:.1%}")
            print(f"  精确率: {metrics['precision']:.1%}")
            print(f"  召回率: {metrics['recall']:.1%}")
            print(f"  夏普比: {metrics['sharpe']:.2f}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # 对比结果
    print(f"\n{'=' * 70}")
    print("模型对比结果")
    print("=" * 70)
    print(f"{'模型':<25} {'信号':<10} {'准确率':<10} {'精确率':<10} {'夏普比':<10}")
    print("-" * 70)

    for name, result in sorted(
        results.items(), key=lambda x: x[1]["metrics"]["accuracy"], reverse=True
    ):
        sig = result["signal"]
        m = result["metrics"]
        sig_desc = "看多" if sig > 0.3 else ("看空" if sig < -0.3 else "中性")
        print(
            f"{name:<25} {sig:+.3f}({sig_desc}) {m['accuracy']:.1%}     {m['precision']:.1%}     {m['sharpe']:.2f}"
        )

    # 最佳模型
    if results:
        best_model = max(results.items(), key=lambda x: x[1]["metrics"]["accuracy"])
        print(
            f"\n最佳模型: {best_model[0]} (准确率 {best_model[1]['metrics']['accuracy']:.1%})"
        )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="增强版ML策略对比")
    parser.add_argument("--stock", type=str, default="600519", help="股票代码")
    parser.add_argument("--stocks", type=str, help="多个股票代码，逗号分隔")

    args = parser.parse_args()

    if args.stocks:
        for stock in args.stocks.split(","):
            analyze_stock(stock.strip())
    else:
        analyze_stock(args.stock)
