# 快速开始指南

## 系统优化概览

本次优化完成了 P0、P1、P2 三个优先级的 12 个核心任务，显著提升了系统的：

- ✅ **稳定性** - 统一异常处理、日志系统
- ✅ **性能** - 多级缓存、并发优化
- ✅ **可靠性** - 配置验证、单元测试
- ✅ **功能完善** - 连板股策略、数据库支持

---

## 1. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装 TA-Lib（技术指标库）
# Ubuntu/Debian:
sudo apt-get install libta-lib-dev

# macOS:
brew install ta-lib

# Windows: 下载预编译 wheel
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
```

## 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必需的 API Keys
# 必需项：IWENCAI_API_KEY, MX_APIKEY
# 可选项：LONGCAT_API_KEY, XUNFEI_API_KEY, GLM_API_KEY
```

## 3. 验证配置

```bash
# 验证配置是否正确
python -c "from quant_system.config_validator import check_config_with_exit; check_config_with_exit()"
```

## 4. 运行测试

```bash
# 运行单元测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_core.py -v
```

---

## 新功能使用

### 1. 日志系统

```python
from quant_system import get_logger

logger = get_logger('my_strategy')

logger.debug("调试信息")
logger.info("运行信息")
logger.warning("警告")
logger.error("错误")

# 交易日志
from quant_system.logger import log_trade, log_signal

log_trade(action='BUY', code='600519', price=1800.0, shares=100, reason='突破买入')
log_signal(signal_type='BUY', code='600519', score=85.5)
```

### 2. 缓存系统

```python
from quant_system import cached

@cached(ttl=3600)  # 缓存 1 小时
def fetch_stock_data(code: str):
    # 耗时操作
    return data

# 使用缓存管理器
from quant_system import cache_manager

cache_manager.set('key', 'value', ttl=3600)
value = cache_manager.get('key')

# 查看缓存统计
stats = cache_manager.get_stats()
print(stats)
```

### 3. 数据库支持

```python
from quant_system import init_database, get_database

# 初始化数据库
db = init_database(db_type='sqlite', db_path='data/quant_system.db')

# 添加交易日志
db.add_trade_log('BUY', '600519', 1800.0, 100, '突破买入')

# 更新持仓
db.update_position('600519', '贵州茅台', 100, 1800.0, 1900.0)

# 查询统计
stats = db.get_statistics()
print(stats)
```

### 4. 连板股策略

```python
from quant_system import LimitUpStrategy

strategy = LimitUpStrategy()

# 选股
stocks = strategy.select_stocks()

for stock in stocks:
    print(f"{stock['code']} - {stock['score']}分")

# 买入判断
decision = strategy.should_buy('600519', current_price=1850, yester_close=1800)
if decision['should_buy']:
    print(f"建议买入：{decision['reason']}")
```

### 5. 智能卖出检查清单

```python
from quant_system import SmartSellStrategy, SellChecklist

strategy = SmartSellStrategy()
checklist = SellChecklist()

# 添加检查项
checklist.add_check("主力资金检查", True)
checklist.add_check("技术趋势检查", False, "趋势向下")

# 获取结果
result = checklist.get_result()
print(f"通过率：{result['passed_count']}/{result['total_count']}")

# 是否卖出
should_sell = checklist.should_sell(critical_fail_count=2)
print(f"建议卖出：{should_sell}")
```

### 6. 异常处理

```python
from quant_system import (
    handle_exceptions,
    retry,
    validate_not_none,
    ValidationException,
)

@handle_exceptions(default_return=[])
def safe_fetch_data():
    # 异常时会返回空列表
    return fetch_data()

@retry(max_attempts=3, delay=1.0)
def call_api_with_retry():
    # 失败会自动重试 3 次
    return call_api()

@validate_not_none('code', 'price')
def buy_stock(code, price, shares=100):
    # 自动验证 code 和 price 不为 None
    return execute_buy(code, price, shares)
```

### 7. 配置验证

```python
from quant_system import validate_config, ConfigValidator

# 简单验证
if validate_config():
    print("配置验证通过")

# 详细报告
validator = ConfigValidator()
validator.validate_all()
report = validator.get_report()
print(f"错误数：{report['error_count']}")
print(f"警告数：{report['warning_count']}")
```

---

## API 服务启动

```bash
# 启动 API 服务
uvicorn api.quant_api:app --host 0.0.0.0 --port 8000 --reload

# 访问 Swagger UI
# http://localhost:8000/docs
```

---

## 模块说明

| 模块 | 文件 | 功能 | 版本 |
|------|------|------|------|
| **核心** | daily_picker.py | 每日选股 | v1.0 |
|  | position_monitor.py | 持仓监控 | v1.0 |
|  | sentiment_analyzer.py | 情绪分析 | v1.0 |
|  | backtest_engine.py | 回测引擎 | v1.0 |
|  | risk_manager.py | 风控系统 | v1.0 |
| **AI** | ai_council/ | AI 多模型决策 | v2.0 |
| **策略** | smart_sell_strategy.py | 智能卖出 | v2.0 |
|  | limit_up_strategy.py | 连板股策略 | ✨ v2.1 |
| **工具** | logger.py | 日志系统 | ✨ v2.1 |
|  | exceptions.py | 异常处理 | ✨ v2.1 |
|  | cache.py | 缓存系统 | ✨ v2.1 |
|  | database.py | 数据库支持 | ✨ v2.1 |
|  | config_validator.py | 配置验证 | ✨ v2.1 |

---

## 常见问题

### Q1: TA-Lib 安装失败

```bash
# Ubuntu/Debian
sudo apt-get install libta-lib-dev
pip install TA-Lib

# macOS
brew install ta-lib
pip install TA-Lib

# Windows
# 下载预编译 wheel: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.25‑cp39‑cp39‑win_amd64.whl
```

### Q2: 环境变量未生效

```bash
# 检查 .env 文件是否存在
ls -la .env

# 检查变量是否拼写正确
grep IWENCAI .env

# 在代码中打印验证
import os
print(os.getenv('IWENCAI_API_KEY'))
```

### Q3: 数据库初始化失败

```python
# 确保 data 目录存在
import os
os.makedirs('data', exist_ok=True)

# 检查文件权限
ls -la data/
```

### Q4: 缓存不生效

```python
# 检查缓存目录
from quant_system.cache import cache_manager
print(cache_manager.get_stats())

# 清除缓存
cache_manager.clear()
```

---

## 更新日志

### v2.1.0 (2026-05-03)

**新增功能:**
- ✨ 日志系统 - 统一日志记录
- ✨ 异常处理 - 专用异常类和装饰器
- ✨ 缓存系统 - 多级缓存（内存/文件/Redis）
- ✨ 数据库支持 - SQLite/PostgreSQL
- ✨ 配置验证 - 启动前检查
- ✨ 连板股策略 - 涨停基因分析

**优化改进:**
- 🔧 补全 requirements.txt
- 🔧 修复 TODO 数据源
- 🔧 添加单元测试
- 🔧 优化异常处理
- 🔧 完善卖出检查清单

**Bug 修复:**
- 🐛 修复 print 调用
- 🐛 修复数据源 TODO
- 🐛 修复配置缺失

---

## 获取帮助

- 📖 查看 [README.md](README.md) 了解完整功能
- 📝 查看 [OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md) 了解优化详情
- 🧪 运行 `pytest tests/ -v` 确保一切正常
- ❓ 遇到问题请查看 `LOG_FILE` 配置中的日志文件

---

*快速开始指南版本：v2.1.0*
*更新日期：2026-05-03*
