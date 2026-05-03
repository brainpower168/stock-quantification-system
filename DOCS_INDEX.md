# 炒股大师量化系统 - 文档导航

## 快速开始

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [QUICKSTART.md](QUICKSTART.md) | 5分钟快速上手指南 | 新手必读 |
| [.env.example](.env.example) | 环境变量配置模板 | 配置API Key |
| [notebooks/README.md](notebooks/README.md) | Jupyter实战案例 | 快速上手 |

## 核心文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目总览 |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API接口文档 |

## 实战案例

| 案例 | 文件 | 核心功能 |
|------|------|----------|
| 选股流程实战 | [notebooks/01_选股流程实战.ipynb](notebooks/01_选股流程实战.ipynb) | 主力资金筛选、DDX分析、分级推荐 |
| AI Council决策实战 | [notebooks/02_AI_Council决策实战.ipynb](notebooks/02_AI_Council决策实战.ipynb) | 多模型投票、共识决策、风险评估 |
| 持仓监控实战 | [notebooks/03_持仓监控实战.ipynb](notebooks/03_持仓监控实战.ipynb) | 持仓管理、止损止盈、资金流向监控 |

## 监控系统

| 文档 | 说明 |
|------|------|
| [monitoring/README.md](monitoring/README.md) | Prometheus + Grafana监控部署指南 |
| [monitoring/docker-compose.yml](monitoring/docker-compose.yml) | 一键启动监控服务 |

## 优化报告

| 文档 | 说明 | 日期 |
|------|------|------|
| [OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md) | P0-P1优化报告 | 2026-05-03 |
| [P3_OPTIMIZATION_SUMMARY.md](P3_OPTIMIZATION_SUMMARY.md) | P3长期优化总结 | 2026-05-03 |
| [FINAL_OPTIMIZATION_REPORT.md](FINAL_OPTIMIZATION_REPORT.md) | 最终优化报告 | 2026-05-03 |

## 开发指南

| 文档 | 说明 |
|------|------|
| [CODE_REFACTORING_GUIDE.md](CODE_REFACTORING_GUIDE.md) | 代码重构指南 |
| [TYPING_GUIDE.md](TYPING_GUIDE.md) | 类型注解规范 |

## 运维文档

| 文档 | 说明 |
|------|------|
| [Dockerfile](Dockerfile) | Docker容器配置 |
| [docker-compose.yml](docker-compose.yml) | Docker Compose编排 |

## 常用命令

```bash
# 环境检查
python scripts/check_env.py

# 运行测试
pytest tests/

# 启动Jupyter Notebook
cd notebooks && jupyter notebook

# 启动监控服务
cd monitoring && docker-compose up -d

# 测试推送功能
python scripts/realtime_push_service.py --test
```

## 问题排查

| 问题 | 解决方案 |
|------|----------|
| API Key未配置 | 复制 .env.example 为 .env，填入真实Key |
| 依赖包缺失 | pip install -r requirements.txt |
| TA-Lib安装失败 | Windows下载预编译wheel安装 |
| 钉钉推送失败 | 检查DINGTALK_APP_SECRET是否配置 |
| Grafana无法访问 | 检查端口3000是否被占用 |
