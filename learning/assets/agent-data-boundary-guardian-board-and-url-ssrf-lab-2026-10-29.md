# Agent 主权数据边界、Guardian V3 只读消息板与 URL/NAT64 防 SSRF 验收实验室（2026-10-29）

**2026-10-29 范围与执行声明：本包中的 Python 3.11+ 标准库参考契约（`harness_contracts.py`）与 24 项单测 / 6 项单点变异校准套件（`test_harness_contracts.py`）已在本地无网络正常模式（`python3 -B`）与优化模式（`python3 -B -O`）下实际执行，24/24 基线测试 PASS、6/6 定向单点 mutation KILLED；各上游产品宿主运行时（Azure MCP Server `4.0.0-beta.3`、Microsoft Agent Framework Python、Google ADK Python、NVIDIA NeMo Guardrails Rust Relay Plugin、OpenAI Agents Python SDK、OpenAI Codex CLI/App-Server、Anthropic Claude Code CLI、Planning with Files Hooks）均为 `NOT_RUN`（仅基于 2026-10-29 实测 HTTP 200 的 15 项固定 40 位 SHA 源码补丁与原始文件静态审阅与本地标准库契约建模）。**

本入口汇集三支柱 6 组核心控制面/数据面机制的无模型离线参考契约、12 张 POC 验收卡、架构边界图与选型问答：
1. **微软 Azure MCP Server (`microsoft/mcp` `4.0.0-beta.3`)**：ResiliencyAgent A2A `DataBoundaryResolver` 主权路由（ARM `dataBoundaries` `"EU"->"eu"`、`"GLOBAL"->"row"`，非公有云与未知值 Fail-Closed，`b3f862be`）、`LocalFileSnapshotter` `1434 KiB` / 禁重解析点 / TOCTOU `ZeroMemory` 快照与 `ArtifactWriter` 不可信文件名净化防穿越，以及 Monitor `IngestionLogDataValidator` `1 MiB` 与 Schema 预检（`cd2556e5`）。
2. **微软 Agent Framework (`microsoft/agent-framework` Python)**：`RedisContextProvider` NUL（`\\x00`）域分隔 `SHA-256` 作用域 Token（`af_scope_v1_*`）防 RediSearch Tag 分隔符注入串台（`9b72ed4f`），以及 `AgentTriggeredCompactionStrategy` / `UnloadSkillsCompactionStrategy` 强制 `store=False` 客户端管理历史、单次消费标记 `_agent_compaction_trigger_consumed` 与异常原位恢复（`c2a8f91b`）。
3. **Google ADK Python (`google/adk-python`)**：`_url_validator.py` 拦截 URL authority 反斜杠解析器差分（`http://169.254.169.254\@example.com/`）并剥离 NAT64 `64:ff9b::/96`、6to4 与 IPv4-mapped 内嵌私网地址（`4d0cd985`）；`skills/models.py` 将标识符校验正则末尾从 `$` 全面替换为 `\Z` 防尾部单换行注入（`e2e9336a`）。
4. **NVIDIA NeMo Guardrails & OpenAI Agents Python SDK**：NeMo Relay `PreToolUse` Rust 客户端禁 URL 内嵌账密、禁重定向（`Policy::none()`）、拦截 10 项 `CLIENT_OWNED_HEADERS` 与错误脱敏（`7d2ef097`）；OpenAI Agents Python SDK 在 Function Tool 失败时置位 `sibling_category_failure` 立即停止并行 `shell`/`computer`/`apply_patch` 原生工具队列并提供 `2 * 0.1s` 双阶段收尾窗口保根因异常（`cd26bbbc`）。
5. **OpenAI Codex (`openai/codex`)**：Guardian V3 本地 SQLite 消息板 `message_board_guardian_1.sqlite`（主线程 `ReadWrite` vs Reviewer `ReadOnly` 仅允许自订阅、`OnceLock` Canonical Path 防篡改与 `deleted_boards` Tombstone，`bca6cff1`）、Guardian 采集保留完整 `original_bytes` 至 `prepare_sync_content` 延迟截断且晋升最新 5 条工具证据为 `Required`（`83a9600a`），以及企业 Config-Server OAuth 与模型凭据登出解耦（`ec513795`）和 Code-Mode Host gRPC 仅限 `OpenSession` 替换防副作用重放（`5fdb50af`）。
6. **Anthropic Claude Code (`v2.1.309`–`v2.1.312`) & 社区 Hook 纵深防御**：`mods/sec-default` 在 `tool.check` 中执行双遍重算（`next.to(e, 'append')`）防止用户层 Mod 放宽组织级 `deny`/受保护 `ask` 并锁定 19 个高危环境变量（`a5b0f2e0`）；`v2.1.309`–`v2.1.312` 修复沙箱外 shell rc/profile、symlink `denyWrite` 与 `--mcp-config` 逃逸并停止发送 `claude_code.safety_event`（`0e1f4789`）；对照 `OthmanAdi/planning-with-files` `v3.26.0` 的 `python -I -B`、`O_NOFOLLOW` 快照与 `hook_is_main` 子代理 Fail-Closed 跳过（`5d29800b`）。

## 配套文件导航

- [完整实验说明、12 张 POC 验收卡与架构图](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/README.md) (`7946aeae26a7bd68e82be1b853362c0f395ccf4a4c9a5a84c396218d01c4c478`)
- [标准库参考契约实现 `harness_contracts.py`](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/harness_contracts.py) (`6a9868b45b865f3811bd2fce52937b8aa8193719231d79291e37d3a2b8fd9b57`)
- [24 项单测与 6 项变异校准套件 `test_harness_contracts.py`](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/test_harness_contracts.py) (`4958bc5a0f88465d798a11b3bc3925f144bca3954af391301f2b68eacd5f72c0`)
- [15 项固定源码补丁与原始文件溯源清单 `fixtures/provenance.json`](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/fixtures/provenance.json) (`62d11759b4cfac0a7bcacd9cb9392cfafc2c894d084aa07a57c3642377625739`)
- [离线执行摘要 `run-summary.json`](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/run-summary.json) (`c4b4fb850f84fe7b92af5d09add83df6f49ad924965396772fe63dfe79092794`)
- [字节 SHA256 清单 `SHA256SUMS`](agent-data-boundary-guardian-board-and-url-ssrf-lab-2026-10-29/SHA256SUMS) (`001d79702e4e2761bbb73fcb9dda6e9003a0f5a6a90570bd3711c7c22096ae90`)

叶文件 SHA-256 详见子目录 `README.md` 与 `SHA256SUMS`（`SHA256SUMS` 覆盖子目录内 5 个配套文件，不包含 `SHA256SUMS` 清单自身与本顶层入口文件；在仓库发布树中，本顶层入口文件的 SHA-256 由外层 `learning/catalog.json` 索引记录）。
