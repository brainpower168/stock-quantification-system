# Type Hints for quant_system package

[Overview]
本文件定义量化系统核心模块的类型注解标准

[Type Aliases]
主要类型别名定义:

- `Dict[str, Any]` -> `DataDict`
- `Optional[str]` -> `MaybeStr`
- `Callable[..., bool]` -> `Validator`
- `Union[int, float]` -> `Numeric`
- `List[Dict[str, Any]]` -> `StockList`
- `Tuple[float, float]` -> `PriceRange`

[Examples]
类型注解使用示例:

```python
from typing import Dict, List, Optional, Union, Callable, Tuple, Any

# 类型别名
DataDict = Dict[str, Any]
MaybeStr = Optional[str]
Numeric = Union[int, float]
StockList = List[Dict[str, Any]]

# 函数签名
def analyze_stock(
    code: str,
    start_date: str,
    end_date: Optional[str] = None,
    threshold: float = 0.05
) -> Dict[str, Any]:
    """分析股票"""
    ...

# 类属性
class Strategy:
    def __init__(self) -> None:
        self.threshold: float = 0.05
        self.enabled: bool = True
        self.callbacks: List[Callable[[str], None]] = []
    
    def execute(self, code: str) -> Optional[Dict[str, Any]]:
        """执行策略"""
        return {'code': code}
```

[Common Patterns]
常用模式:

1. **Optional**: 参数可选
   ```python
   def fetch(code: str, api_key: Optional[str] = None) -> DataDict:
   ```

2. **Union**: 多种类型
   ```python
   def parse(value: Union[str, int, float]) -> Numeric:
   ```

3. **Callable**: 回调函数
   ```python
   def on_signal(callback: Callable[[str, float], None]) -> None:
   ```

4. **Generic**: 泛型
   ```python
   from typing import TypeVar, Generic
   
   T = TypeVar('T')
   
   class Cache(Generic[T]):
       def get(self, key: str) -> Optional[T]:
   ```

[Best Practices]
最佳实践:

1. 所有公共 API 必须添加类型注解
2. 函数返回值必须指定类型
3. 复杂类型使用类型别名简化
4. 使用 `Optional` 明确表示可能为 None
5. 使用 `Union` 明确表示多种可能类型
6. 使用 `Any` 仅在无法确定类型时
7. 使用 `@overload` 处理重载函数
8. 使用 `Protocol` 定义接口
