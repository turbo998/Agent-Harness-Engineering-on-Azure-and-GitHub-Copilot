# LogAct：意图、裁决与副作用边界（5分钟恢复性Meta资产）

日期：2026-10-01
对象：`facebookresearch/logact` 固定到 `d5c33229f5bf8833779f871c04f9773d85adc70a`
状态：只读研究产物；未编译、未安装、未运行仓库代码；所有宿主产品卡均为 `NOT_RUN`。
证据范围：固定源码静态分析与故障注入设计；不代表宿主产品运行验收。
用途：给客户/POC/QA快速区分“执行前意图日志 + policy裁决”与“真实工具成功/副作用安全边界”。

## 0. 一句话结论

LogAct 的关键价值是把工具执行前的 **Intention** 持久写入 AgentBus，并等待 policy pipeline 返回 `approved / reason / log_position`；但该结果只是“裁决”，**不等于工具已成功执行，也不等于外部副作用恰好一次**。当前 OSS 本地插件还明确存在两个边界：本地 policy 默认允许（OnByDefault），hook 故障返回非阻断状态；Claude enforced 模式下拒绝票转成 `ask`，不是不可绕过的 `deny`。

POC 还必须处理三个具体协议边界：**同文本 RPC 重试会新建 intention；错误响应可能发生在 Commit 已落盘之后，必须进入 UNKNOWN 对账；policy 约束是 minimum 而非 exact snapshot**。`FirstBooleanWins` 既不是 quorum，也不是最快模型获胜：孤立请求中 voters 按 ID 排序求值并依次写票。以下将这些结论落实到字段、序列图与 AC-11/12，而不是只加免责声明。

## 1. 固定源码引用（只引用固定 SHA）

| 编号 | 证据点 | 固定源码引用 |
|---|---|---|
| S1 | `CommitIntentionOutcome` 只含 `approved/reason/log_position`；`commit_intention` 会等待 safety pipeline，`approved` 是 decider verdict。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/api/src/traits.rs` lines 22-32, 62-75 |
| S2 | `FirstBooleanWinsApplicator` 的状态键按 `bus_id` 与 policy id 区分；写状态使用 expected position 与新 position。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/policy_decider_applicator.rs` lines 79-120, 230-241 |
| S3 | 同一 position 重放返回 `last_payload`；旧 position 报 `StalePosition`。 | 同上 lines 184-195 |
| S4 | pending intention 遇到匹配的首个 boolean vote 即生成 Commit/Abort 并清空 pending；不是多数票/全票机制。 | 同上 lines 198-216, 245-271 |
| S5 | 本地 SQLite 服务在 policy register 缺失时 bootstrap `DeciderPolicy::OnByDefault`。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/grpc/local_server/src/sqlite_backed_commit_service.rs` lines 59-78 |
| S6 | Claude hook：`enforced=false` 不输出裁决；approved=true 也不输出；拒绝且 enforced=true 输出 `permissionDecision: ask`。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/cli/src/claude_hooks.rs` lines 103-122 |
| S7 | 插件记录 Claude Code、Codex、Muse Code lifecycle；`PreToolUse` 通过 CommitService policy engine；hook 失败非阻断，本地 policy 当前默认允许。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/plugins/logact-oss/README.md` lines 3-5, 47-48 |
| S8 | MIT 许可允许使用/复制/修改/分发，但软件按“AS IS”无担保；许可证不等于安全保证。 | `https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/LICENSE` lines 1-21 |

### 1.1 五条源码纵深结论（静态证据，不是运行结果）

| 发现 | 证据与机制 | 直接改变的 POC 设计 |
|---|---|---|
| D1 请求身份不等于日志身份 | E1:12-32 command 只有 bus/intention；E4:77-92,161-167 包装调用；E5:598-627 每次 propose 独立 append；结果位置指 intention。相同文本再提形成新 position。 | 稳定 `(tenant_id,bus_id,request_id)` + payload hash 与 operation 映射；不能以字符串里的 tool-use-id 自动获得幂等。见 AC-11。 |
| D2 持久化分阶段，error 不证明未提交 | E5:813-919 先 applicator CAS，再 produced append，最后 engine cursor/policy CAS；E5:736-759 读到该 intention 首次 Commit/Abort 返回。E9:41-51,75-106 是单次条件写；E10:35-45,62-90 配置 WAL/FULL；E12:90-133 同库不同连接，不构成全管线事务。E11:33-57 映射传输错误。 | 对账 log、applicator checkpoint、engine cursor 三态；UNKNOWN 与业务 Abort 分开。SQLite 结论以文件系统正常持久性为前提，不是任意硬件丢写保证。成功响应也不是所有游标已越过该决策。 |
| D3 replay 只复用最新已持久结果 | **voter** E6:142-170 相等 position 回放完整 Vote，旧 position stale，求值在 put 前；**decider** E7:184-241 保存 last_payload/pending；E5:354-391 容忍 stale。E13:126-144 定义 applicator 重放契约。 | 恢复必须关联日志与 checkpoint 一致点；不宣称历史 LLM 票可免费、逐字重算。记录 model/voter attempt 与持久化状态，不让 voter 做业务副作用。AC-02/03 已就地修正。 |
| D4 minimum 不是 exact policy pin | E2:46-54 拒绝外部 constraint；E5:247-267,598-674 附 MinimumPolicyVersion 并检查下限；E8:18-71 相同/旧版本无 batch，复用 voter_id 却改变配置会报错；E5:877-918,1002-1014 仅 expected version 匹配且 new version 前进时应用 batch。 | intention 前可能插入更高政策；审计实际生效 batch，而非只记 provider 初读值。回滚发新 epoch，配置变化发新 voter identity；精确 pin 需扩展。 |
| D5 多 voter 非 quorum，single pending 有并发边界 | E5:846-875,977-986 按 voter ID 顺序 await/append；E7:41-45,198-216,245-249 只保留一个 pending，首个匹配布尔票决策；E3:125-144 每请求 spawn_local。 | 不承诺 deny-overrides；初版每 bus 单 in-flight。`I_A,I_B,V_A,V_B` 可导致 A 票被忽略是条件性静态推导，须 AC-12 证实调度前缀，不冒充复现。 |

### 1.2 深入证据索引 E1—E13

S1—S8 与 E1—E13 分开编号，避免把 decider 的 replay 误归到 voter。下列来源均固定同一 SHA；13 份源码内容摘要已核对，所列 URL 于 2026-10-01 复核可达。可达性与内容完整性核查不等于产品实测。

| ID | 固定源码（行号见 D1—D5/验收卡） |
|---|---|
| E1 | [api/src/traits.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/api/src/traits.rs) |
| E2 | [grpc/src/translation.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/grpc/src/translation.rs) |
| E3 | [core/src/channeled.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/core/src/channeled.rs) |
| E4 | [v1/src/commit_service_v1.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/src/commit_service_v1.rs) |
| E5 | [engine/src/base_engine.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/base_engine.rs) |
| E6 | [engine/src/stateless_voter_adapter.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/stateless_voter_adapter.rs) |
| E7 | [engine/src/policy_decider_applicator.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/policy_decider_applicator.rs) |
| E8 | [engine/src/policy.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/policy.rs) |
| E9 | [impls/sqlite/src/lib.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/sqlite/src/lib.rs) |
| E10 | [bus sqlite_db.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/bus/impls/sqlite/src/sqlite_db.rs) |
| E11 | [grpc/src/handler.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/grpc/src/handler.rs) |
| E12 | [local_server sqlite_backed_commit_service.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/grpc/local_server/src/sqlite_backed_commit_service.rs) |
| E13 | [engine/src/applicator.rs](https://raw.githubusercontent.com/facebookresearch/logact/d5c33229f5bf8833779f871c04f9773d85adc70a/logact/commit_service/impls/v1/engine/src/applicator.rs) |

## 2. 架构图：意图、裁决、效果边界

```text
User / Agent turn
      |
      v
Host adapter PreToolUse  --(hook failure: nonblocking diagnostic, not fail-closed)--> Native host flow
      |
      v
CommitSvc.commit_intention
      |
      v
Durable AgentBus / SQLite
  - append Intention
  - append Vote / Commit / Abort
  - remember decider state per bus + policy id
      |
      v
Policy voter / decider
  - OnByDefault: allow baseline when unconfigured local register is bootstrapped
  - FirstBooleanWins: first matching boolean vote decides Commit or Abort
      |
      v
Decision returned to adapter
  approved + reason + log_position
      |
      +--> audit record: decision exists before tool attempt
      |
      +--> human/native permission layer still applies
      |
      v
Tool execution / external side effect
  - success/failure is a separate event stream
  - exactly-once for external effects must be designed outside the decision log
```

边界标注：日志裁决不是工具成功证明；持久化裁决可帮助重放/审计，但不能单独替代 sandbox、IAM、egress control、secret 管控或业务幂等键。

## 3. 三种落地方案比较（方案设计，不声称上游均已提供）

| 方案 | 定义 | 适合场景 | 优点 | 主要风险/边界 | POC验收重点 |
|---|---|---|---|---|---|
| audit-only | 只采集 UserPrompt/PreToolUse/PostToolUse/Stop 与裁决记录；不阻断宿主工具流。 | 研发审计、复盘、低风险团队试点。 | 对宿主行为侵入低；先建立证据链。 | 拒绝票若不接入阻断层，不能防止工具执行；hook故障非阻断时只剩诊断。 | 证明每个工具尝试前有 intention 记录；证明失败时不会误报“已阻断”。 |
| human-gated | 拒绝/高风险裁决升级为人工或宿主原生权限询问；执行仍由宿主/人确认。 | 高风险命令、数据导出、生产变更的半自动流程。 | 保留人类判断；适合 Claude `ask` 语义。 | 人可批准，故不是硬安全边界；无人值守自动化会卡住或行为不一致。 | 验证 Claude negative vote 在 enforced=true 下为 `ask` 而非 `deny`；记录人工决策。 |
| enforced adapter | 自建适配层在工具执行前强制检查裁决；拒绝时 adapter 不调用工具。 | 需要强约束的内部代理平台。 | 可把裁决接到真实执行门。 | 本文不声称上游当前 OSS 插件默认就是 fail-closed；仍需处理 adapter 绕过、hook失败、外部幂等、权限隔离。 | 注入 hook故障/存储故障/重复请求，确认拒绝策略、恢复策略和外部副作用恰好一次由平台实现。 |

## 4. 合成事件（用于POC讨论，不含真实secret/生产数据）

### 合成事件 A：允许但工具仍失败

| 字段 | 值 |
|---|---|
| event_id | `synthetic-logact-2026-10-01-A` |
| host_product | `Claude Code / Codex / Muse Code` 均 `NOT_RUN` |
| phase | `PreToolUse -> decision -> PostToolUseFailure` |
| intention | “读取项目 README 并生成摘要” |
| decision | `approved=true`, `reason=ON_BY_DEFAULT policy`, `log_position=1201` |
| effect | 工具调用阶段发生文件不存在错误，真实副作用为 `none` |
| 结论 | `approved=true` 仅代表裁决允许，不代表工具成功。 |

### 合成事件 B：拒绝票在 Claude enforced 中升级为 ask

| 字段 | 值 |
|---|---|
| event_id | `synthetic-logact-2026-10-01-B` |
| host_product | `Claude Code` `NOT_RUN` |
| phase | `PreToolUse -> negative vote -> hook output` |
| intention | “向外部网络上传疑似客户文件” |
| decision | `approved=false`, `reason=policy: external exfiltration risk`, `log_position=1218` |
| adapter_outcome | Claude hook 在 enforced=true 时输出 `permissionDecision=ask`，不是 `deny`。 |
| 结论 | 这是 human-gated 行为；无人值守场景不能把它宣传成不可绕过强制拒绝。 |

## 5. 验收卡（含前提/步骤/期望/负控）

> 执行状态：以下为 POC 验收设计卡，本轮全部 `NOT_RUN`。不得把源码自带测试或静态阅读写成“本轮已通过”。

### AC-01：裁决字段不等于工具成功

- 前提：固定源码版本 `d5c33229f5bf8833779f871c04f9773d85adc70a`；宿主产品卡 `NOT_RUN`；只使用合成工具事件。
- 步骤：构造一个 PreToolUse intention，policy 返回 `approved=true`；随后模拟工具执行失败的 PostToolUseFailure。
- 期望：报告中出现 `approved/reason/log_position` 与独立的工具失败结果；不得把 `approved=true` 写成“工具已执行成功”。
- 负控：若报告仅因 `approved=true` 标记业务完成，则验收失败。

### AC-02：同一 bus/policy/position 重放幂等的是裁决状态，不是外部副作用

- 前提：FirstBooleanWins 同一 `bus_id`/policy identity 的**最新输入**已成功保存 state；尚未前进到更大 position。voter 的相等位置复用另见 E6，不能只用 decider 的 S3 证明 voter 行为。
- 步骤：对同一 BusEntry 重复 apply；分别观测 decider `last_payload`、voter 已持久 Vote（含 reason/config）。另设 voter 求值完成但 put 失败的负控。
- 期望：相等于最后已持久 position 时复用原 payload；旧输入不保证重新求值。put 前失败后的重试可能再次求值，不能承诺 LLM 调用 at-most-once。（E6:142-170；E7:184-241）
- 负控：把“重新调用相同文本 RPC”当作相同 position replay、把 checkpoint 当全历史缓存、或因 payload 复用宣称外部副作用 exactly-once，均失败。

### AC-03：旧 position 在 applicator 报 StalePosition，engine 可以跳过

- 前提：同一 state key 已保存较新的 position。
- 步骤：分别观测内部 applicator apply 与 engine `apply_tolerating_stale`，不混用两个 API 层的期望。
- 期望：applicator 返回 `StalePosition` 且不覆盖新 state；engine 将该错误视为 None 并跳过，这是明确容许的恢复路径，并非必须向 RPC 暴露错误。（E6:142-149；E7:184-195；E5:354-391）
- 负控：若旧事件覆盖 state，或验收要求 engine 对每个 stale 必须报错/输出诊断才算安全，则判为实现或验收设计错误；不把内部异常自动定性为 RPC 漏洞。

### AC-04：first-boolean-wins 不是多数票/否决优先

- 前提：pending intention 已存在；随后两个 voter 先后给出 boolean vote。
- 步骤：先输入 `approved=true`，再输入 `approved=false`。
- 期望：首个匹配 boolean vote 产生 Commit 并清空 pending；后续 false 不得被描述成自动否决。
- 源码回归设计：隔离请求安装 `a_allow=true`、`z_deny=false`，预期 allow 票先入日志；交换两者 ID 排序应改变首票。engine 按 voter_id 字典序依次 await 匹配 voters，再按 produced 顺序 append，不是响应最快者胜出；慢的后置 voter 仍可能延迟整批票落盘。（E5:846-875,977-986；E7:198-216）
- 负控：若产品文案写“多评审投票/全票通过/一票否决”，则验收失败。

### AC-05：OnByDefault 基线必须暴露为风险边界

- 前提：本地 SQLite policy register 缺失或新建；未配置自定义 policy。
- 步骤：启动隔离实例并观察初始化 policy state。
- 期望：基线是 `DeciderPolicy::OnByDefault`；客户材料写明“当前本地 policy 默认允许”。
- 负控：若材料称“默认拒绝/默认 fail-closed/开箱即安全沙箱”，则验收失败。

### AC-06：hook 故障 nonblocking

- 前提：宿主 hook 环境可模拟 socket 不可达、存储不可达或 hook 进程错误。
- 步骤：触发 PreToolUse 时断开本地服务；记录宿主看到的 hook 状态。
- 期望：材料说明 hook failure 返回诊断与非阻断状态；必须另设 adapter/sandbox 才能 fail-closed。
- 负控：若 hook 故障被写成“工具一定不会执行”，则验收失败。

### AC-07：Claude negative vote 在 enforced=true 下是 ask

- 前提：Claude hook 处于 `enforced=true`；policy 对 PreToolUse 返回 `approved=false`。
- 步骤：记录 hook 输出字段。
- 期望：输出 `permissionDecision=ask` 与 reason；材料称其为人工/宿主权限询问。
- 负控：若写成 `deny`、不可绕过拒绝或无人值守强制阻断，则验收失败。

### AC-08：approved=true 在 Claude hook 中不输出裁决，保留原生权限流

- 前提：Claude hook `enforced=true`；policy 返回 `approved=true`。
- 步骤：观察 hook stdout/宿主原生权限流。
- 期望：hook 对 approved case 不输出特殊 permissionDecision；宿主原生权限流程仍可继续工作。
- 负控：若材料声称 LogAct approval 会自动替代宿主权限系统，则验收失败。

### AC-09：audit-only 模式不得宣传成强制边界

- 前提：仅安装/接入日志采集或只读审计；没有 adapter 阻断工具调用。
- 步骤：对高风险 intention 产生 negative decision，但不接阻断层。
- 期望：审计中能看到拒绝原因；工具是否执行取决于宿主/适配器，不得由审计层宣称阻断。
- 负控：如果 audit-only POC 被当成“安全门已上线”，则验收失败。

### AC-10：许可证与安全保证分离

- 前提：引用 MIT 许可正文；未完成供应链、依赖、运行时隔离审计。
- 步骤：在客户材料“许可/风险”处同时列出 MIT 与 “AS IS / no warranty”。
- 期望：可说明许可宽松，但不以 MIT 代表安全、合规、生产可用。
- 负控：若材料出现“MIT 所以可安全生产启用/无需审计”，则验收失败。

### AC-11 / F1：Commit 已落盘但回复失败——先对账，禁止盲目重提

- 状态/前提：`NOT_RUN`；未来仅在授权临时 SQLite、固定 SHA、FirstBooleanWins + 确定性 counting voter、无真实副作用的 stub 中执行。准备可观测 SQL/append/回复切点，不能将计划写成已注入。
- 步骤一：在 **Commit append 成功之后、最终 engine-state put** 注入 `BackendUnavailable`；观测 RPC error 与已存在终态。CAS conflict 可重试，不保证每次冲突都对外报错，故此切点明确用不可用错误。
- 步骤二：另一个干净样本在内部全部成功、oneshot/gRPC 回复送达前丢 ack；重开同库。先查原 intention 的首次 Commit/Abort，再分别测试原 entry replay 与重新提交同文本 RPC。
- 静态预期：分阶段持久化可留下“日志有 Commit、客户端 UNKNOWN、cursor 落后”；新 RPC 会得到新 intention，原 entry 最新已持久票可复用。允许重复输出，不能以“Commit 物理条数必须为一”作为唯一断言。（E5:736-759,813-919；E6:142-170；E3:136-160；E11:33-57）
- 观测：第 9 节字段全量落账，特别是 request/operation、所有 intention positions、首次终态、RPC status、三个持久态位置、voter attempt 与 stub effect receipt。
- 验收：UNKNOWN 能关联回原 operation；相同业务请求不得重复执行 stub；同 request_id 不同 hash 必须冲突拒绝。append-ack 丢失且无法找回原 position 时保持 UNKNOWN 并判定恢复接口缺口，不以再次 propose 掩盖。
- 负控：无 inbox 直接同文本重提应暴露新 position；把 gRPC `ABORTED` 当业务 `approved=false`、把 error 当“未提交”、或断言外部去重表自动与 AgentBus 原子提交，均失败。

### AC-12 / F2：同 bus 并发与政策插队——两个变体分库验证

- 状态/前提：`NOT_RUN`；两个 barrier 控制客户端、确定性 voter、FirstBooleanWins、隔离日志/stub。每请求 spawn_local 不等于每 bus 串行。（E3:125-144）
- 变体 A：暂停 A 于 intention append 后、Vote 产生前，让 B append；必须捕获 `I_A,I_B,V_A,V_B` 目标前缀，未出现则记 `INCONCLUSIVE`，不得拿正常排队当注入成功。
- A 静态预期：single `pending: Option<i64>` 被 B 覆盖，V_A 可能被忽略；B 可决策，A 读尽无决策后可能 forced Abort。该 interleaving 是保守源码推导，**尚未端到端复现，不是已证实安全绕过**。（E7:41-45,198-216；E5:719-733）
- 变体 B：新库中将 A 暂停于 `append_resolved_policy` 返回后、intention append 前；另一请求应用 v+1（变更 decider policy），再恢复 A。记录 A 的 minimum 及 intention 前实际生效 policy。
- B 静态预期：更高版本可满足最低版本，不会仅因不是 exact v 而拒绝；旧 intention 不因 provider 后来变化自动重新裁决。policy identity 改变也不迁移旧 pending。（E2:46-54；E5:247-267,598-625；E7:79-101）
- 验收/观测：保留完整 bus 顺序、PolicyBatch expected/new version、decider identity、A/B 首终态及 reason；对照每 bus 单 in-flight 后是否消除 pending 覆盖型拒绝。minimum 产品准确展示版本；承诺 exact 的产品必须另有版本栅栏，插队时拒绝/重新审批，不得宣称上游已具备。
- 负控：再执行 AC-04 的 voter ID 交换回归；增加否决 voter 不得被判成 quorum。若 pending 覆盖未经目标前缀确认、或把 v+1 合法处理直接报漏洞，结论无效。

## 6. 客户问答模板

**Q：这和普通 trace/logging 有什么不同？**
A：它把工具执行前的 intention 放进持久日志，并让 policy pipeline 在工具尝试前给出裁决；普通事后日志通常只能复盘已发生行为。

**Q：它能保证危险工具不会执行吗？**
A：不能这样笼统承诺。当前本地 OSS 插件材料显示 hook failure 非阻断、当前 local policy 默认允许；Claude enforced 拒绝票是 `ask`。若需要强制拒绝，必须另设计 enforced adapter、sandbox/IAM/egress 与故障 fail-closed 策略。

**Q：`approved=true` 能当作成功凭证吗？**
A：不能。`approved` 是 decider verdict；工具执行成功、失败、部分副作用、重试幂等是后续层的问题。

**Q：它是否提供 exactly-once 副作用？**
A：不提供这样的保证。只复用同 state identity 下最新已持久 position 的 payload；voter 求值后写入失败仍可重算，旧 position 在 applicator 报 stale 而 engine 可跳过。RPC 重试还会产生新 intention。外部 effect 必须单独设计可恢复幂等与 receipt。（E5/E6/E7）

**Q：超时后拿同样文本再提交，能查回上次结果吗？**
A：不能当作查询。公开 command 没有 request_id 去重接口，`Outcome.log_position` 是 intention 位置，不是 Commit 位置，且调用完成前不向客户端提供。POC 要持久化 business key/hash，并能原子绑定或可靠找回原 intention；否则丢 ack 必须 UNKNOWN，不能直接再 propose。（D1；AC-11）

**Q：数据库报错是不是代表政策拒绝？**
A：不是。业务 Abort 是正常响应中的 `approved=false`；并发错误可映射成 gRPC `ABORTED`，其他存储/播放错误也不是政策结论。Commit append 后 cursor put 仍可能失败，错误时必须对账原 intention 的首次终态。（D2；AC-11）

**Q：能指定精确政策版本或把版本号调小回滚吗？**
A：当前 RPC 拒绝调用方 policy_version_constraint，engine 附的是 MinimumPolicyVersion。相同/旧 provider 版本不生成新 batch；回滚应发布递增 epoch，改变既有 voter config 要换 voter identity。exact snapshot 需接口及执行前栅栏扩展，不是当前能力。（D4；AC-12）

**Q：加两个模型评审就是多数通过或安全否决优先吗？**
A：FirstBooleanWins 不是。隔离请求首票顺序受 voter ID 排序影响；应另设计明确 quorum/deny-overrides decider 或聚合 voter，并让每 bus 单 in-flight 成为初版 POC 约束。（D5；AC-04/12）

## 7. 宿主产品卡

| 宿主 | 本轮状态 | 可说 | 不可说 |
|---|---|---|---|
| Claude Code | `NOT_RUN` | 源码显示 Claude hook 在 enforced=false/approved=true 时不输出裁决；拒绝且 enforced=true 输出 ask。 | 不可说本轮实测 Claude；不可说 reject=deny。 |
| Codex | `NOT_RUN` | 插件 README 声称记录 Codex lifecycle events。 | 不可说本轮安装/运行 Codex；不可说 Codex 强制阻断已验证。 |
| Muse Code | `NOT_RUN` | 插件 README 声称记录 Muse Code lifecycle events。 | 不可说本轮安装/运行 Muse；不可说 Muse 强制阻断已验证。 |

## 8. POC 最小交付清单（不实现代码）

1. 一页架构边界图及第 10 节序列图：明确 intention、decision、host permission、tool effect，以及三种持久态/回复边界。
2. AC-01—AC-10 原十卡保留并就地校正；新增 AC-11/F1、AC-12/F2，合计十二卡，全部 NOT_RUN。
3. 两个合成事件：允许但失败、拒绝但 ask。
4. 风险声明：MIT 许可不等于安全；不替代 sandbox/IAM/egress/secret 管控；日志裁决不等于工具成功或副作用恰好一次。
5. 按第 9 节交付 operation 对账表、终态日志引用与 effect receipt；UNKNOWN 恢复缺口必须作为验收失败暴露。

## 9. 可复用 POC 对账字段与规则（数据契约，不是新增实现）

**组件归属：**可信入口、持久 operation inbox、每 bus 单 in-flight coordinator、对账器及 effect-idempotency executor 都是 POC 待建组件，不是现有 LogAct 功能。公开 Commit response 只给 `approved/reason/log_position`；其余字段来自入口、日志读取、内部观测或动作端 receipt，不得伪称 RPC 原生返回。

以 operation 主表 + append-only attempts/decisions/effects 子表交付；位置用原生整数或无损十进制字符串，未知用 `null`，不能用零假装已知。公开样本不存原始工具参数/secret，保留脱敏摘要和受控证据引用。

| 字段/类型 | 采集方与用途/约束 |
|---|---|
| `schema_version: string`, `source_sha: string`, `run_id: string`, `run_status: enum` | POC 元数据；本稿样本为 `NOT_RUN`，不混入未来运行记录。 |
| `tenant_id, bus_id, request_id: string` | 可信入口；联合唯一业务键，tenant 来自认证上下文而非不可信工具文本。bus 身份统一编码后使用。 |
| `operation_id: string`, `canonicalization_version: string`, `payload_hash: string` | inbox 持久绑定业务键与规范化 payload 摘要；固定规范化版本/哈希算法，覆盖工具、参数及相关执行目标。相同 key 不同 hash 为 CONFLICT；同内容同 key 返回原 operation，不能新 propose。hash 不是权限或输入真实性证明。 |
| `attempt_id: string`, `attempt_kind: enum`, `started_at, observed_at: timestamp` | attempts 子表；区分 `RPC_PROPOSE / ENTRY_REPLAY / RECONCILE / EFFECT`，时间仅辅助观测，不代替日志顺序。 |
| `intention_position: int64?`, `candidate_intention_positions: int64[]`, `mapping_status: enum`, `mapping_evidence_ref: string?` | LogAct response/可靠日志关联；`UNRESOLVED / UNIQUE / AMBIGUOUS`。Outcome 位置是 intention，不是终态；丢 ack 可为 null。发现多 position 不挑一个直接执行，先隔离/对账重复逻辑请求。 |
| `rpc_status: string?`, `rpc_error_owner: string?`, `rpc_approved: bool?`, `rpc_reason: string?` | RPC/服务诊断；error 时 approved 留 null。transport ABORTED 与正常 response approved=false 分开，owner 记录 engine/voter/decider（若可观测）。 |
| `first_terminal_position: int64?`, `terminal_kind: enum?`, `terminal_reason: string?`, `terminal_intention_position: int64?`, `terminal_evidence_ref: string?` | decisions 子表，直接读取日志：按 bus 顺序找**引用该 intention 的首个 Commit/Abort**。关联不靠时间或文本近似；额外终态另存 `duplicate_terminal_positions`，保留异常不覆盖首态。 |
| `provider_version_observed: int64?`, `minimum_policy_version: int64?`, `effective_policy_version: int64?` | provider 观测、intention constraint、日志政策回放，三个值分列；不能拿 provider 值充当 effective。 |
| `policy_batch_position: int64?`, `policy_expected_version: int64?`, `policy_new_version: int64?`, `decider_identity: string?`, `voter_ids_ordered: string[]` | 从实际被应用的 batch/engine 状态取得；仅“最后出现的 batch”不足以证明已应用，须验证 expected/new 条件。无 batch 的 bootstrap 以初始化证据另记，不能虚构 batch position。 |
| `engine_last_applied_position: int64?`, `applicator_checkpoints: object[]`, `log_observed_high_watermark: int64?`, `recovery_snapshot_ref: string?` | 三种持久态分开：checkpoint 数组含 owner identity、last position、payload 证据引用及采样时刻。engine slot 存最后应用 position，下一位置另行派生，不把它当 Commit ack。恢复证据说明日志/checkpoints 是否一致，不能只恢复 bus 就承诺相同模型票。 |
| `voter_evaluation_attempt_id: string?`, `voter_result_persisted: bool?` | 内部观测；区分真实模型求值、持久 Vote replay、求值后 put 失败；无法观测用 null，不推断成本为零。 |
| `decision_state: enum`, `reconciliation_reason: string?`, `reconciled_at: timestamp?` | inbox：`UNKNOWN / COMMIT / ABORT / CONFLICT`。这是 POC 状态，不是 LogAct 原生枚举。证据不足维持 UNKNOWN。 |
| `effect_idempotency_key: string?`, `effect_state: enum`, `effect_receipt_id: string?`, `effect_receipt_ref: string?`, `effect_attempt_id: string?` | effect 子表；key 绑定 operation + 具体动作/目标，不能每 retry 换 key。状态 `NOT_ATTEMPTED / IN_FLIGHT / UNKNOWN / SUCCEEDED / FAILED`；动作端 receipt 才证明效果。动作 ack 丢失进入 effect UNKNOWN，先查询目标，不自动重做。 |

**对账状态机：**入口持久化 operation → 提交期间 `decision_state=UNKNOWN` → 原 intention 的首终态确认后 COMMIT 或 ABORT。COMMIT 且 mapping UNIQUE、身份/hash/政策要求及宿主权限检查均通过，才可交给独立 executor；ABORT 不执行。RPC error/timeout 不直接改变为 ABORT，也不触发新 RPC。effect 状态与 decision 状态正交，COMMIT + effect FAILED 完全合法。

**必须暴露的原子性缺口：**外部 inbox 与 AgentBus 是两个提交边界。要关闭“append 成功但位置 ack 丢失”，需服务/日志侧 request-id 原子唯一映射，或有可证明唯一的标记找回和可靠恢复查询；把 request_id 塞入 intention 文本不自动满足此条件。找不到或发现多个候选时阻止执行，记录 UNKNOWN/AMBIGUOUS，POC 恢复验收不通过。既有接口也未提供 exact policy pin 或 quorum 聚合；有这些产品承诺就必须另做接口/实现扩展，本轮不实现。

### 合成对账行 C：终态已存在，RPC error，效果未发生

仅用于填表练习，所有位置为合成值、不是运行测量：

| 业务关联 | 初始观测 | 日志对账后 | 动作端 |
|---|---|---|---|
| `tenant-demo / bus-demo / req-C` → `op-C`；hash 在真实 POC 由规范化器计算，本样本不伪造 | `rpc_status=UNAVAILABLE`；`rpc_approved=null`；`decision_state=UNKNOWN`；response 未给 position | 受控测试观测确认原 `intention_position=1201`；`first_terminal_position=1204`；`terminal_kind=Commit`；mapping UNIQUE → decision COMMIT | `effect_state=NOT_ATTEMPTED`；receipt=null；不能仅凭日志宣称执行成功 |

若删除受控映射证据，C 行必须退回 mapping UNRESOLVED / decision UNKNOWN，而不能凭相同文本猜 position。政策审计及宿主授权仍未填写时，即便终态 COMMIT 也不能启动 executor。

## 10. 序列图：持久化/回复边界与故障恢复

下图均为源码推导及 POC 设计，`NOT_RUN`。P1 日志、P2 applicator checkpoints、P3 engine state 是不同持久态；即使共用 SQLite 路径也不是一个大事务。U 为待建 POC 组件。正常路径基于 E1/E4/E5/E6/E7/E9/E10/E12；错误映射基于 E11。

```mermaid
sequenceDiagram
    participant C as Client
    participant U as POC inbox/coordinator (待建)
    participant E as CommitService/engine
    participant L as P1 AgentBus log
    participant A as voter/decider
    participant S as P2 applicator checkpoints
    participant K as P3 engine cursor/policy
    participant X as POC executor/target (待建)
    C->>U: business key + canonical payload
    U->>U: 持久 operation/hash; 每 bus 单 in-flight
    U->>E: Commit(bus, intention); 非 request-id 幂等 API
    E->>K: load engine state + resolve provider
    opt policy plan 要求更新
        E->>L: append PolicyBatch
    end
    E->>L: append Intention + MinimumPolicyVersion
    L-->>E: intention position I (客户端此时未获知)
    loop 按日志驱动, 每个匹配 entry
        E->>L: read entry
        E->>A: apply: decider 再按 ID 顺序 voters
        A->>S: CAS 最新输入结果 (求值在 put 前)
        S-->>A: 持久结果 ack
        A-->>E: produced payload
        E->>L: 按 produced 顺序 append Vote/Commit/Abort
        L-->>E: 日志 append ack
        E->>K: 最后 CAS cursor/policy
        K-->>E: state ack (可能失败)
    end
    E->>L: poll 引用 I 的首次终态
    L-->>E: Commit/Abort
    E-->>U: approved/reason/log_position=I
    U->>U: 终态对账 + 实际政策 + 原生权限检查
    opt COMMIT 且全部执行门通过
        U->>X: 独立 effect_idempotency_key
        X-->>U: target receipt 或 effect UNKNOWN
    end
    U-->>C: 分开返回 decision_state / effect_state
```

恢复查询箭头表示**待建对账通路**，不是现成的 Commit RPC 查询方法；必须满足第 9 节的可靠映射条件。

```mermaid
sequenceDiagram
    participant U as POC inbox (待建)
    participant E as engine
    participant L as AgentBus
    participant K as engine cursor store
    participant R as reconciler (待建)
    E->>L: append Commit(intention=I)
    L-->>E: append ack
    E->>K: final cursor put
    K-->>E: F1a BackendUnavailable
    E-->>U: RPC error, 不是业务 Abort
    Note over U,L: F1b 独立样本: 全部成功但 RPC ack 丢失, 也进入 UNKNOWN
    U->>U: 保存 UNKNOWN, 禁止再次 propose
    U->>R: 原 operation + 可靠身份映射证据
    R->>L: 查原 I 的首次 Commit/Abort + 政策上下文
    L-->>R: 终态及日志位置证据
    R-->>U: UNIQUE 映射时对账; 否则保持 UNKNOWN
    Note over E,K: 后续恢复驱动可复用最新持久 payload, 允许重复日志输出
    Note over U,E: 重新 RPC 同文本会新建 intention, 不是重放原 I
```

F2 的顺序不藏在并发箭头里：变体 A 需要实际捕获 `I_A → I_B → V_A → V_B` 才能讨论 pending 覆盖；变体 B 需要捕获 `A resolve(v) → B 应用 PolicyBatch(v+1) → I_A(min=v)`。这是两个独立实验，不能用同一次失败同时证明并发与 exact-version 结论。
