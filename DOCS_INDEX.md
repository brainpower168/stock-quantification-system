# 炒股大师量化系统 - 文档导航

## 快速开始

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [QUICKSTART.md](QUICKSTART.md) | 5分钟快速上手指南 | 新手必读 |
| [.env.example](.env.example) | 环境变量配置模板 | 配置API Key |

## 核心文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目总览 |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API接口文档 |

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

# 启动服务
docker-compose up -d
```

## 问题排查

| 问题 | 解决方案 |
|------|----------|
| API Key未配置 | 复制 .env.example 为 .env，填入真实Key |
| 依赖包缺失 | pip install -r requirements.txt |
| TA-Lib安装失败 | Windows下载预编译wheel安装 |
