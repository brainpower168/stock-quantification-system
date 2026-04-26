# 炒股大师量化交易系统

[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Python](https://img.shields.io/badge/python-3.7+-blueviolet)]()

多因子选股、持仓监控、情绪分析、回测验证于一体的量化交易系统。

## ✨ 功能特性

- **每日选股** - 问财+妙想+AI投票，Top N推荐
- **持仓监控** - 止损/止盈预警，DDX退出信号
- **情绪分析** - 恐贪指数、涨跌停比、北向资金、板块热度
- **回测验证** - 验证策略胜率、最大回撤、夏普比率
- **高收益策略** - 涨停板接力、龙头分歧转一致、事件驱动
- **HTTP API** - 提供RESTful API，方便其他系统调用
- **Python客户端** - 提供Python客户端库，方便集成

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

### 方式二：直接使用

```bash
# 不安装，直接调用脚本
python quant_system/daily_picker.py --top-n 3
```

## 🚀 快速开始

### 1. 作为Python包使用

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

# 策略回测
backtester = Backtester()
result = backtester.run(strategy="limit_up", params={"holding_period": 5})
validation = backtester.validate_strategy(strategy="limit_up")
print(f"回测结果: {result}")
print(f"验证结果: {validation}")
```

### 2. 启动API服务

```bash
# 安装API依赖
pip install fastapi uvicorn

# 启动服务
cd api
python quant_api.py

# 或者从项目根目录启动
uvicorn api.quant_api:app --host 0.0.0.0 --port 8000 --reload
```

API服务启动后，可以访问：
- Swagger文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

### 3. 使用Python客户端

```python
from client.quant_client import QuantClient

# 创建客户端
client = QuantClient(base_url="http://localhost:8000")

# 健康检查
health = client.health_check()
print(f"健康检查: {health}")

# 获取每日选股
picks = client.get_daily_picks(top_n=3)
print(f"每日选股: {picks}")

# 检查持仓
positions = [
    {"symbol": "603931", "cost": 32.00, "shares": 1000, "current_price": 31.50}
]
alerts = client.check_positions(positions)
print(f"持仓预警: {alerts}")

# 获取市场情绪
sentiment = client.get_sentiment()
print(f"市场情绪: {sentiment}")

# 运行回测
backtest = client.run_backtest(strategy="limit_up", params={"holding_period": 5})
print(f"回测结果: {backtest}")
```

## 📖 API文档

启动API服务后，访问 http://localhost:8000/docs 查看完整的API文档（Swagger UI）。

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/daily-pick` | POST | 每日选股 |
| `/api/check-positions` | POST | 批量检查持仓 |
| `/api/sentiment` | GET | 市场情绪分析 |
| `/api/backtest` | POST | 策略回测 |
| `/api/health` | GET | 健康检查 |

## 🛠️ 配置

配置文件位于 `config/` 目录（如果需要）：

```python
# config/default.py
DEFAULT_CONFIG = {
    'daily_pick': {
        'top_n': 3,
        'min_score': 60.0,
        'weights': {
            'ddx': 0.30,
            'momentum': 0.20,
            'trend': 0.15,
            'fundamental': 0.15,
            'sentiment': 0.10,
            'event': 0.10
        }
    },
    'position_monitor': {
        'stop_loss': -3.0,
        'stop_profit': 10.0,
        'trailing_stop': 2.0,
        'ddx_exit_threshold': -2.0
    },
    'sentiment': {
        'fear_greed_threshold': 70,
        'limit_up_threshold': 50,
        'north_bound_threshold': 100
    },
    'backtest': {
        'start_date': '2020-01-01',
        'end_date': '2025-12-31',
        'initial_capital': 100000,
        'commission': 0.0003,
        'slippage': 0.001
    }
}
```

## 🧪 测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=quant_system --cov-report=html
```

## 🤝 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📧 联系方式

- 作者：炒股大师
- 邮箱：your-email@example.com
- Gitee：[@brainpower168](https://gitee.com/brainpower168)

## 🙏 致谢

- 问财API提供金融数据
- 妙想API提供资金流向数据
- FastAPI提供API框架

---

**⚠️ 免责声明**：本系统仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。