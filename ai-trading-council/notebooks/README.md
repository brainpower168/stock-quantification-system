# Jupyter Notebook 实战案例

本目录包含3个实战案例，帮助你快速上手量化交易系统。

## 案例列表

| 案例 | 文件 | 核心功能 | 难度 |
|------|------|----------|------|
| 选股流程实战 | `01_选股流程实战.ipynb` | 主力资金筛选、DDX分析、分级推荐 | ⭐⭐ |
| AI Council决策实战 | `02_AI_Council决策实战.ipynb` | 多模型投票、共识决策、风险评估 | ⭐⭐⭐ |
| 持仓监控实战 | `03_持仓监控实战.ipynb` | 持仓管理、止损止盈、资金流向监控 | ⭐⭐ |

## 快速开始

### 1. 安装依赖

```bash
cd ai-trading-council
pip install -r requirements.txt
pip install jupyter  # 安装Jupyter
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 数据源API（至少配置一个）
MX_APIKEY=your_miaoxiang_api_key          # 妙想API（首选）
IWENCAI_API_KEY=your_iwencai_api_key      # 问财API（备用）
GS_API_KEY=your_guoxin_api_key            # 国信API

# AI模型API
LONGCAT_API_KEY=your_longcat_api_key      # LongCat API（必需）
SPARK_API_KEY=your_spark_api_key          # 讯飞星火API（可选）
GLM_API_KEY=your_glm_api_key              # 智谱GLM API（可选）
```

### 3. 启动Jupyter

```bash
cd notebooks
jupyter notebook
```

### 4. 运行案例

在浏览器中打开对应的 `.ipynb` 文件，按 `Shift+Enter` 逐个运行单元格。

## 案例详解

### 案例1：选股流程实战

**学习目标**：
- 掌握主力资金流入数据获取
- 理解DDX指标含义
- 学会分级推荐制度

**核心流程**：
```
获取TOP N → 筛选DDX转正 → 分级推荐 → 推送钉钉
```

**关键代码**：
```python
from daily_stock_selector import DailyStockSelector

selector = DailyStockSelector()
top_stocks = selector.get_top_main_inflow(top_n=20)
recommendations = selector.grade_stocks(top_stocks)
```

**输出示例**：
```
【A级】强烈推荐
  - 贵州茅台(600519)
    涨幅: 2.5%
    主力流入: 5.2亿
    10日DDX: 3.45

【B级】可以关注
  - 宁德时代(300750)
    涨幅: 1.8%
    主力流入: 3.1亿
    10日DDX: 1.23
```

---

### 案例2：AI Council决策实战

**学习目标**：
- 理解多模型投票机制
- 掌握共识决策生成
- 学会风险评估

**核心流程**：
```
初始化Council → 分析股票 → 各模型投票 → 共识决策 → 生成报告
```

**关键代码**：
```python
from council_engine import CouncilEngine

engine = CouncilEngine()
decision = engine.analyze_stock("600519", "贵州茅台")

print(f"最终决策: {decision.final_decision}")
print(f"置信度: {decision.confidence:.2%}")
```

**输出示例**：
```
最终决策: BUY
置信度: 72.50%

【LongCat】量化专家
  决策: BUY
  置信度: 75%
  理由: DDX连续5日流入，技术面突破20日均线...

【讯飞星火】基本面分析师
  决策: HOLD
  置信度: 60%
  理由: PE偏高，但ROE稳定，业绩增长良好...

【智谱GLM】技术分析师
  决策: BUY
  置信度: 80%
  理由: K线形态显示上涨趋势，成交量放大...
```

---

### 案例3：持仓监控实战

**学习目标**：
- 掌握持仓管理
- 学会止损止盈设置
- 理解资金流向监控

**核心流程**：
```
添加持仓 → 设置止损止盈 → 检查预警 → 资金流向监控 → 生成报告
```

**关键代码**：
```python
from position_monitor import PositionMonitor

monitor = PositionMonitor()
monitor.add_position("600519", "贵州茅台", 100, 1800.0)

# 设置止损止盈
monitor.set_alert_rules({
    "stop_loss_pct": -0.05,  # -5%
    "take_profit_pct": 0.10,  # +10%
})

# 检查预警
alerts = monitor.check_alerts()
```

**输出示例**：
```
=== 持仓状态 ===
股票         持仓     成本       现价       盈亏       盈亏率
----------------------------------------------------------------------
贵州茅台     100      1800.00    1850.00    5000.00    2.78%
宁德时代     200      200.00     195.00     -1000.00   -2.50%

总盈亏: 4000.00元

=== 预警信息 ===
🟡 宁德时代(300750)
   类型: STOP_LOSS
   消息: 接近止损线(-5%)，当前-2.5%
```

## 常见问题

### Q1: API Key从哪里获取？

| API | 获取地址 | 说明 |
|-----|----------|------|
| 妙想 | 东方财富开放平台 | 需申请，数据最完整 |
| 问财 | 同花顺开放平台 | 需申请，每日有限制 |
| 国信 | 国信证券iQuant | 需开户，免费 |
| LongCat | LongCat官网 | AI模型API |

### Q2: 数据源优先级是什么？

**必须遵循的优先级**（避免浪费API调用次数）：
1. **妙想API**（首选，无限制，数据最完整）
2. **问财API**（备用，每日有限，节省使用）
3. **国信API**（补充，实时行情、财务数据）
4. **腾讯财经**（最后备用，仅实时价格）

### Q3: 如何调试代码？

在Jupyter中，可以在任意单元格插入调试代码：

```python
# 查看变量
print(top_stocks)

# 查看类型
print(type(top_stocks))

# 查看帮助
help(selector.get_top_main_inflow)
```

### Q4: 如何保存运行结果？

Jupyter会自动保存 `.ipynb` 文件。如需导出：

```bash
# 导出为Python脚本
jupyter nbconvert --to script 01_选股流程实战.ipynb

# 导出为HTML
jupyter nbconvert --to html 01_选股流程实战.ipynb

# 导出为PDF
jupyter nbconvert --to pdf 01_选股流程实战.ipynb
```

## 进阶学习

### 推荐阅读

1. **DDX指标详解** - `../docs/DDX指标使用指南.md`
2. **AI Council架构** - `../docs/AI_Council设计文档.md`
3. **交易纪律** - `../MEMORY.md` 中的"用户交易习惯与教训"

### 实战建议

1. **先运行案例1** - 熟悉选股流程
2. **再运行案例3** - 设置持仓监控
3. **最后运行案例2** - 使用AI Council辅助决策

### 自定义扩展

在案例基础上，你可以：

1. **修改筛选条件** - 调整涨幅、DDX阈值
2. **添加新指标** - 如换手率、量比
3. **集成其他策略** - 如2560战法、一夜持股法
4. **对接实盘** - 使用 `live-trading` 模块

## 技术支持

遇到问题？查看：
- 项目文档：`../DOCS_INDEX.md`
- 环境检查：`../scripts/check_env.py`
- 单元测试：`../tests/`

---

**祝你交易顺利！** 📈
