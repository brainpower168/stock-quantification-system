# 贡献指南

感谢你对炒股大师量化交易系统的关注！我们欢迎任何形式的贡献，包括但不限于：

- 提交Issue报告bug或提出新功能
- 提交Pull Request改进代码或文档
- 完善测试用例
- 改进文档

## 🚀 如何贡献

### 1. 报告Bug

如果你发现了bug，请：

1. 检查 [Issue列表](https://gitee.com/brainpower168/stock-quantification-system/issues) 确认没有重复
2. 提交新的Issue，包含：
   - 清晰的标题和描述
   - 重现步骤
   - 期望行为和实际行为
   - 系统环境信息（OS、Python版本等）
   - 相关日志或截图

### 2. 提出新功能

如果你有新功能的想法，请：

1. 提交新的Issue，标记为"功能请求"
2. 清晰描述功能需求和使用场景
3. 如果可能，提供简单的实现思路

### 3. 提交代码

#### 第一步：Fork仓库

1. 访问项目主页：https://gitee.com/brainpower168/stock-quantification-system
2. 点击右上角"Fork"按钮

#### 第二步：克隆你的Fork

```bash
git clone https://gitee.com/你的用户名/stock-quantification-system.git
cd stock-quantification-system
```

#### 第三步：添加上游仓库

```bash
git remote add upstream https://gitee.com/brainpower168/stock-quantification-system.git
```

#### 第四步：创建特性分支

```bash
git checkout -b feature/你的特性描述
```

#### 第五步：开发和提交

```bash
# 进行你的修改
# ...

# 添加修改的文件
git add .

# 提交修改（使用清晰的提交信息）
git commit -m "feat: 添加涨停板策略模块"

# 推送到你的Fork
git push origin feature/你的特性描述
```

#### 第六步：创建Pull Request

1. 访问你的Fork页面
2. 点击"对比并创建Pull Request"
3. 填写PR标题和描述
4. 等待审核

## 📝 代码规范

### Python代码规范

- 遵循 [PEP 8](https://pep8.org/) 代码风格
- 使用类型提示（Type Hints）
- 函数和类要有清晰的文档字符串（Docstring）
- 变量名要有意义，避免使用单字母变量（循环变量除外）

### 提交信息规范

采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

类型包括：
- **feat**: 新功能
- **fix**: 修复bug
- **docs**: 文档更新
- **style**: 代码格式调整（不影响代码运行的变动）
- **refactor**: 重构（既不是新功能也不是bug修复）
- **perf**: 性能优化
- **test**: 测试相关
- **chore**: 构建过程或辅助工具的变动

示例：
```
feat(api): 添加持仓批量查询接口

- 新增 /api/positions/batch 端点
- 支持同时查询多个持仓状态
- 添加相应的单元测试

Closes #123
```

## 🧪 测试

提交代码前，请确保：

1. 所有现有测试通过：
   ```bash
   pytest tests/ -v
   ```

2. 新功能包含相应的测试用例

3. 测试覆盖率不降低

## 📖 文档

如果修改了API或添加了新功能，请同时更新文档：

- 更新 `README.md`
- 更新API文档（如果在 `docs/` 目录下）
- 添加使用示例

## 🔍 代码审查

所有Pull Request都需要经过代码审查：

1. 项目维护者会审查你的代码
2. 可能需要修改才能合并
3. 请及时回应审查意见

## 📄 许可证

 By submitting a Pull Request, you agree that your contributions will be licensed under the MIT License.

## 💬 联系方式

如果你有任何疑问，可以：

- 在 [Issue](https://gitee.com/brainpower168/stock-quantification-system/issues) 中提问
- 联系项目维护者：your-email@example.com

---

再次感谢你的贡献！🎉