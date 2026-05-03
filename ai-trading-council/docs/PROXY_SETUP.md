# 代理配置指南

## 问题

外部API（讯飞、妙想、问财、智谱）需要代理才能访问。

## 解决方案

### 方案一：使用系统代理（推荐）

1. **启动代理软件**（如Clash、V2Ray、Shadowsocks等）

2. **设置环境变量**：
```bash
# Windows CMD
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890

# Windows PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# Linux/Mac
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

3. **验证代理**：
```bash
curl -I https://api.miaoxiang365.com
```

### 方案二：在代码中配置代理

在 `trading_agents_live.py` 中设置：

```python
import os
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
```

### 方案三：使用千帆代理

千帆代理已配置：`http://127.0.0.1:51353/api/qianfanproxy/`

但需要确认支持的模型。

## 常见代理端口

| 软件 | 默认端口 |
|------|----------|
| Clash | 7890 |
| V2Ray | 10808 |
| Shadowsocks | 1080 |
| SSR | 1087 |

## 测试API连接

```bash
# 测试妙想API
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.miaoxiang365.com/api/v1/stock/quote?code=600519

# 测试讯飞API
curl -X POST https://spark-api-open.lingxi.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"spark-lite","messages":[{"role":"user","content":"你好"}]}'
```

## 当前状态

- ✅ 千帆代理可用（但模型有限）
- ❌ 外部API需要代理
- ⏳ 等待用户配置代理
