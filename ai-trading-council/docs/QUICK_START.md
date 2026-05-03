# TradingAgents 快速启动指南

## 🚀 5分钟快速开始

### 1. 测试系统（无需配置）

```bash
cd ai-trading-council

# 测试TradingAgents系统
python agents/test_trading_agents.py

# 测试完整选股流程
python scripts/test_full_workflow.py

# 运行每日选股（模拟数据）
python scripts/daily_scheduler.py --once
```

### 2. 配置代理（访问外部API）

**Windows CMD:**
```cmd
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

**Windows PowerShell:**
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
```

**Linux/Mac:**
```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

### 3. 配置API Key

在 `.env` 文件中配置：

```env
# 数据源API（必填）
MX_APIKEY=your_miaoxiang_api_key
IWENCAI_API_KEY=your_wencai_api_key
GS_API_KEY=your_guoxin_api_key

# LLM API（选填一个）
XUNFEI_API_KEY=your_xunfei_api_key
ZHIPU_API_KEY=your_zhipu_api_key
LONGCAT_API_KEY=your_longcat_api_key

# 钉钉推送（可选）
DINGTALK_WEBHOOK=your_webhook_url
DINGTALK_APPSECRET=your_app_secret
```

### 4. 启动定时任务

```bash
# 启动定时调度（每日9:30和15:00运行）
python scripts/daily_scheduler.py --schedule

# 手动运行一次
python scripts/daily_scheduler.py --once
```

---

## 📊 系统架构

```
选股流程：
1. 获取主力资金流入TOP N
2. 筛选（主力>5000万 + DDX>0 + 涨幅<5%）
3. TradingAgents深度分析
   ├─ 多空辩论（多头 vs 空头）
   ├─ 研究经理综合决策
   ├─ 交易员形成提案
   ├─ 风控辩论（激进 vs 保守 vs 中立）
   └─ 投资组合经理最终决策
4. 生成报告（5级评级 + 执行摘要）
5. 推送到钉钉（可选）
```

---

## 🎯 5级评级系统

| 评级 | 含义 | 操作建议 |
|------|------|----------|
| **Buy** | 强烈买入 | 积极建仓，可提高到15-20%仓位 |
| **Overweight** | 增持 | 分批买入，首次5-10%仓位 |
| **Hold** | 持有 | 观望，不操作 |
| **Underweight** | 减持 | 减仓一半，等反弹再卖 |
| **Sell** | 卖出 | 清仓离场 |

---

## 📁 核心文件

```
ai-trading-council/
├── agents/
│   ├── trading_agents_system.py       # 核心系统
│   ├── trading_agents_live.py         # 实盘对接
│   └── test_trading_agents.py         # 测试脚本
├── scripts/
│   ├── enhanced_stock_selector.py     # 增强版选股器
│   ├── test_full_workflow.py          # 完整流程测试
│   └── daily_scheduler.py             # 定时任务
└── docs/
    ├── TRADING_AGENTS_INTEGRATION.md  # 整合报告
    ├── TRADING_AGENTS_SETUP.md        # 配置指南
    └── PROXY_SETUP.md                 # 代理配置
```

---

## 🔧 常见问题

### Q1: 外部API无法访问？

**A:** 需要配置代理，参考第2步。

### Q2: 如何使用真实LLM？

**A:** 配置API Key后，修改 `daily_scheduler.py`:

```python
# 替换这行
self.llm = MockLLM()

# 改为
from trading_agents_live import XunfeiLLMWrapper
self.llm = XunfeiLLMWrapper(os.getenv("XUNFEI_API_KEY"))
```

### Q3: 如何使用真实数据源？

**A:** 配置API Key后，修改 `daily_scheduler.py`:

```python
# 替换 _get_stock_data() 方法
def _get_stock_data(self):
    from trading_agents_live import DataSourceManager
    ds = DataSourceManager()
    return ds.get_top_main_inflow(20)
```

### Q4: 如何修改筛选条件？

**A:** 修改 `_filter_stocks()` 方法:

```python
def _filter_stocks(self, stocks):
    filtered = []
    for stock in stocks:
        # 修改这些条件
        if stock.get("main_inflow", 0) < 1e8:  # 主力>1亿
            continue
        if stock.get("ddx_10", 0) < 2:  # 10日DDX>2
            continue
        if stock.get("change_pct", 0) > 3:  # 涨幅<3%
            continue
        filtered.append(stock)
    return filtered
```

---

## 📈 示例输出

```markdown
# 每日选股报告

**时间**: 2026-05-03 16:05:00

---

## 1. 贵州茅台 (600519)

**🔵 增持**

**基本信息**
- 价格: 1850元
- 涨幅: 2.5%
- 主力流入: 5.00亿
- 10日DDX: 4.1

**TradingAgents决策**
- 摘要: 建议增持，首次买入5-10%，等回调加仓
- 逻辑: 基本面强劲（ROE 18%），技术面向好（MACD金叉）...
- 目标价: 1950
- 持有周期: 1-3个月
```

---

## 🎓 进阶使用

### 自定义分析师报告

```python
analyst_reports = {
    "market_report": "自定义市场分析...",
    "fundamentals_report": "自定义基本面分析...",
    "sentiment_report": "自定义情绪分析...",
    "news_report": "自定义新闻分析...",
}
```

### 自定义辩论轮数

```python
# 默认2轮辩论
result = system.run_full_analysis("600519", analyst_reports)

# 修改为3轮
system.bull_bear_debate.run_debate(state, rounds=3)
```

### 获取详细辩论历史

```python
result = system.run_full_analysis("600519", analyst_reports)

# 多空辩论历史
print(result["debate_result"]["bull_history"])
print(result["debate_result"]["bear_history"])

# 风控辩论历史
print(result["risk_debate"]["aggressive_history"])
print(result["risk_debate"]["conservative_history"])
```

---

## 📞 支持

- GitHub Issues: https://github.com/TauricResearch/TradingAgents
- 文档: `docs/TRADING_AGENTS_INTEGRATION.md`
- 代理配置: `docs/PROXY_SETUP.md`
