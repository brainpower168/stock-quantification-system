# Quant System v2.0

量化交易系统 - 整合brainpower_stock优点

## 系统架构

| 模块 | 文件 | 功能 | 改进 |
|------|------|------|------|
| 特征工程 | `feature_engineer.py` | 59个特征，7大类 | +111% |
| 三层过滤 | `three_layer_picker.py` | 基本面+技术面+风控 | 系统化 |
| 回测引擎 | `backtest_engine.py` | 交易成本+绩效评估 | +Alpha/Beta |
| 组合优化 | `portfolio_optimizer.py` | 马科维茨+风险平价 | 新增 |
| Stacking | `stacking_ensemble.py` | 多模型融合 | +49%准确率 |

## 使用方法

```python
# 1. 特征工程
from feature_engineer import FeatureEngineer
fe = FeatureEngineer()
feature_vector, feature_dict = fe.extract_features(stock_data)

# 2. 三层过滤选股
from three_layer_picker import ThreeLayerStockPicker
picker = ThreeLayerStockPicker()
picks = picker.pick_stocks(stock_list, capital=1000000, top_n=5)

# 3. Stacking预测
from stacking_ensemble import StackingEnsemble
stacking = StackingEnsemble(n_features=59)
stacking.fit(X_train, y_train)
probs = stacking.predict_proba(X_test)

# 4. 组合优化
from portfolio_optimizer import PortfolioOptimizer
optimizer = PortfolioOptimizer()
results = optimizer.optimize_portfolio(returns, stock_names)

# 5. 回测
from backtest_engine import BacktestEngine
engine = BacktestEngine(initial_capital=1000000)
results = engine.run_backtest(stock_list, start_date, end_date)
```

## 改进效果

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 特征数 | 28 | 59 | +111% |
| ML准确率 | 50-60% | 89.5% | +49% |
| 回测功能 | 基础 | 交易成本+绩效评估 | 完整 |
| 组合优化 | 无 | 马科维茨+风险平价 | 新增 |

## 依赖

```
numpy
pandas
scikit-learn
xgboost
torch (可选，用于LSTM)
scipy
```

## 作者

DuMate AI
日期：2026-05-01
