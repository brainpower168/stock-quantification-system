# 代码重构指南

## 重构目标

降低模块耦合，提升代码可维护性和可测试性。

## 重构原则

### 1. 单一职责原则 (SRP)
每个模块/类只负责一项职责。

**重构前:**
```python
class TradingSystem:
    def fetch_data(self): ...
    def analyze(self): ...
    def execute_trade(self): ...
    def send_notification(self): ...
```

**重构后:**
```python
class DataFetcher: ...
class Analyzer: ...
class TradeExecutor: ...
class Notifier: ...
```

### 2. 依赖注入 (DI)
避免硬编码依赖，使用依赖注入。

**重构前:**
```python
class Strategy:
    def __init__(self):
        self.db = Database()  # 硬编码
```

**重构后:**
```python
class Strategy:
    def __init__(self, db: Database):
        self.db = db  # 依赖注入
```

### 3. 接口隔离 (ISP)
使用 Protocol 定义接口。

```python
from typing import Protocol

class DataProvider(Protocol):
    def get_price(self, code: str) -> float: ...
    def get_volume(self, code: str) -> int: ...

class TencentAPI(DataProvider): ...
class IwencaiAPI(DataProvider): ...
```

### 4. 策略模式
将算法封装为独立策略。

```python
class SellStrategy(Protocol):
    def should_sell(self, position: dict) -> bool: ...

class StopLossStrategy: ...
class TakeProfitStrategy: ...
class TechnicalStrategy: ...
```

### 5. 观察者模式
事件通知系统。

```python
class EventBus:
    def subscribe(self, event: str, callback: Callable): ...
    def publish(self, event: str, data: dict): ...

# 使用
event_bus.subscribe('trade.executed', send_notification)
event_bus.publish('trade.executed', {'code': '600519'})
```

## 重构检查清单

- [ ] 函数长度 < 50 行
- [ ] 类复杂度 < 10
- [ ] 单元测试覆盖 > 80%
- [ ] 无重复代码 (DRY)
- [ ] 清晰的命名
- [ ] 完整的类型注解
- [ ] 文档字符串
- [ ] 异常处理完善

## 重构工具

```bash
# 代码格式化
black quant_system/

# 导入排序
isort quant_system/

# 代码检查
flake8 quant_system/
pylint quant_system/

# 复杂度分析
xenon quant_system/ --max-absolute C
```

## 重构步骤

1. **分析**: 识别代码异味
2. **测试**: 确保有足够测试覆盖
3. **小步**: 每次只做小的重构
4. **验证**: 测试通过再继续
5. **提交**: 及时提交重构成果

## 常见代码异味

- ❌ 过长函数 (>50 行)
- ❌ 过大类 (>500 行)
- ❌ 重复代码
- ❌ 过多的参数 (>5 个)
- ❌ 深层嵌套 (>3 层)
- ❌ 魔法数字
- ❌ 注释掉的代码
- ❌ 过紧的耦合
