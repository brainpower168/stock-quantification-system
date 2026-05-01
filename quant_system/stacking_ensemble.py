# -*- coding: utf-8 -*-
"""
量化交易系统 - Stacking集成学习模块 v2.0
升级：多模型融合 + 元学习器
作者：DuMate AI
日期：2026-05-01
功能：LSTM + XGBoost + RF + GB -> Stacking集成
"""

import numpy as np
import pandas as pd
from datetime import datetime
import os
import json
import warnings

warnings.filterwarnings("ignore")

# 导入sklearn
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

# 尝试导入XGBoost
try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("[Warning] XGBoost not installed, using GradientBoosting instead")

# 尝试导入PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset

    HAS_PYTORCH = True
except ImportError:
    HAS_PYTORCH = False
    print("[Warning] PyTorch not installed, LSTM will be skipped")


# ==================== LSTM模型 ====================
class LSTMModel(nn.Module):
    """LSTM模型"""

    def __init__(self, input_size, hidden_size=64, num_layers=2, output_size=1):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size, hidden_size, num_layers, batch_first=True, dropout=0.2
        )
        self.fc = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)

        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])  # 取最后一个时间步的输出
        out = self.sigmoid(out)
        return out


class LSTMClassifier:
    """LSTM分类器包装器"""

    def __init__(
        self, input_size, hidden_size=64, num_layers=2, epochs=50, batch_size=32
    ):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.epochs = epochs
        self.batch_size = batch_size
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def fit(self, X, y):
        """训练模型"""
        if not HAS_PYTORCH:
            return self

        # 转换数据形状 (n_samples, n_features) -> (n_samples, seq_len, n_features)
        X_seq = X.reshape(X.shape[0], 1, X.shape[1])

        # 转换为Tensor
        X_tensor = torch.FloatTensor(X_seq).to(self.device)
        y_tensor = (
            torch.FloatTensor(y.values if hasattr(y, "values") else y)
            .reshape(-1, 1)
            .to(self.device)
        )

        # 创建DataLoader
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        # 初始化模型
        self.model = LSTMModel(self.input_size, self.hidden_size, self.num_layers).to(
            self.device
        )
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        # 训练
        self.model.train()
        for epoch in range(self.epochs):
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

        return self

    def predict_proba(self, X):
        """预测概率"""
        if not HAS_PYTORCH or self.model is None:
            return np.column_stack([np.ones(len(X)) * 0.5, np.ones(len(X)) * 0.5])

        self.model.eval()
        with torch.no_grad():
            X_seq = X.reshape(X.shape[0], 1, X.shape[1])
            X_tensor = torch.FloatTensor(X_seq).to(self.device)
            probs = self.model(X_tensor).cpu().numpy()

        return np.column_stack([1 - probs.flatten(), probs.flatten()])


# ==================== Stacking集成学习器 ====================
class StackingEnsemble:
    """Stacking集成学习器"""

    def __init__(self, n_features):
        self.n_features = n_features
        self.base_models = {}
        self.meta_model = None
        self.scaler = StandardScaler()

        # 初始化基础模型
        self._init_base_models()

    def _init_base_models(self):
        """初始化基础模型"""
        # Random Forest
        self.base_models["rf"] = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )

        # Gradient Boosting
        self.base_models["gb"] = GradientBoostingClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
        )

        # XGBoost (如果可用)
        if HAS_XGBOOST:
            self.base_models["xgb"] = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss",
            )

        # LSTM (如果可用)
        if HAS_PYTORCH:
            self.base_models["lstm"] = LSTMClassifier(
                input_size=self.n_features, hidden_size=64, num_layers=2, epochs=50
            )

        # 元学习器
        self.meta_model = LogisticRegression(random_state=42)

    def fit(self, X, y):
        """
        训练Stacking模型
        :param X: 特征矩阵
        :param y: 标签
        :return: self
        """
        print(f"[Stacking Ensemble Training]")
        print(f"   Samples: {X.shape[0]}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Base Models: {list(self.base_models.keys())}")
        print()

        # 标准化
        X_scaled = self.scaler.fit_transform(X)

        # 划分训练集和验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        # 训练基础模型并生成元特征
        meta_features = np.zeros((X_val.shape[0], len(self.base_models)))

        for i, (name, model) in enumerate(self.base_models.items()):
            print(f"[Training {name.upper()}...]")

            try:
                model.fit(X_train, y_train)

                # 预测概率
                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(X_val)[:, 1]
                else:
                    probs = model.predict(X_val)

                meta_features[:, i] = probs

                # 计算验证集性能
                y_pred = (probs > 0.5).astype(int)
                acc = accuracy_score(y_val, y_pred)
                print(f"   Accuracy: {acc:.4f}")

            except Exception as e:
                print(f"   Error: {e}")
                meta_features[:, i] = 0.5

        print()

        # 训练元学习器
        print(f"[Training Meta-Learner (Logistic Regression)...]")
        self.meta_model.fit(meta_features, y_val)

        # 计算Stacking性能
        y_pred_stacking = self.meta_model.predict(meta_features)
        stacking_acc = accuracy_score(y_val, y_pred_stacking)
        print(f"   Stacking Accuracy: {stacking_acc:.4f}")
        print()

        # 重新训练基础模型在全部数据上
        print(f"[Retraining base models on full data...]")
        for name, model in self.base_models.items():
            try:
                model.fit(X_scaled, y)
            except:
                pass

        return self

    def predict_proba(self, X):
        """
        预测概率
        :param X: 特征矩阵
        :return: 概率数组
        """
        X_scaled = self.scaler.transform(X)

        # 生成元特征
        meta_features = np.zeros((X.shape[0], len(self.base_models)))

        for i, (name, model) in enumerate(self.base_models.items()):
            try:
                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(X_scaled)[:, 1]
                else:
                    probs = model.predict(X_scaled)
                meta_features[:, i] = probs
            except:
                meta_features[:, i] = 0.5

        # 元学习器预测
        return self.meta_model.predict_proba(meta_features)

    def predict(self, X):
        """预测类别"""
        probs = self.predict_proba(X)[:, 1]
        return (probs > 0.5).astype(int)

    def get_feature_importance(self):
        """获取特征重要性（基于RF和XGBoost）"""
        importance = {}

        if "rf" in self.base_models:
            try:
                importance["rf"] = self.base_models["rf"].feature_importances_
            except:
                pass

        if "xgb" in self.base_models and HAS_XGBOOST:
            try:
                importance["xgb"] = self.base_models["xgb"].feature_importances_
            except:
                pass

        return importance


# ==================== 数据生成器 ====================
class DataGenerator:
    """数据生成器"""

    @staticmethod
    def generate_classification_data(n_samples=1000, n_features=59, random_state=42):
        """生成分类数据"""
        np.random.seed(random_state)

        # 生成特征
        X = np.random.randn(n_samples, n_features) * 0.5 + 0.5

        # 生成标签（基于前30个特征）
        weights = np.ones(n_features)
        weights[:30] = 2.0

        logits = X @ weights
        probabilities = 1 / (1 + np.exp(-logits))
        y = (probabilities > 0.6).astype(int)

        # 添加噪声
        noise_mask = np.random.rand(n_samples) < 0.1
        y[noise_mask] = 1 - y[noise_mask]

        return X, y


# ==================== 主程序 ====================
def main():
    """主函数 - Stacking集成学习演示"""
    print("=" * 70)
    print("[Stacking Ensemble v2.0]")
    print("=" * 70)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 生成测试数据
    print("[Generating test data...]")
    X, y = DataGenerator.generate_classification_data(n_samples=1000, n_features=59)
    print(f"   Samples: {X.shape[0]}")
    print(f"   Features: {X.shape[1]}")
    print(f"   Positive Ratio: {y.sum() / len(y) * 100:.1f}%")
    print()

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"[Train/Test Split]")
    print(f"   Train: {X_train.shape[0]} samples")
    print(f"   Test: {X_test.shape[0]} samples")
    print()

    # 创建Stacking模型
    stacking = StackingEnsemble(n_features=X.shape[1])

    # 训练
    stacking.fit(X_train, y_train)

    # 测试
    print("[Testing on held-out data...]")
    y_pred = stacking.predict(X_test)
    y_proba = stacking.predict_proba(X_test)[:, 1]

    # 计算指标
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }

    print()
    print("=" * 70)
    print("[TEST RESULTS]")
    print("=" * 70)
    print(f"\nAccuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1_score']:.4f}")
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")

    print("\n" + "=" * 70)
    print("[OK] Stacking Ensemble test completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
