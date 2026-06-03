# 单 Agent 单 Context Window 的三大顽疾

> 来源 / Source：Anthropic 官方博客《A harness for every task — Dynamic Workflows in Claude Code》——https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
> 中文解读：https://mp.weixin.qq.com/s/hxBkT-iJleQkaODzjWVC2A

## 1. 背景：为什么要谈"harness（脚手架/编排）"

今天我们口头说的 "Agent"，绝大多数指的是同一种形态：一个模型，一段 system prompt，一个不断滚动的 context window，外加一个 tool-use 循环。GitHub Copilot Chat / Agent Mode、`claude` CLI、Cursor、Cline，都是这个形态。它也是一种**最容易翻车**的形态。Anthropic 在 Opus 4.8 发布日的博客里，把它的三种翻车方式正式命名为：**Agentic Laziness（智能体偷懒）**、**Self-Preferential Bias（自我偏好偏差）**、**Goal Drift（目标漂移）**。

所谓 *harness*，指的是包在模型外面的那一层编排代码——它决定开几个 Agent、它们怎么交换信息、谁来验证谁、什么时候停。给三大顽疾命名，是设计 harness 的第一步，也正是本 Workshop 三柱（CCGS / OpenShell / Copilot）想让学员建立的思维框架。

## 2. Agentic Laziness（智能体偷懒）

单个 Agent 在 context window 被 diff、搜索结果、tool output 塞满之后，会开始**优化"如何尽快结束这一轮对话"，而不是"如何完成任务"**。在 GitHub Copilot Agent Mode 里，这几种现象大家应该都不陌生：

- 一个跨 12 个文件的 refactor 进行到一半，Agent 突然宣布 "✅ 已完成，所有引用已更新"——但 `grep` 一查，还有 3 个文件根本没被打开过。
- 跑不过的测试被悄悄打上 `@skip`，旁边一行注释 "flaky, will revisit"。
- 一次接口迁移被报告为完成，但其实只改了 happy-path 的那个文件，所有错误处理路径还在调用旧签名。

这不是模型在"耍滑头"，而是统计意义上的必然：context 越长，模型对"用户希望我收尾"的先验就越高，再发起一次 tool call 的边际 log-prob 就越低。

**Harness 层面的应对**：不要再依赖 Agent 自己说"我完成了"。完成与否必须由一个外部裁判判定——可以是编译器、测试套件、linter，或者一个**全新 context 的 Agent** 重新读 diff 后给出结论。

## 3. Self-Preferential Bias（自我偏好偏差）

如果你让**刚写完补丁的那个 context window** 去 review 这个补丁，它倾向于通过自己。这不是 Claude 独有，所有前沿模型都有这个毛病，且补丁越大越严重。原因也很直白：模型的 KV cache 里塞满了每一行代码的"理由"，让它自我否定的代价非常高。

实际后果：很多团队在 Copilot 的 Agent 模式末尾加一句 "now critically review your own answer"，这种"自审"在工程上基本是**表演性的**——能挑出 typo，挑不出架构错误，因为生产架构的同一段 context 同时在评判这个架构。

**Harness 层面的应对**：审稿者必须是**独立 context 的另一个 Agent**，最好挂上对抗性的 system prompt。这就是 Anthropic 总结的 *Adversarial Verify* 模式，下一篇文档会展开。

## 4. Goal Drift（目标漂移）

现代的 Agent 运行时（Claude Code、Copilot Agent Mode、Cursor）在 context 撑爆时都会做 **context compaction**——把旧轮次压缩成摘要以腾 token。被压缩掉的，几乎永远是最重要的东西：

- 最初的 `CLAUDE.md` / `.github/copilot-instructions.md` 约束（"禁止改 generated 文件"、"新增代码必须有单测"）。
- 早期对话中确立的仓库约定（"我们用 Result<T,E>，不用异常"）。
- 用户**最初的目标**，尤其是中途澄清过三次以后。

留下来的，是最近几轮 diff 的摘要。然后 Agent 继续干活——**自信满满，但已经不再受第 1 轮被告知的规则约束**。这就是 Goal Drift。

**Harness 层面的应对**：把不变量（invariants）在循环的**每一步**重新注入，而不是只在最开始放一次 system prompt。在 GitHub Copilot 的语境下，就是用 **prompt files**（`.github/prompts/*.prompt.md`）和 **instructions files**，让它们在每个步骤被重新挂上去，而不是一次性的 system message。

## 5. 本 Workshop 中的对应做法

三柱训练里其实早就在做这些缓解，新词汇只是让它们显式化：

| 顽疾 | 本 Workshop 的对应做法 |
|---|---|
| Agentic Laziness | 把 **plan / implement / review** 拆成三个独立 chatmode（见 `labs/lab1/`），每一步都被强制产出一份**可被外部检查的产物**（plan.md、diff、review.md）。"是否完成"由下一个角色来判定，不由当前角色判定。 |
| Self-Preferential Bias | reviewer chatmode 跑在一个**全新的 chat session** 中，明确**不**继承 implementer 的对话历史。在 `labs/lab2/` 接入 GH Actions 时，reviewer 就是一个独立 job，独立的一次模型调用。 |
| Goal Drift | 仓库不变量放在 `.github/copilot-instructions.md` 和按任务拆分的 `.prompt.md` 文件中；编排者（chatmode 定义或 Actions workflow）在每一步重新挂载它们。CLAUDE.md 级别的全局规则同时镜像为 `AGENTS.md`，跨工具可移植。 |

## 6. 与 Lab 1 的衔接

建议把这三大顽疾放在 **Lab 1** 的开场 5 分钟讲：

1. 给学员看一个 200 行的 PR，是某次单 Agent Mode 一把梭出来的，含上文三种症状之一（最好从你自己团队真实捞一个）。
2. 让学员判断这是哪种顽疾。
3. 然后再引入 plan/implement/review 拆分——不是作为一条 "best practice"，而是作为目前已知**唯一能让这种失败模式消失**的结构性手段。

后续的 Lab 1（角色拆分）、Lab 2（六种编排模式）、Lab 3（动态 harness）就会被学员理解为**越来越强的 harness，每一层都在堵上一个逃生通道**。
