# Agent 沙箱前置围栏、远端技能完整性与录制轨迹回放验收实验室（2026-10-21）

**2026-10-21 范围与执行声明：本包中的 Python 3.11+ 标准库参考契约（`harness_contracts.py`）、OpenAI Cookbook 15 条录制轨迹离线回放数据（`fixtures/cookbook_recorded_traces.json`）与测试套件（`test_harness_contracts.py`）已在本地无网络正常模式（`python3 -B`）与优化模式（`python3 -B -O`）下实际执行，24/24 基线测试 PASS、7/7 定向单点 mutation KILLED；各上游产品宿主运行时（GitHub Copilot CLI/SDK、MAF ASP.NET Core 宿主、Azure MCP Server 二进制、Google ADK VMaaS 远端沙箱、MCP TypeScript SDK 进程、OpenAI Codex App Server / CLI、Anthropic Claude Code CLI）均为 `NOT_RUN`（仅固定 SHA 源码/patch/轨迹静态审阅与本地标准库回放）。**

本入口汇集三支柱 6 组核心控制面/数据面机制的无模型离线参考契约、15 条录制轨迹离线回放、12 张 POC 验收卡、架构边界图与选型问答：
1. **微软 GitHub Copilot SDK**：`managedSettings.permissions.limitTo` 主机级闭环出口交集（严格区分 `null` 不限与 `[]` 全拒）及 `createSession`/`resumeSession` 在 MCP Server 启动前注入 `sandboxConfig`（`20d75a71` / `51e9556d`）。
2. **微软 MAF .NET**：`MapAGUIServer` Scoped/Transient 生命周期修正、请求级动态选择器 `null -> 404` 零存储读取短路，以及 `ToolApprovalAgent` 重复审批 `RequestId` 状态擦除与持久化（`30bc5c1b` / `8ab068b8`）。
3. **Google ADK Python**：VMaaS 远端沙箱 `DEADLINE_EXCEEDED` 识别与 `STATE_RUNNING` 下严禁重试非幂等命令的 At-most-once 状态机（`019b2b21`）。
4. **MCP 官方 TypeScript SDK (`SEP-2640`) & OpenAI Codex**：远端技能客户端 `SkillsClient.read` 四重完整性核验（`isWithin` 线性防逃逸、文件大小、SHA-256、`SKILL.md` Frontmatter 双向比对与缓存污染自动 `refresh`）及 Codex `--cloud-skills-snapshot` 冻结云端技能快照边界（`46d9c992` / `e776b27e`）。
5. **OpenAI Codex & Anthropic Claude Code `v2.1.304`**：Codex 并发登录/登出代数围栏（`c6e4438a`）、Claude Code `tool.check` 新增 `decider: "person"` 强制人工/宿主回调批准（拦截 Auto Mode 代批与无回调 Headless 执行）及关闭受管 `CLAUDE.md` 的 3 个高危环境变量边界（`772c6bee` / `a6e289a2`）。
6. **OpenAI Cookbook `harness_aware_plugin_evals` 15 条录制轨迹离线回放**：完整复刻 `eval_grading.py` 与 `assert_codex_result.py`，对 `l2-trace.json`（5/5 PASS）、`l3-trace-before.json`（3/5，精确复现 Case 4 CPI 与 Case 5 Employment 在 Codex 系统提示词驱动下越界拉取序列号失败）及 `l3-trace-after.json`（注入 MCP `initialize.instructions` 后恢复 5/5 PASS）执行确定性回放对账（`5bd6cb40`）。

## 配套文件导航

- [完整实验说明、12 张 POC 验收卡与架构图](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/README.md) (`46578bc27bec54c519d6b8b8593e987c6cf70602e447173aa78f9fcef4c498c8`)
- [标准库参考契约与轨迹回放判分器 `harness_contracts.py`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/harness_contracts.py) (`2d6345808324e4fce3c5d5452a7f01f0e2ea13851808ae8f6cb4a49867349618`)
- [24 项单测与 7 项变异校准 `test_harness_contracts.py`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/test_harness_contracts.py) (`bb821aa0919839a5076962435ddc7c92e439651fbd7c8bb7cdad39ec76636413`)
- [固定源码溯源清单 `fixtures/provenance.json`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/fixtures/provenance.json) (`9c31754d49e8600c770ba6816d7d0b88835f8fa344414a7767cac1be1d591f77`)
- [OpenAI Cookbook 15 条录制轨迹投影 `fixtures/cookbook_recorded_traces.json`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/fixtures/cookbook_recorded_traces.json) (`4685b8f72f579e80abe8fb51dbc9a4c131529e9cee2cc7583dfa5123ffde8db9`)
- [离线执行摘要 `run-summary.json`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/run-summary.json) (`47176b95f9923f3003bec5a21ffe3e73fb88cc6d14d73f0015e3e639e405175d`)
- [字节 SHA256 清单 `SHA256SUMS`](agent-sandbox-skill-integrity-and-trace-replay-lab-2026-10-21/SHA256SUMS) (`51d410c3072d0d8b7b3ee01c1be6bf12c754cf1af31a51822ca8792fea0e9726`)

叶文件 SHA-256 详见子目录 `README.md` 与 `SHA256SUMS`（`SHA256SUMS` 覆盖子目录内 6 个文件，不包含清单自身；本顶层入口文件由 `learning/catalog.json` 索引绑定 SHA-256）。
