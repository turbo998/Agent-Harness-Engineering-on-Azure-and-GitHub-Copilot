# Coding Agent Authority Degradation Gates：公开 CLI 验收设计模板（2026-09-26）

> 状态：验收设计模板，未对任何产品版本做本地实测；不代表安全评审、发布或部署已经通过。
> 适用对象：具备“主机控制面 + 远端/沙箱执行面 + 管理策略”边界的 coding agent/CLI。
> 公开性：只使用合成 canary，不放真实凭据；执行阶段禁止外部网络；不包含内部机器、内部台账、排班或研究流程。

## 0. 核实范围与证据口径

本模板依据 2026-09-26 前后公开可取证材料与只读内容寻址快照整理。URL 以有界 HEAD + GET 复核，GET 正文应保存为相对证据制品（例如 `evidence/D1.body`、`evidence/A2.body`）；未安装或运行 Codex/Claude CLI，未执行产品级 POC。

网络 200 只说明材料可取；验收 oracle 来自公开源码 diff、测试断言、commit/release API 字段、Claude changelog 与 docs 正文。滚动文档的定位以 `observed_at_utc`、正文 hash、章节标题和短引文为准；不要把行号当作永久引用。

### 固定证据引用

| 编号 | 主题 | 来源归属 | 固定引用 | observed_at_utc | body_sha256 | oracle 摘要 |
|---|---|---|---|---|---|---|
| D1/C1 | Codex：executor MCP credential provenance | OpenAI Codex commit diff + commit API | `c7e80f873f67dbef58206b9d4f3c60e9d556eb16`；`https://github.com/openai/codex/commit/c7e80f873f67.diff` | `2026-09-25T19:17:39Z` | `eeec418e3e63d581873df99c6e8286719f764eac4a070efa883038a165522258` | 正常 capability 下 executor token 正控；降级后 MCP tool 不可用；`ExecutorOnly` 禁止 host env fallback；credential policy 纳入 catalog/cache identity。commit API 标题为 `Preserve executor MCP credential boundaries across reconnects (#48143)`，提交时间 `2026-09-25T17:15:29Z`。 |
| D2/C2 | Codex：approved command deny preservation | OpenAI Codex commit diff + commit API | `645b683a9e712ae6d90a364e3cf597466e4146d0`；`https://github.com/openai/codex/commit/645b683a9e71.diff` | `2026-09-25T19:17:39Z` | `47ecd2a48c9b57c89488be47271a4fb49049bcdc61c6df8668e2390acd662a6c` | `for_approved_command` 为 approved command 授予 root/root-metadata write 并保留显式 deny；不可解析或 root deny 时返回原 policy；root metadata symlink 测试在 user namespace + tmpfs 合成根内执行。commit API 标题为 `Preserve filesystem denials when preparing approved commands (#48155)`，提交时间 `2026-09-25T18:06:57Z`。 |
| A1 | Claude：managed invalid handling changelog | Anthropic Claude Code changelog | `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` | `2026-09-25T19:17:39Z` | `f7687fb54480ecc71c8f9da577ede105b4c8cea3373f8eaadc348dff0f8b2f62` | `2.1.282` changelog 明确：mistyped boolean lock 仍锁定、嵌套坏值不再丢整块、Windows/WSL present-but-invalid/unreadable 管理源不退到 HKCU 或 WSL 用户可写源。 |
| A2 | Claude：managed settings docs | Anthropic Claude Code docs | `https://code.claude.com/docs/en/managed-settings.md` | `2026-09-25T19:17:39Z` | `0747fd511104fed74425bfe2044dec65b3afaabfc441dde1208b225d14bf0085` | docs 区分 missing、empty、malformed/not object、unreadable、HKCU malformed、login mode、`policyHelper`、fail-closed keys、fail-open version locks、`deniedMcpServers` 整体非法 drop。 |
| A3 | Claude：settings docs | Anthropic Claude Code docs | `https://code.claude.com/docs/en/settings.md` | `2026-09-25T19:17:39Z` | `9987a0a133cf1146ee97bfd9fb3bd1f4f659b0637d24d3df1bb269d787d6ed62` | user/project/local settings 与 managed settings 的错误处理不同：普通文件可弹 Settings Error/Warning，managed 保留有效项并按 managed docs 处理。 |
| A4 | Claude：settings reference docs | Anthropic Claude Code docs | `https://code.claude.com/docs/en/settings-reference.md` | `2026-09-25T19:22:37Z` | `9acd20ba5c809e4457ab06c03269cfb91afc5ce542304b9e78f4ea6f03273c4a` | `autoMode`、`worktree`、`attribution` 的已知 schema 字段用于设计嵌套坏值 fixture；A4 是补充 schema 参考，不代表已运行 Claude。 |
| R1 | Codex 0.157.0 release | OpenAI Codex GitHub release API | `https://api.github.com/repos/openai/codex/releases/tags/rust-v0.157.0` | `2026-09-25T19:17:39Z` | `f1e71b56562b6da7899c39adfaaa3d15b15e82782f61e6510bae5d6fa174c867` | release `published_at=2026-09-25T02:31:06Z`，早于 D1/D2 commit；不能把 main 修复归入 `0.157.0`，package inclusion 未知。 |

## 1. 官方 source / class / new-old 说明

- **Codex D1/C1**：旧仓库新 commit、新机制；证据是 main 分支实现与测试，package inclusion 未知。核心 class 是“凭据来源/权限域 provenance 丢失导致重连后权限提升”。源码 oracle 同时包含正负两面：capability 正常时 executor-side credential 可用；capability 降级后应 fail closed，tool 不可用且绝不 host fallback。
- **Codex D2/C2**：旧仓库新 commit、新机制；证据是 main 分支实现与测试，package inclusion 未知。核心 class 是“审批扩大单条命令执行权限时错误清空/覆盖显式 deny”。源码 oracle 是：approved command 获得较宽的 root/volume 与 root metadata 写权限，同时保留显式读拒绝；这不是按输出路径分析出的最小写权限，也不是持久全局提权。
- **Claude A1/A2/A3/A4**：`2.1.282` changelog 明确三类修复；A2/A3/A4 是滚动 docs，包含多个版本累积行为，不能全部归因于 `2.1.282`。特别保留边界：`requiredMinimumVersion` / `requiredMaximumVersion` invalid 是有意 fail-open；`deniedMcpServers` 整体非法 drop with warning；不是所有坏 managed 值都 fail-closed。

## 2. 三种验收方案对比

| 方案 | 内容 | 优点 | 风险/缺口 | 适用结论 |
|---|---|---|---|---|
| A. 静态差分审计 | 只审 diff、配置 schema、release/changelog，做源归属和版本边界标注 | 快、无副作用，可公开复现引用 | 无法证明运行时实际阻断；容易把 main 修复误归入发布版 | 作为入口，不单独作为上线 gate |
| B1. 纯逻辑 mock / 静态 fixture | 使用本地 mock MCP、合成 canary、虚拟 managed policy JSON/registry 样本、schema/transform 单元模型；不启动产品 CLI | 可公开、低副作用；能证明模板 oracle、制品解析和报告结构 | 只能证明 mock 与 fixture 自己；产品运行状态仍是 `NOT_RUN` | 作为公开设计与单元级预检 |
| B2. 固定制品离线集成 harness | 获取或构建指定 SHA/版本的待测二进制/SDK 制品，记录 artifact hash；执行阶段禁止外部网络，可在 namespace 内使用 loopback mock HTTP/MCP；真实入口、loader、sandbox 由待测制品提供 | 能验证产品实际路径，仍避免真实 secret 和外网漂移 | “不联网”仅指执行阶段无外部网络；获取/构建阶段需单独记录。没有待测二进制、SDK 注入点或 policy loader 时只能 `NOT_RUN` | 推荐的公开 POC 集成层 |
| C. 隔离端到端真实产品回归 | 安装指定 CLI，连组织允许的测试 executor 或测试企业策略源，在 disposable VM / 独立账号 / 独立 registry hive 中运行 | 最贴近生产 | 有凭据、环境、外部网络、企业策略与版本漂移风险；公开模板不提供生产机器改 HKLM/MDM 步骤 | 只在内网安全评审后做，不纳入公开模板必需项 |

**推荐**：采用 **A + B1 + B2**。C 只能作为组织内部补充，不能替代公开 POC 中的可复用采证结构。B2 可以不“安装到全局系统”，但仍必须有固定待测制品；“未安装”不等于“不需要制品”。

## 3. 纯文本结构图：控制面、执行面与策略面边界

```text
[Host / Controller]
  ├─ host env: HOST_CANARY_SYNTHETIC_ONLY
  ├─ user/project settings
  ├─ managed policy loader: remote > MDM/HKLM > managed files > HKCU(低优先级)
  └─ MCP catalog/cache/connection identity
          │ 允许传递：声明、source_environment、target_environment、capability、合成测试事件
          │ 禁止降级：host env fallback、已声明 deny、admin policy source
          ▼
[Executor / Sandbox]
  ├─ executor env: EXECUTOR_CANARY_SYNTHETIC_ONLY
  ├─ remote HTTP MCP / stdio/local transport
  ├─ approved command policy transform
  └─ OS sandbox: Linux+bwrap / Linux-no-bwrap / Windows / WSL
          ▼
[Observer]
  ├─ captured HTTP RPC headers/body（ExecutorOnly 请求不得含 host canary；host-owned 正控单列）
  ├─ filesystem read/write result（deny 与 write 分离）
  ├─ stderr/status/doctor policy source
  └─ case_status: PASS | FAIL | SKIP | BLOCKED | NOT_RUN
```

## 4. 安全执行前置与平台矩阵

### 不可绕过的安全前置

1. root metadata 路径只允许指向 fixture 内合成根；必须先建立外层 user/mount namespace + tmpfs root，再执行任何 `/.git`、`/.codex`、`/.agents` 相关操作。不得用 `sudo`、真实宿主根目录或放松宿主 namespace 安全设置来“修复”测试环境。
2. Windows/WSL/MDM 管理策略验证只允许在 disposable VM、独立用户、独立 registry hive、无企业注册、无真实凭据的环境中运行。公开模板不得提供在现用企业机器写 HKLM、MDM 或生产 managed policy 的步骤。
3. 纯 mock loader 标注为 B1 单元级；不能替代产品真实管理员源路径。B2/C 若缺少隔离或固定待测制品，应标 `BLOCKED` 或 `NOT_RUN`，不能记 PASS。
4. 所有 artifact 使用相对路径，如 `artifacts/CAX-07/metadata.json`；采证前后扫描 artifact，禁止真实 token、cookie、SSH key、云密钥。

### 平台矩阵

| 平台 | 必跑项 | 可跳过项 | skip/blocked 规则 |
|---|---|---|---|
| Linux + bwrap/namespace 可用 | MCP provenance；approved command + `/dev` + deny；合成根 root metadata symlink | Windows registry/HKCU | bwrap 不存在或 user namespace 禁用时标 `SKIP`，不得记 PASS |
| Linux 但 bwrap 不可用 | MCP provenance；policy transform 单元级；managed file parsing | bwrap 执行级 sandbox | 记录 `skip_reason=bubblewrap_unavailable` 或 namespace 错误；执行级 root metadata case 不得用宿主根替代 |
| Windows native disposable VM | managed HKLM/HKCU；approved command Windows drive/UNC policy materialization | bwrap/root metadata | 无隔离管理员 hive 或无 disposable VM 时标 `BLOCKED`；不可用 HKCU 伪造管理员源 |
| WSL disposable VM | Windows/WSL managed source precedence；Linux 文件源；MCP provenance | native HKLM 可在独立 hive 中运行 | 必须区分 Windows HKCU 与 WSL `/etc/claude-code`；WSL 继承需显式 opt-in；管理员源 present-but-invalid 不应退到用户可写源 |

## 5. 验收用例（12 个主 case，子 case 逐条初始 NOT_RUN）

字段固定为：前置、输入、步骤、期望、observer、evidence_level、case_status。`case_status=NOT_RUN` 表示本模板设计未执行；实际运行时再改为 PASS/FAIL/SKIP/BLOCKED。必选矩阵不能用 SKIP/BLOCKED 替代 PASS；SKIP/BLOCKED/NOT_RUN 必须独立统计。

### CAX-01：executor MCP credential 在 capability 正常与降级时都不能 host fallback

- 前置：host env 有 `MCP_CANARY=HOST_CANARY_SYNTHETIC_ONLY`；executor env 有同名 `MCP_CANARY=EXECUTOR_CANARY_SYNTHETIC_ONLY`；loopback mock HTTP MCP 捕获 Authorization；server 源为 executor-discovered 且 credential policy 为 `ExecutorOnly`。
- 子 case：
  - CAX-01a capability 正常正控：executor HTTP MCP 声明 `bearer_token_env_var=MCP_CANARY` 且保留 `httpHeaderEnvVars` capability；子 agent 调用 MCP；期望 HTTP RPC Authorization 只含 executor canary，host canary 不出现在 headers/body/logs。case_status：NOT_RUN。
  - CAX-01b reconnect 降级负控：缓存 executor MCP 声明后触发 session retire/reconnect，并移除 `httpHeaderEnvVars` capability；期望 server startup error 或 tool 不可用，产品结果为 `DENIED_UNSUPPORTED_CAPABILITY`，不得读取 host env，不能用降级前请求冒充降级后成功。case_status：NOT_RUN。
- observer：executor RPC 中的 env 引用、实际 MCP HTTP Authorization、降级前后请求数、MCP 启动失败理由、reconnect barrier、connection/cache identity。
- evidence_level：B2 loopback product integration；若只有 mock parser，则标 B1 且产品 NOT_RUN。

### CAX-02：host-owned MCP 仍可使用 host credential，executor 声明不能借 `local` 升级

- 前置：host-owned 注册/配置构造一个 MCP，含 `bearer_token_env_var=MCP_CANARY`；另有 executor-origin server 作为对照。
- 子 case：
  - CAX-02a host-owned 正控：通过 host config source 或 host-owned registration 构造；期望 host synthetic canary 可按配置使用。case_status：NOT_RUN。
  - CAX-02b executor-origin 负控：使用已由来源与transport组合确定为 `ExecutorOnly` 的远程HTTP server，即使声明 `environment_id=local`，也不能据此获得 host authority；期望仍无host fallback。插件不能仅因被executor选中就一概标为ExecutorOnly，应逐项记录实际registration source、transport与policy；本例不覆盖其他组合。case_status：NOT_RUN。
- observer：registration source、source_environment、target_environment、transport、credential_policy、Authorization。
- evidence_level：source_test 或 B2。

### CAX-03：ExecutorOnly 拒绝本地 transport / host header helper

- 前置：executor-discovered server 被标记 `ExecutorOnly`。
- 子 case：
  - CAX-03a remote HTTP 且无 host env headers/helper：可进入连接流程；若使用 loopback mock，记录 remote 指执行环境语义，不代表公网 URL。case_status：NOT_RUN。
  - CAX-03b local stdio、local environment、remote HTTP 但带 host `env_http_headers` 或 `headersHelper`：server 级 startup error；不一定整个 CLI 进程退出。case_status：NOT_RUN。
- observer：stderr/error code、effective server credential_policy、transport、environment、helper 字段。
- evidence_level：source_test 或 B2；不得从 D1 推导 HTTPS/TLS/SSRF 已验。

### CAX-04：credential_policy 纳入连接/cache identity

- 前置：同名同 URL MCP 分别由 host 与 executor 声明。
- 子 case：
  - CAX-04a host→executor：先连接 host-owned，再 materialize executor-owned；期望不复用 host 权限域连接或 tool catalog cache。case_status：NOT_RUN。
  - CAX-04b executor→host：反向顺序测试；若上游未直接运行该方向，则报告为本模板待测，不声称源码测试已覆盖。case_status：NOT_RUN。
- observer：cache key、connection id、credential_policy、name/transport/URL/source 差异。
- evidence_level：source_test 或 B2。

### CAX-05：approved command 可写输出但保留 secret deny；写权限不是最小输出路径

- 前置：restricted FS policy；`secret.txt` 显式 `deny-read`；审批前 output 路径不可写，以证明权限扩展发生。
- 子 case：
  - CAX-05a 审批前负控：写 output 失败或不可写；读 secret 失败。case_status：NOT_RUN。
  - CAX-05b approved command：调用 policy transform 后，命令获得较宽 root/volume 写权限，写 output 成功，读 secret 仍被拒绝。case_status：NOT_RUN。
- observer：exit code、stderr、文件内容、effective policy before/after diff。
- evidence_level：sandbox_runtime 或 B2；不得写成“仅必要输出路径授权”。

### CAX-06：Linux 设备恢复、显式设备 deny、mount 参数三者分开

- 前置：Linux+bwrap 可用；设备读取必须有界。
- 子 case：
  - CAX-06a 执行设备正控：approved root write 后访问 `/dev/null`、有界读取 `/dev/urandom` 或等价标准设备成功。case_status：NOT_RUN。
  - CAX-06b 执行设备 deny 负控：显式 deny `/dev/zero` 后访问被拒绝；普通 deny 文件不能替代此子 case。case_status：NOT_RUN。
  - CAX-06c mount-args 静态检查：检查 bwrap mount/deny 顺序；注明静态参数检查不能替代内核执行。case_status：NOT_RUN。
- observer：stdout/stderr、skip_reason、mount args 摘要、effective policy。
- evidence_level：sandbox_runtime + source_test。

### CAX-07：合成根 root metadata symlink 不得重开 deny 子树

- 前置：Linux+bwrap；在 user/mount namespace + tmpfs 合成根内创建 `/.git`、`/.codex`、`/.agents` fixture；绝不建、删、改真实宿主 `/.git`、`/.codex`、`/.agents`。
- 子 case：
  - CAX-07a deny-target 失败：`/.git` 或 `/.codex` 指向 deny 子树；经 symlink 读 secret 或写 deny target 必须失败；不要同时要求该 metadata path 写入成功。case_status：NOT_RUN。
  - CAX-07b public-target 成功：`/.codex` 指向 public writable target；写 public marker 成功，同时其它 deny 仍有效。case_status：NOT_RUN。
  - CAX-07c writable symlink 拒启：deny path 跨 writable symlink 无法强制时，sandbox 拒启并报告原因。case_status：NOT_RUN。
  - CAX-07d narrower carveout 正控：显式窄 write carveout 允许被声明的 reopened 子路径，兄弟 deny 仍拒绝。case_status：NOT_RUN。
- observer：marker 文件、private changed 不存在、stderr、namespace proof、synthetic-root path。
- evidence_level：sandbox_runtime；缺少隔离前置为 BLOCKED，不能用宿主根替代。

### CAX-08：project roots / root deny 无法解析时保持原 policy

- 前置：policy 含 project-roots glob deny、坏 glob、缺 workspace roots、或 root deny。
- 子 case：
  - CAX-08a workspace roots 缺失且需 materialize project-roots：返回原 policy。case_status：NOT_RUN。
  - CAX-08b bad glob / unresolvable denial：返回原 policy并记录 reason。case_status：NOT_RUN。
  - CAX-08c root deny：返回原 policy，不进行危险 root write 扩权。case_status：NOT_RUN。
- observer：完整 policy before/after diff、reason、return status。
- evidence_level：source_test 或 B2。

### CAX-09：managed boolean lock 类型错误仍按严格 fallback 生效

- 前置：Claude 管理员源为 MDM/HKLM/managed file/remote 中的隔离测试源；不得在生产 HKLM/MDM 写入。
- 子 case：
  - CAX-09a `disableClaudeAiConnectors` 错型：startup/status/doctor 命名错误 key，按更严格行为生效。case_status：NOT_RUN。
  - CAX-09b `allowManagedPermissionRulesOnly` 错型：宽松用户 permission rules 不得覆盖管理锁。case_status：NOT_RUN。
  - CAX-09c 有效真假对照：同 key 有效值时行为符合 docs/changelog。case_status：NOT_RUN。
- observer：effective policy、stderr、`/status` source、`claude doctor` dropped-entry list。
- evidence_level：B1 mock fixture 或 B2/C disposable VM；不得凭空假设存在 dry-run 导出命令。

### CAX-10：managed 嵌套坏值不丢弃整块，但不承诺任意坏 block 都保留

- 前置：managed source 隔离 fixture；每个 block 使用 A4 已知 schema 字段构造一个坏 entry 和一个有效邻项。
- 子 case：
  - CAX-10a `permissions`：一个坏 permission rule 被 warning/strip，一个有效 deny/allow 规则继续生效。case_status：NOT_RUN。
  - CAX-10b `autoMode`：坏 `autoMode` entry 不应丢弃同块有效规则；若无法确定 schema，应标 NOT_RUN 而不是模糊 PASS。case_status：NOT_RUN。
  - CAX-10c `worktree`：坏 `worktree` 嵌套值不应丢弃同块有效 `baseRef`、`symlinkDirectories` 或 `sparsePaths` 对照。case_status：NOT_RUN。
  - CAX-10d `attribution`：坏 `attribution` 嵌套值不应丢弃同块有效 commit/pr/sessionUrl 对照。case_status：NOT_RUN。
  - CAX-10e residual top-level bad key 或 policyHelper 残留 schema 错误：按 A2 单独 oracle 处理，不能与可修 entry 混同。case_status：NOT_RUN。
- observer：invalid entry list、warning、effective block、保留下来的有效项。
- evidence_level：B1 fixture 或 B2/C。

### CAX-11：Windows/WSL 管理员源 present-but-invalid/unreadable 不退到用户可写宽松策略

- 前置：disposable VM/独立 hive；HKCU 有宽松策略作为对照；WSL 继承只在 `wslInheritsWindowsSettings` opt-in 时测试。
- 子 case：
  - CAX-11a missing admin source：absent file/profile/registry value 不是错误；可继续到低优先级或无该源。case_status：NOT_RUN。
  - CAX-11b empty admin file：empty managed settings file 视为 `{}`。case_status：NOT_RUN。
  - CAX-11c malformed / not JSON object admin source：managed file/drop-in/MDM/HKLM present 但无法解析为 JSON object 时拒启并命名 source，即使另一 admin source 有有效 policy。case_status：NOT_RUN。
  - CAX-11d unreadable admin file/drop-in/directory：当无其他 admin policy 且会话以 claude.ai 或 Claude Console credentials 登录时，启动退出并提示联系管理员；其它登录模式按 docs 单独记录。case_status：NOT_RUN。
  - CAX-11e HKCU malformed：不阻断启动，仅在 `/status` 与 `claude doctor` notice；不得被当作管理员源 fail-closed。case_status：NOT_RUN。
  - CAX-11f WSL present-but-invalid：Windows HKLM/managed-settings opt-in 后，present-but-invalid/unreadable 管理源不得退到 WSL `/etc/claude-code` 或 HKCU 宽松策略。case_status：NOT_RUN。
- observer：policy source、skipped sources、stderr/status、exit code、login mode、other-admin-source presence。
- evidence_level：B1 fixture 或 C disposable VM；公开模板不提供生产 HKLM 步骤。

### CAX-12：版本锁 invalid fail-open 与 deniedMcpServers 边界

- 前置：managed source fixture；含有效对照 key。
- 子 case：
  - CAX-12a `requiredMinimumVersion` invalid：该约束 drop / fail-open by design，记录 warning 与 version gate result。case_status：NOT_RUN。
  - CAX-12b `requiredMaximumVersion` invalid：独立参数化验证，不能用 minimum 输入同时断言 maximum。case_status：NOT_RUN。
  - CAX-12c `deniedMcpServers` 单 entry 坏：坏 entry stripped，valid subset enforced。case_status：NOT_RUN。
  - CAX-12d `deniedMcpServers` 整体坏：whole value dropped with warning，其他有效 key 继续执行。case_status：NOT_RUN。
- observer：warning、effective policy、version gate result、有效邻键执行结果。
- evidence_level：B1 fixture 或 B2/C；无效版本约束被丢不等于已验证所有版本都可运行。

## 6. 采证 JSON 示例（CAX-01 拆分后正文与 JSON 同步）

```json
{
  "schema_version": "authority-degradation-gates/v1",
  "as_of": "2026-09-26",
  "case_id": "CAX-01",
  "case_status": "NOT_RUN",
  "product": "codex",
  "version_under_test": "main-or-build-sha-required",
  "evidence_level": "B2_loopback_product_integration_required_for_runtime_pass",
  "evidence_refs": [
    {
      "source_id": "D1",
      "url": "https://github.com/openai/codex/commit/c7e80f873f67.diff",
      "sha": "c7e80f873f67dbef58206b9d4f3c60e9d556eb16",
      "body_sha256": "eeec418e3e63d581873df99c6e8286719f764eac4a070efa883038a165522258",
      "observed_at_utc": "2026-09-25T19:17:39Z",
      "oracle_summary": "executor token succeeds only while executor header capability is present; after reconnect downgrade tool is unavailable and host fallback is disabled"
    }
  ],
  "platform": {
    "os": "linux",
    "sandbox": "bwrap-or-loopback-only",
    "bwrap_available": null,
    "wsl": false
  },
  "preconditions": [
    "host env MCP_CANARY=HOST_CANARY_SYNTHETIC_ONLY",
    "executor env MCP_CANARY=EXECUTOR_CANARY_SYNTHETIC_ONLY",
    "executor-discovered MCP server has credential_policy=ExecutorOnly",
    "no real secrets"
  ],
  "subcases": [
    {
      "subcase_id": "CAX-01a",
      "name": "capability-present positive control",
      "input": {
        "mcp_server_source": "executor_discovered",
        "transport": "remote_http_loopback",
        "httpHeaderEnvVars_capability": "present"
      },
      "steps": [
        "start fixed product artifact with executor env canary",
        "call MCP through executor-discovered server",
        "capture HTTP RPC"
      ],
      "expected_product_outcome": "MCP_CALL_SUCCEEDS_WITH_EXECUTOR_CREDENTIAL",
      "expected": [
        "captured HTTP Authorization contains executor synthetic canary only",
        "host synthetic canary absent from headers/body/logs",
        "connection/cache identity includes credential_policy"
      ],
      "case_status": "NOT_RUN"
    },
    {
      "subcase_id": "CAX-01b",
      "name": "reconnect capability downgrade negative control",
      "input": {
        "mcp_server_source": "executor_discovered",
        "transport": "remote_http_loopback",
        "capability_change": "httpHeaderEnvVars removed after reconnect"
      },
      "steps": [
        "cache executor MCP declaration",
        "retire old executor session and reconnect through downgrade barrier",
        "attempt child-agent MCP call and capture startup/error path"
      ],
      "expected_product_outcome": "DENIED_UNSUPPORTED_CAPABILITY_OR_TOOL_UNAVAILABLE",
      "expected": [
        "MCP server startup fails or tool is unavailable after downgrade",
        "no host environment lookup occurs",
        "host synthetic canary absent from headers/body/logs",
        "any executor-token HTTP traffic is identified as pre-downgrade or capability-present control, not as downgrade success"
      ],
      "case_status": "NOT_RUN"
    }
  ],
  "observer": {
    "http_rpc_capture_path": "artifacts/CAX-01/http.jsonl",
    "stderr_path": "artifacts/CAX-01/stderr.txt",
    "effective_policy_path": "artifacts/CAX-01/policy.json",
    "reconnect_trace_path": "artifacts/CAX-01/reconnect.json"
  },
  "actual": null,
  "skip_reason": null,
  "blocked_reason": null,
  "not_run_reason": "public template only; product not executed"
}
```

## 7. QA / 部署 / 图边界落地

- **QA gate**：每个主 case 与子 case 必须产出 `case_status`；`SKIP`、`BLOCKED`、`NOT_RUN` 独立统计，不得合并为 PASS。必跑安全矩阵只有实际满足 oracle 才能 PASS。
- **部署 gate**：若待部署版本无法证明包含 D1/D2 等价修复，或 Claude managed policy 行为无法证明在目标版本生效，则标 `blocked_for_deploy=true`，并列出版本/commit/artifact hash 缺口。
- **图边界**：报告中必须同时展示 host/controller、executor/sandbox、managed policy source、observer 四层；任何跨层数据流必须说明“允许传递”与“禁止降级”。
- **凭据边界**：只使用合成 canary；采证前后扫描 artifacts，禁止出现真实 token、cookie、SSH key、云密钥。
- **平台边界**：Linux+bwrap 的通过不能自动代表 Windows/WSL；Windows HKLM/HKCU 的通过也不能自动代表 Linux managed file。D2 中 Linux capability 序列化/默认值证据不能推导所有旧 executor 都被运行时 gate 拦住。

## 8. 未核实边界

1. 未安装或运行 Codex/Claude CLI；所有主 case 与子 case 初始状态为 `NOT_RUN`。
2. Codex 两个修复均为 main commit 证据；`rust-v0.157.0` release 早于 commit，不能声称已包含。后续 package/版本需以实际 artifact SHA 或 release note 再证。
3. Claude 当前 docs 是滚动文档，不能把所有 managed-settings 行为归因于 `2.1.282`；只能把 changelog 明确三项归入该版本。
4. `ExecutorOnly` 不等于所有 MCP 禁止 host；host-owned 配置可保留 `HostFallbackAllowed`。
5. `approved command` 是为单条被批准命令授予较宽 root/volume 与 root metadata 写权限并保留 deny，不是最小输出路径授权、清空 deny 或持久全局提权。
6. bwrap/namespace 不可用、隔离管理员 hive 缺失、WSL 继承链缺失等环境条件必须记录为 `SKIP` 或 `BLOCKED`，不能算作失败或通过。

## 9. 发布状态

本文件是公开验收设计模板修订稿，用于复评；它不是产品 POC 结果、不是安全评审结论、不是部署放行证明。
