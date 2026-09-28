# 微软 MAF reasoning replay 与 Azure MCP 身份遥测／namespace gate：公开验收模板

适用对象：解决方案架构师（SA）、平台工程、应用安全及客户验收团队。版本日期：2026-09-29。

> **证据状态：源码静态核验完成；源级测试 NOT_RUN；发行包包含关系 UNVERIFIED。** 本文是需要适配测试环境的验收设计，不是测试通过报告，不是微软发布公告。两项变化分别对应固定源码提交，不是 09-29 新 release。文中“预期”来自固定提交源码／测试断言或明确标注的补充验收要求，不代表已运行观察。

配套 [MAF 固定源码离线实验](maf-reasoning-replay-offline-lab-2026-09-29.md) 使用原创 runner 运行了所选真实源码入口；这不等于本模板全部参数组合、上游原 pytest 或云集成矩阵已完成。MCP 仍仅静态研究。

## 1. 验收目标与不可外推的边界

- **MAF**：固定提交 `62337887116c604ff542dbec44dd4cddd814295c`，验证 Foundry 原生 reasoning payload 可以参与本地无状态工具回放，并拒绝 reasoning／工具组损坏及跨组重复 reasoning ID。[A1–A4]
- **Azure MCP**：固定提交 `5bf6e024152bf4cd414fcc62d87749a702b04503`，验证身份标签来自已解析目录／注册项，及 SingleProxy 子目录查询在缓存命中前检查 namespace。[B1–B8]
- **不承诺**：所有供应商都能无密文回放、云端 background 恢复已通过、exactly-once 工具执行、全部日志已脱敏、namespace 等于 Azure RBAC、动态配置在所有缓存层即时生效。
- **依赖与包归属**：仓库中的包名／版本／changelog 只证明源码声明；没有核实 PyPI wheel、NuGet、npm 或已部署二进制包含上述提交。不得通过未授权云部署来弥补依赖闭包或包来源未核实。

## 2. 文字架构图与完整主调用路径

```text
MAF：合成 provider 响应／事件
  ├─ 非流式：Foundry._parse_response_from_openai → 父类解析
  │           → _attach_foundry_reasoning_replay_item
  └─ 流式：Foundry._parse_chunk_from_openai → 父类解析
              → output_item.done 时附加 payload → ChatResponse.from_updates
       ↓ Content.additional_properties[__foundry_reasoning_replay_item__]
  完整历史／checkpoint：reasoning + function_call + function_result
       ↓ get_response → _inner_get_response（无 continuation_token）
  _prepare_request → 验证 options → Foundry._prepare_options → 父类._prepare_options
       ↓ 根据 continuation 标记判断服务端存储路径
  _prepare_messages_for_openai
       → _prepare_reasoning_items_for_openai
       → _validate_reasoning_groups_for_stateless_replay
       → _prepare_message_for_openai：同一 provider reasoning ID 只序列化一次
       ↓ 通过后才进入 SDK create／parse／stream（本验收全部 mock）
  失败：ChatClientInvalidRequestException；禁止删除单独 reasoning 来绕过

MCP：tools/call + 原始 name／arguments
       ↓ McpRuntime：开启 Activity；不直接写原始 name 为 ToolName
       ↓ [可选 Composite：初始化目录，按工具路由]
       ├─ CommandFactory：筛选 → 命令解析 → canonical 身份 → 模式／elicitation／参数 gate → ExecuteAsync
       ├─ Registry：初始化 discovery／clients／list → Tool filter → map 解析
       │            → 注册身份 → 模式 gate → CallToolAsync(original name)
       ├─ Server／Namespace：目录解析 → 规范 area → 规范 command
       │            → 可选 sampling 修正并重新匹配目录 → 模式 gate → 调用
       └─ SingleProxy：learn／command → namespace gate（先于子缓存）
                    → 允许目录 → canonical 名 → 本地或远程调用
                    → 被禁／空目录：Unknown 身份 → RootLearn
                         └─ 有 sampling capability 且 intent 非空：仍可能 SampleAsync
       ↓ Activity 标签、返回文本、日志、sampling、进度通知：分别验收
```

### 2.1 MAF：逐源追踪与负控语义

1. **保存入口**：Foundry 先调用父类解析，再把合格 reasoning payload 附加到对应 `text_reasoning`；未找到对应内容时创建空文本 reasoning 内容。流式只在 `response.output_item.done` 附加这一原生回放 payload。[A1，299–349、366–381]
2. **验证并非内容审查**：白名单为 `type/id/response_id/status/summary/content/encrypted_content`；`type` 必须为 `reasoning`，两个 ID 必须为非空字符串，`summary/content` 必须为 list。没有强制 `encrypted_content`，没有验证列表元素的隐私属性，也没有要求 `status=completed`。不能把“保留完成事件”误写成“校验器拒绝所有非完成状态”。[A1，85–98、299–314]
3. **重建优先级**：公共层先找 truthy `protected_data`／`encrypted_content`；没有时才调用 provider hook。Foundry hook 倒序寻找同 ID 的有效 stored payload，不是按状态或时间戳排序；上游流式测试证明特定 added→done 顺序下选择 `resp_complete`，不证明任意乱序流都正确。[A1，284–296；A2，1984–2038；A3，616–655]
4. **请求路径**：`_prepare_request` 先取 client、验证 options、准备消息，然后 SDK transport 才被调用。服务端存储分支由非空字符串 `conversation_id/previous_response_id/conversation` 决定，**不只由 `store=False` 决定**；验收无状态时须清空这些标记及 `continuation_token`。已有 continuation_token 的 background 路径直接 retrieve，是不同路径。[A2，781–796、840–976、1608–1623]
5. **组完整性**：公共层先重建 replayable ID 集合，再依分组 annotation 或消息顺序划分组；针对含 reasoning 且有工具 call ID 的组检查缺失／不可重建 ID，并拒绝同一 reasoning ID 出现在不同组，即使另一组有有效密文。不能把这一检查称为完整的 call/result 一一配对验证，也不能推导它拒绝所有纯 reasoning 历史重复。[A2，1756–1848；A4，1878–1993]
6. **负控证据强度**：Foundry 四项测试主要调用解析与 `_prepare_request`，断言序列化结果或异常；OpenAI 跨组 ID 与部分压缩测试经 `get_response` 并断言 `with_raw_response.create.assert_not_awaited()`。后者只证明目标 SDK 方法未被 await，不证明初始化、文件、日志或其他 IO 全无。[A3、A4]
7. **隐私**：checkpoint 中的 reasoning metadata、summary/content、response ID、密文和 raw representation 均按敏感数据处理；字段白名单不是匿名化。业务日志仅记录合成标记／字段存在性／组数量／异常类别，禁止复制真实 payload。业务所需回放存储与日志脱敏应分层，不能为了日志清理破坏可回放历史。

### 2.2 MCP：逐源追踪与负控语义

1. **Runtime／Composite 不提前相信输入**：Runtime 不直接把 `request.Params.Name` 写入身份标签；Composite 未命中时写双 Unknown，命中则交给子 loader。空参数和部分初始化失败的身份标签可能不存在，不能一律要求 Unknown。[B1、B2、B9]
2. **Registry**：先初始化 discovery/client/list，之后才执行 Tool filter 和 map 查找；未找到／filter 拒绝写双 Unknown，错误文本仍回显原名；找到后用 `kvp.ServerName`、`kvp.Tool.Name`，远端调用用 `OriginalToolName`，并非把暴露名前缀随意小写。已解析后被 read-only／HTTP gate 拒绝仍可能保留合法 canonical 身份。[B3，89–191、215–345；B10]
3. **CommandFactory**：Tool filter 和命令查找后才写身份，再检查 read-only／HTTP、elicitation、参数解析，最后执行。这里是“已解析目录身份”，不应统一描述为所有 loader 都执行字符串小写转换。`Tool` 筛选使用 `Contains`，不能未经负控就称为精确名称白名单。[B4，77–252；B3，111–128]
4. **Server／Namespace**：先形成当前可用命令目录，大小写无关匹配后使用目录中的 command 和 provider／namespace 正式名。Server 用 provider metadata.Name；SingleProxy 的 discovery area 用 metadata.Id，两者不能混为一个字段契约。未知 command 可 sampling 一次再重新匹配，不能直接执行模型输出；空目录的 command 修正路径不 sampling，但 learn 路径另有逻辑。[B5、B6、B7、B11]
5. **SingleProxy 子缓存 gate**：`GetToolCommandsAsync` 和 `GetToolsInGroupAsync` 在读取缓存前检查当前 Namespace。禁止 namespace 返回空目录，learn／execute 转到 RootLearn；上游负控断言不调用 `GroupCommands`、命令 `ExecuteAsync` 或 discovery `GetOrCreateClientAsync`。[B7，285–360、397–488；B8，338–400]
6. **拒绝并非零 IO／统一错误状态**：上述负控在 `supportsSampling=true` 时明确期待一次 `sampling/createMessage`；拒绝可能返回根目录引导而非 `IsError=true`。RootLearn 可能 discovery，sampling 可带 intent 和目录，其他路径可带参数及进度通知。`IsServerCommandInvoked=false` 不等于“未与模型交互”。`SupportsSampling` 仅检测 capability 存在，不等于完成了客户授权或成本审批。[B7，363–394、818–943；B8；B12]
7. **新增缓存边界负控**：上游 warmCache 先预热的是特定工具的子目录，不是 RootLearn 的 `_cachedTools`。后者初始化后直接返回，未在返回时重新过滤；Namespace 的 `_availableNamespaces` 是 Lazy，子缓存也优先返回。因此不能从现有测试推出所有模式支持配置热收紧。必须补测“先预热根目录→收紧→再次 root learn”，包括 sampling 返回禁用项；这是静态风险线索，尚未动态复现，不能表述为已确认线上漏洞。[B7，192–247、363–394；B6，36–50、592–630；B8]
8. **保护范围仅限指定标签**：错误文本、日志中的原始 tool/command/intent、参数名、subscription 与其他 metadata 仍需独立评估。Runtime 仍接收原始请求参数并记录部分其他字段，不能声称端到端 PII 已消除，也不能用此机制替代认证、Azure RBAC 或资源级授权。[B1、B3、B5–B7]

## 3. Run card A — Foundry 无状态 reasoning 回放

| 字段 | 验收填写／执行要求 |
|---|---|
| Run ID／负责人 | `MAF-REPLAY-<客户自定批次>`；执行人、验收人、UTC 开始／结束时间待填 |
| 当前状态 | **NOT_RUN**；本文仅静态证据，所有 observed 字段留空 |
| 输入／源码 | 完整固定 SHA 源码；正常导入同 SHA 的 core/openai/foundry；合成 reasoning、call、result；不得抽取函数模拟源码测试 |
| 先决条件 | 授权隔离实验环境；Python 满足项目声明；审核全部 conftest/import 副作用；固定依赖 wheel、传递依赖、哈希、来源清单；依赖闭包未满足则 BLOCKED |
| 依赖声明 | Foundry 声明 Python >=3.10、core >=1.19.0,<2、openai 集成 >=1.14.2,<2、azure-ai-projects >=2.2.0,<2.7.0 等；这些是声明范围，不是本文验证过的兼容组合 [A5] |
| 隔离 | 无 Azure／OpenAI 凭据，无宿主凭据挂载；网络 deny；不调用 configure_azure_monitor；project_client 与所有 SDK create/parse/stream/retrieve 使用 mock；显式启用审核过的 pytest-asyncio，禁用无关自动加载插件 |
| 入口 | Foundry 测试文件 [A3] 的下列四个精确 node；OpenAI 文件 [A4] 的跨组重复 ID、缺 payload、部分压缩负控 |
| 观测 | 记录实际 module 来源（对外仅 repo-relative path）、依赖锁摘要、collect 清单、pytest XML、序列化字段存在性与合成 ID、各 SDK 方法计数、网络拦截记录 |
| 通过 | 上游目标节点全部收集且执行；A01–A07 的已实现子用例断言满足；负控在指定 transport 前失败；不产生真实凭据或数据外传 |
| 失败／停止 | 收集为零、skip/xfail、未实现补充用例、依赖不完整、任一外部连接、真实 endpoint／credential 出现均不得报 PASS；分开报告 FAIL/BLOCKED/NOT_RUN |
| 清理／回退 | 终止隔离进程，删除临时合成 checkpoint；仅保留脱敏结果、依赖哈希与计数；不对生产历史做原地压缩／修复 |
| 最终记录 | `source_sha=…; dependencies=UNVERIFIED; collected=未填; executed=未填; pass/fail/skip=未填; network=未观测; package_mapping=UNVERIFIED` |

**授权后的执行配方（本文未执行）：** 工作目录为获批源码树的 `python/packages/foundry`，使用预装离线依赖的解释器，不触发在线安装。先 collect-only，核对四个节点，再去掉 `--collect-only` 执行同一命令；pytest 配置和插件须在隔离环境中审核后使用。

```sh
python -m pytest --collect-only -q -m 'not integration' \
  tests/foundry/test_foundry_chat_client.py::test_stateless_replay_uses_foundry_reasoning_item_without_encrypted_content \
  tests/foundry/test_foundry_chat_client.py::test_streaming_stateless_replay_prefers_completed_foundry_reasoning_item \
  tests/foundry/test_foundry_chat_client.py::test_stateless_replay_rejects_incomplete_foundry_reasoning_item \
  tests/foundry/test_foundry_chat_client.py::test_stateless_replay_rejects_malformed_stored_foundry_reasoning_item
```

随后在 openai 包目录，对 [A4] 中 `test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport`、`test_stateless_reasoning_group_without_encrypted_content_is_rejected_before_transport`、`test_partially_compacted_reasoning_group_is_rejected_before_transport` 逐个使用相同 collect→执行流程。A04/A07 的补充断言需要另行实现，不得把上游已有测试通过当成补充项已通过。Foundry 实际 conftest 位于 `tests/foundry/conftest.py`。[A6]

## 4. Run card B — MCP canonical telemetry 与 namespace gate

| 字段 | 验收填写／执行要求 |
|---|---|
| Run ID／负责人 | `MCP-GATE-<客户自定批次>`；执行人、验收人、时间待填 |
| 当前状态 | **NOT_RUN**；源码测试断言已读，不是测试运行结果 |
| 输入／源码 | 固定 MCP SHA 完整树；Azure.Mcp.Core.Tests 与引用项目；内存 fake commandFactory、discovery、McpClient、McpServer；合成 `user@example.com`，不使用客户真实标识 |
| 先决条件 | 核对 global.json 和项目依赖；该 SHA 声明 .NET SDK 10.0.401、latestFeature rollForward、Microsoft.Testing.Platform；测试项目引用 xunit.v3.mtp-v2／NSubstitute，但传递依赖及 NuGet 闭包尚未核实 [B13、B14] |
| 隔离 | 审核后才构建／加载测试代码；离线 restore 缓存经哈希批准，运行阶段 --no-restore；网络 deny、无云凭据、禁止真实子 server 启动；所有 sampling 由内存 fake 返回 |
| 入口 | `core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Azure.Mcp.Core.Tests.csproj`；Runtime、六种 loader 对应测试类；优先 [B8–B11] 中点名负控 |
| 执行顺序 | 先确认获批 SDK 及该版本 MTP/xUnit 的 help/list/filter 语法，再列出精确测试清单；只运行选择的 unit tests，不运行项目中 live tests；未核过滤器不提供“可直接运行”的猜测命令 |
| 计数维度 | `ExecuteAsync`、远端 `CallToolAsync`、discovery、GetOrCreateClient、ListTools、sampling、progress、日志／exporter 分别计数；设置内存 ActivityListener，记录标签存在／Unknown／canonical 三态 |
| 缓存矩阵 | 冷缓存、只预热子目录、预热 RootLearn 根目录分别建 fixture；之后把 Namespace 收紧为 storage；learn/execute 与 sampling on/off 分开记录 |
| 通过 | B01–B09 所有要求项实际执行且断言成立；身份标签不含未解析原始名；禁止命令不执行；sampling 与其他 IO 符合单独授权；热更新不支持时须在客户边界明确改为重建 loader 后验证 |
| 停止／失败 | 暖根目录仍暴露禁用项、采样超出约定次数、递归／超时、错误文本泄漏客户数据、真实 discovery／网络、测试未收集均不得通过；仅 Activity status=Ok 不足以通过 |
| 清理／回退 | dispose loader／ActivityListener 与 fake clients，清空所有缓存，删除合成日志；回退到已批准配置或重建实例，不在线修改权限来“让测试成功” |
| 最终记录 | `source_sha=…; dependency_closure=UNVERIFIED; case_id=…; expected=…; observed=未填; calls=未观测; result=NOT_RUN; package_mapping=UNVERIFIED` |

**执行防误用**：MTP 与传统 VSTest 的过滤参数不可默认互换。完整源码、SDK、项目引用、测试扩展和过滤语法均核实后，才能形成客户环境的精确命令并写入 run record。B09 为新增验收设计，尚无本文提供的可运行补充测试文件。不能设置 `TEST_PROXY_URL` 使 Registry 初始化被跳过后，把空目录导致的拒绝冒充真实 registry gate 验证。[B3，222–232]

## 5. 16-case 验收矩阵

每行是一个验收 case，可含参数化子项；**全部运行状态为 NOT_RUN**。U=已有上游测试断言；S=源码可直接定位；E=需补充实现。要求记录 `expected/observed/evidence/result` 四栏，未执行的 observed 不填 0。

| ID | 前置／刺激 | 预期与负控观测 | 来源／覆盖 |
|---|---|---|---|
| A01 | 无 continuation 标记；有效 Foundry 原生 payload，无 encrypted_content；call+result 完整 | 重建 reasoning→call→output，保留 response_id；非所有 provider 通用 | A1/A3；U |
| A02 | 同 ID 的 added(resp_incomplete)→done(resp_complete) | 聚合回放选择 resp_complete；不得外推任意乱序 | A1/A3；U |
| A03 | reasoning ID 在，回放 payload 缺失或仅含 id | `_prepare_request` 抛 invalid request；补充 get_response 的全 transport mock 负控 | A3/A4；U+E |
| A04 | 无其他密文／有效 payload 兜底；逐项变异 type、空 id、缺 response_id、summary/content 非 list；加入未知字段 | 不合格 payload 不可用于有工具的无状态组；未知字段剔除；list 内合成敏感标记不会因外层校验自动脱敏 | A1；S+E |
| A05 | 两工具组复用 reasoning ID；后一组带有效密文 | 拒绝；异常提及两个 call；create 不被 await | A2/A4；U |
| A06 | compaction 只排除 reasoning、保留同组 call | 拒绝并提示 atomic compaction；不能删 reasoning“修复” | A4；U |
| A07 | 同一历史分别无 continuation 标记／带有效 previous_response_id；store 均 false | 分支由 continuation 标记决定；后者不重复 inline reasoning/function_call；此单元断言不证明服务端接受 | A2；S+E |
| B01 | Runtime→fake loader；含原始异常名 | Runtime 不抢写 ToolName/ToolArea；子 loader 设置后不覆盖；空参数允许标签 absent | B1/B9；U |
| B02 | Server：STORAGE + ACCOUNT_LIST；再用未知 command | 前者 canonical storage/account_list 并执行一次；后者 ToolName Unknown、合法 area 可保留；采样关 | B5/B11；U |
| B03 | Registry：未知名或 Tool filter 禁用项，使用合成邮箱 | 双 Unknown、目标执行零；错误文本可回显邮箱，必须单列泄漏面；初始化 IO 独立计数 | B3/B10；U+E |
| B04 | Composite 未知名／已知名；CommandFactory 未知名 | 未解析不下发目标执行；Unknown；已知 Composite 交子 loader 设置身份，不提前污染 | B2/B4；S，上游测试存在 |
| B05 | 已解析 Registry 写工具 + read-only；对照 Server 预过滤掉同类命令 | 两者都不得执行；Registry 可保留已知名，Server 可 Unknown；拒绝≠必须双 Unknown | B3/B5/B10/B11；U |
| B06 | Namespace allow storage；keyvault 或合成邮箱，learn/execute；采样关 | 双 Unknown；合法 STORAGE 配未知命令为 Unknown/storage；不可依赖原名做审计身份 | B6；S，上游测试存在 |
| B07 | SingleProxy 禁 keyvault；冷／子目录热缓存；learn/execute；sampling=false | 不返回禁用子命令、不 GroupCommands、不 Execute、不 GetOrCreateClient；sampling=0 | B7/B8；U |
| B08 | SingleProxy 禁 keyvault，冷缓存；learn/execute；sampling=true，fake 返回 keyvault | 目标命令不执行；双 Unknown；**sampling 恰一次**；可返回根引导而非 error | B7/B8；U |
| B09 | 先 RootLearn 预热根目录，再收紧 namespace；sampling off/on；另测子缓存热+sampling on | 客户要求禁项不再列出／执行、无递归与超额采样；源码根缓存可能不满足，必须实测或声明需重建 loader | B7/B8；S+E，不可报已通过 |

B08 的“一次”只适用于给定 fixture，不是所有 SingleProxy 错误分支的通用采样上限。B09 不可被 B07 的子目录 warmCache 覆盖。

## 6. 合成事件与结果记录模板

以下 JSON 是**验收夹具／期望记录格式，不是产品原生日志，也不是实测结果**。所有 ID 和邮箱为合成值；字段 `expected` 与 `observed` 分开。真实测试报告不得将 null 自动转为零。

```json
{
  "kind": "fixture.maf.replay",
  "synthetic": true,
  "case_id": "A01",
  "options": {"store": false},
  "provider_reasoning_item": {
    "type": "reasoning",
    "id": "rs_synthetic_a",
    "response_id": "resp_synthetic_complete",
    "summary": [],
    "content": []
  },
  "function_call": {
    "type": "function_call",
    "id": "fc_synthetic_a",
    "call_id": "call_synthetic_a",
    "name": "lookup_probe",
    "arguments": "{\"step\":1}",
    "status": "completed"
  },
  "function_result": {
    "type": "function_call_output",
    "call_id": "call_synthetic_a",
    "output": "probe-result-step-1"
  },
  "expected": {"replayable": true, "encrypted_content_required": false},
  "observed": null,
  "execution": "NOT_RUN"
}
```

```json
{
  "kind": "acceptance.mcp.namespace",
  "synthetic": true,
  "case_id": "B08",
  "fixture": {
    "loader": "SingleProxyToolLoader",
    "namespace_allow": ["storage"],
    "cache": "cold",
    "supportsSampling": true,
    "sampling_reply": "keyvault",
    "request": {
      "name": "azure",
      "arguments": {"intent": "List synthetic secrets", "tool": "keyvault", "command": "secret_list", "learn": false}
    }
  },
  "expected": {
    "identity": {"ToolName": "<Unknown>", "ToolArea": "<Unknown>"},
    "target_execute_calls": 0,
    "target_client_create_calls": 0,
    "sampling_createMessage_calls": 1,
    "return_mode": "root-guidance"
  },
  "observed": null,
  "execution": "NOT_RUN"
}
```

```json
{
  "kind": "acceptance.mcp.privacy-negative-control",
  "synthetic": true,
  "case_id": "B03",
  "input_name": "user@example.com",
  "expected": {
    "ToolName": "<Unknown>",
    "ToolArea": "<Unknown>",
    "response_may_echo_input": true,
    "end_to_end_redaction_proven": false
  },
  "observed": null,
  "execution": "NOT_RUN"
}
```

客户报告必须增加：源码 SHA、依赖锁摘要、用例／参数组合、采集点、观测时间、mock 与真实 IO 边界、计数、错误类别、网络拦截结果、结论。禁止把 reasoning payload、原始 intent、用户输入或错误全文默认发送到遥测系统。

## 7. SA 客户问答

**Q：是否只升级一个公开包就能得到这些能力？**
A：尚不能确认。源码提交与发行包是两层证据；须取得包制品哈希、版本、构建来源及包含提交的证明，再对实际制品回归。changelog-entry 或 pyproject 版本不等于包含关系。[A5、B15]

**Q：无 encrypted_content 就可以安全记录 reasoning 吗？**
A：不可以。此变化是 Foundry 回放契约兼容，不是隐私放行。原生 payload 可能承载敏感信息；只保留必要的受控 checkpoint，遥测不记录其内容。[A1]

**Q：为什么不能按 message 随意压缩历史？**
A：reasoning 与工具调用是有关联的组。部分移除会破坏回放；应验证完整组原子压缩，或使用真正有效的服务端 continuation，不能制造 continuation ID 或删除 reasoning 绕过失败。[A2/A4]

**Q：跨组重复 ID 带密文为什么仍拒绝？**
A：全局存在一个可重建 payload 不足以证明它属于每个工具组；公共验证器显式拒绝跨组复用，以免错误复用另一组数据。[A2/A4]

**Q：ToolName 是 Unknown，是否整个请求已脱敏？**
A：没有。Registry 错误文本仍可能回显原始名，其他日志／参数／metadata 也须独立审计。Unknown 是未解析身份，不是全链路匿名化证明。[B1/B3]

**Q：namespace 被禁后，还会产生模型成本吗？**
A：可能。给定 SingleProxy 负控在支持 sampling 时调用一次 sampling/createMessage。sampling 应另设同意、数据边界、预算与计数，不要将命令执行零次解释为模型交互零次。[B7/B8/B12]

**Q：热缓存收紧一定即时生效吗？**
A：只读到了子目录查询前的当前 Namespace gate 与对应测试。根目录缓存、其他 loader 缓存不是同一保证；先做 B09，必要时明确配置变更必须重建实例，不能承诺无缝热更新。[B6–B8]

**Q：canonical 身份能替代 RBAC 吗？**
A：不能。它解决输入名与解析身份的遥测混淆；资源访问仍需认证、授权、最小权限及独立审计。

**Q：这份材料已经证明生产可用了吗？**
A：没有。本模板证明固定 SHA 的相关代码与测试断言可定位，并给出验收设计。原始上游 pytest／MCP 测试项目和本模板完整集成矩阵未运行，其完整测试依赖闭包与发行包归属未核实。配套 MAF lab 单独锁定了原创 runner 所用依赖并执行所选真实源码入口；那不是完整矩阵、发行包或生产验证。生产结论必须基于获授权环境里的实际结果。

## 8. 固定 SHA 来源与实际核验

下列链接均为固定 SHA 原始文件 URL，本文编制时实际 HTTP GET 返回 **200**。A1–A6、B1–B11、B15 的对应文件还与已获取的同 SHA 内容做 SHA-256 一致性复核；B12–B14 为补充直接抓取核验。HTTP 200／内容一致只证明所引文件可获取，**不证明测试执行、供应链签名或发行包含关系**。行号用于定位，结论以固定内容为准。

### MAF

- **A1** [Foundry `_chat_client.py`](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/agent_framework_foundry/_chat_client.py)：85–98、230–381；原生 payload 保存、校验、provider hook、事件路径。
- **A2** [OpenAI `_chat_client.py`](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/agent_framework_openai/_chat_client.py)：781–976、1583–2038；prepare→group validation→serialization→SDK 边界及 continuation 分支。
- **A3** [Foundry 测试](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/test_foundry_chat_client.py)：544–721；四项回放断言；另有标记 integration 的 background 工具循环，不在本文执行范围。
- **A4** [OpenAI 测试](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/tests/openai/test_openai_chat_client.py)：1878–1993；缺 payload、跨组 ID、部分压缩及 create 未 await 的断言。
- **A5** [Foundry pyproject](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/pyproject.toml)：1–54；包／依赖／pytest 声明，不作为发行包含证明。
- **A6** [Foundry conftest](https://raw.githubusercontent.com/microsoft/agent-framework/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/conftest.py)：测试环境和 mock fixture。

### MCP

- **B1** [McpRuntime](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/Runtime/McpRuntime.cs)：38–119；Activity、loader 下发、错误分支；128–174 为其他 metadata 面。
- **B2** [CompositeToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/CompositeToolLoader.cs)：85–203；初始化、未命中与委派。
- **B3** [RegistryToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/RegistryToolLoader.cs)：89–191、215–345；身份、错误回显、初始化 IO、prefix/original name。
- **B4** [CommandFactoryToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/CommandFactoryToolLoader.cs)：77–252；查找、模式 gate、elicitation 与执行。
- **B5** [ServerToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/ServerToolLoader.cs)：114–393、395–592；canonical 匹配、目录、sampling、远程调用。
- **B6** [NamespaceToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/NamespaceToolLoader.cs)：36–50、160–537、539–753；Lazy namespace、命令 gate、本地执行和 sampling。
- **B7** [SingleProxyToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/SingleProxyToolLoader.cs)：126–488、491–943；完整 learn/execute 分支、缓存、执行边界、sampling。
- **B8** [SingleProxyToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/SingleProxyToolLoaderTests.cs)：306–400；未知工具异常及六个 disabled namespace 参数组合。
- **B9** [McpRuntimeTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/Runtime/McpRuntimeTests.cs)：委派前无身份标签及子 loader 标签保留的断言。
- **B10** [RegistryToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/RegistryToolLoaderTests.cs)：298–443、read-only/HTTP 测试；错误回显与 canonical 身份。
- **B11** [ServerToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/ServerToolLoaderTests.cs)：308–400 及 sampling correction 测试；大小写、未知身份与模式拒绝。
- **B12** [BaseToolLoader](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/BaseToolLoader.cs)：192–230、451–466；sampling capability、转发与模式筛选辅助函数。
- **B13** [global.json](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/global.json)：SDK 与测试 runner 声明。
- **B14** [Azure.Mcp.Core.Tests.csproj](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Azure.Mcp.Core.Tests.csproj)：项目引用、unit/live 混合属性及测试依赖。
- **B15** [Azure changelog entry](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/servers/Azure.Mcp.Server/changelog-entries/alzimmer-tool-telemetry-validation.yaml) 与 [Fabric changelog entry](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/servers/Fabric.Mcp.Server/changelog-entries/alzimmer-tool-telemetry-validation.yaml)：仓库变更记录；不等于 NuGet/npm 包已包含提交。

- **B16** 补充负控测试：[CompositeToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/CompositeToolLoaderTests.cs)、[CommandFactoryToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/CommandFactoryToolLoaderTests.cs)、[NamespaceToolLoaderTests](https://raw.githubusercontent.com/microsoft/mcp/5bf6e024152bf4cd414fcc62d87749a702b04503/core/Azure.Mcp.Core/tests/Azure.Mcp.Core.Tests/Areas/Server/Commands/ToolLoading/NamespaceToolLoaderTests.cs)：分别支持 B04 的委派／未知命令及 B06 的允许身份断言；均已 HTTP 200 与 SHA-256 内容一致性核验，未运行。

**验收结论填写规则**：只有实际执行、有证据且符合客户授权边界的项目才可填 PASS。源码支持、测试存在、HTTP 可访问、包版本存在是不同证据层，不能互相替代。
