# 炒股大师量化交易系统

[![Version](https://img.shields.io/badge/version-2.0.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Python](https://img.shields.io/badge/python-3.7+-blueviolet)]()

多因子选股、持仓监控、情绪分析、回测验证、AI多模型决策于一体的量化交易系统。

## ✨ 功能特性

### 基础功能
- **每日选股** - 问财+妙想+AI投票，Top N推荐
- **持仓监控** - 止损/止盈预警，DDX退出信号
- **情绪分析** - 恐贪指数、涨跌停比、北向资金、板块热度
- **回测验证** - 验证策略胜率、最大回撤、夏普比率
- **高收益策略** - 涨停板接力、龙头分歧转一致、事件驱动
- **HTTP API** - 提供RESTful API，方便其他系统调用
- **Python客户端** - 提供Python客户端库，方便集成

### 🆕 AI Trading Council (v2.0新增)
- **多AI模型投票** - LongCat、讯飞星火、智谱GLM等多模型协同决策
- **记忆系统** - Hindsight记忆集成，从交易中学习
- **交易编排器** - 选股→AI决策→风控检查→执行交易，一键运行
- **数据缓存** - 减少API调用，提升效率
- **多数据源验证** - 国信、妙想、问财、腾讯财经多方对比
- **表现跟踪** - 策略表现追踪，因子有效性分析

## 📦 安装

### 方式一：从源码安装（推荐）

```bash
# 克隆仓库
git clone https://gitee.com/brainpower168/stock-quantification-system.git
cd stock-quantification-system

# 安装依赖
pip install -r requirements.txt

# 以可编辑模式安装（开发时推荐）
pip install -e .
```

### 方式二：配置API Keys

```bash
# 复制环境变量模板
cp templates/.env.example .env

# 编辑 .env 文件，填入你的 API Keys
# 必需：LONGCAT_API_KEY, XUNFEI_API_KEY, GLM_API_KEY
# 数据源：GS_API_KEY, MX_APIKEY, IWENCAI_API_KEY
```

## 🚀 快速开始

### 1. 基础功能使用

```python
from quant_system import DailyPicker, PositionMonitor, SentimentAnalyzer, Backtester

# 每日选股
picker = DailyPicker()
picks = picker.pick(top_n=3, min_score=60)
print(f"今日推荐: {picks}")

# 持仓监控
positions = [
    {"symbol": "603931", "cost": 32.00, "shares": 1000, "current_price": 31.50}
]
monitor = PositionMonitor()
alerts = monitor.check(positions)
print(f"持仓预警: {alerts}")

# 情绪分析
analyzer = SentimentAnalyzer()
sentiment = analyzer.analyze()
suggestion = analyzer.get_trading_suggestion()
print(f"市场情绪: {sentiment}")
print(f"操作建议: {suggestion}")
```

### 2. AI Trading Council 使用

```python
from quant_system.ai_council import TradingCouncil, TradingOrchestrator

# 单股AI分析
council = TradingCouncil()
result = council.run_council_analysis("600519")
print(f"共识决策: {result['consensus']}")
print(f"置信度: {result['confidence']:.2f}")

# 完整交易流程
orchestrator = TradingOrchestrator()
result = orchestrator.run(mode="daily")
print(f"交易信号: {result['signals']}")

# 查看股票记忆
memory = council.get_stock_memory("600519")
print(f"历史经验: {memory['experiences']}")

# 反思交易表现
insights = council.reflect_on_performance(days=30)
print(f"洞察: {insights}")
```

### 3. 启动API服务

```bash
# 安装API依赖
pip install fastapi uvicorn

# 启动服务
uvicorn api.quant_api:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 AI Trading Council API

### 命令行使用

```bash
# 单股分析
python -m quant_system.ai_council.council_engine --stock 600519

# 批量分析
python -m quant_system.ai_council.council_engine --stocks 600519,000001,300750

# 查看决策历史
python -m quant_system.ai_council.council_engine --history --days 7

# 查看股票记忆
python -m quant_system.ai_council.council_engine --memory --stock 600519

# 反思交易表现
python -m quant_system.ai_council.council_engine --reflect --days 30

# 运行交易编排器
python -m quant_system.ai_council.trading_orchestrator --mode daily
```

### 配置文件

AI Council 配置文件位于 `config/council_config.example.json`：

```json
{
  "models": {
    "longcat": {
      "enabled": true,
      "api_key_env": "LONGCAT_API_KEY",
      "role": "quant_expert",
      "weight": 1.0
    },
    "xunfei": {
      "enabled": true,
      "api_key_env": "XUNFEI_API_KEY",
      "role": "fundamental_analyst",
      "weight": 1.2
    },
    "glm": {
      "enabled": true,
      "api_key_env": "GLM_API_KEY",
      "role": "technical_analyst",
      "weight": 1.0
    }
  },
  "decision_weights": {
    "capital_flow": 0.35,
    "technical_indicators": 0.30,
    "fundamental": 0.15,
    "sector_momentum": 0.12,
    "market_sentiment": 0.08
  }
}
```

## 🛠️ 数据源配置

| 数据源 | 用途 | API Key环境变量 |
|--------|------|-----------------|
| 国信证券 | 行情、财务、选股 | GS_API_KEY |
| 妙想 | 资金流向（最详细） | MX_APIKEY |
| 问财 | 智能选股 | IWENCAI_API_KEY |
| 腾讯财经 | 实时股价 | 无需 |

### 多数据源对比策略

重要决策时，系统会自动调用多个数据源对比验证：

- **买入前**：妙想+国信对比资金流向，腾讯+westockdata对比股价
- **卖出前**：妙想看每日明细，westockdata看技术位
- **选股**：国信+问财对比结果

## 🧪 测试

```bash
# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=quant_system --cov-report=html
```

## 📁 项目结构

```
stock-quantification-system/
├── quant_system/
│   ├── __init__.py
│   ├── daily_picker.py          # 每日选股
│   ├── position_monitor.py      # 持仓监控
│   ├── sentiment_analyzer.py    # 情绪分析
│   ├── backtest_engine.py       # 回测引擎
│   ├── risk_manager.py          # 风控系统
│   ├── data_sources.py          # 数据源封装
│   └── ai_council/              # 🆕 AI Trading Council
│       ├── __init__.py
│       ├── council_engine.py    # AI多模型投票
│       ├── hindsight_memory.py  # 记忆系统
│       ├── trading_orchestrator.py  # 交易编排器
│       ├── data_cache.py        # 数据缓存
│       ├── performance_tracker.py   # 表现跟踪
│       └── ...
├── config/
│   └── council_config.example.json  # AI Council配置模板
├── templates/
│   └── .env.example             # 环境变量模板
├── api/
│   └── quant_api.py             # HTTP API
├── client/
│   └── quant_client.py          # Python客户端
└── tests/                       # 测试
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 问财API提供金融数据
- 妙想API提供资金流向数据
- FastAPI提供API框架
- Hindsight提供记忆系统框架

---

**⚠️ 免责声明**：本系统仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
