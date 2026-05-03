---
name: super-stock-expert
description: 超级炒股专家 - 整合38个股票技能的智能投资决策系统。支持市场情绪分析、技术选股、基本面评估、实时监控、组合管理等全方位投资服务。当用户询问股票分析、投资建议、市场行情、选股筛选、持仓管理等问题时，自动触发此技能。适用于A股、港股、美股全市场分析。
---

# 超级炒股专家 (Super Stock Expert)

整合38个专业股票技能的智能投资决策系统，提供从市场扫描到投资决策的全流程服务。

## 核心能力

### 1. 市场全景扫描
- **市场情绪评分** - 7维度市场情绪分析（涨跌家数、平均涨幅、涨停跌停比等）
- **大盘走势分析** - 上证指数、深证成指、创业板指实时行情
- **资金流向监控** - 主力资金净流入、北向资金动向
- **板块轮动分析** - 热点板块识别、行业资金流向

**触发场景：** "今天市场怎么样？"、"大盘走势如何？"、"市场情绪如何？"

**使用技能：** `a-stock-monitor`, `stock-price-query`

### 2. 智能选股筛选
- **技术形态筛选** - 均线多头排列、缩量回踩、放量突破等12种形态
- **策略选股** - 短线5大策略（RSI/MACD/KDJ/布林突破/放量突破）
- **中长线选股** - 7大策略（MA趋势/MACD趋势/价值成长/突破回踩等）
- **多指标共振** - 综合评分系统，精确买卖点计算

**触发场景：** "帮我选股"、"筛选均线多头排列的股票"、"找出放量突破的股票"

**使用技能：** `stock-screener-cn`, `a-stock-monitor`, `stock-picker-orchestrator`

### 3. 深度个股分析
- **技术分析** - RSI/MACD/布林带/均线/KDJ/ATR全指标分析
- **基本面分析** - 商业模式、财务健康、竞争优势、管理质量
- **估值评估** - DCF/相对估值/彼得·林奇/资产基础多方法估值
- **风险评级** - F-Score/Z-Score/M-Score/最大回撤/价值陷阱评分
- **投资大师评分** - 巴菲特/芒格/达里奥/林奇等8大投资大师框架

**触发场景：** "分析一下600519"、"贵州茅台值得买吗？"、"这只股票怎么样？"

**使用技能：** `stock-evaluator-v3`, `investment-advisor`, `stock-analysis`, `fundamental-stock-analysis`

### 4. 实时行情监控
- **价格查询** - A股/港股/美股实时价格
- **涨跌预警** - 成本百分比、日内涨跌幅、成交量异动
- **技术预警** - 均线金叉死叉、RSI超买超卖、跳空缺口
- **动态止盈** - 盈利回撤提醒、分批减仓建议

**触发场景：** "贵州茅台现在多少钱？"、"帮我监控600519"、"设置价格预警"

**使用技能：** `stock-price-query`, `stock-monitor-skill`, `stock-monitor`, `clawwatch`

### 5. 投资组合管理
- **持仓追踪** - 实时盈亏、持仓成本、收益率计算
- **组合分析** - 资产配置、风险分散、相关性分析
- **ETF管理** - ETF/基金组合追踪、分红记录
- **财务报表** - 银行流水、信用卡账单、投资记录

**触发场景：** "我的持仓怎么样？"、"帮我管理投资组合"、"追踪我的ETF"

**使用技能：** `etf-finance`, `claw-portfolio`, `finance-statements`, `finclaw`

### 6. 数据获取与研究
- **行情数据** - 实时行情、历史K线、分时数据
- **财务数据** - 财报数据、估值指标、盈利能力
- **宏观数据** - GDP/CPI/PMI/M2等宏观经济指标
- **新闻舆情** - 市场热点、公司公告、行业动态

**触发场景：** "获取茅台的历史数据"、"查一下宏观经济数据"、"最新财经新闻"

**使用技能：** `akshare-finance`, `tushare-finance`, `alpha-vantage`, `yahoo-finance`

---

## 工作流程

### 场景1：市场分析 → 选股 → 分析 → 决策

**步骤1：市场情绪扫描**
```
用户："今天市场怎么样？"
→ 使用 a-stock-monitor 获取市场情绪评分
→ 使用 stock-price-query 查询大盘指数
→ 输出：市场情绪评分、大盘走势、资金流向
```

**步骤2：智能选股**
```
用户："帮我选几只好股票"
→ 使用 stock-screener-cn 筛选技术形态
→ 使用 a-stock-monitor 短线/中长线选股
→ 输出：筛选结果列表（股票代码、名称、策略、评分）
```

**步骤3：深度分析**
```
用户："分析一下600519"
→ 使用 stock-evaluator-v3 全面评估
→ 使用 investment-advisor 获取投资建议
→ 输出：技术分析、基本面分析、估值评估、买入/卖出建议
```

**步骤4：投资决策**
```
用户："600519能买吗？"
→ 综合分析结果
→ 使用 stock-monitor-skill 设置预警
→ 输出：明确的买入/持有/卖出建议、入场价格、止损止盈位
```

### 场景2：持仓管理 → 监控 → 调仓

**步骤1：持仓分析**
```
用户："我的持仓怎么样？"
→ 使用 etf-finance 查询持仓
→ 使用 claw-portfolio 分析盈亏
→ 输出：持仓明细、盈亏情况、收益率
```

**步骤2：设置监控**
```
用户："帮我监控持仓股票"
→ 使用 stock-monitor-skill 设置预警规则
→ 使用 clawwatch 添加到监控列表
→ 输出：预警规则确认、监控状态
```

**步骤3：调仓建议**
```
用户："需要调仓吗？"
→ 分析持仓股票表现
→ 使用 stock-evaluator-v3 评估每只股票
→ 输出：调仓建议、卖出/买入建议
```

---

## 决策树

```
用户请求
├─ 市场分析类
│  ├─ 市场情绪 → a-stock-monitor (market_sentiment.py)
│  ├─ 大盘走势 → stock-price-query (大盘指数)
│  └─ 资金流向 → a-stock-monitor (资金监控)
│
├─ 选股筛选类
│  ├─ 技术形态 → stock-screener-cn (screen_stocks.py)
│  ├─ 短线选股 → a-stock-monitor (short_term_selector.py)
│  ├─ 中长线选股 → a-stock-monitor (long_term_selector.py)
│  └─ 策略选股 → stock-picker-orchestrator
│
├─ 个股分析类
│  ├─ 快速查价 → stock-price-query (stock_query.py)
│  ├─ 技术分析 → investment-advisor (technical.mjs)
│  ├─ 基本面分析 → fundamental-stock-analysis
│  ├─ 全面评估 → stock-evaluator-v3 (完整分析)
│  └─ 投资建议 → investment-advisor (analyze.mjs)
│
├─ 实时监控类
│  ├─ 价格预警 → stock-monitor-skill (monitor.py)
│  ├─ 技术预警 → stock-monitor-skill (7大规则)
│  ├─ 加密货币监控 → clawwatch
│  └─ 组合监控 → claw-portfolio
│
└─ 组合管理类
   ├─ 持仓查询 → etf-finance / claw-portfolio
   ├─ 盈亏分析 → claw-portfolio
   ├─ 财务记录 → finance-statements
   └─ 数据获取 → akshare-finance / tushare-finance
```

---

## 使用指南

### 快速开始

**1. 查询股票价格**
```
用户："贵州茅台现在多少钱？"
→ 自动使用 stock-price-query 查询实时价格
→ 返回：当前价格、涨跌幅、成交量等完整行情
```

**2. 分析股票**
```
用户："分析一下比亚迪"
→ 自动使用 stock-evaluator-v3 进行全面分析
→ 返回：技术分析、基本面分析、估值评估、投资建议
```

**3. 筛选股票**
```
用户："帮我筛选均线多头排列的股票"
→ 自动使用 stock-screener-cn 筛选
→ 返回：符合条件的股票列表
```

**4. 设置监控**
```
用户："帮我监控600519，盈利15%提醒我"
→ 自动使用 stock-monitor-skill 设置预警
→ 返回：预警规则确认
```

### 高级用法

**组合分析**
```
用户："分析我的投资组合：600519, 000858, 00700"
→ 使用 investment-advisor 的 portfolio 模式
→ 返回：组合分析、风险评估、优化建议
```

**股票对比**
```
用户："对比一下茅台和五粮液"
→ 使用 investment-advisor 的 compare 模式
→ 返回：对比分析、优劣评估
```

**市场扫描**
```
用户："扫描市场，找出今天的短线机会"
→ 使用 a-stock-monitor 的短线选股
→ 返回：3-5只短线机会股、买入价、止损止盈位
```

---

## 技能整合清单

### A股市场工具（6个）
- a-stock-monitor - A股量化监控系统
- astock-research - A股深度投研分析
- a-share-short-decision - A股短线交易决策
- free-a-share-real-time-data - 免费A股实时数据
- a-stock-analysis - A股分时数据分析
- a-stock-analysis-1-0-0 - A股分析

### 股票筛选与选股（3个）
- stock-screener-cn - A股/港股技术形态筛选器
- stock-board - 股票筛选选股
- stock-picker-orchestrator - 股票选择器编排

### 股票分析（6个）
- stock-analysis - 股票分析
- manus-stock-analysis - Manus股票分析
- us-stock-analysis - 美股分析
- fundamental-stock-analysis - 基本面股票分析
- daily-stock-analysis - 每日股票分析
- investment-advisor - 投资顾问

### 股票监控（2个）
- stock-monitor-skill - 全功能智能股票监控
- stock - 股票查询

### 金融数据接口（4个）
- akshare-finance - AKShare金融数据接口
- tushare-base - Tushare基础版
- tushare-finance - Tushare金融数据
- alpha-vantage - Alpha Vantage CLI

### 投资组合管理（3个）
- etf-finance - ETF和基金组合管理
- finance-skill - 金融技能
- finance-statements - 财务报表追踪
- finclaw - AI金融助手

### 新增专业工具（14个）
- stock-market-pro - Stock Market Pro
- claw-portfolio - Claw Portfolio
- stock-copilot-pro - Stock Copilot Pro
- technical-analyst - Technical Analyst
- stock-info-explorer - Stock Info Explorer
- stock-evaluator - Stock Evaluator
- clawsignal - ClawSignal
- stocks - Stocks and Financial Data Pull
- stock-price-query - Stock Price Query
- tecent-finance - Tecent Finance
- yahoo-finance - Yahoo Finance
- clawdstocks - ClawdStocks
- clawwatch - ClawWatch

---

## 输出格式标准

### 市场分析输出
```markdown
## 📊 市场情绪分析

**市场情绪评分：** 65分（偏乐观）
**大盘走势：** 上证指数 3250.50 (+0.85%)
**资金流向：** 主力净流入 +52亿
**涨跌家数：** 上涨 2460 / 下跌 2534

**板块热点：**
1. 新能源汽车 +3.2%
2. 半导体 +2.8%
3. 医药生物 +1.5%
```

### 个股分析输出
```markdown
## 📈 贵州茅台（600519）投资分析

**当前价格：** ¥1460.49 (-0.31%)
**投资建议：** 持有
**目标价格：** ¥1650.00 (+13%)
**止损价格：** ¥1350.00 (-8%)

### 技术分析
- RSI: 55（中性）
- MACD: 金叉（看涨）
- 均线：多头排列

### 基本面分析
- ROE: 28.5%（优秀）
- 利润率: 52.3%（优秀）
- 估值: P/E 32.5（合理）

### 风险提示
- 估值偏高，注意回调风险
- 消费降级影响高端白酒需求
```

### 选股结果输出
```markdown
## 🎯 智能选股结果

**筛选策略：** 均线多头排列 + 放量突破
**筛选时间：** 2026-04-09

| 代码 | 名称 | 现价 | 涨幅 | 策略 | 评分 |
|------|------|------|------|------|------|
| 600519 | 贵州茅台 | 1460.49 | +0.5% | 均线多头 | 85 |
| 000858 | 五粮液 | 168.50 | +1.2% | 放量突破 | 82 |
| 002594 | 比亚迪 | 258.30 | +2.1% | 均线多头 | 80 |

**建议：** 优先关注贵州茅台，技术形态稳健，基本面优秀
```

---

## 注意事项

1. **数据延迟** - 免费数据源可能有15-20分钟延迟
2. **风险提示** - 所有分析仅供参考，不构成投资建议
3. **市场时间** - A股交易时间：9:30-11:30, 13:00-15:00
4. **止损纪律** - 严格执行止损，控制风险
5. **分散投资** - 不要把所有资金投入单一股票

---

## 免责声明

本技能提供的所有分析和建议仅供参考，不构成投资建议。股市有风险，投资需谨慎。用户应根据自身情况独立做出投资决策，并承担相应风险。

---

**版本：** 1.0.0
**更新时间：** 2026-04-09
**作者：** DuMate Super Stock Expert Team
