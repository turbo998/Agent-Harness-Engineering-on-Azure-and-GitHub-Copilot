<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 渐进式教学 Workshop 工程模式速查（GitHub Template + Action 自动推进）

> **2026-07-10 来源快照**：`Azure-Samples/foundry-hosted-agents-workshop`。原记录中 README/`advance_step.py`/`render_readme.py` 三份源码返回 200；可达性不等于机制已实测。本文评估工程设计，不以 star/fork 推断质量或动机。
> **[→harness] 本篇适合作为渐进式 workshop 设计参考。**

## 一句话是什么

微软官方发布的「Travel Assistant」渐进式 Foundry Agent Framework 教学模板：参与者从 **fork 一个 GitHub Template 仓库**开始，每完成一步就 `git push`，一个 GitHub Action 自动把下一步的教学内容和起始代码铺到仓库里、**重写 README.md 为下一步的说明**——参与者永远只看到"当前该做什么"，不需要翻多个文档或手动 checkout 分支。

## 为什么现在值得记录（适用场景）

1. **合作伙伴自助学习**（不需要我们在场逐步讲解）；
2. **多人共学时的进度追踪**（每个人的仓库 fork 里 `.workshop_instance/.workshop-state.json` 就是他们的进度存档）。

## 核心机制拆解（源码级，非营销 README 转述）

### 1. 目录角色三分（这是最值得抄的设计决策）

```
repo-root/
  README.md                      # 【契约】永远是"当前步骤"的内容——参与者只看这个文件
  travel_assistant/               # 【交付物】参与者实际编写/运行的 agent 代码，逐步增量
  .workshop/                      # 【教学素材，只读】出题者维护：每步的起始代码快照 + README 片段
    step_files/<N>/
    docs/partials/、docs/steps/
    scripts/advance_step.py       # 状态机引擎（纯 stdlib，无需装依赖即可在 GH Actions 里跑）
    scripts/render_readme.py      # README 拼装器（header + 进度条 + 当前步骤正文 + footer）
  .workshop_instance/             # 【运行时状态，参与者专属】
    .workshop-state.json          # 当前 step 编号 + schema 版本
    workshop_backups/step-<N>/    # 每次推进前，参与者对上一步的个人修改自动备份于此
  .github/workflows/
    advance-on-push.yml           # push 到 main 时触发：调用 advance_step.py 前先判定"这次 push 算不算完成一步"
```

**教学工程原则**：素材（`.workshop/`）与交付物（`travel_assistant/`）与运行时状态（`.workshop_instance/`）三者**物理隔离在不同目录**，出题者更新素材不会覆盖参与者的代码，参与者的备份不会污染素材目录。若某个 workshop 存在“文档和 demo 代码混放”的假设场景，这会是优先考虑的改进点。

### 2. 双模式推进（云端 Action 与本地脚本共享同一状态机）

- **Actions 模式**：参与者 `git push` 到 `main` → `advance-on-push.yml` 触发 → 判断本次 push 是否只动了"工作坊机器目录"（`.github/`、`.workshop/`、Makefile 等）—— 如果只动了这些，**不推进**（这是为了让参与者能拉取上游素材更新而不误触发进度）；否则调用 `advance_step.py` 推进一步。
- **本地模式**（无网络/无 Actions 权限场景，如企业内网离线 workshop）：参与者自己跑 `python .workshop/scripts/advance_step.py --expected-current-step <N> --auto-commit`，推进逻辑与云端共用同一状态机——**同一份 Python 脚本被两条路径复用**，降低双实现失配风险；但云端 Action 与本地运行的权限、网络、凭据和审计环境仍不同，不能据此断言效果完全一致。
- **`--auto-commit` 只 stage 工作坊管理的路径**（`README.md`/`.workshop_instance/.workshop-state.json`/`travel_assistant/`/备份目录），不会误将参与者未跟踪的散落文件一并提交——这是"自动化脚本要不要 `git add -A`"的一个好范例（不要，显式列路径）。
- **`SKIP_ADVANCE_SENTINEL`（`[skip-advance]` commit message 标记）**：`--reset` 类操作会重写 state 文件到*同一个*步骤（可能是空 diff），仅凭"state 文件变没变"无法判断是否该拦截自动推进,于是用一个**显式的 commit message 哨兵字符串**来兜底,这是"状态机的边界条件判断,单一信号不够用时加显式信号"的具体例子。

### 3. Step marker 驱动渲染，而非硬编码文件名

`README.md` 顶部藏一个 HTML 注释 `<!-- step: N -->`，`render_readme.py` 靠正则解析这个 marker 决定"当前在哪一步"、要拼哪个 `docs/steps/<N>.md` 片段——**状态存在文件内容里，而不是文件名或额外的元数据服务**，这样"当前是第几步"这件事在 `git diff`/`git blame` 里一目了然，出问题时人工也能读懂状态，不需要额外工具解析。

### 4. `_root` 覆盖目录解决"有些文件不该进交付物快照"的问题

多数 step 的起始代码要铺进 `travel_assistant/`（参与者的交付物目录），但有些文件（如 `travel_toolbox/toolbox.yaml`）**必须在仓库根目录**、且**不能**被 `azd ai agent init` 之类的工具误当成"要打包进 agent 镜像的一部分"扫进去。用一个保留子目录名 `_root` 存放"应铺到仓库根而非 `travel_assistant/` 内"的文件——这是"教学交付物目录 vs 部署工具自动扫描范围"两者边界不重合时的一个具体解法；在“demo 代码目录”与“部署脚本实际扫描目录”不完全重合的假设场景下，这个模式可作为参考。

### 5. 9 个 step 的能力递进顺序（可直接借鉴的教学序列设计）

| Step | 内容 | 递进逻辑 |
|---|---|---|
| 1 | 基础 hosted agent | 先能跑起来 |
| 2 | Function tools（天气/时间/汇率）| 加确定性工具调用 |
| 3 | MCP 集成（外部旅行文档）| 加外部数据/工具协议 |
| 4 | Foundry Toolbox（Code Interpreter + web search）| 加平台托管工具 |
| 5 | RAG（Azure AI Search 目的地知识库）| 加检索增强 |
| 6 | 打包为 Skill | 把前面的行为封装复用 |
| 7 | 多 agent（flight/hotel/activities 专家协同）| 单体→多智能体 |
| 8 🧪 | Durable workflow（experimental）| 加持久化/断点续跑 |
| 9 🧪 | Foundry Memory（experimental）| 加跨会话记忆 |

**教学排序的价值判断**：把"多 agent 协同"放在"RAG"之后、"打包 skill"之前——先让参与者积累够多可复用的能力（工具+RAG），再学"怎么把这些行为封装成可分发的 skill"，最后才学"怎么协调多个这样的 agent"。这个顺序本身就是一个可复用的"能力递进"参考序列，尤其是**"先单 agent 吃满能力、再学多 agent 编排"**这个先后关系，可与常见 MAF 编排原语（Sequential/Concurrent/Handoff/Group）教学顺序对齐。

## SA 落点（这如何让我的工作更快更好）

| 场景 | 具体动作 |
|---|---|
| **技术问答** | 客户问"有没有官方的 Foundry Agent Framework 渐进式教程"——现在有具体名字和 URL 可以甩出去，不用现编 demo 大纲。 |
| **POC 部署** | 这个仓库本身就是一个可 fork 直接跑的 9 步 POC 骨架（travel assistant），比从零撸 demo 快；`_root` 覆盖机制解决的"toolbox.yaml 不能被 agent 镜像扫描"问题，如果我们自己的 POC 也用 `azd ai agent init`，直接踩得上同一个坑，可以提前预警客户。 |
| **架构图** | Step 7"多 agent 协同"和 Step 8"durable workflow"的组件关系，可以作为「渐进式 agent 能力分层」架构图的分层依据（对照多 agent / MCP / A2A 架构图）。 |
| **harness workshop 改版** | **参考落点**：目录三分（素材/交付物/运行时状态）+ 双模式推进（云端 Action / 本地脚本共享同一状态机）+ step marker 驱动渲染，三个设计可用于假设中的 workshop 改版，把“讲义”演进为“可执行的教学状态机”。建议改版前通读 `advance_step.py`（1059 行）全文而非仅本篇摘要。 |

## Fail-loud（未核实项）

- 未验证这套机制在**多人协作同一 fork**（而非每人各自 fork）场景下是否会冲突——README 假设的是"每个参与者拥有自己的仓库副本"。
- `.github/workflows/` 目录内容因 GitHub API 限流（`contents` 端点 403）**未直接读取** `advance-on-push.yml` 全文，上述"只动机器目录不触发推进"的判断逻辑是从 `advance_step.py` 里的常量注释（`SKIP_ADVANCE_SENTINEL` 附近）反推的，**不是从 workflow YAML 源码直接确认**——下次访问建议改用 `raw.githubusercontent.com/.../.github/workflows/advance-on-push.yml` 绕开 API 限流直接读取完整判定逻辑。
- 该仓库创建于 2026-07-06，处于早期阶段（star/fork 均个位数），**未核实**是否已有其他团队/客户实际使用过，也未核实是否会持续维护。

## 核实的 URL

- https://github.com/Azure-Samples/foundry-hosted-agents-workshop （200，API 核实 owner_type=Organization）
- https://raw.githubusercontent.com/Azure-Samples/foundry-hosted-agents-workshop/main/README.md （200，全文读取）
- https://raw.githubusercontent.com/Azure-Samples/foundry-hosted-agents-workshop/main/.workshop/scripts/advance_step.py （200，1059 行，读取前 60 行确认核心机制）
- https://raw.githubusercontent.com/Azure-Samples/foundry-hosted-agents-workshop/main/.workshop/scripts/render_readme.py （200，280 行，读取前 70 行确认 step marker 机制）
