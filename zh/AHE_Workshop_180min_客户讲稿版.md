# GitHub Copilot Harness Engineering Workshop — 客户讲稿版（180分钟）

## Slide 1: 开场欢迎
**要点：**
- 欢迎参加180分钟GitHub Copilot深度工作坊
- 本次主题：Harness Engineering — 驾驭AI编程的工程方法
- 动手为主，5个Lab贯穿全程

**讲稿：** 欢迎各位！今天我们用3小时深入探索GitHub Copilot的工程化用法。不只是写代码补全，而是学会如何系统性地驾驭AI Agent，让它成为团队真正的生产力倍增器。

---

## Slide 2: 调查学员背景（Copilot使用情况）
**要点：**
- 举手调查：谁在日常使用Copilot？
- 使用过Chat模式？Agent模式？
- 了解学员水平，调整讲解节奏

**讲稿：** 在开始之前，我想快速了解大家的背景。请举手示意：日常使用Copilot补全的？用过Copilot Chat的？尝试过Agent模式的？这帮助我调整今天的节奏。

---

## Slide 3: 工作坊目标与议程概览
**要点：**
- 目标：掌握Harness Engineering三层模型，能独立配置10个Agent角色
- 议程：理论讲解→Lab实操→多Agent协作→端到端发布
- 产出：可直接带回团队使用的配置文件和Prompt模板

**讲稿：** 今天的目标很明确——你将带走一套完整的AI工程化配置，包括10个Agent角色定义和6个Prompt模板，可以直接在团队中落地使用。

---

## Slide 4: AI辅助开发的三个阶段（Completions→Chat→Agent）
**要点：**
- Completions：被动补全，Tab接受
- Chat：主动对话，上下文问答
- Agent：自主执行，多步骤任务编排

**讲稿：** AI辅助开发经历了三个阶段。从最初的代码补全，到交互式Chat，再到如今的Agent模式——AI可以自主读文件、跑终端、提PR。今天重点就是如何驾驭Agent。

---

## Slide 5: AI-DLC全生命周期概念
**要点：**
- AI-DLC = AI-Development Life Cycle
- 覆盖：需求分析→设计→编码→审查→测试→部署
- 每个环节都可由专属Agent承担

**讲稿：** AI-DLC是将AI嵌入软件开发全生命周期的理念。不只是写代码那一步，从需求拆解到最终发布，每个环节都有对应的Agent角色来提升效率。

---

## Slide 6: Lab 1 引导（AI-DLC全生命周期实操）
**要点：**
- 用Copilot Agent完成一个从需求到代码的完整流程
- 体验Agent自主读取上下文、生成代码、运行测试
- 时间：15分钟

**讲稿：** 现在进入Lab 1。请打开实验手册，用Copilot Agent模式完成一个小功能的全生命周期。重点感受Agent如何自主完成多步骤任务。

---

## Slide 7: Harness Engineering三层模型（Rules/Roles/Workflows）
**要点：**
- Rules：全局规则，安全护栏
- Roles：10个Agent角色定义
- Workflows：6个Prompt模板驱动的标准流程

**讲稿：** Harness Engineering的核心是三层模型。规则层设底线，角色层定分工，工作流层驱动标准化执行。三层配合，让AI输出可控、可预测、可复用。

---

## Slide 8: 规则层 copilot-instructions.md（安全护栏、代码标准）
**要点：**
- `.github/copilot-instructions.md` 是全局指令文件
- 定义代码风格、安全约束、禁止模式
- 所有Agent自动继承这些规则

**讲稿：** 规则层通过copilot-instructions.md实现。把团队的编码规范、安全红线写进去，所有Agent交互都会自动遵循。这是企业级使用的第一步。

---

## Slide 9: 角色层 10个Agent角色总览表
**要点：**
- 10个角色：Architect、Planner、Coder、Reviewer、Tester、Debugger、DocWriter、SecurityAuditor、Refactorer、Deployer
- 每个角色有专属system prompt和职责边界
- 存放在 `.github/agents/` 目录

**讲稿：** 我们预定义了10个Agent角色，各司其职。从架构师到部署员，每个角色都有明确的职责和约束。就像一个虚拟团队，各自专注自己擅长的事。

---

## Slide 10: 工作流层 Prompt模板驱动（6个模板）
**要点：**
- 6个模板：需求分析、技术设计、代码生成、代码审查、测试生成、发布检查
- 模板标准化输入输出格式
- 存放在 `.github/prompts/` 目录

**讲稿：** 工作流层用6个Prompt模板驱动标准化流程。模板定义了输入什么、输出什么、格式怎样，确保不同人使用Agent的结果一致且高质量。

---

## Slide 11: Lab 2 引导（Harness Engineering实践）
**要点：**
- 配置copilot-instructions.md和Agent角色文件
- 用不同角色完成对应任务
- 时间：20分钟

**讲稿：** Lab 2请大家动手配置三层模型。先写规则文件，再创建至少3个Agent角色，最后用Prompt模板执行一个标准流程。

---

## Slide 12: 茶歇
**要点：**
- 休息10分钟
- 可趁机检查Lab进度
- 有问题可随时找助教

**讲稿：** 休息10分钟！喝杯咖啡，消化一下前半段内容。有任何问题随时交流。

---

## Slide 13: 多Agent协作模式（串行vs并行，参考gstack）
**要点：**
- 串行：Agent A输出 → Agent B输入，流水线模式
- 并行：多Agent同时工作，结果合并
- gstack参考架构：分层编排多Agent

**讲稿：** 单个Agent强大，但多个Agent协作才是真正的生产力飞跃。串行模式像流水线，并行模式像团队协作。gstack提供了一套分层编排的参考架构。

---

## Slide 14: 代码审查军团概念（4个reviewer角色各司其职）
**要点：**
- Logic Reviewer：业务逻辑正确性
- Security Reviewer：安全漏洞扫描
- Performance Reviewer：性能瓶颈识别
- Style Reviewer：代码风格与规范

**讲稿：** 代码审查军团是多Agent并行的典型场景。4个Reviewer各看一个维度，最后汇总意见，比单人审查更全面、更快速。

---

## Slide 15: Lab 3 引导（多Agent串行协作）
**要点：**
- Architect → Planner → Coder 串行流水线
- 上一步输出作为下一步输入
- 时间：15分钟

**讲稿：** Lab 3体验串行协作。先让Architect出方案，Planner拆任务，Coder写实现。感受Agent之间上下文如何流转。

---

## Slide 16: Lab 4 引导（多角色联合代码审查）
**要点：**
- 同一段代码交给4个Reviewer并行审查
- 对比不同角色发现的不同问题
- 时间：15分钟

**讲稿：** Lab 4让4个Reviewer同时审查一段代码。你会发现Security Reviewer和Performance Reviewer关注的点完全不同，多维度审查大幅提升代码质量。

---

## Slide 17: 端到端发布流程 Think→Plan→Build→Review→Test→Ship
**要点：**
- 6阶段闭环：Think→Plan→Build→Review→Test→Ship
- 每阶段对应特定Agent和Prompt模板
- 全流程可追溯、可复现

**讲稿：** 端到端发布流程将前面所学串联起来。从产品思考到最终发布，6个阶段形成闭环，每步都有对应的Agent和模板支撑，实现工程化的AI辅助开发。

---

## Slide 18: Lab 5 引导（端到端发布流程实操）
**要点：**
- 完成一个功能从Think到Ship的完整流程
- 综合运用多Agent和Prompt模板
- 时间：25分钟

**讲稿：** 最后的综合Lab！请完成一个小功能的端到端发布，走完Think到Ship全流程。这是今天所有内容的综合演练。

---

## Slide 19: 企业落地建议（渐进式采纳路线图）
**要点：**
- 第1月：部署规则层，全员使用copilot-instructions.md
- 第2月：引入3-5个核心Agent角色
- 第3月：推广Prompt模板和多Agent协作流程

**讲稿：** 企业落地建议渐进式推进。先从规则层开始，统一编码规范；再逐步引入Agent角色和工作流模板。不要一步到位，让团队逐步适应。

---

## Slide 20: 总结、资源链接与Q&A
**要点：**
- 回顾：三层模型 + 5个Lab + 10个Agent + 6个模板
- 资源：GitHub文档、示例仓库、社区讨论区
- 开放Q&A

**讲稿：** 今天我们从AI辅助开发的演进讲到Harness Engineering的落地实践。带走你的配置文件和模板，回去就能用。现在开放提问，有什么问题都可以聊！
