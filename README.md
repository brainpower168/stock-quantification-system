# 炒股大师量化交易系统

[![Version](https://img.shields.io/badge/version-3.0.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Python](https://img.shields.io/badge/python-3.7+-blueviolet)]()

多因子选股、持仓监控、情绪分析、回测验证、AI多模型决策于一体的量化交易系统。

## 系统架构

```
量化系统 v3.0
├── 数据层：DuckDB存储、数据缓存
├── 因子层：205个因子库
├── 策略层：智能选股、行业对冲
├── 分析层：热点监控、市场状态检测
├── 回测层：高性能回测引擎（JIT加速）
├── 决策层：增强版AI决策系统
└── 交易层：实盘交易接口（预留）
```

## 核心功能

### 基础功能
- **每日选股** - 问财+妙想+AI投票，Top N推荐
- **持仓监控** - 止损/止盈预警，DDX退出信号
- **情绪分析** - 恐贪指数、涨跌停比、北向资金、板块热度
- **回测验证** - 验证策略胜率、最大回撤、夏普比率
- **高收益策略** - 涨停板接力、龙头分歧转一致、事件驱动
- **HTTP API** - 提供RESTful API，方便其他系统调用
- **Python客户端** - 提供Python客户端库，方便集成

### AI Trading Council (v2.0新增)
- **多AI模型投票** - LongCat、讯飞星火、智谱GLM等多模型协同决策
- **记忆系统** - Hindsight记忆集成，从交易中学习
- **交易编排器** - 选股→AI决策→风控检查→执行交易，一键运行
- **数据缓存** - 减少API调用，提升效率
- **多数据源验证** - 国信、妙想、问财、腾讯财经多方对比
- **表现跟踪** - 策略表现追踪，因子有效性分析

### v3.0 新增功能
- **热点事件监控** - 30秒实时刷新，智能影响深度判定
- **高性能回测引擎** - JIT加速，59万条/秒
- **市场状态检测** - 波动率、趋势强度、市场状态识别
- **增强版AI决策** - 四步决策流程，5级评级输出
- **行业对冲策略** - 智能行业配对，风险对冲建议
- **DuckDB数据存储** - 高性能列式存储，亚秒级查询

## 安装

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

## 快速开始

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

### 3. 量化系统 v3.0 使用

```python
from quant_system.quant_system import QuantSystem

# 创建系统实例
system = QuantSystem()

# 单股分析
result = system.analyze_stock("600519", industry="白酒")
print(f"评级: {result['decision']['rating']}")
print(f"置信度: {result['decision']['confidence']:.0%}")

# 批量筛选
df = system.screen_stocks(["600519", "000001", "300750"], top_n=10)

# 组合分析
positions = [
    {"stock_code": "600519", "stock_name": "贵州茅台", "industry": "白酒", "position_value": 100000},
    {"stock_code": "300750", "stock_name": "宁德时代", "industry": "新能源", "position_value": 120000},
]
portfolio_result = system.analyze_portfolio(positions)

# 热点事件
events = system.get_hot_events(limit=20)
```

### 4. 启动API服务

```bash
# 安装API依赖
pip install fastapi uvicorn

# 启动服务
uvicorn api.quant_api:app --host 0.0.0.0 --port 8000 --reload
```

## 数据源配置

| 优先级 | 数据源 | 用途 | API Key环境变量 | 调用限制 |
|--------|--------|------|-----------------|----------|
| 1 | 妙想 | DDX、资金流向、选股 | MX_APIKEY | 无限制 |
| 2 | 问财 | DDX、资金流向、选股 | IWENCAI_API_KEY | 每日有限 |
| 3 | 国信 | 实时行情、财务数据 | GS_API_KEY | 无限制 |
| 4 | 腾讯财经 | 实时股价 | 无需 | 无限制 |

### 多数据源对比策略

重要决策时，系统会自动调用多个数据源对比验证：

- **买入前**：妙想+国信对比资金流向，腾讯+westockdata对比股价
- **卖出前**：妙想看每日明细，westockdata看技术位
- **选股**：国信+问财对比结果

## 策略系统

### 自适应策略
- 震荡市 → 均值回归策略（布林带）
- 牛市 → 趋势策略（MA金叉）
- 熊市 → 风控策略（空仓）

### 实战策略
- 尾盘30分钟选股
- 2560战法
- 一夜持股法
- 最笨交易法
- 麻雀战法
- 突破信号策略
- 题材炒作策略

## 风控系统

- 单股最大仓位：20%
- 止损比例：5%
- 止盈比例：10%
- 行业集中度监控
- 组合风险评估

## 测试

```bash
# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=quant_system --cov-report=html
```

## 项目结构

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
│   ├── quant_system.py          # 🆕 统一入口
│   ├── hot_event_monitor.py     # 🆕 热点监控
│   ├── high_performance_backtest.py  # 🆕 高性能回测
│   ├── market_state_detector.py # 🆕 市场状态检测
│   ├── enhanced_ai_decision.py  # 🆕 增强版AI决策
│   ├── industry_hedge_strategy.py  # 🆕 行业对冲
│   ├── duckdb_storage.py        # 🆕 DuckDB存储
│   └── ai_council/              # AI Trading Council
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

## 更新日志

### v3.0 (2026-05-04)
- 新增热点事件监控系统
- 新增高性能回测引擎（JIT加速）
- 新增市场状态检测
- 新增增强版AI决策系统
- 新增行业对冲策略
- 新增DuckDB数据存储
- 统一量化系统入口

### v2.0
- 新增AI Trading Council多模型投票
- 新增Hindsight记忆系统
- 新增交易编排器
- 新增数据缓存
- 新增多数据源验证

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- 问财API提供金融数据
- 妙想API提供资金流向数据
- FastAPI提供API框架
- Hindsight提供记忆系统框架

---

**免责声明**：本系统仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
