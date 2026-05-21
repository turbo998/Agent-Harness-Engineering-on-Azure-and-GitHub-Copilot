# 实验 4：Spec-Driven Development with GitHub Spec-Kit

## 实验目标

体验从 **手作多 Agent handoff（Lab 3）** 升级到 **工业化 SDD 多 Agent 流水线** 的关键一跃：

```
/speckit.constitution → /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.analyze → /speckit.implement
        宪法                规约               技术计划            任务拆分            跨产物审查           落地实现
```

完成后,学员应能够:

1. 理解 **Spec-Driven Development (SDD)** 的核心理念:把"对话式开发"沉淀为可审计、可复用、可分工的规约产物
2. 看懂 spec-kit 注入的 `.specify/` 与 `.github/agents/speckit.*` 目录结构
3. 使用 spec-kit 内置的 14 个 agent 完成一个 mini feature 的 SDD 全流程(implement 仅口述)
4. 理解 spec-kit 的 agent handoff 与 Lab 3 手作 handoff 的对应关系

## 实验时长

**30–35 分钟**(讲师演示为主,学员可选跟做)

## 与 Lab 3 的关系

> **承接**: Lab 3 教你"为什么要多 Agent + 如何手写 handoff";Lab 4 给你"现成的 SDD 多 Agent 流水线模板"。

| 维度 | Lab 3:手作 Multi-Agent | Lab 4:Spec-Kit 工业化 SDD |
|---|---|---|
| Agent 数量 | 4 个自定义(developer / test / sec / doc) | 14 个 `speckit.*` 内置 agent |
| Handoff 机制 | 学员用自然语言切换 `@agent` | 每个 agent frontmatter 声明 `handoffs:` 字段,Copilot Chat 给按钮 |
| 产物 | 代码 + 测试 + 文档(分散) | `constitution.md` + `spec.md` + `plan.md` + `tasks.md`(分阶段沉淀) |
| 审计性 | 弱(全在 Chat 历史里) | 强(每个阶段都是 git tracked markdown) |
| 任务并行 | 学员脑内规划 | `tasks.md` 自动标 `[P]` 并行标记 |
| 适用范围 | 单仓库小任务 | 任何中大型 feature / 团队协作 |

**叙事弧线**: 手作 → 工业化 → 规约驱动。

---

## 前置条件 / 环境检查

### 必备

- Python **3.11+**(spec-kit 0.8 起强制)
- `uv` 包管理器(或 pipx / pip --user)
- VS Code **Insiders**(Custom Agents 支持最稳)+ GitHub Copilot Chat
- 已完成 Lab 2 / Lab 3,熟悉 `lab-starter` 的 Ticket Service 代码

### 一键检查

```bash
specify check
```

预期输出:`✔ git`, `✔ python>=3.11`, `✔ copilot integration` 全绿。

### 如果讲师 VM 没有预装 — Fallback

```bash
# 安装 uv(如未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 specify-cli(锁定主分支,避免 0.10 破坏性变更)
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 验证
specify --version   # 期望 0.8.x.dev 或更高
```

> ⚠️ **0.10 破坏性变更预警**: `--ai copilot` 已 deprecated,0.10 起强制 `--integration copilot`。**本 Lab 文档统一使用新语法**。

### 讲师演示用预置 tag(强烈推荐)

为避免现场跑 `specify init` 踩坑(网络 / Python 版本 / 现有 `copilot-instructions.md` 冲突),仓库已预置 git tag:

```bash
cd lab-starter
git checkout speckit-baseline    # 直接切到 init 完成后的状态
```

该 tag 包含:
- `.specify/`(36 个文件:templates、scripts、memory、workflows)
- `.github/prompts/speckit.*.prompt.md`(14 个)
- `.github/agents/speckit.*.agent.md`(14 个,真正的 system prompt 正文在这里)

---

## 实操步骤

### Step 0:概念引入 — 3 min

**讲师话术:**

> 上一个 Lab 我们手作了 4 个 agent 串行协作。但在真实团队里,你不可能每个项目都从零写 agent + 自己规划 handoff 顺序。
>
> GitHub 在 2025 年开源的 **spec-kit** 把这件事工业化了:给你一套 **14 个预置 agent** + 一套 **SDD 工作流模板**(宪法 → 规约 → 计划 → 任务 → 实现),你只需要专注业务,流程由模板兜底。
>
> 这就是 **Spec-Driven Development**:把对话式开发沉淀为可审计的规约产物。

---

### Step 1:看产物目录树 — 3 min

切到预置 tag:

```bash
cd lab-starter
git checkout speckit-baseline
```

在 VS Code Explorer 里展开两个目录:

```
lab-starter/
├── .specify/
│   ├── memory/constitution.md          ← 项目宪法(占位符,待填)
│   ├── templates/                      ← 5 个模板:spec/plan/tasks/checklist/constitution
│   ├── scripts/bash/                   ← 5 个辅助脚本(创建 feature 分支等)
│   ├── workflows/speckit/workflow.yml  ← 整体流程定义
│   └── extensions/git/                 ← 内置 git 扩展(自动分支 + commit hook)
└── .github/
    ├── copilot-instructions.md         ← spec-kit 注入,指引 Copilot 读取当前 plan
    ├── prompts/                        ← 14 个 .prompt.md(每个仅 3 行 frontmatter)
    └── agents/                         ← 14 个 .agent.md(真正的 system prompt,300+ 行/个)
```

**重点指出:**

1. **两层结构**:`.prompt.md` 极简(只声明 `agent: speckit.xxx`),真正逻辑在 `.agent.md` 里 —— 这是 spec-kit 0.8 起的新设计,为了走 VS Code Custom Agents 通道。
2. **handoffs 字段**:打开任意一个 `.github/agents/speckit.specify.agent.md`,看 frontmatter:

   ```yaml
   handoffs:
     - label: Build Technical Plan
       agent: speckit.plan
       prompt: Create a plan for the spec. I am building with...
     - label: Clarify Spec Requirements
       agent: speckit.clarify
   ```

   → 这就是 **Lab 3 手作 handoff 的工业化版本**。每个 agent 显式声明下一步可去哪里,Copilot Chat 会渲染成按钮。

3. **现有 10 个 Workshop 自定义 agent**(architect / red-team 等)与 spec-kit 注入的 14 个 `speckit.*` agent **共存于同一目录**,靠前缀隔离,**无冲突**。

---

### Step 2:`/speckit.constitution` 填项目宪法 — 5 min

在 VS Code Copilot Chat 中输入:

```
/speckit.constitution
```

然后给出宪法内容:

```text
Please populate the constitution for our Ticket Service project with the following principles:

1. **Test Coverage**: All new endpoints must have unit tests + integration tests, with line coverage >= 80%.
2. **API Design**: Follow REST conventions; use plural nouns; return appropriate HTTP status codes (200/201/204/400/404/500).
3. **Security**: Input validation on every endpoint; never leak stack traces in error responses; log auth failures.
4. **Observability**: Every endpoint must log request id + duration; errors logged with full context.
5. **Backward Compatibility**: Never break existing endpoints in a minor release.
```

**预期产物**:`.specify/memory/constitution.md` 被 Copilot 写入完整宪法,替换所有 `[PRINCIPLE_X_NAME]` 占位符。

**讲师话术**:

> 宪法是整个项目所有后续 spec / plan 的 **顶层约束**。后面的 `/speckit.plan` 会自动读取宪法 —— 这就是为什么 plan.md 里会出现"测试覆盖率 80%"这样的强制要求。

---

### Step 3:`/speckit.specify` 写 Search 端点规约 — 6–8 min

我们的 mini feature:**给 Ticket Service 加一个 `GET /tickets/search?q=` 端点**(承接 Lab 2/3 的同一业务线)。

在 Copilot Chat 输入:

```
/speckit.specify
```

然后给出 feature 描述:

```text
Add a search endpoint to the Ticket Service.

Requirements:
- Endpoint: GET /tickets/search?q=<keyword>
- Search behavior: case-insensitive substring match against ticket.title and ticket.description
- Pagination: support ?limit=<n>&offset=<m>, default limit=20, max=100
- Response: { total: number, items: Ticket[] }
- Error handling: 400 if q is empty or > 200 chars
- Performance: must return within 100ms for stores up to 10k tickets
```

**预期产物**:

1. 自动创建分支 `001-ticket-search`(或类似编号 + short-name)
2. 生成 `specs/001-ticket-search/spec.md`(完整规约文档)
3. 生成 `specs/001-ticket-search/checklists/requirements.md`(自动生成的需求 checklist)
4. 写入 `.specify/feature.json`(当前 active feature 元数据)

**讲师话术**:

> 注意三件事:
>
> 1. **自动建分支** —— 强制 git workflow 隔离,每个 feature 一条分支。
> 2. **最多 3 个 `[NEEDS CLARIFICATION]` 标记** —— spec-kit 显式限制,避免规约里塞太多未决问题。
> 3. **checklist 自动产出** —— 不需要你手动列验收标准。

---

### Step 4:`/speckit.plan` + `/speckit.tasks` — 6–8 min

#### 4.1 生成技术计划

```
/speckit.plan
```

prompt:

```text
Plan the implementation using the existing Node.js + Express stack in lab-starter.
Reuse ticketStore.js patterns. Add an in-memory index for fast substring search.
Include test plan using existing jest setup.
```

**预期产物**:`specs/001-ticket-search/plan.md`,包含:
- 技术栈选型(沿用 Node + Express + Jest)
- 数据结构设计(in-memory inverted index)
- 文件改动清单(`ticketStore.js`, `app.js`, `tests/search.test.js`)
- 测试策略(unit + integration + perf benchmark)
- 与宪法 5 条原则的对应关系

#### 4.2 拆分任务

```
/speckit.tasks
```

**预期产物**:`specs/001-ticket-search/tasks.md`,典型形如:

```markdown
## Tasks
- [ ] T001 Add `searchTickets(q, limit, offset)` to ticketStore.js
- [ ] T002 [P] Add input validation helper `validateSearchQuery(q)`
- [ ] T003 Wire GET /tickets/search route in app.js
- [ ] T004 [P] Unit tests for searchTickets in tests/searchTickets.test.js
- [ ] T005 [P] Integration tests for GET /tickets/search in tests/search.api.test.js
- [ ] T006 Performance benchmark (10k tickets, < 100ms)
- [ ] T007 Update docs/api.md
```

**重点讲解 `[P]` 并行标记**:

> spec-kit 自动分析任务依赖,把 **无依赖、改不同文件、可并行** 的任务标 `[P]`。这意味着如果你用 Mission Control 或多个 cloud coding agent,这些 `[P]` 任务可以同时跑。
>
> → 这就是 **Lab 3 的"并行执行"模式被工业化** 的样子。

---

### Step 5:`/speckit.analyze` 跨产物审查 — 3 min

```
/speckit.analyze
```

**预期行为**:spec-kit 以 **只读** 方式跨读 `constitution.md` + `spec.md` + `plan.md` + `tasks.md`,产出结构化审查报告。

**Severity 分级**:

| 等级 | 含义 | 处理 |
|---|---|---|
| **CRITICAL** | 违反宪法 / 内部矛盾 | 必须修复后才能 implement |
| **WARNING** | 设计有风险但不阻塞 | 建议在 plan 里加缓解措施 |
| **INFO** | 优化建议 | 可选 |

**讲师话术**:

> 这是个"只读型 agent" —— 和 Lab 3 的 Security Reviewer 是同一思路:**审查权和修改权分离**。
> 不同的是,spec-kit 的 analyze 是 **跨产物** 审查 —— 它会检查 spec 是否覆盖宪法所有条款、plan 是否落实 spec 所有需求、tasks 是否覆盖 plan 所有改动。这是手作 agent 很难做到的。

---

### Step 6:`/speckit.implement` — 仅口述,2 min

```
/speckit.implement       ← 不在课堂上跑,只口述
```

**讲师话术**:

> implement 阶段会:
>
> 1. 按 `tasks.md` 顺序(尊重 `[P]` 标记并行)逐个执行
> 2. 每完成一个 task,**自动 commit**(由内置 git 扩展驱动)
> 3. 全部完成后,自动跑测试套件
>
> 为什么 **每个 task 自动 commit 很重要**?
>
> - 失败时可以精确回滚到任意 task
> - PR review 时每个 commit 对应一个 task,便于审查
> - 这是 **从"对话式开发"走向"可审计 SDD"** 的最后一公里
>
> 课后作业:在你自己的环境里完整跑一遍 implement,观察 commit 历史。

---

### Step 7:Q&A + 课后作业 — 3 min

---

## 常见坑

| 坑 | 现象 | 解法 |
|---|---|---|
| `--ai copilot` deprecation 警告 | 终端红字 | 改用 `--integration copilot`(0.10 起强制) |
| Python 版本太低 | `specify init` 直接报错 | `winget install Python.Python.3.11` / `pyenv install 3.11` |
| `copilot-instructions.md` 冲突 | 现有自定义指令被覆盖 | 用 `<!-- SPECKIT START --> ... <!-- SPECKIT END -->` 标记合并区域,或在子目录跑 init |
| `.prompt.md` 看起来是空的 | 学员困惑 | 明确告知:真正逻辑在同名 `.agent.md` |
| 14 个 speckit.* agent 淹没自定义 agent 菜单 | 选择器混乱 | 在 VS Code Settings 用 `chat.agent.hide` 隐藏不用的 |
| Copilot Chat 不显示 handoff 按钮 | VS Code 版本旧 | 升级到 VS Code Insiders 最新版 |
| `specify check` 显示 git remote 异常 | repo 没设 origin | `git remote add origin <url>` 后重试 |

---

## 课后作业 / 进阶探索

### 必做

1. 在自己的环境里完整跑一遍 `/speckit.implement`,看每个 task 是否被自动 commit
2. 在 `tasks.md` 里手动加一个新任务(比如"增加 fuzzy match 选项"),观察 implement 如何处理

### 进阶

1. **接入 Mission Control**:把 `[P]` 并行任务分发给多个 cloud coding agent,观察并行 PR
2. **自定义一个 speckit.* agent**:照 spec-kit agent 的写法,加一个 `speckit.security-review.agent.md`,插入到 `analyze → implement` 之间的 handoff
3. **离线安装**:为企业内网环境准备 spec-kit 的离线 wheel 包(参考 `docs/enterprise-deployment-guide.md`)
4. **跨运行时协作**:让 Copilot 跑 SDD 前半段(constitution→tasks),把 tasks.md 交给 Hermes Agent 在 Azure VM 上跑 implement

---

## 实验完成标准

- [ ] 理解 SDD 的 6 阶段流水线(constitution → specify → plan → tasks → analyze → implement)
- [ ] 能在 VS Code 里看到 `.specify/` 与 `.github/agents/speckit.*` 的目录结构
- [ ] 完成 `/speckit.constitution` 填写
- [ ] 完成 `/speckit.specify` 并看到自动建分支 + spec.md
- [ ] 完成 `/speckit.plan` + `/speckit.tasks` 并能解释 `[P]` 标记
- [ ] 跑过 `/speckit.analyze` 并理解 severity 分级
- [ ] 能说出 spec-kit handoff 与 Lab 3 手作 handoff 的对应关系

---

## 参考链接

- GitHub Spec-Kit 仓库: <https://github.com/github/spec-kit>
- SDD 理念介绍(GitHub Blog): <https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai>
- VS Code Custom Agents 文档: <https://code.visualstudio.com/docs/copilot/customization/custom-agents>
- 本 workshop 评估报告: `docs/speckit-eval-report.md`(讲师内部资料)
- Lab 3 复习: `zh/labs/lab3-multi-agent-collaboration.md`
