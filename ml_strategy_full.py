#!/usr/bin/env python3
"""
完整版机器学习策略系统
- 真实数据（Baostock - 免费）
- DDX + 主力资金因子
- 多模型对比（sklearn/XGBoost/LSTM）
- 回测验证
"""

import sys
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import baostock as bs

# ML库
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score

# XGBoost
import xgboost as xgb

# PyTorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 用户自选股
WATCHLIST = [
    ("sh.601138", "工业富联"),
    ("sz.002475", "立讯精密"),
    ("sz.002460", "赣锋锂业"),
    ("sz.002281", "光迅科技"),
    ("sz.002463", "沪电股份"),
    ("sz.300750", "宁德时代"),
    ("sz.300476", "胜宏科技"),
    ("sz.000988", "华工科技"),
]


class BaostockFetcher:
    """Baostock数据获取器（免费）"""

    def __init__(self):
        # 登录baostock
        self.lg = bs.login()
        print(f"Baostock登录: {self.lg.error_msg}")

    def get_kline(self, code: str, days: int = 500) -> Optional[pd.DataFrame]:
        """获取日K线数据"""
        try:
            # 计算日期范围
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime(
                "%Y-%m-%d"
            )

            # 获取K线数据
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",  # 2=前复权
            )

            if rs.error_code != "0":
                print(f"[ERROR] {rs.error_msg}")
                return None

            # 转换为DataFrame
            data_list = []
            while (rs.error_code == "0") & rs.next():
                data_list.append(rs.get_row_data())

            if len(data_list) == 0:
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 转换数据类型
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            for col in [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "turn",
                "pctChg",
            ]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.rename(
                columns={
                    "turn": "turnover",
                    "pctChg": "change_pct",
                }
            )

            # 只取最近N天
            if len(df) > days:
                df = df.tail(days)

            return df

        except Exception as e:
            print(f"[ERROR] 获取K线失败 {code}: {e}")
            return None

    def get_money_flow(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """获取资金流向数据"""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime(
                "%Y-%m-%d"
            )

            # 获取资金流向
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,peTTM,pbMRQ,psTTM,pcfNcfTTM",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
            )

            if rs.error_code != "0":
                return None

            data_list = []
            while (rs.error_code == "0") & rs.next():
                data_list.append(rs.get_row_data())

            if len(data_list) == 0:
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            return df

        except Exception as e:
            return None

    def get_stock_data(self, code: str, days: int = 500) -> pd.DataFrame:
        """获取完整数据"""
        df = self.get_kline(code, days)

        if df is None:
            return None

        # 模拟主力资金（基于成交量变化）
        # 真实DDX需要付费数据源
        df["main_inflow"] = df["volume"].pct_change() * df["close"] * df["volume"] * 0.1
        df["main_inflow"] = df["main_inflow"].fillna(0)

        return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """构建特征矩阵（28个特征）"""
    c = df["close"]
    v = df["volume"]
    ret = c.pct_change()

    features = pd.DataFrame(index=df.index)

    # ========== 价格动量特征 (4个) ==========
    features["f_ret_1d"] = ret
    features["f_ret_5d"] = c.pct_change(5)
    features["f_ret_10d"] = c.pct_change(10)
    features["f_ret_20d"] = c.pct_change(20)

    # ========== 波动特征 (3个) ==========
    features["f_vol_5d"] = ret.rolling(5).std()
    features["f_vol_10d"] = ret.rolling(10).std()
    features["f_vol_20d"] = ret.rolling(20).std()

    # ========== 均线系统 (4个) ==========
    features["f_ma5_ratio"] = c / c.rolling(5).mean()
    features["f_ma10_ratio"] = c / c.rolling(10).mean()
    features["f_ma20_ratio"] = c / c.rolling(20).mean()
    features["f_ma60_ratio"] = c / c.rolling(60).mean()

    # ========== 量价关系 (2个) ==========
    features["f_volume_ratio"] = v / v.rolling(20).mean()
    features["f_turnover"] = (
        df["turnover"] if "turnover" in df.columns else v / v.rolling(20).mean()
    )

    # ========== 技术指标 (8个) ==========
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

    # ========== 主力资金特征 (5个) ==========
    if "main_inflow" in df.columns:
        features["f_main_inflow"] = df["main_inflow"]
        features["f_main_inflow_5d"] = df["main_inflow"].rolling(5).sum()
        features["f_main_inflow_10d"] = df["main_inflow"].rolling(10).sum()
        features["f_main_trend"] = df["main_inflow"].rolling(5).mean()
        features["f_main_ratio"] = df["main_inflow"] / (df["amount"] + 1) * 100
    else:
        features["f_main_inflow"] = 0
        features["f_main_inflow_5d"] = 0
        features["f_main_inflow_10d"] = 0
        features["f_main_trend"] = 0
        features["f_main_ratio"] = 0

    # ========== 日内特征 (2个) ==========
    features["f_high_low_ratio"] = (df["high"] - df["low"]) / c
    features["f_close_open_ratio"] = (c - df["open"]) / df["open"]

    # 清理inf
    features = features.replace([np.inf, -np.inf], np.nan)

    return features


def walk_forward_sklearn(features, labels, model_type="random_forest"):
    """sklearn模型训练"""
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
    """XGBoost训练"""
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
        lstm_out, _ = self.lstm(x)
        out = lstm_out[:, -1, :]
        out = self.fc(out)
        return out.squeeze()


def walk_forward_lstm(features, labels, seq_len=20):
    """LSTM训练"""
    predictions = pd.Series(0.0, index=features.index)
    min_train_size = 252 + seq_len
    retrain_freq = 20

    scaler = StandardScaler()
    features_scaled = pd.DataFrame(
        scaler.fit_transform(features), index=features.index, columns=features.columns
    )
    features_scaled = features_scaled.fillna(0)

    model = None

    for i in range(min_train_size, len(features)):
        if model is None or (i - min_train_size) % retrain_freq == 0:
            X_train = []
            y_train = []

            for j in range(seq_len, i):
                X_train.append(features_scaled.iloc[j - seq_len : j].values)
                y_train.append(labels.iloc[j])

            X_train = np.array(X_train)
            y_train = np.array(y_train)

            if len(X_train) < 50:
                continue

            X_tensor = torch.FloatTensor(X_train).to(device)
            y_tensor = torch.FloatTensor(y_train).to(device)

            model = LSTMModel(
                input_size=features.shape[1],
                hidden_size=64,
                num_layers=2,
                dropout=0.2,
            ).to(device)

            optimizer = optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.BCELoss()

            model.train()
            dataset = TensorDataset(X_tensor, y_tensor)
            loader = DataLoader(dataset, batch_size=32, shuffle=True)

            for epoch in range(10):
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()

        X_today = features_scaled.iloc[i - seq_len : i].values
        if np.isnan(X_today).any():
            continue

        X_tensor = torch.FloatTensor(X_today).unsqueeze(0).to(device)

        model.eval()
        with torch.no_grad():
            prob = model(X_tensor).item()

        predictions.iloc[i] = prob * 2 - 1

    return predictions.fillna(0.0).clip(-1.0, 1.0)


def backtest_strategy(df, signals, initial_capital=100000, commission=0.001):
    """回测策略"""
    signals = signals.reindex(df.index)
    close = df["close"]

    position = 0
    capital = initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(len(signals)):
        signal = signals.iloc[i]
        price = close.iloc[i]

        if signal > 0.3 and position == 0:
            shares = int(capital * 0.95 / price)
            cost = shares * price * (1 + commission)
            capital -= cost
            position = 1
            trades.append(
                {
                    "date": signals.index[i],
                    "type": "BUY",
                    "price": price,
                    "shares": shares,
                }
            )

        elif signal < -0.3 and position == 1:
            revenue = shares * price * (1 - commission)
            capital += revenue
            position = 0
            trades.append(
                {
                    "date": signals.index[i],
                    "type": "SELL",
                    "price": price,
                    "shares": shares,
                }
            )
            shares = 0

        equity = capital + shares * price
        equity_curve.append({"date": signals.index[i], "equity": equity})

    equity_df = pd.DataFrame(equity_curve).set_index("date")
    returns = equity_df["equity"].pct_change()

    total_return = (equity_df["equity"].iloc[-1] / initial_capital - 1) * 100
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    max_drawdown = (equity_df["equity"] / equity_df["equity"].cummax() - 1).min() * 100

    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "num_trades": len(trades) // 2,
        "equity_curve": equity_df,
    }


def analyze_stock(code: str, name: str, fetcher: BaostockFetcher):
    """分析单只股票"""
    print(f"\n{'=' * 70}")
    print(f"股票: {code} {name}")
    print("=" * 70)

    # 获取真实数据
    print("获取真实数据...")
    df = fetcher.get_stock_data(code, days=500)

    if df is None or len(df) < 300:
        print(f"[ERROR] 数据不足")
        return None

    print(f"数据范围: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"数据行数: {len(df)}")
    print(f"最新价格: {df['close'].iloc[-1]:.2f}")

    # 构建特征
    features = build_features(df)
    labels = (df["close"].pct_change(5).shift(-5) > 0).astype(int)

    print(f"\n特征数量: {len(features.columns)}")

    # 训练模型
    results = {}

    models = [
        ("随机森林", "random_forest", walk_forward_sklearn),
        ("XGBoost", "xgboost", walk_forward_xgboost),
        ("LSTM", "lstm", walk_forward_lstm),
    ]

    for model_name, model_type, func in models:
        print(f"\n训练 {model_name}...")

        try:
            if model_type == "lstm":
                signals = func(features, labels)
            elif model_type == "xgboost":
                signals = func(features, labels)
            else:
                signals = func(features, labels, model_type)

            backtest = backtest_strategy(df, signals)

            valid = signals != 0
            pred = (signals[valid] > 0).astype(int)
            true = labels[valid].astype(int)
            accuracy = accuracy_score(true, pred) if len(pred) > 0 else 0

            results[model_name] = {
                "signal": signals.iloc[-1],
                "accuracy": accuracy,
                "backtest": backtest,
            }

            print(f"  准确率: {accuracy:.1%}")
            print(f"  总收益: {backtest['total_return']:+.1f}%")
            print(f"  夏普比: {backtest['sharpe']:.2f}")
            print(f"  最大回撤: {backtest['max_drawdown']:.1f}%")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # 对比结果
    print(f"\n{'=' * 70}")
    print("模型对比")
    print("=" * 70)
    print(
        f"{'模型':<15} {'信号':<12} {'准确率':<10} {'总收益':<12} {'夏普比':<10} {'最大回撤':<10}"
    )
    print("-" * 70)

    for model_name, result in sorted(
        results.items(), key=lambda x: x[1]["backtest"]["sharpe"], reverse=True
    ):
        sig = result["signal"]
        sig_desc = "看多" if sig > 0.3 else ("看空" if sig < -0.3 else "中性")
        bt = result["backtest"]
        print(
            f"{model_name:<15} {sig:+.3f}({sig_desc}) {result['accuracy']:.1%}     {bt['total_return']:+.1f}%      {bt['sharpe']:.2f}     {bt['max_drawdown']:.1f}%"
        )

    return {
        "code": code,
        "name": name,
        "results": results,
    }


def main():
    """主函数"""
    print("=" * 70)
    print("机器学习策略系统 - 真实数据 + 回测验证")
    print("=" * 70)
    print(f"设备: {device}")
    print(f"数据源: Baostock（免费）")
    print(f"特征: 28个（含主力资金因子）")

    fetcher = BaostockFetcher()

    all_results = {}

    # 测试自选股
    for code, name in WATCHLIST[:4]:
        result = analyze_stock(code, name, fetcher)
        if result:
            all_results[code] = result

    # 总结
    print(f"\n{'=' * 70}")
    print("总结")
    print("=" * 70)

    for code, result in all_results.items():
        print(f"\n{result['name']} ({code}):")
        best = max(result["results"].items(), key=lambda x: x[1]["backtest"]["sharpe"])
        bt = best[1]["backtest"]
        print(f"  最佳模型: {best[0]}")
        print(
            f"  收益: {bt['total_return']:+.1f}%, 夏普: {bt['sharpe']:.2f}, 回撤: {bt['max_drawdown']:.1f}%"
        )


if __name__ == "__main__":
    main()
