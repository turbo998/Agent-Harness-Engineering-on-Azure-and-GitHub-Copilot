# Agent 调用级归因、沙箱凭据字节替换与闭卷评测网关验收实验室（2026-10-27）

**2026-10-27 范围与执行声明：本目录中的 Python 3.11+ 标准库参考契约（[`harness_contracts.py`](harness_contracts.py)）与 24 项单测 / 6 项单点变异校准套件（[`test_harness_contracts.py`](test_harness_contracts.py)）已在本地无网络正常模式（`python3 -B`）与优化模式（`python3 -B -O`）下实际执行，24/24 基线测试 PASS、6/6 定向单点 mutation KILLED（详见 [`run-summary.json`](run-summary.json)）；各上游产品宿主运行时（Microsoft Agent Framework Python/.NET、Azure AI AgentServer、GitHub Copilot SDK AHP Host、Google ADK `/run_live` 服务端、MCP Go SDK、NVIDIA NeMo Helix、OpenAI Codex MITM Proxy & CLI、Anthropic Claude Code CLI）均为 `NOT_RUN`（仅基于 2026-10-27 固定 SHA 源码补丁静态审阅与本地标准库契约建模）。**

---

## 一、 架构全景与核心问题

在企业级 AI Agent 从单机原型走向多租户生产宿主（Foundry Hosted Agents、Copilot Runtime-Supervised Host、自托管沙箱、企业联邦 MCP 与闭卷基准评测）的过程中，解决方案架构师（SA）常面临以下 6 类边界失守风险：

1. **声明式治理与污点模型串台（MAF Python/.NET）**：将安全拦截器配置外置为 JSON 声明时，若允许动态反射导入或在异常回显中打印 `config` 字典，会导致代码执行与敏感配置泄漏；同时，多实例并发启用 FIDES 信息流控制（IFC）时，若 `quarantined_llm` 依赖进程级全局槽位（last-writer-wins），会导致不同安全等级的 Agent 互相串用隔离模型客户端，甚至显式设为 `None` 的 Agent 意外继承其他 Agent 的客户端。
2. **宿主准入凭据、状态键与模型调用归因混用（Azure AI AgentServer & GitHub Copilot SDK）**：企业 Agent 使用自身的 Managed Identity 调用模型时，如何向模型层传递最终发起人（`x-ms-original-subject`）以供配额计费与滥用审计，同时保证该身份既不从会话状态键（`x-agent-user-id`）静默推导，也不泄漏给外部平台工具？同理，Copilot SDK 的 AHP Host 如何在不把准入 Token 当作推理凭据的前提下实施零信任准入与优雅排水（Graceful Drain）？
3. **实时双向流挂死与跨信任域 Token 泄漏（Google ADK & MCP Go SDK）**：WebSocket 双向流若用 `FIRST_EXCEPTION` 等待收发双协程，当客户端发来畸形帧使接收协程记录日志后正常 `return` 时，发送协程与底层 Runner 会永久挂死（Wedged Socket），且 Pydantic 默认报错会把用户输入写入服务端日志；而在 MCP 企业托管授权（Enterprise Managed Auth）中，若未校验 RFC 9207 `iss` 与 RFC 8693 置换出的 `issued_token_type == id-jag`，客户端可能将高权限的企业 IdP `access_token` 直接转发给外部第三方 MCP Server 授权端。
4. **离线沙箱评测的“托管联网工具”旁路（NVIDIA NeMo Helix）**：即便评测容器设置了 `network_mode = "no-network"`，容器仍须访问模型网关；若所调用的模型路由背后开启了托管联网搜索（Hosted Web Search）或动态路由器（如 Switchyard）位于闭卷中间件之后，所谓“闭卷评测（Closed-Book）”将形同虚设。
5. **沙箱内明文凭据暴露与硬预算崩盘（OpenAI Codex & Cookbook）**：若把云厂商 Secret 直接注入 Agent 沙箱环境变量，极易被 Prompt Injection 窃取；而在多智能体共享 Token 账本中，一刀切的硬限额（`SessionBudgetExceeded`）会导致任务在收尾前崩溃。
6. **组织级安全插件下限绕过与嵌套 CLI 提权（Anthropic Claude Code）**：当组织部署多层安全插件时，哪些层级有权通过 `next.to(e, "user")` 重新向用户层开放事件？当 Hook 在 `/tmp` 等共享目录下派生嵌套 `claude -p` 辅助进程时，如何防止继承内置 `Bash`/`WebFetch` 工具或触发 `<cwd>/.claude/settings.json` 中的 `apiKeyHelper` 代码执行？

```
+---------------------------------------------------------------------------------------------------+
|                   Enterprise Multi-Tenant Agent Harness Boundary Architecture                     |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [Caller / Entra User]                                                                            |
|     |  x-ms-original-subject: oid="...", tid="...", idtype="user" (RFC 9651 Dictionary Subset)    |
|     |  x-agent-user-id: state-partition-key  |  x-agent-foundry-call-id: call-77                  |
|     v                                                                                             |
|  +---------------------------------------------------------------------------------------------+  |
|  | 1. Host Admission & Attribution Plane (Azure AgentServer / Copilot AHP Host / MAF Hooks)    |  |
|  |   - Malformed x-ms-original-subject -> Fast-fail HTTP 400 (x-platform-error-source=platform)|  |
|  |   - Channel Separation:                                                                     |  |
|  |       * State Store Key        -> user_id ONLY (never inferred as original_subject)         |  |
|  |       * Platform Tool Headers  -> {x-agent-foundry-call-id} ONLY                            |  |
|  |       * Model Per-Call Headers -> {x-ms-original-subject, x-agent-foundry-call-id}          |  |
|  |   - Copilot AHP Host: mode="github"|"none"|"custom" (exact identity + future RFC3339 exp;   |  |
|  |     admission token NEVER used for inference; setAllowCreatingNewSessions drain switch)     |  |
|  |   - MAF Hooks Declaration 1.0: posture.tool_seam_host_error=="terminate", dict lookup only  |  |
|  +---------------------------------------------------------------------------------------------+  |
|     |                                                        |                                    |
|     | (A) Sandbox / Tool / Live Stream Plane                 | (B) Model / Eval Gateway Plane     |
|     v                                                        v                                    |
|  +------------------------------------------------+  +-----------------------------------------+  |
|  | 2. Sandbox Egress, MCP Auth & Subprocess Plane |  | 3. Closed-Book & Rollout Budget Plane   |  |
|  |  - Codex MITM v2 Body Secret Substitution:     |  |  - NeMo Helix Closed-Book Route Gate:   |  |
|  |    * Sandbox holds 16..256B ASCII placeholders |  |    * Any step no-network -> requires    |  |
|  |    * Proxy rejects gzip/trailers/client digests|  |      VirtualModel (after read authz)    |  |
|  |    * Substitutes on original bytes, updates    |  |    * request_middleware[-1] MUST equal  |  |
|  |      Content-Length, THEN signs AWS SigV4      |  |      "nemo-evals-closed-book"           |  |
|  |  - MCP Go SDK Enterprise Auth:                 |  |  - Codex Rollout Budget:                |  |
|  |    * RFC 9207 iss check + RFC 8693 id-jag gate |  |    * enforce_limit=true -> hard stop    |  |
|  |  - Claude Code Sec-Default & Nested Spawn:     |  |    * enforce_limit=false -> advisory    |  |
|  |    * Only prepend tier reopens user (<65536 re)|  |      0-remaining reminder, turn finishes|  |
|  |    * Nested claude -p: --restricted --tools "" |  |  - MAF FIDES Quarantine Scope:          |  |
|  |  - Google ADK /run_live: FIRST_COMPLETED +     |  |    * Per-config bound client wins over  |  |
|  |    1007 close + type-only redacted warning log |  |      process-global slot (incl. None)   |  |
|  +------------------------------------------------+  +-----------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 二、 固定源码溯源表（2026-10-27 核验快照）

以下 14 个上游源码补丁均在 2026-10-27 通过 HTTPS 抓取验证（`HTTP 200`），原始响应字节数与 SHA-256 记录于 [`fixtures/provenance.json`](fixtures/provenance.json)：

| Source ID | 所属支柱与仓库 | 固定 Commit SHA (40位) | 核心审阅路径 | 捕获字节数 | 捕获补丁 SHA-256 | 运行时状态 |
| :--- | :--- | :--- | :--- | ---: | :--- | :--- |
| `S01_MAF_AGENT_HOOKS_DECLARATION` | 微软 `microsoft/agent-framework` | `18adf808a57eb6668fc773162037b311d36c5678` | `python/packages/core/agent_framework/_agent_hooks.py` | 69,399 | `cdeb2e8314b28b4823f5231ed39aac6cfa996ffb0c8358bea8b0076523219b5c` | `upstream_product_NOT_RUN` |
| `S02_MAF_FIDES_QUARANTINE_SCOPE` | 微软 `microsoft/agent-framework` | `7db56c05f949b39535fef6d5a9bfdf645e3beffc` | `python/packages/core/agent_framework/security.py` | 13,241 | `c82decb2cdef3221a1dce5627bc2c8ef463ec2bf4000baa57b685c6852ce355c` | `upstream_product_NOT_RUN` |
| `S03_MAF_FOUNDRY_TOOLBOX_APPROVAL` | 微软 `microsoft/agent-framework` | `264439f7f5c71713051b8db4e51fd04f33fcb422` | `dotnet/src/Microsoft.Agents.AI.Foundry.Hosting/FoundryToolboxService.cs` | 21,801 | `78182e5a0c659814d27071c411ea47c51d1cbf9a6be11e3d46ac190fcbe75807` | `upstream_product_NOT_RUN` |
| `S04_COPILOT_SDK_AHP_HOST_AUTH` | 微软 `github/copilot-sdk` | `f2b720c8ec368e035a4d5c72b012fd41b0d533e4` | `nodejs/src/host.ts`, `python/copilot/host.py` | 1,253,629 | `8fdb3ebb5d1c0e117082231088e178372b137152ea452882911b4f972918b139` | `upstream_product_NOT_RUN` |
| `S05_AZURE_AGENT_SERVER_ORIGINAL_SUBJECT` | 微软 `Azure/azure-sdk-for-python` | `a7dd9f37e99f6ae8f3ba6a764e11f86736e37035` | `sdk/agentserver/azure-ai-agentserver-core/azure/ai/agentserver/core/_request_context.py` | 262,324 | `95822bf48e9c21131942af4d46efa8b5eec864f64d26602486f30df307ad2b29` | `upstream_product_NOT_RUN` |
| `S06_GOOGLE_ADK_RUN_LIVE_WEDGE_FIX` | AI Labs `google/adk-python` | `3b227d6ec82490dae6473f681dcc825b1ac31679` | `src/google/adk/cli/api_server.py` | 12,173 | `ac2e2e5dc996f1cc886ce70b4ed8e4c4f0dd5c4b8670dceed009ec7d21fa7f64` | `upstream_product_NOT_RUN` |
| `S07_MCP_GO_SDK_RFC9207_ISS` | AI Labs `modelcontextprotocol/go-sdk` | `fa799c5fc2e2e0f8aa578aa918a6e39607bd0142` | `auth/extauth/oidc_login.go` | 10,334 | `6c1a5566a485446322072cc4a7a25e5bd29bf3c113f19b3dcf73aa4bd9571cd9` | `upstream_product_NOT_RUN` |
| `S08_MCP_GO_SDK_ID_JAG_TOKEN_TYPE` | AI Labs `modelcontextprotocol/go-sdk` | `6f47cb7983b371b60460f730beab9794adc9f04c` | `auth/extauth/enterprise_handler.go` | 6,865 | `2ec197a55becea225f5048f906a832a51eeb61d222a3ca53a0756e5ef1bcfc3e` | `upstream_product_NOT_RUN` |
| `S09_NEMO_HELIX_CLOSED_BOOK_MIDDLEWARE` | AI Labs `NVIDIA-NeMo/nemo-helix` | `8c3ef7f50c88ba6ff1775350dd4cdfa5473c7b9a` | `plugins/nemo-evals/src/nemo_evals/jobs/gateway_models.py` | 30,517 | `14e09194943fff1c88ec9ed2e0623771fe244398f0dc95cedc82fe7da4d02bd6` | `upstream_product_NOT_RUN` |
| `S10_CODEX_MITM_V2_BODY_SECRET_SUBSTITUTION` | Coding CLI `openai/codex` | `619531225b29dcf6437ec6571537f9da9da002bc` | `codex-rs/network-proxy/src/secret_substitution.rs`, `mitm.rs` | 43,992 | `c628cd31719fbc2c78ea277341338a1707cf65136f54bd1b6b212c696053950c` | `upstream_product_NOT_RUN` |
| `S11_CODEX_ADVISORY_ROLLOUT_BUDGET` | Coding CLI `openai/codex` | `77eb019ad039d21e5a346e77568739993a7f94cd` | `codex-rs/core/src/rollout_budget.rs` | 9,898 | `ce95608c0fe676d40ff60dc0cb57ae0c5dfa466458c43603b2e1fbcc62436036` | `upstream_product_NOT_RUN` |
| `S12_COOKBOOK_DATABRICKS_SANDBOX_EXEC_SERVER` | Coding CLI `openai/openai-cookbook` | `8495326b6f1b7cec94e7f5e393a4045e328a268e` | `examples/agents_api/sandboxes/databricks/README.md` | 704,376 | `4e3ef42f581510c978fd3f6cc2c8088f4d4220a3bc0026e7fdcea4dff3e52a37` | `upstream_product_NOT_RUN` |
| `S13_CLAUDE_CODE_2_1_310_CHANGELOG` | Coding CLI `anthropics/claude-code` | `b70dc4113ad72e0ee44f7b1b95afaf510b53ee98` | `CHANGELOG.md` (`v2.1.305`–`v2.1.310`) | 25,735 | `97164d41202215ffda0938b3527010ef5a6da9d4edc09e14422e61c4d00e5d4a` | `upstream_product_NOT_RUN` |
| `S14_CLAUDE_CODE_SEC_DEFAULT_REOPEN_GATE` | Coding CLI `anthropics/claude-code` | `318b7e6ac4e726e88a4ad326214866a93c373b1b` | `mods/sec-default/README.md` | 1,514 | `a7599e0595e3044f9f1a2a6f8b62aa8fb3de2fd122f43f113ea9449cffb9c594` | `upstream_product_NOT_RUN` |

---

## 三、 12 张 POC 验收门禁卡（Acceptance Gates）

每张卡片均包含 `precondition`、`stimulus`、`expected`、`negative`、精确源码锚点与本地测试绑定（产品宿主实机状态统一为 `NOT_RUN`，本地标准库契约状态为 `PASS`）。

### Gate 01 — MAF `agent-hooks-declaration/1.0` 零反射加载与 `terminate` 姿态门禁
- **Source Ref**: `S01_MAF_AGENT_HOOKS_DECLARATION` (`microsoft/agent-framework@18adf808a57eb6668fc773162037b311d36c5678`, `python/packages/core/agent_framework/_agent_hooks.py`)
- **Precondition**: 使用 `create_agent_hooks_middleware_from_declaration` 加载 JSON/dict 声明文档与宿主提供的 `interceptors` 映射。
- **Stimulus**: 传入 `declaration="agent-hooks-declaration/1.0"`、`posture.tool_seam_host_error="terminate"` 及 `kind="agent_framework.interceptor"` 绑定。
- **Expected**: 构造期校验通过并为每次 Agent `run` 创建密封（sealed）会话；按 `config.name` 或 `binding.id` 执行纯字典查找。
- **Negative Control**: 若 `tool_seam_host_error="continue"`、包含动态导入键（`module`/`import_path`）或引用未注册拦截器（且 `config` 含敏感 token），立即抛出异常且错误消息绝不回显 `config` 敏感值。
- **Observed**: 本地契约测试 `test_01`/`test_02`/`test_03` `PASS`；MAF 宿主运行时 `NOT_RUN`。

### Gate 02 — MAF FIDES `quarantined_llm` 作用域客户端隔离（防全局槽位串台）
- **Source Ref**: `S02_MAF_FIDES_QUARANTINE_SCOPE` (`microsoft/agent-framework@7db56c05f949b39535fef6d5a9bfdf645e3beffc`, `python/packages/core/agent_framework/security.py`)
- **Precondition**: 同一进程内并发实例化 `SecureAgentConfig(quarantine_chat_client=alpha)`、`SecureAgentConfig(quarantine_chat_client=beta)` 与 `SecureAgentConfig(quarantine_chat_client=None)`。
- **Stimulus**: 在各自 `LabelTrackingFunctionMiddleware` 作用域下调用 `quarantined_llm`，同时设置进程级 `set_quarantine_client(beta)`。
- **Expected**: 实例 A 仅调用 `alpha`，实例 B 仅调用 `beta`；显式配置 `None` 的实例因 `_quarantine_client_bound=True` 保持 `None`，绝不回退读取全局槽位中的 `beta`；仅无中间件的独立调用回退至全局槽位。
- **Negative Control**: 若将绑定判断误写为 `middleware.quarantine_client_override or get_quarantine_client()`（对应变异 `M1`），显式禁用隔离 LLM 的 Agent 会错误继承全局客户端。
- **Observed**: 本地契约测试 `test_04` `PASS`（变异 `M1` `KILLED`）；MAF 宿主运行时 `NOT_RUN`。

### Gate 03 — MAF .NET `FoundryToolboxService` 工具审批策略 Fail-Closed 映射
- **Source Ref**: `S03_MAF_FOUNDRY_TOOLBOX_APPROVAL` (`microsoft/agent-framework@264439f7f5c71713051b8db4e51fd04f33fcb422`, `FoundryToolboxService.cs`)
- **Precondition**: Foundry Toolbox 从远端 MCP Server 发现工具并解析 `ProtocolTool.Meta["tool_configuration"]`。
- **Stimulus**: 分别传入无 `_meta`、`require_approval="never"`、`require_approval="always"` 及未知策略 `require_approval="on_risk"` 或非对象 `tool_configuration`。
- **Expected**: 无配置或 `"never"` 直接包装为 `ConsentAwareMcpClientAIFunction`；`"always"` 包装为 `ApprovalRequiredAIFunction`；若底层服务已要求审批则优先保留审批；未知或格式错误的显式配置记录 Warning 并强制走 `ApprovalRequiredAIFunction`（Fail-Closed）。
- **Negative Control**: 将未知审批枚举值当作 `false` 放行会造成高危工具未审执行。
- **Observed**: 本地契约测试 `test_05` `PASS`；.NET 运行时 `NOT_RUN`。

### Gate 04 — Azure AI AgentServer `x-ms-original-subject` RFC 9651 解析与三通道隔离
- **Source Ref**: `S05_AZURE_AGENT_SERVER_ORIGINAL_SUBJECT` (`Azure/azure-sdk-for-python@a7dd9f37e99f6ae8f3ba6a764e11f86736e37035`, `_request_context.py`)
- **Precondition**: 请求进入 `Responses`/`Invocations`/`Activity` 宿主，携带 `x-ms-original-subject`、`x-agent-user-id` 与 `x-agent-foundry-call-id`。
- **Stimulus**: 解析 `x-ms-original-subject: oid="obj-01", tid="tenant-01", idtype="user"` 并分别调用 `model_attribution_headers()` 与 `platform_headers()`。
- **Expected**: `model_attribution_headers()` 返回按次传入模型端点的 `{x-ms-original-subject, x-agent-foundry-call-id}`，保持模型自身认证 Header 不变；`platform_headers()` 仅含 `x-agent-foundry-call-id`，绝不向平台工具泄漏 `x-ms-original-subject`；当请求未带 `x-ms-original-subject` 时，绝不从 `x-agent-user-id` 或旧版 `x-ms-original-subject-oid` 推导。
- **Negative Control**: 重复 Header、未知键、带分号参数、缺失三元组任一字段或含控制字符/非 ASCII 字符时，入口返回 `HTTP 400`（`x-platform-error-source: platform`）或抛出 `ValueError`，绝不静默降级为无归因调用（变异 `M2` `KILLED`）。
- **Observed**: 本地契约测试 `test_06`/`test_07`/`test_08` `PASS`；AgentServer 宿主 `NOT_RUN`。

### Gate 05 — GitHub Copilot SDK `AhpHostAuthentication` 零信任准入与新会话排水阀门
- **Source Ref**: `S04_COPILOT_SDK_AHP_HOST_AUTH` (`github/copilot-sdk@f2b720c8ec368e035a4d5c72b012fd41b0d533e4`, `nodejs/src/host.ts`, `python/copilot/host.py`)
- **Precondition**: 启动 Runtime-Supervised AHP Host，配置 `authentication`（`github` / `none` / `custom`）及 `allowCreatingNewSessions`。
- **Stimulus**: 在 `mode="custom"` 下设置 `requireIdentity="org-owner-42"`，传入准入 Token 并触发 `authenticate` 回调返回 `{identity, expires_at}`。
- **Expected**: 仅当 `identity == requireIdentity` 且 `expires_at` 为严格大于当前时间的合法带时区 RFC3339 时间戳时允许准入；准入 Token 仅作连接校验，绝不作为模型推理凭据（`used_as_inference_credential=False`）；调用 `setAllowCreatingNewSessions(False)` 后拒绝新建会话但保持存量会话。
- **Negative Control**: 缺省 `authentication`、启用 `githubEnvironment` 却非 `github` 模式、身份不匹配或过期时间戳一律 Fail-Closed 拒绝。
- **Observed**: 本地契约测试 `test_09` `PASS`；Copilot CLI/SDK 宿主 `NOT_RUN`。

### Gate 06 — Google ADK `/run_live` 畸形帧防挂死（`FIRST_COMPLETED`）与 PII 零泄漏日志
- **Source Ref**: `S06_GOOGLE_ADK_RUN_LIVE_WEDGE_FIX` (`google/adk-python@3b227d6ec82490dae6473f681dcc825b1ac31679`, `src/google/adk/cli/api_server.py`)
- **Precondition**: ADK Web Server `/run_live` 启动 `forward_events()` 与 `process_messages()` 双向协程。
- **Stimulus**: 客户端发送含敏感用户文本与非法字段的畸形 JSON 帧，触发 `LiveRequest.model_validate_json` 的 `ValidationError`。
- **Expected**: 仅在 `LiveRequest.model_validate_json` 局部捕获 `ValidationError`，日志仅记录排序去重后的 `error["type"]` 列表（剥离用户输入与虚构字段名）；设置 `close_code=1007` 并 `return`；主循环通过 `asyncio.wait(..., return_when=FIRST_COMPLETED)` 立即感知并在 `finally` 中关闭队列、取消且 `await` 兄弟协程后发送 WebSocket `1007` 关闭帧。
- **Negative Control**: 旧版使用 `FIRST_EXCEPTION` 会因 `process_messages()` 正常返回而永久挂死 `forward_events()`，且直接打印 `ValidationError` 会将用户隐私写入服务端日志。
- **Observed**: 本地契约测试 `test_10`/`test_11` `PASS`；ADK Web Server `NOT_RUN`。

### Gate 07 — MCP Go SDK 企业授权双重门禁：RFC 9207 `iss` 防混淆与 `id-jag` 令牌类型强校验
- **Source Ref**: `S07_MCP_GO_SDK_RFC9207_ISS` (`fa799c5fc2e2e0f8aa578aa918a6e39607bd0142`) & `S08_MCP_GO_SDK_ID_JAG_TOKEN_TYPE` (`6f47cb7983b371b60460f730beab9794adc9f04c`) (`modelcontextprotocol/go-sdk`)
- **Precondition**: MCP Client 执行 OIDC PKCE 登录并向企业 IdP 发起 RFC 8693 Token Exchange 以获取访问外部 MCP Server 的断言令牌。
- **Stimulus**: 检查授权回调的 `iss` 参数与 Token Exchange 响应中的 `issued_token_type`。
- **Expected**: 若 IdP 元数据声明 `authorization_response_iss_parameter_supported=true` 则 `iss` 必填；无论是否声明支持，只要出现 `iss` 就必须严格匹配 `meta.Issuer`；Token Exchange 返回的 `issued_token_type` 必须严格等于 `urn:ietf:params:oauth:token-type:id-jag` 才允许转发给外部 MCP 授权服务器。
- **Negative Control**: 若 IdP 退化返回 `urn:ietf:params:oauth:token-type:access_token` 而客户端未拦截（对应变异 `M3`），会将企业内网 IdP `access_token` 泄露给第三方 MCP Server。
- **Observed**: 本地契约测试 `test_12`/`test_13` `PASS`（变异 `M3` `KILLED`）；Go SDK 运行时 `NOT_RUN`。

### Gate 08 — NVIDIA NeMo Helix 闭卷评测路由门禁（强制末尾 `nemo-evals-closed-book` 请求中间件）
- **Source Ref**: `S09_NEMO_HELIX_CLOSED_BOOK_MIDDLEWARE` (`NVIDIA-NeMo/nemo-helix@8c3ef7f50c88ba6ff1775350dd4cdfa5473c7b9a`, `gateway_models.py`)
- **Precondition**: 提交 Harbor Agent 评测任务集，其中任一任务的 `environment`、`agent` 或单个 `step` 配置了 `network_mode="no-network"` 或 `allow_internet=False`。
- **Stimulus**: 传入非免模型 Agent（如 `codex`）及目标 `VirtualModel` 路由配置。
- **Expected**: 先执行 `authorize_source_read` 校验调用者对该 `VirtualModel` 的读取权限（防通过报错信息探测他人路由配置），随后强制校验 `virtual_model.request_middleware[-1].name == "nemo-evals-closed-book"`；免模型内置 Agent（`oracle`/`nop`）直接豁免。
- **Negative Control**: 裸模型名、黑盒导入 Agent、仅在 `response_middleware` 挂载闭卷中间件，或在 `nemo-evals-closed-book` 之后又挂载动态路由器 `nemo-switchyard`（对应变异 `M4`）一律抛出 `ValueError("closed_book_required: ...")`。
- **Observed**: 本地契约测试 `test_14`/`test_15`/`test_16` `PASS`（变异 `M4` `KILLED`）；NeMo Helix 集群 `NOT_RUN`。

### Gate 09 — OpenAI Codex MITM v2 请求体凭据字节替换与后置 AWS SigV4 签名
- **Source Ref**: `S10_CODEX_MITM_V2_BODY_SECRET_SUBSTITUTION` (`openai/codex@619531225b29dcf6437ec6571537f9da9da002bc`, `secret_substitution.rs`, `mitm.rs`)
- **Precondition**: 沙箱内仅持有 16~256 字节的不透明 ASCII 占位符；宿主机 `codex-network-proxy` 配置 `network.mitm.version = 2` 与作用域 Hook。
- **Stimulus**: 沙箱向匹配的 HTTPS 端口发起含占位符的请求，代理执行 `body_secret_substitution.apply` 后再执行 `aws_sigv4` 签名。
- **Expected**: 仅在原始字节上单遍查找非重叠匹配（杜绝递归展开其他占位符），校验展开后总长不超过 `max_body_bytes`（默认 8 MiB，上限 16 MiB）且窗口扫描工作量 `<= 256 MiB`，移除 `transfer-encoding`/`trailer` 并重算真实 `content-length` 后再计算 SigV4 签名哈希。
- **Negative Control**: 非 `identity` 压缩编码、含 HTTP Trailers、客户端自带摘要头（`digest`/`content-md5`/`x-amz-content-sha256`/`x-amz-checksum-*`，对应变异 `M5`）、占位符互为子串或 Secret 内含占位符时直接 Fail-Closed（403）。
- **Observed**: 本地契约测试 `test_17`/`test_18`/`test_19` `PASS`（变异 `M5` `KILLED`）；Codex Rust Proxy `NOT_RUN`。

### Gate 10 — OpenAI Codex Rollout Budget 软硬双模控制（`enforce_limit` vs Advisory 零余额提醒）
- **Source Ref**: `S11_CODEX_ADVISORY_ROLLOUT_BUDGET` (`openai/codex@77eb019ad039d21e5a346e77568739993a7f94cd`, `rollout_budget.rs`) & `S12_COOKBOOK_DATABRICKS_SANDBOX_EXEC_SERVER` (`openai/openai-cookbook@8495326b`)
- **Precondition**: 主 Agent 与 Subagents 共享 `RolloutBudgetConfig`，配置 `limit_tokens` 与 `reminder_at_remaining_tokens`。
- **Stimulus**: 累计加权 Token 消耗达到或超过 `limit_tokens`，分别测试 `enforce_limit=True` 与 `enforce_limit=False`。
- **Expected**: `enforce_limit=True` 时返回预算耗尽并触发 `SessionBudgetExceeded` 终止当前及后续 Turn；`enforce_limit=False`（Advisory 模式）下不终止会话，但向模型注入 `remaining_tokens=0` 的预算提醒，允许 Agent 优雅收尾。
- **Negative Control**: 在自托管沙箱（如 Databricks `codex exec-server`）中传入主 `OPENAI_API_KEY` 而非最小权限 `api.agents.environments.connect` Executor Key 会被服务端 403 拒绝。
- **Observed**: 本地契约测试 `test_20` `PASS`；Codex CLI `NOT_RUN`。

### Gate 11 — Anthropic Claude Code `mods/sec-default` 组织级 Reopen 权限边界与 65,536 正则上限
- **Source Ref**: `S13_CLAUDE_CODE_2_1_310_CHANGELOG` (`b70dc4113ad72e0ee44f7b1b95afaf510b53ee98`) & `S14_CLAUDE_CODE_SEC_DEFAULT_REOPEN_GATE` (`318b7e6ac4e726e88a4ad326214866a93c373b1b`) (`anthropics/claude-code`)
- **Precondition**: 内置 `sec-default` 插件默认通过 `next.to(e, "append")` 将受保护事件路由至受管 `append` 层，跳过 `user` 层。
- **Stimulus**: 插件在 Hook 中声明 `next.to(e, "user")` 尝试向用户层重新开放事件；工具调用被规则/Auto Mode/沙箱拦截（`stopped`/`prompted`/`sent_back`）。
- **Expected**: 仅当插件位于 `sec-default` 之上的组织级 `prepend` 层、事件匹配其静态 `matcher`/`door` 宽度且正则表达式长度 `<= 65,536` 字符时才允许 Reopen；每当工具调用被 `stopped`/`prompted`/`sent_back` 时发射 `claude_code.safety_event` OTel 事件。
- **Negative Control**: 位于 `sec-default` 之下的插件调用 `next.to(e, "user")` 无效（`append` 下限优先）；正则超过 65,536 字符拒绝读取并拒绝 Reopen（变异 `M6` `KILLED`）。
- **Observed**: 本地契约测试 `test_21` `PASS`（变异 `M6` `KILLED`）；Claude Code CLI `NOT_RUN`。

### Gate 12 — 嵌套 `claude -p` 辅助进程防提权与 `/tmp` 配置投毒封堵
- **Source Ref**: `S13_CLAUDE_CODE_2_1_310_CHANGELOG` (`anthropics/claude-code@b70dc411`) & 社区安全修复对照 `yonatangross/orchestkit@b850f51af1a66623b8a5c7c34ef7cdf7ee325a9d` (`src/hooks/src/lib/session-identity.ts`)
- **Precondition**: 父 Agent 会话在 Hook 或后台任务中以非交互模式（`claude -p`）且工作目录位于 `/tmp`（或不可信目录）派生轻量模型子进程（如生成标题或摘要）。
- **Stimulus**: 审计子进程的启动参数列表 `argv`。
- **Expected**: 必须显式包含 `--restricted`（忽略 `<cwd>/.claude/settings.json`，防止攻击者在 `/tmp/.claude/settings.json` 植入 `apiKeyHelper` 实现任意代码执行）与 `--tools ""`（清空内置 `Bash`/`WebFetch` 工具，防止绕过父会话 `--restricted` 限制）。
- **Negative Control**: 仅传 `--settings '{"disableAllHooks":true}'` 而不传 `--restricted` 与 `--tools ""` 会导致子进程仍可执行内置 `Bash` 工具或加载 `/tmp` 下的恶意配置。
- **Observed**: 本地契约测试 `test_22` `PASS`；Claude Code CLI `NOT_RUN`。

---

## 四、 本地复演命令与哈希绑定清单

在任意具备 Python 3.11+ 的无网络环境中，进入本目录执行以下命令即可复演全部 24 项基线测试与 6 项单点变异校准：

```bash
python3 -B -m unittest discover -s . -p 'test_harness_contracts.py' -v
python3 -B -O -m unittest discover -s . -p 'test_harness_contracts.py' -v
sha256sum -c SHA256SUMS
```

### 子目录文件清单与导航
- [标准库参考契约实现 `harness_contracts.py`](harness_contracts.py)
- [24 项单测与 6 项变异校准套件 `test_harness_contracts.py`](test_harness_contracts.py)
- [14 项固定源码补丁溯源清单 `fixtures/provenance.json`](fixtures/provenance.json)
- [离线执行与变异校准结果摘要 `run-summary.json`](run-summary.json)
- [子目录字节校验清单 `SHA256SUMS`](SHA256SUMS)（绑定本子目录内除 `SHA256SUMS` 自身外的 5 个文件；父目录顶层入口文件由仓库 `learning/catalog.json` 索引绑定 SHA-256）
