🌐 [English](../README.md) | 中文

# Agent Harness Engineering on Azure

> 🚀 180分钟企业级 Agent Harness Engineering on Azure 工作坊 — 从基础补全到多智能体协作，全面掌握 Copilot 工程化实践。

## 🆕 v2 新变化

| 维度 | v1 | v2 |
|------|----|---|
| 时长 | 120 分钟 | **180 分钟** |
| 实验数 | 3 Labs | **5 Labs** |
| 智能体 | 3 Agents | **10 Agents** |
| Prompt 模板 | 1 Prompt | **6 Prompts** |

## 📁 文件清单

| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明文档 |
| `.github/copilot-instructions.md` | Copilot 全局指令配置 |
| `.github/agents/*.md` | 10 个自定义智能体定义 |
| `.github/prompts/*.prompt.md` | 6 个可复用 Prompt 模板 |
| `labs/lab-1/` | Lab 1 实验材料 |
| `labs/lab-2/` | Lab 2 实验材料 |
| `labs/lab-3/` | Lab 3 实验材料 |
| `labs/lab-4/` | Lab 4 实验材料 |
| `labs/lab-5/` | Lab 5 实验材料 |
| `src/` | 示例应用源码 |
| `package.json` | Node.js 项目配置 |
| `LICENSE` | MIT 许可证 |

## 🤖 智能体角色表（10 Agents）

| 智能体 | 角色 | 职责 |
|--------|------|------|
| `code-reviewer` | 代码审查员 | 审查代码质量、风格与最佳实践 |
| `architect` | 架构师 | 系统设计、技术选型与架构决策 |
| `investigator` | 调查员 | 深入分析问题根因与上下文 |
| `release-engineer` | 发布工程师 | 管理发布流程、版本号与变更日志 |
| `product-reviewer` | 产品审查员 | 从产品视角评估功能完整性与用户体验 |
| `performance-engineer` | 性能工程师 | 识别性能瓶颈并提供优化方案 |
| `red-team` | 红队 | 对抗性测试，发现潜在攻击面 |
| `security-reviewer` | 安全审查员 | 检查安全漏洞与合规性 |
| `test-engineer` | 测试工程师 | 编写与优化测试用例，提升覆盖率 |
| `doc-writer` | 文档工程师 | 生成与维护技术文档和 API 文档 |

## 📝 Prompt 模板表（6 Prompts）

| 模板 | 用途 | 典型场景 |
|------|------|----------|
| `add-endpoint` | 新增 API 端点 | 快速生成 RESTful 路由、控制器与测试 |
| `fix-bug` | 修复缺陷 | 根据 Issue 描述定位并修复 Bug |
| `code-review` | 代码审查 | 对 PR 进行结构化审查与反馈 |
| `design-feature` | 功能设计 | 输出功能方案、数据模型与接口定义 |
| `investigate-issue` | 问题排查 | 分析日志与堆栈，定位根因 |
| `ship-release` | 发布上线 | 生成 Changelog、Tag 与发布清单 |

## 🧪 实验概览（5 Labs）

| Lab | 主题 | 时长 | 重点 |
|-----|------|------|------|
| Lab 1 | Copilot 基础与代码补全 | 30 min | 行内补全、Chat 面板、上下文感知 |
| Lab 2 | 自定义指令与 Prompt 工程 | 30 min | `copilot-instructions.md`、Prompt 模板 |
| Lab 3 | 智能体协作（Agent Mode） | 40 min | 多智能体调用、角色分工 |
| Lab 4 | 端到端功能开发 | 40 min | 从设计到发布的全流程实战 |
| Lab 5 | 安全审查与红队对抗 | 40 min | 安全扫描、对抗性 Prompt、防护策略 |

## ✅ 前置条件

- **VS Code** 最新版（推荐 1.90+）
- **GitHub Copilot** 有效许可证（Individual / Business / Enterprise）
- **Node.js 18+**（用于示例项目运行）
- Git 基本操作能力

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/<org>/copilot-workshop.git
cd copilot-workshop

# 2. 安装依赖
npm install

# 3. 用 VS Code 打开
code .

# 4. 确认 Copilot 扩展已启用，进入 labs/lab-1/ 开始实验
```

## 📚 参考资料

- [garrytan/gstack](https://github.com/garrytan/gstack) — GStack 参考架构
- [GitHub Copilot 官方文档](https://docs.github.com/en/copilot)
- [Copilot Extensions & Agents](https://docs.github.com/en/copilot/customizing-copilot)

## 📄 License

[MIT](../LICENSE)
