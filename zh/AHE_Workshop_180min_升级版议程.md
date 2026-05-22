# GitHub Copilot Workshop 180分钟升级版议程

> **版本**: v2.0 | **时长**: 180分钟 (含10分钟弹性缓冲) | **Labs**: 5个

---

## 议程总览

| 序号 | 环节 | 时长 | 累计时间 |
|------|------|------|----------|
| 0 | 开场 | 10min | 0:10 |
| 1 | 第一部分：AI-DLC 概念 | 15min | 0:25 |
| L1 | Lab 1：AI-DLC 全生命周期 | 20min | 0:45 |
| 2 | 第二部分：Harness Engineering 深度讲解 | 20min | 1:05 |
| L2 | Lab 2：Harness Engineering 实践 | 25min | 1:30 |
| ☕ | 茶歇 | 10min | 1:40 |
| 3 | 第三部分：多Agent协作与角色分工 | 15min | 1:55 |
| L3 | Lab 3：多Agent串行协作 | 20min | 2:15 |
| L4+ | **Lab 4+（进阶选修）：基于 GitHub Spec-Kit 的规格驱动开发** | **30–35min** | *(承接 Lab 3 的工业化升级)* |
| L4 | Lab 4：多角色联合代码审查 | 20min | 2:35 |
| 4 | 第四部分：端到端发布流程 | 10min | 2:45 |
| L5 | Lab 5：端到端发布流程 | 25min | 3:10 |
| 5 | 总结与Q&A | 10min | 3:20 |

> 💡 总计 200min 的内容，10min 弹性缓冲可根据学员节奏调整各 Lab 时间。

---

## 详细议程

### 0. 开场 (10min) ⏱ 0:00-0:10

**目标**: 破冰、了解学员背景、设定期望

- 讲师自我介绍
- 破冰互动：「你目前使用 Copilot 的频率？」(举手/投票)
- 快速调查学员背景：开发语言、团队规模、AI 工具使用经验
- Workshop 目标与议程预览
- 环境检查：确认 VS Code + Copilot Chat 就绪

### 1. 第一部分：AI-DLC 概念 (15min) ⏱ 0:10-0:25

**目标**: 理解 Copilot 演进路径与 AI-DLC 全生命周期

- **Copilot 演进三阶段**
  - Completions（代码补全）→ Chat（对话式编程）→ Agent（自主代理）
  - 每个阶段的能力跃迁与使用场景
- **AI-DLC 全生命周期概念**
  - AI 辅助开发生命周期 (AI-Development Life Cycle)
  - 从需求分析到部署运维的全链路 AI 赋能
  - 与传统 SDLC 的对比

### Lab 1：AI-DLC 全生命周期 (20min) ⏱ 0:25-0:45

**目标**: 体验 Ask → Plan → Agent 三模式

- 任务：基于 ticket-service 需求，分别使用三种模式
  - Ask 模式：询问技术方案
  - Plan 模式：生成实施计划
  - Agent 模式：自动生成代码
- 对比三种模式的输出差异

### 2. 第二部分：Harness Engineering 深度讲解 (20min) ⏱ 0:45-1:05

**目标**: 掌握 Harness Engineering 三层模型与多角色体系

- **三层模型**
  - 🔧 **规则层 (Rules)**: `.github/copilot-instructions.md` — 全局行为约束
  - 🎭 **角色层 (Agents)**: `.github/agents/*.md` — 专家角色定义
  - 🔄 **工作流层 (Prompts)**: `.github/prompts/*.prompt.md` — 可复用流程模板
- **多角色 Agent 体系** (参考 gstack 理念)
  - 10个专业 Agent 角色分工
  - Agent 间的协作与串联
- **安全护栏**
  - 输入过滤、输出约束、行为边界
  - 防止 prompt injection 与越权操作
- **完整性原则**
  - 确保 AI 生成代码的可测试性、可审查性
  - 人机协作的检查点设计

### Lab 2：Harness Engineering 实践 (25min) ⏱ 1:05-1:30

**目标**: 配置三层模型文件

- 任务 1：编写 `copilot-instructions.md` 全局规则
- 任务 2：创建自定义 Agent（如 `@api-designer`）
- 任务 3：编写 `.prompt.md` 工作流模板
- 验证：调用自定义 Agent 并观察行为变化

### ☕ 茶歇 (10min) ⏱ 1:30-1:40

### 3. 第三部分：多Agent协作与角色分工 (15min) ⏱ 1:40-1:55

**目标**: 理解多 Agent 协作模式

- **10个 Agent 角色介绍**
  - `@code-reviewer` — 代码审查专家
  - `@red-team` — 安全红队
  - `@api-designer` — API 设计师
  - `@test-strategist` — 测试策略师
  - `@perf-analyst` — 性能分析师
  - `@doc-writer` — 文档工程师
  - `@devops-pilot` — DevOps 领航员
  - `@arch-advisor` — 架构顾问
  - `@accessibility-checker` — 无障碍检查员
  - `@tech-debt-tracker` — 技术债务追踪者
- **协作模式**
  - 串行模式：Agent A 输出 → Agent B 输入
  - 并行模式：多 Agent 同时审查同一代码
- **代码审查军团概念**
  - 多视角审查：功能 + 安全 + 性能 + 可访问性
  - 类比真实团队的 code review 流程

### Lab 3：多Agent串行协作 (20min) ⏱ 1:55-2:15

**目标**: 实践 Agent 串行协作链

- 任务：`@api-designer` 设计接口 → `@code-reviewer` 审查 → `@test-strategist` 生成测试
- 观察每个 Agent 如何基于前一个的输出工作
- 记录协作链的优势与局限

> 🔗 **承接 Lab 4+**：刚才我们**手作**的「设计师 → 审查员 → 测试师」交接链，本质上就是一条规格驱动开发（SDD）流水线的雏形。在 Lab 4+ 中，我们将用 **GitHub Spec-Kit** 把同样的协作模式**工业化** —— 把临时的 Agent 串联升级为可复现的 `specify → plan → tasks → implement` 工具链。

### Lab 4+（进阶选修）：基于 GitHub Spec-Kit 的规格驱动开发 (30–35min) ⏱ *选修*

**目标**: 把 Lab 3 的手作多 Agent 交接工业化为可复用的 SDD 流水线

- 在 Workshop 仓库中安装并初始化 [GitHub Spec-Kit](https://github.com/github/spec-kit)
- 通过 SDD 四阶段驱动一个完整特性：
  - `/specify` —— 撰写可执行的规格说明
  - `/plan` —— 生成技术方案
  - `/tasks` —— 拆解为可执行任务
  - `/implement` —— 通过 Copilot Agent 模式执行
- 对比 Lab 3 的手作协作链：可复现性、可追溯性、团队规模化
- 实验材料：[`zh/labs/lab4-spec-driven-development.md`](labs/lab4-spec-driven-development.md)

### Lab 4：多角色联合代码审查 (20min) ⏱ 2:15-2:35

**目标**: 体验多角色并行审查

- 任务：对同一段代码分别调用：
  - `@code-reviewer` — 发现代码质量问题
  - `@red-team` — 发现安全漏洞
  - `@perf-analyst` — 发现性能瓶颈
  - `@accessibility-checker` — 发现无障碍问题
- 汇总审查报告，体会多角色价值

### 4. 第四部分：端到端发布流程 (10min) ⏱ 2:35-2:45

**目标**: 理解 Think→Plan→Build→Review→Test→Ship 全流程

- **gstack 六阶段模型**
  - Think: 需求澄清与技术调研
  - Plan: 任务拆解与方案设计
  - Build: 代码生成与实现
  - Review: 多角色审查
  - Test: 自动化测试生成
  - Ship: 发布与部署
- **Prompt 模板驱动工作流**
  - 每个阶段对应一个 `.prompt.md`
  - 模板串联实现端到端自动化
  - `ship-release.prompt` 示例

### Lab 5：端到端发布流程 (25min) ⏱ 2:45-3:10

**目标**: 完成 Think→Ship 全流程

- 任务：使用 prompt 模板驱动完整发布流程
  - 使用 `think-clarify.prompt` 澄清需求
  - 使用 `plan-tasks.prompt` 拆解任务
  - 使用 Agent 模式 Build 代码
  - 使用 `review-multi.prompt` 多角色审查
  - 使用 `test-generate.prompt` 生成测试
  - 使用 `ship-release.prompt` 生成发布清单
- 回顾全流程，讨论企业落地可行性

### 5. 总结与Q&A (10min) ⏱ 3:10-3:20

**目标**: 总结要点，展望落地

- **关键收获回顾**
  - AI-DLC 全生命周期理念
  - Harness Engineering 三层模型
  - 多 Agent 协作的实践价值
- **企业落地建议**
  - 渐进式引入：规则 → 角色 → 工作流
  - 团队标准化 Prompt 模板库
  - 安全与合规考量
- **gstack 对比**
  - Workshop 内容与 gstack 方法论的映射
  - 进一步学习路径
- **资源链接**
  - GitHub Copilot 官方文档
  - gstack 项目地址
  - awesome-copilot 资源合集
- **Q&A 互动**
