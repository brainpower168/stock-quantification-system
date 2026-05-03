# 监控系统

本目录包含量化交易系统的监控组件，支持Prometheus + Grafana可视化监控。

## 架构

```
量化系统 → Metrics Exporter → Prometheus → Grafana
    ↓
钉钉推送
```

## 快速开始

### 方式一：Docker部署（推荐）

```bash
# 1. 启动Prometheus和Grafana
cd monitoring
docker-compose up -d

# 2. 启动指标导出器
python start_monitoring.py

# 3. 访问Grafana
# http://localhost:3000
# 用户名: admin
# 密码: admin123
```

### 方式二：手动部署

```bash
# 1. 安装Prometheus
# 下载: https://prometheus.io/download/
# 解压后编辑 prometheus.yml

# 2. 安装Grafana
# 下载: https://grafana.com/grafana/download

# 3. 启动指标导出器
python start_monitoring.py --port 9091

# 4. 启动Prometheus
prometheus --config.file=prometheus.yml

# 5. 启动Grafana
grafana-server
```

## 组件说明

### 1. Metrics Exporter（指标导出器）

**文件**: `scripts/metrics_exporter.py`

**功能**:
- 导出Prometheus格式的指标
- 支持HTTP接口访问
- 支持文件导出

**指标类型**:

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `position_market_value` | Gauge | 持仓市值 |
| `position_profit_loss` | Gauge | 持仓盈亏 |
| `position_profit_loss_pct` | Gauge | 盈亏率 |
| `fund_main_inflow` | Gauge | 主力流入（亿） |
| `fund_ddx` | Gauge | DDX指标 |
| `signal_count` | Gauge | 信号统计 |
| `api_success_rate` | Gauge | API成功率 |
| `cache_hit_rate` | Gauge | 缓存命中率 |

**使用方法**:

```bash
# 启动HTTP服务器
python scripts/metrics_exporter.py --port 9091

# 导出到文件
python scripts/metrics_exporter.py --export-file metrics.txt

# 测试模式
python scripts/metrics_exporter.py --test
```

### 2. Signal Pusher（信号推送）

**文件**: `scripts/signal_pusher.py`

**功能**:
- 实时推送交易信号
- 支持钉钉推送
- 支持WebSocket实时推送

**信号类型**:

| 类型 | 说明 | 优先级 |
|------|------|--------|
| STOCK_PICK | 选股信号 | 高/中 |
| AI_DECISION | AI决策 | 高/中/低 |
| POSITION_ALERT | 持仓预警 | 高/中 |
| FUND_FLOW | 资金流向 | 高/中 |
| BREAKOUT | 突破信号 | 高 |
| STOP_LOSS | 止损提醒 | 高 |
| TAKE_PROFIT | 止盈提醒 | 中 |

**使用方法**:

```python
from signal_pusher import SignalPusher, SignalType, SignalPriority

pusher = SignalPusher()

# 推送选股信号
pusher.push_signal(
    signal_type=SignalType.STOCK_PICK,
    stock_code="600519",
    stock_name="贵州茅台",
    title="选股推荐 - A级",
    message="符合选股条件",
    data={"涨幅": "2.5%", "主力流入": "5.2亿"},
    priority=SignalPriority.HIGH
)
```

### 3. Realtime Push Service（实时推送服务）

**文件**: `scripts/realtime_push_service.py`

**功能**:
- 集成选股、AI Council、持仓监控
- 自动推送信号到钉钉
- 支持持续监控模式

**使用方法**:

```bash
# 单次运行
python scripts/realtime_push_service.py --mode once

# 持续监控（每5分钟）
python scripts/realtime_push_service.py --mode monitor --interval 300

# 测试模式
python scripts/realtime_push_service.py --test
```

### 4. Monitoring Service（监控服务）

**文件**: `monitoring/start_monitoring.py`

**功能**:
- 启动Prometheus指标导出器
- 后台收集持仓、资金流向、信号等指标

**使用方法**:

```bash
# 启动监控服务
python monitoring/start_monitoring.py --port 9091
```

## Grafana面板

### 面板配置

**文件**: `monitoring/grafana/dashboards/quant_dashboard.json`

**面板内容**:

1. **持仓总览**
   - 总市值
   - 总盈亏
   - 盈亏率
   - 活跃持仓数

2. **持仓明细**
   - 股票名称
   - 股票代码
   - 市值
   - 盈亏

3. **资金流向监控**
   - 主力流入趋势图
   - 流出预警

4. **DDX趋势**
   - DDX指标趋势
   - 正负分界线

5. **信号统计**
   - 各类信号数量
   - 饼图展示

6. **系统状态**
   - API成功率
   - 缓存命中率

### 导入面板

1. 访问 Grafana: http://localhost:3000
2. 登录（admin/admin123）
3. 左侧菜单 → Dashboards → Import
4. 上传 `quant_dashboard.json` 或粘贴JSON内容
5. 选择Prometheus数据源
6. 点击Import

## Prometheus配置

**文件**: `monitoring/prometheus.yml`

**配置说明**:

```yaml
global:
  scrape_interval: 30s  # 每30秒采集一次

scrape_configs:
  - job_name: 'quant_system'
    static_configs:
      - targets: ['host.docker.internal:9091']  # Windows/Mac
        # Linux: ['localhost:9091']
```

**注意**:
- Windows/Mac使用 `host.docker.internal` 访问宿主机
- Linux需要使用 `localhost` 或宿主机IP

## 告警规则

### Grafana告警

**资金流出预警**:
- 条件: 主力流入 < -1亿
- 频率: 每5分钟检查
- 通知: 配置钉钉/邮件通知

### 配置告警通道

1. Grafana → Alerting → Contact points
2. 添加钉钉Webhook
3. 配置通知策略

## 环境变量

在 `.env` 文件中配置:

```env
# WebSocket
WS_PORT=8765
WS_ENABLED=true

# Prometheus
PROMETHEUS_PORT=9091

# Grafana
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin123
```

## 完整启动流程

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env，填入API Key

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动监控服务
python monitoring/start_monitoring.py &

# 4. 启动Docker服务
cd monitoring
docker-compose up -d

# 5. 访问Grafana
# http://localhost:3000

# 6. 启动实时推送服务（可选）
python scripts/realtime_push_service.py --mode monitor
```

## 常见问题

### Q1: Grafana无法连接Prometheus？

检查Prometheus是否正常运行:
```bash
curl http://localhost:9090/-/healthy
```

检查Prometheus配置:
```bash
curl http://localhost:9090/api/v1/targets
```

### Q2: 指标数据不更新？

检查指标导出器是否运行:
```bash
curl http://localhost:9091/metrics
```

检查后台收集器日志。

### Q3: Docker容器启动失败？

检查端口占用:
```bash
# Windows
netstat -ano | findstr :9090
netstat -ano | findstr :3000

# Linux/Mac
lsof -i :9090
lsof -i :3000
```

### Q4: 钉钉推送失败？

检查钉钉配置:
```bash
python scripts/dingtalk_push.py --message "测试消息"
```

查看日志确认错误原因。

## 性能优化

### 1. 减少采集频率

编辑 `prometheus.yml`:
```yaml
global:
  scrape_interval: 60s  # 从30秒改为60秒
```

### 2. 限制历史数据

编辑 `prometheus.yml`:
```yaml
global:
  retention: 7d  # 只保留7天数据
```

### 3. 使用缓存

指标导出器会自动缓存数据，避免重复计算。

## 扩展功能

### 1. 添加自定义指标

在 `metrics_exporter.py` 中添加:

```python
self.add_metric("custom_metric", value, {"label": "value"})
```

### 2. 添加自定义面板

在Grafana中创建新面板，使用PromQL查询:

```
# 查询示例
avg(position_profit_loss_pct) * 100
sum(position_market_value)
rate(signal_total[5m])
```

### 3. 集成其他监控工具

支持导出到:
- InfluxDB
- Elasticsearch
- TimescaleDB

---

**监控让交易更透明！** 📊
