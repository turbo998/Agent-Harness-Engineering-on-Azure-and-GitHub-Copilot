# 编码 Agent 双 CLI 验收资产：Codex 目录预算生命周期与 Claude 模型准入

**日期：2026-09-27｜用途：客户技术问答、隔离 POC、架构评审｜公开版｜非生产配置推荐**

核心结论：**目录展示预算不是执行权限；历史里有 snapshot 不等于模型当前可见；模型家族 alias 不是版本冻结；blocked `--model` 可能 fallback 而非全局拒绝启动。** 本文把 Codex 固定提交与 Claude Code 2.1.283 文档转成可验收资产。所有 CLI / SDK / provider / host 均 **NOT_RUN**；示例配置均为合成夹具，**不承诺任何模型在真实账号、区域、provider 或版本中可用**。

## 1. 证据、边界与 URL 复核

以下固定 diff、tag 源码及官方文档已读取正文，所列 URL 于 2026-09-27 实际请求最终 HTTP 200。Codex 为既有目录预算主题的新生命周期实现；Claude 为 2.1.283 新控制键。未安装或执行 CLI，没有调用模型、SDK、云端或上游测试。

|ID|来源 URL|支持结论|边界|
|---|---|---|---|
|C1|https://github.com/openai/codex/commit/e72da2b53805894878023d01949a25a082e0a5cb.diff|Codex commit `e72da2b` 新增 catalog allocation、cloud fingerprint、rebalance、history diff 相关实现与测试|commit 级证据；未跑测试|
|C2|https://api.github.com/repos/openai/codex/commits/e72da2b53805894878023d01949a25a082e0a5cb|commit 元数据与时间|不等于发行包可用|
|C3|https://registry.npmjs.org/@openai/codex/latest|npm latest 显示 `0.157.1`|npm endpoint 可变；未下载包|
|C4|https://raw.githubusercontent.com/openai/codex/rust-v0.157.1/codex-rs/ext/skills/src/world_state_catalogs.rs|`rust-v0.157.1` 源码仍是旧共享 render，缺新 allocation/rebalance 符号|只证明 tag 源码层未含该实现；不声称所有未来/alpha 包状态|
|A1|https://raw.githubusercontent.com/anthropics/claude-code/7779afb12e3635f46f56ec823979d68350ae000b/CHANGELOG.md|Claude Code 2.1.283 changelog：新增 `availableModelsMatch` 与 `deniedModels`；同时 fixed 中 revert 2.1.282 `claude-ai` reservation|公告级与文档级；非实机行为验证|
|A2|https://code.claude.com/docs/en/model-config.md|block specific models、fallback、surface coverage、provider delivery 语义|文档行为预期；provider 未 smoke|
|A3|https://code.claude.com/docs/en/settings-reference.md|`availableModelsMatch` / `deniedModels` Scope=Managed、exact/prefix、deny 语义|managed 来源需实际部署验证|
|A4|https://registry.npmjs.org/@anthropic-ai/claude-code/latest|npm latest/版本端点为 `2.1.283`|未下载或执行原生包|

**证据类型**：固定 commit 的 raw/diff 可按固定 URL 复核内容；docs、registry latest/dist-tags、普通 HTML 都是可变快照，须随取证保留抓取时间与正文 SHA-256，不能要求之后抓取永远同 hash，也不能把文档 SHA 当固定源码/包级证据。

**发布边界**：Codex `e72da2b` 不能写成已进入 npm `0.157.1`；Claude managed 模型准入只来自 2.1.283 指定来源与文档，旧版会忽略新键，应配 `requiredMinimumVersion=2.1.283`。

## 2. Codex：四个状态面必须拆开验收

`e72da2b53805894878023d01949a25a082e0a5cb` 的核心变化是：在执行环境 ready/unavailable、history compaction/resume、cloud/filesystem 目录共存时，稳定“模型可见的目录展示”，但不把展示缓存提升为执行授权。

### 2.1 机制解读

1. **目录预算 allocation**：从全部 model-visible cloud 目录元数据计算 BLAKE3 fingerprint，并保存 `total_budget / cloud_limit / cloud_catalog_fingerprint`。executor ready 状态和 provider warning 不是 fingerprint 输入。默认先给 filesystem 预留四分之一；cloud 空或禁用时，未用预算交回 filesystem。
2. **只缩不涨的 cloud cap**：只有 filesystem 确有条目遗漏、且共享渲染能让全部目录不丢条目时，才缩小 cloud cap；仅描述截短不触发。相同 cloud fingerprint + total budget 下 cap 只减不增，避免 VM 断连后目录反复膨胀。
3. **history diff 与 availability update**：相同 executor 目录恢复时，仅当目录正文仍在真实 history 中才发 “available again” 短消息。保存的是展示历史，不是执行权限；每步 discovery 仍决定真实可用目录。
4. **compaction/resume**：compaction 只保留 allocation 元数据，不保留已渲染正文。新上下文窗口需要时重新注入完整目录，避免“有 snapshot 但模型看不到目录”。

### 2.2 Codex 八个验收用例（全部产品 host = NOT_RUN）

|ID|状态面|合成输入|精确预期|判定|
|---|---|---|---|---|
|CX-01|目录预算|cloud 有 model-visible 条目，filesystem 未知；total budget 固定|初始 `cloud_limit = total - floor(total/4)`；allocation 记录 total、cloud_limit、cloud fingerprint|NOT_RUN；需读取请求中的 world state / snapshot|
|CX-02|预算 rebalance|filesystem 确有 omitted_count>0；共享渲染可容纳 cloud+filesystem 全目录|cloud cap 缩小到共享渲染的 cloud metadata cost；不丢 cloud 条目；同一 allocation 内后续不可自动涨回|NOT_RUN|
|CX-03|描述截短反例|filesystem 无 omitted entry，仅 description 被截短|不得触发 rebalance；cloud cap 不因描述截短而变|NOT_RUN|
|CX-04|executor unavailable|上一轮有 executor skills 正文；本轮 discovery 无 selected-environment skills|可记录 lastAvailableFingerprint；不得把历史正文当执行权限；本轮 selected-environment 目录为空；不推断其他工具权限|NOT_RUN|
|CX-05|executor reattach|同一 executor 目录恢复，且真实 history 仍含旧目录正文|只发短 “previously listed selected-environment skills are available again” 更新；不重复注入完整正文|NOT_RUN|
|CX-06|compact + resume|turn 后 compaction，随后新窗口 resume|compaction snapshot 只含 allocation 元数据；新窗口若无真实正文，应重新注入完整目录而非只发 available-again|NOT_RUN|
|CX-07|目录或预算改变|cloud catalog fingerprint 或 total budget 改变|新建 allocation；可重新计算 cap，不受旧 cap 只缩不涨约束|NOT_RUN|
|CX-08|发行包映射|npm latest `@openai/codex=0.157.1`，对照 `rust-v0.157.1` source|不得宣称 `e72da2b` 已在当前稳定包可用；只能说 tag 源码层未含该实现|NOT_RUN；仅 curl/source read|

## 3. Claude Code 2.1.283：exact + deny managed 模型准入

2.1.283 增加两个 managed-only 控制键：`availableModelsMatch` 与 `deniedModels`。它们解决“模型 family allowlist 会随新 minor 自动放行”的验收窗口问题。

### 3.1 机制解读

1. **`availableModelsMatch="exact"`**：具体模型 ID 仅允许该版本，包括该版本 dated IDs；新 minor 必须显式加入。仅 family alias（如 `["opus"]`）允许整个家族，不能当冻结版本；同一有效列表若还列该 family 的具体 ID，会禁用该 family wildcard。`best`、`opusplan`、`default` 条目忽略。exact 影响 Default 的前提是 managed list 至少命名一个有效 model/family；空列表或仅含上述忽略条目，不能靠 exact 阻断 Default。`deniedModels` 是独立限制。
2. **`deniedModels` deny 优先**：被列入 deny 的模型即使被 `availableModels` 允许也被阻断；没有 allowlist 时也可单独使用。`claude-opus-5-5` 覆盖该 minor 的 dated/provider-specific 写法；无 minor 的 `claude-opus-5` 还会挡后续 minor，若只挡 5.0 应写 `claude-opus-5-0`。
3. **来源与版本门**：两键只读 Managed scope；user/project/local/`--settings` 中均被忽略并警告。旧版忽略两键，所以必须同时配置 `requiredMinimumVersion=2.1.283`。
4. **fallback 必须先分支**：blocked `--model`、`ANTHROPIC_MODEL` 或 `model` setting 会被丢弃并解析 Default，不能把显式选择当作原始 Default。若 `enforceAvailableModels=true` 且 `availableModels` 非空，blocked Default 按 allowlist 外模型处理，重映射到列表中首个允许且可用的模型，而非先选同 family。否则（本文 CL-06 固定 false/未设置），只有原始 Default 被阻断时才依次尝试同 family 最新允许版本、Sonnet 最新允许模型、Haiku 最新允许模型、allowlist 首个允许模型；该路径没有允许候选才拒绝启动。exact 的 Default 范围仍受第 1 条限制。true+非空但无条目能解析为允许且可用模型时，文档另规定跳过 enforcement 并仅在 `--debug` 警告；这不撤销 deny/exact，不能用单一“启动失败/成功”概括所有组合。
5. **hook 不是 Default fallback**：hook/background request 指定被 `deniedModels` 阻断的模型时，回到现有 session model；不能套用上面的 Default 家族回退顺序，也不从此推导所有 exact omission 的 hook 行为。

### 3.2 合成 managed settings 示例（不是模型可用性承诺）

```json
{
  "requiredMinimumVersion": "2.1.283",
  "availableModels": ["claude-opus-5", "claude-sonnet-5"],
  "availableModelsMatch": "exact",
  "deniedModels": ["claude-opus-5-5"]
}
```

该示例只表达准入意图：冻结 Opus 5 / Sonnet 5 版本线并显式拒绝 Opus 5.5。它不保证这些模型名在任何账号、provider 或时间点可用。

### 3.3 Claude 十四个验收用例（加 Codex 八个，共 22 个用例 ID；全部产品 host = NOT_RUN）

**共同合成 fixture F（非产品配置 API）**：CLI=2.1.283、最高优先级 managed source 已有效送达；无额外组织限制、无 alias env override、无其他 fallback chain。测试模型目录仅有 `claude-opus-5-5`、`claude-opus-5`、`claude-sonnet-5`，三者在替身中均可用；版本顺序 Opus 5.5 > 5.0。原始 account Default 固定为 `claude-opus-5-5`（无 org default 覆盖）。有效 managed settings 为 `requiredMinimumVersion="2.1.283"`、`availableModels=["claude-sonnet-5","claude-opus-5"]`（顺序固定）、`availableModelsMatch="exact"`、`deniedModels=["claude-opus-5-5"]`；`--model claude-opus-5-5` 是被阻断的显式选择。仅明确引用 F 的卡按列明项覆盖 F；CL-01~CL-05 与 CL-08 是独立 fixture，不继承 F 的 managed 键、启动参数或版本前置。CL-01 无 deny，以隔离 exact omission；CL-02 用允许 Opus family 的 allowlist，以隔离 deny 优先；CL-04 确保有效 managed source 中没有被测两键，以隔离非 managed 来源的忽略行为。这里的 Default 与“可用”均为合成输入假设，不是账号/provider 的实测或可用性保证；真实 host 必须先取得对应候选目录与 Default 的证据，否则 NOT_RUN，不能把替身结果冒充产品结果。

|ID|合成输入|精确预期|判定|
|---|---|---|---|
|CL-01 exact 具体 ID|Managed: `availableModels=["claude-opus-5"]`, `availableModelsMatch="exact"`; 选择 `claude-opus-5-5`|`claude-opus-5-5` 被视为 blocked selection；`/model` picker 隐藏；`/model claude-opus-5-5` 拒绝|NOT_RUN|
|CL-02 dated/provider spelling|Managed deny: `deniedModels=["claude-opus-5-5"]`; 选择 Opus 5.5 dated 或 provider-specific ID|同一 minor 的 dated/provider-specific 写法被 blocked；deny 优先于 allow|NOT_RUN|
|CL-03 family alias 反例|仅 alias fixture：Managed `availableModels=["opus"]`, `availableModelsMatch="exact"`，无 deny、无同 family 具体 ID|`opus` 允许整个 family；不能把 alias 当版本冻结；混合列表例外见 CL-12|NOT_RUN|
|CL-04 非 managed 来源|把 `availableModelsMatch` 或 `deniedModels` 放入 user/project/local/`--settings`|Claude Code 应忽略该键并警告；不得把它记为企业准入边界|NOT_RUN|
|CL-05 旧版门|版本 <2.1.283 且配置了两键，但未配置/未生效 `requiredMinimumVersion`|旧版会忽略两键；验收必须 FAIL 或 NOT_RUN，不得写 PASS|NOT_RUN|
|CL-06 blocked `--model` fallback|F；分别运行 `enforceAvailableModels=false` 与键未设置两个变体|显式 Opus 5.5 被丢弃；原始 Default Opus 5.5 也 blocked；同 family 允许的最新候选为 `claude-opus-5`，故有效 Default 精确为该 ID，而不是列表首项 Sonnet 5；不是一律拒绝启动|NOT_RUN|
|CL-07 无允许 Default|F；固定 enforce=false；deny 覆盖目录全部三项：Opus 5.5、Opus 5、Sonnet 5|otherwise 路径无允许候选，session startup refuses to start；错误指出需修复的 key。不是 true+不可解析列表的无条件 oracle|NOT_RUN|
|CL-08 surface delivery|第三方 provider（如 Microsoft Foundry）仅配置 server-managed admin console|文档预期：第三方 provider 不接收 server-managed，应通过 MDM/managed settings file；不得推断已执行|NOT_RUN|
|CL-09 enforced Default remap|F，仅改 `enforceAvailableModels=true`；非空有效 allowlist 有可用条目|blocked Default 按 allowlist 外模型处理；首个允许且可用条目为 `claude-sonnet-5`，即有效 Default；即使同 family Opus 5 可用也不先选它|NOT_RUN|
|CL-10 exact + 空列表范围|F 改 `availableModels=[]`、`deniedModels=[]`；直接选择 Default；enforce 分别 false/true/未设置|exact 不影响 Default，enforce 对空列表无效，原始 Default `claude-opus-5-5` 不因这两项而 blocked；named selections 仍被空列表阻断。不表示绕过独立 deny 或组织限制|NOT_RUN|
|CL-11 exact + 仅忽略条目范围|F 改 list 为 `["best","opusplan","default"]`、deny=[]、enforce=false；直接选择 Default|列表未命名有效 model/family，exact 不影响 Default；预期仍为原始 `claude-opus-5-5`。仅断言此 Default 范围，不把忽略条目当有效 fallback 候选|NOT_RUN|
|CL-12 alias + 具体 ID 反例|F 改 list 为 `["opus","claude-opus-5"]`、deny=[]、enforce=false；尝试 `/model claude-opus-5-5`|同 family 具体 ID 禁用 opus wildcard；exact 只允许 Opus 5 对应版本及 dated IDs，拒绝这次 Opus 5.5 显式切换|NOT_RUN|
|CL-13 hook/session fallback|F 的 managed policy；已存在允许的 session model=`claude-sonnet-5`；hook/background 指定 deny 中的 Opus 5.5|请求使用现有 session model `claude-sonnet-5`，不走 CL-06 的 Default 家族回退；不外推 exact-only hook omission|NOT_RUN|
|CL-14 enforcement 无可解析项范围|合成目录同 F、Default=Opus 5.5；list=`["claude-sonnet-5"]`，替身中 Sonnet 5 不可用；match=prefix、deny=[]、enforce=true；直接 Default|没有允许且可用的 list entry，enforcement 跳过且仅 `--debug` 警告；无本卡其他阻断时 Default 保留 Opus 5.5。若另加 deny/exact，必须另判，不能把该警告理解为解除全部策略|NOT_RUN|

## 4. 完整 Run Card（双 CLI）

### 4.1 通用前置

- 使用空白测试项目、无生产凭据、无真实写入工具；固定 OS、CLI 包版本、通道、provider、账号类型、登录方式。
- 任何缺版本、缺 managed 来源、缺可观测 trace 的用例写 **NOT_RUN** 或 **SKIP（写明原因）**，不得折算为 PASS。
- 所有示例配置先在隔离环境落盘；禁止在生产 home、全局 managed policy 或真实组织 admin console 中直接试验。
- 记录格式必须分离：`schema_status`、`expected`、`observed`、`case_status`、`host_status`、`evidence_ref`；预期策略决策不得冒充 observed。NOT_RUN 时 `observed=null`；源码/文档只能支持 expected，不是产品 trace。

### 4.2 Codex run steps

1. 固定 commit/包映射：记录 `codex --version`、npm 包、平台；若不是包含 `e72da2b` 的构建，CX-01~CX-07 写 NOT_RUN。
2. 构造 cloud/host/executor 三类 skill catalog，分别控制条目数、描述长度、model-visible 标记与 filesystem omitted_count。
3. 回放 pending→ready→unavailable→reattach→compact→resume 生命周期；每步保存 request history、world state snapshot、catalog body、allocation、tool authorization trace。
4. 对照 CX-01~CX-08 写 expected/observed；尤其检查短 availability update 只在真实 history 仍含正文时出现。
5. 负例：只描述截短不得 rebalance；cloud fingerprint 或 total budget 改变必须新 allocation；历史正文不得被当作本轮执行授权。
6. 清理所有 skills、executor、缓存与临时目录；报告中不得把 offline/source read 写成 host PASS。

### 4.3 Claude run steps

1. 固定 `claude --version`、npm 包、provider、surface（CLI/IDE/Desktop/cloud/SDK/Cowork）与 managed delivery 方式。
2. managed 正例按各卡在最高优先级来源配置版本门、list、match、deny 与 enforce；CL-04 必须移除 managed 的被测键，再独立放入 user/project/local/`--settings`；CL-05 刻意不设或不生效版本门。其余配置按对应 fixture 固定，不将正例配置残留带入负例。
3. 按 CL-01~CL-14 固定各自输入；分别执行 `/model` picker、`/model <name>` 及启动时的 `--model`、`ANTHROPIC_MODEL`、`model` setting；CL-13 的 denied hook/background 请求另记现有 session model，不能套 Default oracle。
4. 先记录 managed 有效 list、enforce 值（区分 false/未设置）、match、deny、原始 account/org Default 及候选可用性，再比较 expected/observed。CL-06 两变体精确预期 Opus 5；CL-09 true+非空列表精确预期 Sonnet 5；CL-07 仅对应 false 且无允许候选的拒绝；CL-10/11 检验 exact 的 Default 范围，CL-14 单列 enforcement 跳过警告。不得统一写成无条件三步回退或“无候选必拒绝”。
5. 对第三方 provider 或 cloud surface，先确认 managed settings 是否送达；未送达则写 NOT_RUN/SKIP，不把 CLI 本地文件推断到云端。
6. 清理 managed fixture；报告保留警告、版本、settings 源、选择前后模型、错误文本。

### 4.4 原创记录 schema（非产品 API）

```json
{
  "case_id": "CL-06-blocked-model-fallback",
  "schema_status": "VALID",
  "fixture_id": "F-enforce-false",
  "expected": {
    "policy_decision": "BLOCK_EXPLICIT_AND_RESOLVE_DEFAULT",
    "original_default": "claude-opus-5-5",
    "effective_default": "claude-opus-5",
    "reason": "false branch; permitted same-family candidate in synthetic fixture F"
  },
  "observed": null,
  "case_status": "NOT_RUN",
  "host_status": "NOT_RUN",
  "evidence_kind": "source_docs_only_not_runtime",
  "evidence_ref": ["A2", "A3"],
  "runtime_evidence_ref": null
}
```

`schema_status=VALID` 仅指本原创记录结构可解析且字段齐全，不表示 CLI 接受 settings 或授权成立。运行后才填 observed 的策略决策/落点及 runtime trace；NOT_RUN/SKIP 无运行观测时保持 null。expected 与 observed 相等也只有在真实对应运行层获得证据后才可判该层 PASS。

## 5. 客户问答落点

- **问：Codex skills 列表恢复了，是不是工具权限也恢复？** 答：不是。`e72da2b` 明确把 display history 和 execution authority 分开；每步 discovery 决定当轮目录可用性；真正执行仍须独立权限控制。
- **问：有 compaction snapshot 是否说明模型看到了目录？** 答：不是。该提交只在 compaction 保留 allocation 元数据；新窗口需要重新注入完整目录。
- **问：Codex 0.157.1 是否已包含该实现？** 答：不能这么说。已核 `rust-v0.157.1` 源码仍缺新 allocation/rebalance；本文不承诺包可用。
- **问：Claude `exact` 是否就是字符串全等？** 答：不是。具体 ID 允许该版本及其 dated IDs；仅 alias 的列表允许整个家族，但同 family 具体 ID 会禁用该 wildcard（CL-03/12）。exact 影响 Default 还须 managed list 至少命名一个有效 model/family；空列表或仅忽略条目不满足，独立 deny 仍有效（CL-10/11）。
- **问：`deniedModels` 和 allowlist 冲突谁赢？** 答：deny 优先；它也能无 allowlist 独用。
- **问：被 blocked 的 `--model` 是否一定启动失败？** 答：不一定；丢弃显式选择后解析原始 account/org Default。false/未设置按 CL-06 的 otherwise 路径（本合成 fixture 到 Opus 5）；true+非空有效 list 按 CL-09 首个允许且可用项重映射（本 fixture 到 Sonnet 5），不能统一称三步回退。CL-07 是无允许候选的拒绝用例；CL-14 的不可解析列表 enforcement 跳过另有 debug 警告且不撤销独立 deny/exact。均是文档预期，不承诺真实模型可用。
- **问：hook 的 blocked model 是否也重选 Default？** 答：CL-13 仅断言 `deniedModels` 阻断的 hook/background 模型回到现有 session model；不是 Default fallback，不据此推断其他 hook 准入规则。

## 6. 交付门槛

本文可用于解释机制和设计验收；没有产品 host 的有效运行证据，不得据此签署生产验收、宣称 Codex 稳定包包含 `e72da2b`、承诺 Claude 任一模型可用，或把本文提升为正式批准结论。
