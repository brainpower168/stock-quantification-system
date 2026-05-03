# API 文档说明

## Swagger/OpenAPI

本系统使用 FastAPI 框架，自带 Swagger UI 和 ReDoc 文档。

### 访问文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API 端点

### 核心 API

#### 1. 健康检查

\`\`\`http
GET /api/v1/health
\`\`\`

响应:
\`\`\`json
{
  "status": "healthy",
  "version": "1.1.0"
}
\`\`\`

#### 2. 数据源状态

\`\`\`http
GET /api/v1/sources
\`\`\`

#### 3. 市场情绪

\`\`\`http
GET /api/v1/market/sentiment
\`\`\`

#### 4. 实时行情

\`\`\`http
POST /api/v1/quote/realtime
Content-Type: application/json

{
  "codes": ["sh600519", "sz000858"]
}
\`\`\`

### 选股 API

#### 每日选股

\`\`\`http
POST /api/v1/stock/pick
Content-Type: application/json

{
  "top_n": 3,
  "min_score": 60.0
}
\`\`\`

### AI Council API

#### AI 分析

\`\`\`http
POST /api/v1/ai/analyze
Content-Type: application/json

{
  "code": "600519",
  "include_memory": true
}
\`\`\`

### 持仓管理

#### 检查持仓

\`\`\`http
POST /api/v1/position/check
Content-Type: application/json

{
  "positions": [
    {
      "code": "600519",
      "cost": 1800.0,
      "shares": 100
    }
  ]
}
\`\`\`

## Python 客户端使用

\`\`\`python
from client.quant_client import QuantClient

# 创建客户端
client = QuantClient(base_url="http://localhost:8000")

# 健康检查
health = client.health_check()

# 获取每日选股
picks = client.get_daily_picks(top_n=3)

# 检查持仓
positions = client.check_positions([...])

# 获取市场情绪
sentiment = client.get_sentiment()
\`\`\`

## 错误处理

API 使用标准 HTTP 状态码:

- \`200\` - 成功
- \`400\` - 请求参数错误
- \`401\` - 未授权
- \`404\` - 资源不存在
- \`500\` - 服务器内部错误

错误响应格式:

\`\`\`json
{
  "detail": "错误信息"
}
\`\`\`

## 认证

目前 API 暂不需要认证。生产环境建议添加:
- API Keys
- JWT Token
- OAuth2

## 速率限制

建议生产环境添加速率限制:
- 普通用户：100 请求/分钟
- VIP 用户：1000 请求/分钟

使用 FastAPI-SlowAPI 或 Nginx 实现。
