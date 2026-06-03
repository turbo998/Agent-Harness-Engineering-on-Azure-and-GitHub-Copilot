# 从静态到动态 Harness 的范式跃迁 + Quarantine 安全模式

> 来源 / Source：Anthropic 官方博客《A harness for every task — Dynamic Workflows in Claude Code》——https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
> 中文解读：https://mp.weixin.qq.com/s/hxBkT-iJleQkaODzjWVC2A

## 1. 本 Workshop 的位置：三柱都是 **静态 Harness**

本 Workshop 的三柱——**CCGS**（Claude Code in GitHub Spaces）、**OpenShell**、**GitHub Copilot**——按 Anthropic 新词汇分类，**都是 static harness（静态脚手架）**。编排图由人在写代码时就敲定：

- `chatmode.md` 定义单个 Agent 的角色和工具预算。
- `prompt.md` 定义单个任务的步骤。
- `workflow.yml` 定义 jobs 之间的 DAG。

这张图在 authoring time 就锁死了。LLM 只能**填空**（要改哪个文件，写什么代码），但编排的**形状**——开几个 Agent、谁审谁、什么时候 fan-out——是你这个 harness 作者拍板的。这通常是正确的默认值：可审计、可复现、爆炸半径可控。

## 2. Dynamic Harness：让 LLM 自己写编排脚本

Opus 4.8 发布日 blog 的新东西是：**让 LLM 在运行时现场吐出一段 JavaScript 编排脚本，然后执行它**。这段脚本可以调用 `agent()`、`parallel()`、`pipeline()` 等原语；它可以临场决定"这个任务需要 12 个并行 worker 加一轮 3 局对抗"，也可以决定"下一个任务一个 Agent 加 `Loop-Until-Stable` 就够了"。Harness 不再是仓库里一份固定文件，而是和答案一起、**逐任务生成**的产物。

为什么这件事重要：一个针对"review PR"调优过的静态 harness，去做"用 Rust 重写整个 runtime"会非常糟糕，反之亦然。Opus 4.8 之前的应对方式是维护一堆 chatmode 和 workflow 形成动物园；而 dynamic harness 的押注是——**模型已经足够强，可以基于任务描述 + 可用原语，当场设计出合适的 harness**。

关键原语：

- `agent({ system, input, tools })` —— 在新 context 里启动一个子 Agent。
- `parallel([...promises])` —— 扇出。
- `pipeline([stepA, stepB, stepC])` —— 串接。

这三个就足以表达[上一篇](./six-orchestration-patterns.md)的 6 种编排模式。

## 3. 真实案例：Bun 项目 Zig → Rust 重写

Blog 拿出来的头号案例，是 **Bun** 团队用 Claude Code 推动了一大块 Zig → Rust 重写。模型生成的 dynamic harness 大致做了这些：

1. **按文件/调用点 fan-out**。对每个 Zig 源文件，开一个**独立 git worktree** 上的 Agent（这样并发改动在文件系统层就不会撞车）。
2. **每个 worker 内部 pipeline**：读 Zig → 生成 Rust → 跑 `cargo check` → 迭代。
3. **对抗式 review**。一个独立 reviewer Agent，**看不到 Zig 原文**，只读 Rust 输出，把所有看着不地道、不健全的地方标出来。
4. **Reduce**。最后一个 Agent 跨文件检查不变量（FFI 签名对齐、共享类型一致），按逻辑块各开一个 PR。

关键在于：**开几个 worktree、review loop 多深、哪些 trivial 文件可以跳过 review**，这些都是模型基于代码库形状现场决定的。一个静态 workflow 作者**不可能预测**到所有这些分支。

## 4. 真实案例：Cat Wu 的 A/B flag 清理

Cat Wu（Anthropic）演示了一个更小、但和 GHCP 用户日常更贴近的场景：清理失效的 A/B feature flag。生成的 dynamic harness：

1. 生成一份查询计划，把所有 flag 引用找出来（ripgrep + LSP）。
2. 对每个调用点做 **Classify-Route**：flag 已恒为 true → inline true 分支；flag 已恒为 false → 删除 false 分支；模糊 → 走人工审查队列。
3. 按文件做 **Loop-Until-Stable** 修改，直到 typechecker 闭嘴。
4. 通过 **Reduce** 所有 per-file diff 生成 changelog。

这里的 harness 很短——大概 40 行生成的 JS——但每一阶段都用到了 6 种模式之一。**模型没有发明新模式，它在组合已知模式**。

## 5. Quarantine（隔离模式）——把隔离纳入编排关注点

整篇 blog 在安全上最关键的概念是 **Quarantine（隔离）**：当一个 Agent 在读不可信内容（网页、陌生人写的 PR description、外部 API 输出）时，**它绝不能同时持有高权限工具**。只有处理过 sanitized summary（脱敏摘要）的另一个 Agent，才有资格调用危险 API。

映射到 Azure 企业场景：

- **Reader Agent**：工具是 `fetch`、`readFile`、`searchWeb`。**没有** Azure Managed Identity。它读世界，然后吐出结构化、脱敏后的摘要（typed JSON，prompt-injection sentinel 已剥离）。
- **Executor Agent**：工具是 `arm.deploy`、`keyvault.getSecret`、`storage.write`。挂着 Managed Identity。它**只**接收脱敏后的摘要，从来看不到外部原始字节。它的 system prompt 不会被 reader 看到的任何东西影响到。

这是分层防御：

| 层 | 机制 | 防住什么 |
|---|---|---|
| 基础设施层 | `disableLocalAuth=true` + Managed Identity + RBAC scoping | 凭据即便被偷也用不了；通往 Azure 的唯一路径是 Agent 进程持有的身份。 |
| Agent 编排层 | Quarantine 模式（reader / executor 拆分） | 不可信内容里的 prompt injection 触达不到 executor 的 tool call，因为 executor 从未见过那段不可信字节。 |

两者**缺一不可**。光靠基础设施层硬化，挡不住"一个全权 Agent 被恶意 README 说服去跑 `rm -rf`"；光靠 Quarantine，挡不住"一把 API key 被泄露"。两者互补。

## 6. Lab 3 收尾：在三柱图上补上第四代

Lab 3 的收尾投影上，我们把 Workshop "三柱" 图扩成四列，加上一列 **Dynamic Harness**，并把演进梳理为：

1. **单 Agent IDE 辅助**（早期 Copilot Chat）——无 harness。
2. **静态 chatmode / prompt-file harness**（Lab 1）——作者写角色拆分。
3. **静态 workflow / 多 Agent DAG**（Lab 2）——作者写编排图。
4. **Dynamic harness**（Lab 3 展望）——模型吐编排图；作者写**原语集**、**预算上限**、**隔离边界**。

作者的工作没有消失，只是**上移了**：你不再写 workflow，转而去写**运行 workflow 的 runtime**——定义有哪些原语、每个被 spawn 出来的 Agent 能持有哪些工具、信任边界在哪、最大花费多少。这是未来 12 个月最值钱的 harness-engineering 技能集，也正是本 Workshop 在为你打底的方向。
