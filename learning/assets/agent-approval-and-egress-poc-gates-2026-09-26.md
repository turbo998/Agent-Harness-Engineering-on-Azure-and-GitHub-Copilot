# Agent 审批与出站双门：公开源码审阅与 POC 验收设计

日期：2026-09-26｜适用：MAF Python 本地工具审批 + Azure MCP 指定服务调用点

> **结论：两道门必须同时成立。** 第一门回答“此次本地执行是否绑定可信会话中实际挂起的请求”，第二门回答“此次网络连接是否符合服务端点与部署出站策略”。审批通过不能豁免出站校验；域名通过也不代表操作者有权执行。
>
> 本文是源码审阅与待执行验收设计，不是安全认证或上线报告。**所有上游测试、实际 Host 集成测试、云服务调用均为 `NOT_RUN`。** 本次仅只读获取公开源码及有界 HEAD 检查；未安装包、执行外部仓库代码或调用 Azure。HEAD 成功只证明文档地址可访问。

## 1. 固定范围与证据等级

- MAF：`microsoft/agent-framework@f9310e5ac2a1b6cf389e82d01c62df8e05cf558b`。
- Azure MCP：`microsoft/mcp@3bb29c54193e3555c3f1d09585d5639632b872c1`。
- 结论限于这两个源码快照；**不证明已发布包包含改动**，不外推至 MAF 其他语言、所有 provider、所有 MCP 工具或 Azure 全服务。
- 在既有精确版本实现与 patch 证据上，额外全文取回四个承重文件：MAF invocation tests、Migrate service、Terraform AVM service、Confidential Ledger service；重点读取实现控制流及测试断言，不只读提交摘要。MCP 三个新增 endpoint 测试文件在 patch 中完整呈现，另核读共用 validator 实现。
- `SOURCE_READ`：实现和断言已读；`LINK_VERIFIED`：公开证据 URL 的有界 HEAD 已核；`NOT_RUN`：没有运行结果。三者不能互相替代。

## 2. 第一道门：审批来源绑定，不是“有同意文本就执行”

### 2.1 精确实现落点

MAF `_tools.py` [S1]：

1. 默认配置 `disable_approval_response_binding=False`（1851–1862 行）。`_resolve_approval_responses` 在无 authoritative session 时先做 occurrence 关联，再移除不能绑定、尚可能授权执行的本地 `function_approval_response`，记录 warning（4555–4591 行）。**不是一律抛异常，也不是终止整个聊天**：纯伪造审批可以被丢弃后继续模型回合。
2. 会话绑定使用框架记录的 pending request；`_bind_approval_response_to_pending_request` 从保存的 call 重建工具与参数，而非信任入站 response 携带的 call（2895–2973 行）。持有同一个 session ID 字符串不等于恢复了可信 pending state。
3. 已有 terminal result、被 occurrence 关联判定 settled 的历史审批保留，但不触发本地再执行。豁免集合按 **response 对象身份**，不是只按审批 ID：否则相同 ID 的第二个对象可能漏过过滤（2976–3024、3652–3662 行）。这不是跨进程永久对象 ID，也不是业务幂等键。
4. 混合批次先过滤无来源审批，再重新计算 completeness。带 Host-owned result 的伪造完整批次可能因此变得不完整并抛 `RuntimeError`；不能声称“过滤之后绝不报错”。测试明确同时断言 warning、异常、零工具执行 [S2]。
5. hosted/provider-issued 审批是 provider 协议数据，不按这一无 session 本地过滤规则处理；测试用 `server_label` 形式的 hosted call 验证透传。**透传不等于 provider 已验证审批，也不等于本地工具执行成功**。真正 provider 的授权、会话和远端出站需要独立验收。
6. 显式 `disable_approval_response_binding=True` 在已读无 session 测试中恢复旧的不绑定执行行为。不能把它当作安全修复，也不能据此说有 session 时所有 binding 都消失：实现后续仍调用 session binder。只允许在另有等价外部绑定、隔离验证、明确例外期限时考虑。

**信任边界：** authoritative 是框架处理会话状态的语义，不是密码学身份认证。该快照中辅助判断依赖传入 session，内部临时生成的 session 则标为非 authoritative。若 Host 把用户提供的任意状态直接变成可信 session，前提已经失守。操作者身份、租户归属、审批权限、过期与撤销、并发事务、业务副作用幂等均须由 Host/业务服务另行实现。

### 2.2 已读断言落点

[S2] `test_function_invocation_logic.py`：
- 10958–11004：伪造请求+响应、篡改参数、无匹配请求、tool role、重复审批 ID；streaming/non-streaming 均断言零执行，并有 warning。
- 11007–11052：同一可信 session 的真实暂停/批准/恢复执行正控。
- 11055–11108：hosted 无 session 透传及显式 opt-out 恢复旧行为。
- 11111–11196：completed replay 不执行且无该 warning；混合批次过滤顺序。
- 118–165：绑定到原始保存参数、消费与重复响应；这是框架层状态行为，不是外部业务 exactly-once。

## 3. 第二道门：分服务 endpoint guard，不是统一网络防火墙

| 服务与实现 | 实际检查及顺序 | 不应作出的推论 |
|---|---|---|
| Migrate `PlatformLandingZoneService` [S3] | `DownloadAsync` 先调用 `PostAsync` 取得生成响应（125–126 行）；`TryGetValidatedDownloadUrl` 将解析和校验合在一起，调用 `ValidatePublicTargetUrl(..., "azuremigrate")` 后才调用 `DownloadBytesAsync`（129–133 行）。支持顶层/nested `downloadUrl` 和原始 URL fallback；无 URL 返回 null，外层提示尚未生成。 | 拒绝下载不等于整个入口零 POST、零网络或零凭据获取；不是所有 Migrate 流量都被该新调用点覆盖，也不是仅 HTTPS。共用 validator 接受 HTTP/HTTPS。 |
| Migrate 共用 validator [S6] | 拒绝私有/保留 IP、保留主机、非 HTTP(S)；域名 DNS 解析全部地址均需通过，解析失败或空结果 fail closed。 | 检查时 DNS 不等于连接时 IP 绑定；未证明 redirect、TOCTOU/rebinding 或真实下载安全。新增测试主要是 DNS 无关拒绝项，没有联网正控。 |
| Terraform `AvmDocsService` [S4] | 解析 host，仅把 `github.com` 改为 `api.github.com` 并加 `/repos`；不改路径里的 `github.com-foo`。`ValidateExternalUrl` 检查 HTTPS + 精确 host，AVM 列表为 `raw.githubusercontent.com`、`api.github.com`。CSV、README 与 fallback 也有调用点。 | 源码明确写明 **只检查 initial request URL，不追踪重定向**。host 合法不代表仓库、路径、内容可信，也不代表工具“运行 Terraform”已被沙箱化。 |
| Terraform 其他文档服务 [S8] | patch 中 `AzApiExamplesService` 的 remarks/content、`AzureRMDocsService` 的主/fallback URL 均调用 external validator，允许 `raw.githubusercontent.com`。 | 只据这些调用点判断，不宣称整个 Terraform namespace 的所有网络或供应链已安全。 |
| Confidential Ledger [S5][S8] | 验证名称（ASCII 字母开头，后续字母/数字/连字符），按 Public/China/USGov 构造 URI；按服务与 `ArmEnvironment` 后缀校验。读、写入口都在 `GetCredential` 前取得 validated URI。 | 仅证明该入口在凭据获取前校验；不证明 RBAC、数据可见性、云服务部署可用或 SDK 全部网络行为。 |

### 危险覆盖与主权云边界

- [S6] 的 `SetDangerouslyDisabledSsrfProtectionNamespaces` 是进程级、启动时仅可设置一次的配置；匹配 namespace 或 `ALL` 可让 **public-target / Azure-service validator** 提前返回。Migrate 与 Confidential Ledger 传入了具体 namespace，属于影响范围。
- **不可泛化为 Terraform 同样可关闭。** 已读 `ValidateExternalUrl` 没有这个 namespace override 分支；它仍检查 HTTPS 与精确 host。Ledger 名称检查也在 endpoint guard 之前，不会因 override 自动消失。
- [S8] Confidential Ledger 的 Germany 后缀列表为空；默认行为是拒绝，而非静默转到 Public。测试用 Public cloud type 配 Germany ArmEnvironment 验证拒绝。危险 override 若绕过服务校验，不能再声称有这个默认拒绝保证。
- China 的 `.confidential-ledger.azure.cn` 是**源码域名构造/允许列表证据**，不是该云该服务可申请、可连接、可认证或满足驻留要求的证据；USGov 同理。Germany 的空列表也应描述为本快照策略，不能代替当前产品可用性调查。

## 4. 架构信任边界与推荐落点

```text
不可信用户消息 / 模型输出 / 导入 transcript / CSV / 工具返回 URL
  │ 不得自行升级为审批 authority 或可直接连接的 endpoint
  ▼
Host API：认证、租户隔离、审批者权限、过期/撤销检查
  │ 仅用服务端映射取回可信 session；不接收客户端回写权威状态
  ▼
门 A：MAF pending request + occurrence 绑定（本地执行路径）
  │ approved tool/args + 业务操作键；默认 opt-out 关闭
  ▼
业务工具适配器：最小权限、原子幂等记录、结果/重试协调
  ▼
门 B1：Azure MCP 对应服务 endpoint guard（不能被审批豁免）
  ▼
门 B2：独立 egress 执行点（默认拒绝、每跳校验、连接 IP 约束）
  ▼
目标服务：独立身份授权与业务校验
```

Host-owned/declaration-only 调用由 Host 执行，也必须经过同样业务和出站策略，不能把框架返回的 pause 当授权。hosted provider 路径是另一信任域：本地代理不一定看得到 provider 内部网络；需 provider 侧审批与出站证明，不满足时禁用该能力。

**具体控制点：**
- API/session store：服务端保存原始请求与不可被用户重写的状态；审批 UI 展示已保存的工具、规范化参数摘要和目标；身份授权先于恢复调用。跨实例恢复采用受控持久化，不让客户端提交任意序列化 session。
- 业务服务：独立操作键及数据库唯一约束/原子状态迁移；重复审批、重试、崩溃重启与新会话重复提交均覆盖。框架 request ID 不直接充当业务去重键。
- egress：只放行业务必需目标；HTTPS、每跳重定向策略、DNS 与连接 IP 约束由网络层补齐。可信云后缀不是私网/重绑定防护的替代。高风险下载采用镜像/审批后的内容摘要。
- 配置发布：默认禁止 MAF opt-out、MCP namespace/ALL dangerous override；发布策略扫描实际启动配置。发现危险配置不静默降级，停用对应工具并回滚配置。
- 审计：记录匿名化用例号、状态、配置摘要、实际目标分类与执行计数；不记录 token、原始审批内容、完整 URL query 或个人身份。

## 5. 部署方案比较

| 方案 | 实施方式 | 优点 | 缺口/代价 | 适用 |
|---|---|---|---|---|
| A. 单进程轻量 POC | Host 内保存可信 session，MCP 保留默认 guards；网络全断开，工具用内存替身 | 快速验证默认变化和回归 | 无法证明跨实例状态、真实网络及 provider 行为；不能据此直接上线 | 离线基线 |
| **B. 有状态审批服务 + 隔离工具 worker + 独立 egress** | 服务端 session/审批数据库；worker 无通用外网，按服务开放出口；业务服务负责幂等 | 将身份、审批、业务幂等、网络责任分开；能覆盖重定向与配置漂移 | 需要会话持久化、事务协调、网络观测；provider 远端仍另验 | **推荐进入受控试点** |
| C. 外部审批 authority / provider 托管 | 外部系统承担等价绑定；必要时显式 opt-out；provider 工具独立治理 | 适配现有审批平台或 hosted 工作流 | 最难证明端到端等价；远端网络不可见；不能仅凭 provider 名称信任 | 已有独立证明与运维能力时 |

推荐顺序 A → B；C 为例外，不为兼容旧 transcript 而默认开启 opt-out。两门中任一 `NOT_RUN` 或失败，只能报告“设计/局部基线完成”，不得宣称生产可上线。

## 6. 待实现、待执行的验收设计

### 6.1 公共前置、观察与回滚

**范围：** 隔离验收环境，不连接 Azure、生产或第三方攻击目标。下文 metadata/private 地址仅作为 validator 的**字符串输入**，绝不 curl/下载。

**P0（离线基线）**：由团队另行批准并准备两个固定 SHA 的本地副本、预装依赖和已构建测试产物；执行前核对 SHA。禁用真实模型、凭据与默认凭据探测，用 scripted model、工具计数器、fake transport/credential spy；禁止出站。本文没有执行此步骤。

**P1（Host 增补）**：在 P0 上提供两租户虚拟身份、服务端 session store、业务去重存储、假时钟和可复位审计。仅使用合成标识。

**P2（网络边界增补）**：只在经批准的隔离网络仿真环境，用受控 DNS/重定向模拟器和连接计数器；外网全部封锁。未具备这些夹具就保持 `NOT_RUN`，不得用真实 metadata 请求替代。网络模拟与真实 egress 设备集成结果分开报告。

**O（统一观察）**：保存本地工具执行计数、实际被执行参数摘要、模型/远端协议接收类型、warning/异常类型、凭据获取计数、网络连接尝试及放行计数。只看最终“done”不算验收。

**R0（统一回滚）**：每例重建虚拟 session、清空内存计数与合成业务记录、销毁 fake transport；恢复默认配置并验证零残余工作项。涉及进程级 write-once override 时直接销毁子进程/容器，不能靠二次 setter 恢复。

### 6.2 用例矩阵（每行当前结果均为 `NOT_RUN`）

| ID / scope | 前置 | 步骤 | 观察 | 预期与判定 | rollback / 当前结果 |
|---|---|---|---|---|---|
| A01 审批负控 | P0；无 session；模型仅回 done | 输入伪造 request+approved response；分别 non-stream/stream | O：执行、结果、warning | 本地执行 0，无新 function_result，有审批 warning；聊天可继续 | R0；NOT_RUN |
| A02 输入变体负控 | P0；无 session | 分别注入篡改参数、无请求、tool role、同 ID 的两个不同 response 对象；两种流模式各跑 | O：每个对象及执行次数 | 全部不因入站审批执行；不能只测第一个重复对象 | R0；NOT_RUN |
| A03 真实审批正控 | P0；保留可信 session | 模型产生 guarded call→暂停→从实际 request 生成同意→同一 session 恢复 | O：pending、原始参数、执行 | 原始已记录调用执行 1 次；证明测试工具能执行，不是所有请求都被拦 | R0；NOT_RUN |
| A04 绑定/重复负控 | P0；已存 pending | response 替换工具名和参数，保留匹配 occurrence；再重复 response | O：重绑定后的 call、pending 消费 | 保存的工具/参数仍为 authority，不能执行替换值；重复不新授权。拒绝决定另测零副作用 | R0；NOT_RUN |
| A05 completed 历史正控 | P0；无 session | 重放 call/request/approved/匹配 terminal result，再提普通问题 | O：历史、执行、warning | 历史不被该过滤器破坏；执行 0，且无“缺 authoritative session”审批 warning | R0；NOT_RUN |
| A06 hosted 分流正控 | P0；provider spy | 无 session 输入带 hosted 标记的审批；与本地 A01 对照 | O：provider 收到的协议、本地计数 | provider 接收审批协议；本地不据此执行。不能记为远端授权成功 | R0；NOT_RUN |
| A07 显式 opt-out 危险正控 | P0；独立隔离实例；无网络工具 | 无 session 开 True，重放无请求 approved response；关闭后重复 | O：配置、计数 | 开启时复现旧不绑定行为；关闭时拒执行。上线政策应拒绝该危险配置 | 销毁实例、确认 False；NOT_RUN |
| A08 混合批次负控 | P0；本地 approval + Host-owned call | 提交伪造同意和有效 Host result，不带 session | O：warning 顺序、RuntimeError、执行 | 先过滤，再发现 mixed batch 不完整；本地执行 0。不是“吞掉错误即通过” | R0；NOT_RUN |
| B01 Migrate 拒绝与空值控 | P0；helper 与入口子步骤分开；入口需自有 fake HTTP helper | helper：向 `TryGetValidatedDownloadUrl` 输入顶层/nested metadata、私网、localhost、ftp，再输入 `{}`、Generating 和非 URL 文本。入口：另调用 `DownloadAsync`，提供有效 context/outputPath，令 fake `PostAsync` 返回相应响应 | helper 只观察异常/null；入口分别记录 `PostAsync`、`DownloadBytesAsync`、credential spy，不能互相代替 | helper 危险 URL 抛 SecurityException、无 URL 返回 null。入口先发生 fake POST，再拒绝危险 URL 或以 InvalidOperationException 提示无 URL；后续下载调用=0，不代表入口 POST=0、总网络=0 或 credential=0；真实网络由隔离设施禁止 | R0；NOT_RUN |
| B02 Migrate 正控与 DNS 控 | P2；受控 DNS | 解析合成正常公网分类地址；再改为含私网地址、空列表、解析失败；download 用 spy | O：全部 DNS 地址、下载调用 | 全公有地址允许继续到 spy；任一私有、空/失败拒绝；不把 DNS 时校验当连接时保证 | 还原 DNS、销毁实例；NOT_RUN |
| B03 Terraform 正负控 | P0；调用 BuildValidatedReleasesUrl | GitHub 正常路径及含 github.com-foo 的路径；再用非允许 host、允许 host 加恶意后缀、私网 IP、http | O：生成 URL、异常、网络计数 | 正控只改 host；负控在发送前拒绝；不接受 host 后缀伪装。无真实 GET | R0；NOT_RUN |
| B04 initial URL / redirect 缺口 | P2；fake HTTP handler 与 egress enforcement | 允许 initial host 返回跨 host 302；再模拟解析通过后连接 IP 转为私网；正控保持合法目标 | O：每跳 URL/IP、连接尝试和放行 | guard-only 不得被算作已防 redirect；推荐方案逐跳/连接阻断违规、合法目标可到 spy。用非网络 fake 演示缺口不等于真实设备通过 | 移除路由/DNS fixture、销毁实例；NOT_RUN |
| B05 Ledger 云/名称控 | P0；cloud config stub；入口需自有可验证的 credential spy | helper：调用 `GetValidatedLedgerUri`，覆盖 Public/China/USGov 合法名称、非法名称、Public cloud type + Germany ArmEnvironment。入口：对非法名及 Germany 拒绝变体，分别调用写入口 `AppendEntryAsync` 和读入口 `GetLedgerEntryAsync`，提供其余有效参数（非空 entryData / 有效合成 transactionId） | helper 观察 URI/异常；读、写入口分别观察校验异常与 credential 调用次序/计数；spy 须另有正控证明可观测且不取真实凭据 | helper 三种后缀仅构造通过，非法名 ArgumentException、Germany SecurityException；只有真实进入读/写入口的拒绝子步骤才能动态断言 credential=0。仅调 URI helper 不证明入口顺序；源码 41–42、72–73 行只作静态顺序证据 | R0；NOT_RUN |
| B06 dangerous override 范围控 | P0；每变体独立子进程；另需 Ledger service helper 与发布配置夹具 | 默认先测拒绝；再分别配置 azuremigrate、confidentialledger、ALL，调用对应 public-target/service validator，同时调用 Terraform external validator。名称子步骤必须另调用 `GetValidatedLedgerUri("bad.name")`，覆盖默认及各 override 变体 | 分开记录 validator 配置匹配/返回、service helper 的名称异常、发布检查结果；无真实网络 | 匹配 override 可绕过 public-target/service guard，Terraform external 不因此绕过；名称子步骤仍应 ArgumentException，因为名称校验在 service helper 内且先于 endpoint guard。单调纯 validator 不能证明名称检查；发布检查必须拒绝危险配置 | 销毁全部子进程，冷启动默认；NOT_RUN |
| H01 身份/session 负控 | P1 | 租户 B 尝试审批 A 的 session；复制 ID；注入任意序列化 pending；再以授权审批者正控恢复 | O：Host 鉴权拒绝与调用进入点 | 非授权请求在进入框架前拒绝；正控可恢复。此为 Host 要求，不是 MAF 已证明能力 | 清合成会话与身份映射；NOT_RUN |
| H02 业务幂等/崩溃控 | P1；业务原子操作键 | 同一操作双并发批准；副作用后、响应前模拟崩溃并重试；换新 session 重提；不同操作键作正控 | O：业务存储副作用、重复返回、恢复状态 | 同业务操作只产生一次有效副作用；不同合法操作可执行。若只靠框架 ID 达成不了则阻止上线 | 清合成业务记录/重启 worker；NOT_RUN |
| X01 双门交叉验收 | P1+P2 | 有效审批+非法目标；无来源审批+合法目标；有效审批+合法目标；两者均非法 | O：门 A/B 事件、业务副作用、出站计数 | 只有两门及业务授权均通过才可到 spy；批准不能豁免 egress，host 允许不能豁免审批 | R0+网络 fixture 清理；NOT_RUN |

### 6.3 固定 runner 与精确测试定位清单（不是已验证命令）

本文只交付源码定位和待执行设计，**不交付可直接运行的脚本或已验证 CLI 命令**；测试发现、collection 和执行均为 `NOT_RUN`。验收团队另行准备固定 SHA 副本、依赖及产物后，须按该版本 runner 的本地 help 确认最终调用，不得从路径存在推断可执行。**不要现场安装、restore、构建或连接真实 provider**；前置不足就记录阻塞与 `NOT_RUN`。

**MAF 定位：** 工作目录为 `MAF_ROOT/python/packages/core`，文件为 `tests/core/test_function_invocation_logic.py`。已有七个函数定位片段如下（A01/A02 共用参数化函数）；只是静态定位，不是 pytest collection 结果：

- A01/A02：`local_approval_response_without_authoritative_session`
- A03：`local_approval_response_executes_with_authoritative_session`
- A04：`session_approval_binding_rebinds_consumes_and_rejects_duplicates`
- A05：`settled_approval_response_replays_without_session_or_warning`
- A06：`hosted_approval_response_passes_through_without_session`
- A07：`disable_approval_response_binding_restores_unbound_behavior`
- A08：`unbound_local_approval_response_is_filtered_before_mixed_batch_validation`

**MCP runner 依据：** 固定 `3bb29c5` 的 `global.json` 指定 SDK `10.0.401`（`rollForward=latestFeature`）与 `Microsoft.Testing.Platform`；`Directory.Build.props` 指定 `net10.0` 并启用 MTP；下列三个 csproj 均引用 `xunit.v3.mtp-v2`。因此不能沿用 VSTest 的 filter expression。`eng/scripts/Test-Code.ps1:313–320` 也使用 MTP trait 选项。SDK 允许 roll-forward，故还须记录实际解析 SDK/runner 版本，不得仅抄配置值。

| 覆盖定位 | 精确 project（相对 MCP_ROOT） | 完整测试类名 |
|---|---|---|
| B01 helper | `tools/Azure.Mcp.Tools.AzureMigrate/tests/Azure.Mcp.Tools.AzureMigrate.Tests/Azure.Mcp.Tools.AzureMigrate.Tests.csproj` | `Azure.Mcp.Tools.AzureMigrate.Tests.Services.PlatformLandingZoneServiceEndpointValidationTests` |
| B03 helper | `tools/Azure.Mcp.Tools.AzureTerraform/tests/Azure.Mcp.Tools.AzureTerraform.Tests/Azure.Mcp.Tools.AzureTerraform.Tests.csproj` | `Azure.Mcp.Tools.AzureTerraform.Tests.AvmDocsServiceEndpointValidationTests` |
| B05 helper | `tools/Azure.Mcp.Tools.ConfidentialLedger/tests/Azure.Mcp.Tools.ConfidentialLedger.Tests/Azure.Mcp.Tools.ConfidentialLedger.Tests.csproj` | `Azure.Mcp.Tools.ConfidentialLedger.Tests.Services.ConfidentialLedgerServiceEndpointValidationTests` |

**执行团队确认清单（尚未执行）：**

1. 核对两个完整 source SHA、依赖/构建记录与 artifact digest；仅工作树 SHA 不能证明预构建产物归属。禁止真实网络、模型、凭据和默认凭据探测。
2. MCP 的 runner help、测试发现及执行均从 `MCP_ROOT` 启动，使仓库 `global.json` 生效；不得在任意 cwd 只传绝对项目目录。以固定 SDK/MTP/xUnit 的实际 help 确认 `dotnet test` 的 `--project` 精确 csproj、`--filter-class` 完整类名及 `--list-tests` 选项；这些只是待确认的接口定位，不是本文已跑过的命令。配置与 TFM 必须匹配预构建产物。
3. 无构建/恢复模式需确认 `--no-build`、`--no-restore`，并保留匹配 SHA 的 `obj` restore 状态与包缓存。只有二进制而无 project restore 状态时阻塞本清单；若改用 test-modules，须另行验证该固定 runner 的方式，不能临时猜命令或联网补依赖。
4. 先 list/collection 并保存发现清单，人工核对仅目标类及所需参数化变体、不含 live/provider 测试，再以相同筛选执行。Migrate 项目声明含 live tests，**不得退化为整项目运行**。任何发现或执行错误立即停止；无测试发现、仅发现未执行、漏变体、只有跳过结果均不得计为 PASS。
5. 上游测试只覆盖 A/B 的部分断言：B01 的入口 POST/下载/凭据计数，B05 的读写入口 credential spy，B06 的 override/名称 helper/发布配置检查均需额外夹具，**不由三组上游类自动覆盖**。A04 拒绝扩展、A07 关闭后重复、B02/B04 与 H/X 同样另验；不能用一个 case PASS 吞掉未跑子步骤。

上述固定配置与源码不能替代固定版本本地验证；本文不据此宣称 runner 可用。B02 的静态 `Dns.GetHostEntry` 没有普通 fake-DNS 注入点，空 `AddressList` 分支需夹具单独证明可达，解析失败不能冒充空列表覆盖。未具备夹具的子步骤继续 `NOT_RUN`。

### 6.4 结果记录与放行条件

每个用例按变体与层级分开保存脱敏记录：`case_id / variant_id / stream_mode / layer / source_sha / artifact_digest / config_digest / fixture_version / status / observed_counts / exception_class / assertion_result / rollback_result`；`layer` 至少区分 helper、service-entry、Host 与 egress，计数区分 POST、下载、凭据、连接尝试/放行。本次所有 `status=NOT_RUN`，不填虚构 observed 值。这只是记录字段设计，不是已交付的机器可验证 schema 或 harness。

- 离线基线：正控可执行，负控零未经授权副作用；源码例外行为必须与预期一致。
- Host 放行：H01、H02、X01 必过；B04 必须证明实际出站执行点有效；默认配置与制品映射可追溯。
- fail closed：测试失败、没有测试被发现、缺关键观测、危险开关未恢复或回滚失败，均禁止放行。发现真实凭据或意外出站，停止测试并按环境事件流程处置。
- 回滚生产设计：停用受影响工具/worker，撤销待处理审批并恢复最后已验配置；不要以打开 opt-out/ALL 来“恢复业务”。业务副作用补偿由业务系统设计，不能假定撤销 session 能撤销已提交操作。

## 7. 面向评审的问答

**Q：升级后导入 transcript 的批准不执行，是 bug 吗？** 可能是预期 breaking default。未完成本地审批要恢复框架记录的可信 session；已完成历史仍可重放。先跑 A01/A03/A05，不能直接开 opt-out。

**Q：出现 warning 就说明安全了吗？** 不。需同时观察工具/业务副作用计数，并验证真实审批正控能执行；混合批次还可能抛错。落点 A01/A08/X01。

**Q：MAF 已去重，业务还要幂等吗？** 要。框架响应关联与消费不证明跨实例、崩溃重试、外部服务提交或新 session 的 exactly-once。落点业务唯一约束与 H02。

**Q：hosted MCP 审批通过，也受同一门保护吗？** 不能这样推断。provider 协议透传是不同路径；本地 A06 只能证明透传，不能证明远端身份/审批/egress。未能取得独立证据则禁用该 hosted 能力。

**Q：Terraform 只访问 GitHub，就没有 SSRF/供应链问题了吗？** 不。initial host 检查没有覆盖 redirect、实际连接 IP、仓库所有者、路径与文档内容。落点 B03/B04、独立 egress 和内容固定摘要。

**Q：China 后缀存在意味着服务可用？Germany 失败意味着配置错？** 都不能直接推断。它们首先是源码构造/允许策略；Germany 当前快照为空列表。落点 B05，服务可用性、认证与合规另做调查，不在本 POC 中连接验证。

## 8. 公开来源与核实记录

固定 runner 配置证据（2026-09-26 HEAD 核实200；只读，未执行）：
- [global.json](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/global.json)
- [Directory.Build.props](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/Directory.Build.props)
- [eng/scripts/Test-Code.ps1](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/eng/scripts/Test-Code.ps1)
- [tools/Azure.Mcp.Tools.AzureMigrate/tests/Azure.Mcp.Tools.AzureMigrate.Tests/Azure.Mcp.Tools.AzureMigrate.Tests.csproj](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.AzureMigrate/tests/Azure.Mcp.Tools.AzureMigrate.Tests/Azure.Mcp.Tools.AzureMigrate.Tests.csproj)
- [tools/Azure.Mcp.Tools.AzureTerraform/tests/Azure.Mcp.Tools.AzureTerraform.Tests/Azure.Mcp.Tools.AzureTerraform.Tests.csproj](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.AzureTerraform/tests/Azure.Mcp.Tools.AzureTerraform.Tests/Azure.Mcp.Tools.AzureTerraform.Tests.csproj)
- [tools/Azure.Mcp.Tools.ConfidentialLedger/tests/Azure.Mcp.Tools.ConfidentialLedger.Tests/Azure.Mcp.Tools.ConfidentialLedger.Tests.csproj](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.ConfidentialLedger/tests/Azure.Mcp.Tools.ConfidentialLedger.Tests/Azure.Mcp.Tools.ConfidentialLedger.Tests.csproj)

下列八个证据 URL 均实际使用有界 `curl -sI -L`（连接超时 8 秒、总时限 30 秒、最多 4 次重定向、只允许 HTTPS）检查，均返回 HTTP 200。新增四文件 GET 内容先保存为结构化 JSON 后审阅；公开文档不附原始抓取、响应头或个人信息。**测试输入 URL 不属于文献链接，未进行网络访问。**

- [S1 — MAF 精确实现 `_tools.py`](https://raw.githubusercontent.com/microsoft/agent-framework/f9310e5ac2a1b6cf389e82d01c62df8e05cf558b/python/packages/core/agent_framework/_tools.py)
- [S2 — MAF 精确测试 `test_function_invocation_logic.py`](https://raw.githubusercontent.com/microsoft/agent-framework/f9310e5ac2a1b6cf389e82d01c62df8e05cf558b/python/packages/core/tests/core/test_function_invocation_logic.py)
- [S3 — Migrate `PlatformLandingZoneService.cs`](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.AzureMigrate/src/Services/PlatformLandingZoneService.cs)
- [S4 — Terraform `AvmDocsService.cs`](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.AzureTerraform/src/Services/AvmDocsService.cs)
- [S5 — Confidential Ledger `ConfidentialLedgerService.cs`](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/tools/Azure.Mcp.Tools.ConfidentialLedger/src/Services/ConfidentialLedgerService.cs)
- [S6 — 共用 `EndpointValidator.cs`](https://raw.githubusercontent.com/microsoft/mcp/3bb29c54193e3555c3f1d09585d5639632b872c1/core/Microsoft.Mcp.Core/src/Helpers/EndpointValidator.cs)
- [S7 — MAF 固定提交与变更](https://github.com/microsoft/agent-framework/commit/f9310e5ac2a1b6cf389e82d01c62df8e05cf558b)
- [S8 — Azure MCP 固定提交、允许列表与完整新增测试](https://github.com/microsoft/mcp/commit/3bb29c54193e3555c3f1d09585d5639632b872c1)

**关键局限：** 未运行上游测试或实际 Host；未核发布包/部署制品归属；未验证真实 provider、会话身份授权、业务幂等、重定向/重绑定网络行为、凭据链或任何云服务可用性。上述未验证项均有验收落点，但不能把设计当成已通过的证据。
