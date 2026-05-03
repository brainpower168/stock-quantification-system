# TradingAgents 对接配置指南

## 网络要求

TradingAgents系统需要访问以下外部API：

| API | 用途 | 地址 |
|-----|------|------|
| 讯飞星火 | LLM决策 | `https://spark-api-open.lingxi.com` |
| 智谱GLM | LLM决策 | `https://open.bigmodel.cn` |
| LongCat | LLM决策 | `https://api.longcat.chat` |
| 妙想 | DDX/资金流向 | `https://api.miaoxiang365.com` |
| 问财 | 选股/财务 | 需要配置 |
| 国信 | 实时行情 | 需要配置 |

## 当前环境状态

```
✗ 讯飞星火API: 无法连接（DNS解析失败）
✗ 妙想API: 无法连接（连接被拒绝）
✗ 网络代理: 未配置
```

## 解决方案

### 方案1：配置网络代理

```bash
# 设置代理
export HTTP_PROXY="http://your-proxy:port"
export HTTPS_PROXY="http://your-proxy:port"
export ALL_PROXY="socks5://your-proxy:port"
```

### 方案2：使用本地LLM

如果无法访问外部API，可以使用本地LLM：

```python
# 使用Ollama本地模型
from langchain_community.llms import Ollama

llm = Ollama(model="qwen2.5:7b")
```

### 方案3：使用模拟数据测试

已创建模拟测试脚本：
- `agents/test_trading_agents.py` - 使用MockLLM测试

## API Key配置

### 讯飞星火

```bash
# 格式：appid:api_key:api_secret
export XUNFEI_API_KEY="your_appid:your_api_key:your_api_secret"
```

### 智谱GLM

```bash
export ZHIPU_API_KEY="your_api_key"
```

### LongCat

```bash
export LONGCAT_API_KEY="your_api_key"
```

### 妙想

```bash
export MX_APIKEY="mkt_xxxxx"
```

### 问财

```bash
export IWENCAI_API_KEY="sk-proj-xxxxx"
```

### 国信

```bash
export GS_API_KEY="your_api_key"
```

## 使用方法

### 1. 完整对接（需要网络）

```bash
# 确保网络可用
python agents/trading_agents_live.py
```

### 2. 模拟测试（无需网络）

```bash
# 使用MockLLM测试
python agents/test_trading_agents.py
```

### 3. 自定义配置

```python
from agents.trading_agents_live import TradingAgentsLive

# 创建系统
live_system = TradingAgentsLive()

# 初始化
live_system.initialize()

# 分析股票
result = live_system.analyze_stock("600519")
print(result['report'])
```

## 已完成的工作

### 核心代码

| 文件 | 说明 | 行数 |
|------|------|------|
| `agents/trading_agents_system.py` | 核心系统（多空辩论、风控辩论） | 447 |
| `agents/trading_agents_integration.py` | 集成脚本 | 182 |
| `agents/trading_agents_live.py` | 实盘对接 | 460 |
| `agents/test_trading_agents.py` | 模拟测试 | 240 |

### 功能特性

- ✅ 多空辩论机制（多头 vs 空头）
- ✅ 风控辩论机制（激进 vs 保守 vs 中立）
- ✅ 5级评级系统（Buy/Overweight/Hold/Underweight/Sell）
- ✅ 结构化输出（Pydantic模型）
- ✅ 数据源对接（妙想、问财、国信）
- ✅ LLM对接（讯飞、智谱、LongCat）
- ✅ 模拟测试（MockLLM）

### 待完成

- ⏳ 网络配置（代理或VPN）
- ⏳ 真实LLM测试
- ⏳ 真实数据源测试
- ⏳ 整合到smart_selector.py
- ⏳ 历史回测

## 故障排除

### 问题1：DNS解析失败

```
Failed to resolve 'spark-api-open.lingxi.com'
```

**解决方案**：
1. 检查网络连接
2. 配置DNS服务器（如8.8.8.8）
3. 使用代理

### 问题2：连接被拒绝

```
Connection refused
```

**解决方案**：
1. 检查防火墙设置
2. 确认API地址正确
3. 使用代理

### 问题3：API Key无效

```
AppIdNoAuthError
```

**解决方案**：
1. 检查API Key格式
2. 确认API Key未过期
3. 联系API提供商

## 下一步

1. **配置网络**：确保能访问外部API
2. **测试LLM**：验证讯飞/智谱/LongCat API
3. **测试数据源**：验证妙想/问财/国信 API
4. **整合选股**：将TradingAgents整合到smart_selector.py
5. **回测验证**：对比多空辩论 vs 单模型决策的效果

---

**创建时间**: 2026-05-03
**状态**: 代码完成，等待网络配置
