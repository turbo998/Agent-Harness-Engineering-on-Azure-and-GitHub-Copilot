<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Claude Code Dynamic Workflows — 第四种编排原语（Subagents / Skills / Agent Teams 之外）

> 截至 **2026-07-07** 核实。官方页面 `code.claude.com/docs/en/workflows`（curl 200）。
> 一句话主旨：**Claude Code 现在有四种"让多个 agent 一起干活"的原语，且谁持有"计划"是唯一的分类轴——Anthropic 官方原文用一张表把四者摆在一起对比，这张表本身就是最好的架构图素材。**

---

## 0. 为什么这条值得单独开一篇（而不是塞进 parity cheatsheet 一行）

1. **官方明确支持 Microsoft Foundry 部署**（连同 Bedrock/Vertex）——原文：*"Dynamic workflows require Claude Code v2.1.154 or later and are available on all paid plans, with Anthropic API access, and on Amazon Bedrock, Google Cloud's Agent Platform, and Microsoft Foundry."* 这是"Claude Code 能不能在 Azure 生态里跑复杂编排"问答的直接论据。
2. **是"计划即代码（plan-as-code）"模式的具体实现**——对架构图工作有直接可画的落点（见 §3）。

---

## 1. 核心区分轴：谁持有"计划"（Anthropic 官方对照表，逐字翻译整理）

| | **Subagents** | **Skills** | **Agent Teams** | **Workflows** |
|---|---|---|---|---|
| 是什么 | Claude 派生的一个 worker | Claude 遵循的指令 | 一个 lead agent 监督对等 sessions | **运行时执行的一段脚本** |
| 谁决定下一步跑什么 | Claude，逐轮决定 | Claude，跟随 prompt | lead agent，逐轮决定 | **脚本本身** |
| 中间结果存在哪 | Claude 的 context window | Claude 的 context window | 共享任务列表 | **脚本变量** |
| 可复用的是什么 | worker 定义 | 指令内容 | team 定义 | **编排逻辑本身** |
| 规模 | 每轮几个委派任务 | 同 subagents | 少数几个长驻 peer | **每次运行几十到几百个 agent** |
| 中断后 | 重启该轮 | 重启该轮 | teammate 继续跑 | **同一 session 内可恢复（resumable）** |

**官方原文金句**：*"A workflow moves the plan into code. With subagents, skills, and agent teams, Claude is the orchestrator: it decides turn by turn what to spawn or assign next, and every result lands in a context window. A workflow script holds the loop, the branching, and the intermediate results itself, so Claude's context holds only the final answer."*

翻译成 SA 语言：**前三种是"Claude 自己临场指挥"，Workflows 是"把指挥逻辑写成可复用、可版本控制、可重跑的脚本"**——更接近传统软件工程里的"编排器代码"而非"每次现场即兴调度"。

---

## 2. 关键机制细节（写进 POC/架构图前必须知道）

### 2.1 触发方式
- **Prompt 里说人话**："use a workflow to ..."，或包含关键字 `ultracode`（v2.1.160 之前是字面触发词 `workflow`，之后放宽为自然语言也生效）。
- **`/effort ultracode`**：把会话整体切到"自动为每个实质性任务规划 workflow"模式（结合 `xhigh` 推理档），**每个任务可能连续触发好几个 workflow**（理解代码→改代码→验证各一个）——**token 消耗和耗时显著上升**，适合"这个任务真的值得砸资源"场景，不建议常态开启。
- **内置 bundled workflow**：`/deep-research <question>`——多角度扇出网页搜索、交叉核验来源、投票裁定每条 claim、输出带引用的报告，**验证不了的 claim 从 v2.1.196 起标"unverified"而非直接判"证伪"**（这条修复本身就是"fail-loud 优于强行下结论"的官方实践佐证）。

### 2.2 脚本长什么样（官方给的最小示例，逐字摘录）
```javascript
export const meta = {
  name: 'audit-routes',
  description: 'Audit every route handler for missing auth checks',
}

const found = await agent('List every .ts file under src/routes/.', {
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})

const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)

return audits.filter(Boolean)
```
- `agent()` 派生一个 subagent；`pipeline()` 对列表中每一项派生一个。容量口径以 Claude Code workflows 当前文档为准：单次运行并发与总量均有上限，适合把循环/条件分支写成可复用脚本。
- 保存位置：`.claude/workflows/`（项目级，随仓库分发）或 `~/.claude/workflows/`（个人级）；保存后即成为 `/<name>` 命令，出现在 `/` 自动补全里——这是把编排逻辑固化为可复用脚本的官方机制。

### 2.3 硬限制（做容量规划/客户预期管理要用）
| 约束 | 数值 | 含义 |
|---|---|---|
| 单次运行最大并发 agent 数 | 16（CPU 核心少的机器更低） | 限制本地资源占用 |
| 单次运行总 agent 数上限 | 1,000 | 防止失控循环 |
| 运行中用户输入 | **不支持**（只有 agent 权限弹窗能暂停） | 要分阶段人工签核，得拆成多个独立 workflow |
| 文件系统/shell 直接访问 | Workflow 脚本本身**没有**，只有它派生的 agent 有 | 脚本是纯编排层，不直接摸文件系统 |
| 跨 session 恢复 | **仅限同一 Claude Code session 内**；退出 CLI 后下次是全新运行 | 无人值守场景要注意——不是"永久后台任务" |

### 2.4 权限与审批（无人值守/自治相关，直接关联 `agent-command-execution-authz-tristack-cheatsheet.md`）
- Workflow 派生的所有 agent **始终以 `acceptEdits` 模式运行**，继承你会话的工具白名单——**不管你会话本身是什么权限模式**。文件编辑自动批准；shell 命令/网络请求/MCP 工具若不在白名单内，仍可能在运行中弹窗打断——长时间运行前建议先把需要的命令加进白名单。
- 审批时机因权限模式而异：Default/accept-edits 模式每次运行都问（除非选了"以后都不问"）；Auto 模式只在首次启动问一次；`claude -p`/Agent SDK/bypass-permissions **完全不问，直接跑**。
- **组织级可关闭**：管理员可在 managed settings 里设 `disableWorkflows: true`，或设环境变量 `CLAUDE_CODE_DISABLE_WORKFLOWS=1`——企业客户想暂缓采用这个新原语时,这是标准答案。

### 2.5 成本
- 一次 workflow 运行可能比同一任务走对话形式消耗**明显更多 token**（很好理解——本质是几十上百个 agent 并行）。
- 官方建议:先在小范围（一个目录而非整个仓库）试跑评估花销,再扩大范围。
- `/workflows` 视图实时显示每个 agent 的 token 用量,可随时停止且不丢失已完成部分的工作。
- **新旋钮（v2.1.202,07-06 才上线）**：`/config` 里的 "Dynamic workflow size" 设置(`unrestricted`/`small`<5 agents/`medium`<15/`large`<50)——是"建议"而非硬限制,显式要求更大规模的 prompt 仍会覆盖它,但能给团队一个默认更保守的基线。

---

## 3. SA 三大日常落点

| 日常 | 落点 |
|---|---|
| **技术问答** | 客户问"Claude Code 能做大规模代码库审计/迁移吗？和 subagent 有什么区别？" → 直接用 §1 的四列对照表回答，比空口描述有说服力；同时能纠正"agent teams 和 workflows 是一回事"的常见混淆。 |
| **POC 部署** | 客户想做"500 文件迁移"/"逐路由安全审计"这类大规模重复性任务的 POC → Dynamic Workflows 的 bundled 示例（`/deep-research`）与官方给的 6 个 example prompt（审计/修复直到检查通过/并行迁移/审查+汇总/多源调研/找问题直到收敛）直接对应大多数企业 POC 场景，可以现场演示而非从零设计编排脚本。 |
| **架构图** | §1 的四路对比表本身就是一张现成的"agent 编排模式选择"决策图素材；§2.2 的"script holds intermediate results in variables, not context window"是画"编排层 vs 执行层"分离架构时的关键设计原则（对应传统系统里"orchestrator 状态外置于 workflow engine 而非常驻进程内存"的经典模式，如 Azure Durable Functions 的 orchestrator function 存档机制）。 |
| **反哺 harness workshop** | 适合补充到“多 agent 编排”章节：单开一页“四种编排原语对照”，直接引用 §1 表格并保留 host/version 标注。**[→harness]** |

---

## 4. Fail-loud：未核实 / 需要下次验证的点

- Microsoft Foundry 上具体如何跑 Claude Code workflows（是否有专门的部署文档/教程）——**本次只核实了官方页面提到"available on ... Microsoft Foundry"这句话，没有找到 Foundry 侧配套的部署指南**，下次可专门搜索 Foundry 文档侧是否有对应说明。
- `/deep-research` 的"投票裁定 claim"具体算法/阈值——官方页面没有展开,标未核实。
- Dynamic Workflows 与本文重点关注的"Microsoft Foundry 部署"两者结合后的**实际计费方式**（是否按 agent 数/token 数在 Foundry 侧单独计价）——未核实。
- 本文全部内容来自单一权威来源（`code.claude.com/docs/en/workflows`,配合 CHANGELOG.md 交叉核实版本时间线),未做第三方评测/社区实测交叉验证。

---

## 5. 核实清单（本文引用来源）

| 来源 | URL | 状态 |
|---|---|---|
| Dynamic workflows 官方页 | https://code.claude.com/docs/en/workflows | 200（mcp_brightdata_scrape_as_markdown 抓取全文） |
| Goals 官方页（`/goal`，用于对照"另一种保持 session 运转"的机制） | https://code.claude.com/docs/en/goal | 200 |
| Remote Control 官方页（用于核实 Foundry 相关表述） | https://code.claude.com/docs/en/remote-control | 200（curl 抓取，含"not available on ... Microsoft Foundry"字样，注意这是 Remote Control 功能的限制，不是 Workflows 功能的限制——两者对 Foundry 的支持范围不同，不要混淆） |
| Claude Code CHANGELOG.md（版本时间线） | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | 200 |
| npm registry（版本发布时间精确核实） | https://registry.npmjs.org/@anthropic-ai/claude-code | 200（v2.1.154 发布于 2026-05-28T15:40:50.400Z） |

> ⚠️ **重要澄清（避免误导）**：`/goal` 与 `/remote-control` 页面均提到 "not available on ... Microsoft Foundry" 或类似限制字样，但那是针对 **Remote Control（远程控制面）** 这个具体功能的限制，与 **Dynamic Workflows 本身在 Foundry 上可用**（workflows 官方页原文）并不矛盾——是两个不同的功能维度，各自的 Foundry 兼容性范围不同，写给客户时务必分开讲清楚,不要合并成一句"Claude Code 在 Foundry 上功能不全"或"完全可用"的笼统结论。
