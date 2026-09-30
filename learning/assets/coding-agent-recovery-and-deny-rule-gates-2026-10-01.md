# 编码代理恢复与 deny-rule 闸门：公开演练模板（2026-10-01）

> 证据等级：**静态源码审阅 / 产品卡全部 NOT_RUN**。未运行 Codex、Claude Code、上游测试、native payload、云端 POC 或真实产品回归。阅读源码不等于执行测试。

## 0. 使用边界

- 目标：把两个 CLI 机制拆成恢复性演练卡、负控和观测事件，供技术问答、隔离 POC 与架构评审使用。
- 测试只用一次性工作区及合成数据；不连接客户凭据。外部插件内容仅作不可信输入，不是执行授权。
- Codex quick_check 机制在 `596ae94...` / `3620b2...` 相关源码中观察到，**稳定源码 tag `rust-v0.159.2` 不含该机制**。npm wrapper 完整性核查不证明 native 二进制内容。
- Claude `16da1e...` 机制在 tag `v2.1.285` 的 `register.ts` 可见，但这不是 native 运行实测。此处只讨论 `sec-default` 在其托管/组织条件下被装载后的权限裁决，不外推所有个人会话；也不同于决定插件能否装载的 `allowManagedModsOnly` 准入机制。

## 1. 两个机制的一句话结论

1. **Codex SQLite 恢复**：可写池打开后对文件身份做一次预算化 `PRAGMA quick_check(1)`；结果要区分 `Complete / Incomplete / CorruptedNeedsFixed / Skipped`。只有命中恢复策略的库才备份重建；`Unavailable` 是报告型边界，不是通用 fail-closed。
2. **Claude deny-rule 保持**：`sec-default` 在 `tool.check` 上先跑完整链，发现用户层可能放宽且托管策略要求 deny rule 保持时，再绕过用户层重跑；只有“带 rule 的 deny”会替换原 verdict。组织层和 builtin override 仍可能生效，策略缓存窗口为 500ms。

## 2. 流程图 A：Codex SQLite 恢复状态机

```mermaid
flowchart TD
  A[打开可写 SQLite pool] --> B[按 FileId 进入一次性 attempt gate]
  B -->|同一 shared config 已尝试| S[Skipped：不可记为健康]
  B -->|首次尝试| C[quick_check(1)，100ms 扫描预算，进度回调每 1000 VM ops]
  C -->|ok| D[Complete]
  C -->|腐败文本或 typed SQLite corruption code| E[CorruptedNeedsFixed]
  C -->|超时/锁/其他未处理错误| F[Incomplete：不可记为腐败]
  E --> G{RecoveryMode}
  G -->|BackupAndRebuild| H[关闭 pool；保留备份；重建后重连]
  G -->|Unavailable| I[报告/记录；返回 pool，不是 fail-closed]
  H --> J[启动成功后提示保留备份与可能丢失的 DB-only metadata]
```

## 3. 流程图 B：Claude deny-rule 两段式权限判断

```mermaid
flowchart TD
  A[tool.check] --> B[运行完整 hook 链 next(e)]
  B --> C{原答案是否非 deny 且 trace 显示用户层可能放宽}
  C -->|否| Z[返回原答案]
  C -->|是| D{托管策略 denyRulesHold?}
  D -->|否：managed literal true opt-out| Z
  D -->|读策略失败/决策失败/未设置| E[默认保护]
  D -->|是| E
  E --> F[绕过 user tier 运行 next.to(e,'append')]
  F --> G{是否为带 rule 的 deny}
  G -->|是| H[返回 held deny；按插件/批次会话内去重通知]
  G -->|否| Z
  B -->|异常 catch| I[只信已存在 deny 或无用户放宽；否则 UNCHECKED_DENY]
```

## 4. 16 张演练卡

### Codex 恢复卡 1：目标库腐败只影响目标备份
- **前提**：运行时日志库或同等 `BackupAndRebuild` 库被判定为 `CorruptedNeedsFixed`；旁路库放置 sentinel。
- **动作**：触发可写池初始化并让 quick check 返回腐败。
- **期望**：只备份并重建目标库及相关 sidecar；其他库 sentinel 保持不变。
- **负控**：把“任何库变化”或“全部目录清理”当作成功均失败。
- **状态**：NOT_RUN；静态源码与上游测试意图审阅。
- **源码出处**：`codex-rs/state/src/sqlite.rs`；`codex-rs/state/src/runtime/recovery.rs`；commit API `https://api.github.com/repos/openai/codex/commits/3620b2caf8afecfcedd5c5c9520c0d239c880f26`。

### Codex 恢复卡 2：thread history 的 Unavailable 不是自动删除
- **前提**：thread history DB 使用 `RecoveryMode::Unavailable`。
- **动作**：让该库被 quick check 判定腐败。
- **期望**：记录腐败/遥测，但不自动备份重建；可读表和历史应尽量保留。
- **负控**：把 `Unavailable` 解释成 fail-closed 或“必然删除重建”均失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/state/src/sqlite.rs` 中 `THREAD_HISTORY_DB`；commit API `https://api.github.com/repos/openai/codex/commits/3620b2caf8afecfcedd5c5c9520c0d239c880f26`。

### Codex 恢复卡 3：锁等待/扫描预算不等于腐败
- **前提**：连接/锁等待或 quick check 扫描超过预算。
- **动作**：构造锁竞争或长扫描场景。
- **期望**：结果应归入连接失败或 `Incomplete`，不可计作 `CorruptedNeedsFixed`。
- **负控**：把 100ms 扫描预算写成启动墙钟 SLA 或腐败率指标均失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/state/src/sqlite/validation.rs`；`codex-rs/state/src/sqlite.rs`。

### Codex 恢复卡 4：取消的首次扫描会留下 attempt cache
- **前提**：同一 `SqliteConfig` / shared quick-check manager，首次检查已插入 FileId 后被取消或未完成。
- **动作**：随后在同 owner/config 下再次打开同一文件。
- **期望**：第二次返回 `Skipped`，不能当作健康通过。
- **负控**：把 `Skipped` 计入 healthy 或强制等待首次健康结果均失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/state/src/sqlite/validation.rs`；commit API `https://api.github.com/repos/openai/codex/commits/3620b2caf8afecfcedd5c5c9520c0d239c880f26`。

### Codex 恢复卡 5：同路径替换文件应按新 FileId 重查
- **前提**：数据库路径相同，但底层文件已被替换。
- **动作**：再次打开该路径。
- **期望**：新 FileId 不命中旧 attempt，quick check 应重新发生。
- **负控**：仅按路径缓存并跳过新文件检查为失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/state/src/sqlite/validation.rs` 使用 `file_id::get_file_id(path)`。

### Codex 恢复卡 6：并发首次扫描不是健康屏障
- **前提**：两个打开请求几乎同时命中同一 shared config 和同一 FileId。
- **动作**：并发发起可写 pool 初始化。
- **期望**：一个 attempt 执行；另一个可能 `Skipped`，并不等待健康结论。
- **负控**：把第二个调用通过看作“已完成完整健康检查”失败。
- **状态**：NOT_RUN。
- **源码出处**：`SqliteQuickCheckManager.quick_check_once`；`codex-rs/state/src/sqlite/validation.rs`。

### Codex 恢复卡 7：伪造错误文本不应冒充 typed corruption
- **前提**：错误消息文本包含类似 “corrupt” 字样，但不是 SQLite typed extended code。
- **动作**：传入纯文本错误与真实 SQLite extended code 两类样本。
- **期望**：纯文本不分类为 typed corruption；真实 `DatabaseCorrupt` / `NotADatabase` 分类为腐败。
- **负控**：继续用字符串匹配 `(code: 11)` 或 `file is not a database` 判定为成功均失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/state/src/runtime/recovery.rs`；commit API `https://api.github.com/repos/openai/codex/commits/596ae94fb00f8325d6bf835a9ebdc90baab4ad33`。

### Codex 恢复卡 8：rollout 恢复不等于无损恢复
- **前提**：发生备份重建并成功启动。
- **动作**：比较线程列表、turns、以及仅存在于数据库中的 metadata。
- **期望**：报告 preserved backups 和可能的 DB-only metadata gap；不要宣称全部状态无损。
- **负控**：仅看到启动成功就声称 lossless restoration 失败。
- **状态**：NOT_RUN。
- **源码出处**：`codex-rs/app-server/tests/suite/v2/sqlite_recovery.rs`；`codex-rs/tui/src/startup_error.rs`。

### Claude deny-rule 卡 9：用户 allow/ask 不能覆盖 rule deny
- **前提**：托管策略要求 deny rules hold，且绕过用户层后得到带 rule 的 deny。
- **动作**：用户层插件返回 allow 或 ask。
- **期望**：最终返回原 rule deny；通知按插件/批次会话内去重，但后续检查仍继续保护。
- **负控**：通知去重导致后续权限检查跳过为失败。
- **状态**：NOT_RUN。
- **源码出处**：`mods/sec-default/hooks/register.ts`；`held-verdict/verdicts/is-rule-deny.ts`；commit API `https://api.github.com/repos/anthropics/claude-code/commits/16da1ecd3ff1e18a0522248f20bce52726e653ff`。

### Claude deny-rule 卡 10：blind allow 仍需 bypass-user 复核
- **前提**：用户 hook 不调用 `next` 并直接 allow。
- **动作**：触发 `tool.check`。
- **期望**：trace 被识别为用户层可能放宽；在策略保护开启时执行 `next.to(e,'append')`。
- **负控**：信任 blind allow 或仅凭插件名判断为失败。
- **状态**：NOT_RUN。
- **源码出处**：`loosened-by-users.ts`；`register.ts`。

### Claude deny-rule 卡 11：不要信返回的用户 rule 文本
- **前提**：用户插件伪造或改写 rule 文本/输入。
- **动作**：同一 pinned question 进入绕过用户层判断。
- **期望**：权威结果来自 bypass-user 评估；只接受其带 rule deny。
- **负控**：把用户返回的 rule 文本当作权威为失败。
- **状态**：NOT_RUN。
- **源码出处**：`register.ts` 中 `next.trace` 与 `next.to(e,'append')` 路径。

### Claude deny-rule 卡 12：plain deny 与 ask-to-allow 不是此机制保护对象
- **前提**：原始或绕过用户层结果没有 `rule` 字段。
- **动作**：返回 plain deny 或 ask-to-allow。
- **期望**：不把机制扩大成“所有 deny 永远保持”；只有带 rule 的 deny 被 held。
- **负控**：宣传 universal deny guarantee 为失败。
- **状态**：NOT_RUN。
- **源码出处**：`is-rule-deny.ts`；`register.ts`。

### Claude deny-rule 卡 13：组织层/builtin override 仍有效
- **前提**：组织层或 builtin hook 产生 override。
- **动作**：与用户层放宽场景共同出现。
- **期望**：机制只针对用户层放宽；组织和 builtin override 仍可能生效。
- **负控**：把 sec-default 描述为绝对不可覆盖为失败。
- **状态**：NOT_RUN。
- **源码出处**：`register.ts`；比较 API `https://api.github.com/repos/anthropics/claude-code/compare/16da1ecd3ff1e18a0522248f20bce52726e653ff...v2.1.285`。

### Claude deny-rule 卡 14：mixed prepend-user batch 要按 engine tier 看
- **前提**：worker batch 的 tier 取首成员，可能同时包含 user 插件。
- **动作**：构造 prepend/user 混合批次且返回更宽松 verdict。
- **期望**：依据 engine-pinned trace 和 batch tier 触发复核，而不是信插件名。
- **负控**：按显示名称白名单/黑名单直接判断为失败。
- **状态**：NOT_RUN。
- **源码出处**：`loosened-by-users.ts`；`ranking` 相关路径。

### Claude deny-rule 卡 15：只有 managed literal true 才 opt out
- **前提**：策略值分别为 managed `true`、字符串 `"true"`、local/project true、缺省、读失败。
- **动作**：观察 `denyRulesHold` 与 `decidedByPolicy`。
- **期望**：只有托管策略中的布尔 true 关闭保护；字符串/local/project 不关闭；读失败默认保护。
- **负控**：把任意 true-like 值或用户设置当 opt-out 为失败。
- **状态**：NOT_RUN。
- **源码出处**：`policy/deny-rules-hold.ts`；`policy/decided-by-policy.ts`；`register.ts`。

### Claude deny-rule 卡 16：规则失败与 500ms 策略缓存窗口
- **前提**：策略读或规则评估失败，或管理员刚改变策略。
- **动作**：分别在缓存窗口内外重复权限检查。
- **期望**：unvouched loosened verdict 被拒；源码 memo TTL 为 500ms，需分别测命中缓存与重新读取策略，不能将其推导为端到端撤权 SLA。
- **负控**：宣称即时撤销或无限缓存均失败。
- **状态**：NOT_RUN。
- **源码出处**：`policy/policy-memo-ms.ts`；`policy/decided-by-policy.ts`；`held-verdict/caught-answer.ts`。

## 5. 两个合成 JSON 事件

```json
{
  "event_schema": "synthetic.cli.recovery.v1",
  "product": "codex",
  "mechanism": "sqlite_quick_check_recovery",
  "source_revision": "596ae94fb00f8325d6bf835a9ebdc90baab4ad33",
  "introduced_by": "3620b2caf8afecfcedd5c5c9520c0d239c880f26",
  "product_test_status": "NOT_RUN",
  "db_kind": "thread_history",
  "quick_check_outcome": "CorruptedNeedsFixed",
  "recovery_mode": "Unavailable",
  "expected_observation": "report_only_pool_returned_not_backup_rebuild",
  "negative_controls": [
    "do_not_count_skipped_as_healthy",
    "do_not_count_incomplete_as_corruption",
    "do_not_treat_100ms_scan_budget_as_startup_sla"
  ],
  "source_urls": [
    "https://raw.githubusercontent.com/openai/codex/596ae94fb00f8325d6bf835a9ebdc90baab4ad33/codex-rs/state/src/sqlite.rs",
    "https://raw.githubusercontent.com/openai/codex/596ae94fb00f8325d6bf835a9ebdc90baab4ad33/codex-rs/state/src/sqlite/validation.rs"
  ]
}
```

```json
{
  "event_schema": "synthetic.cli.deny_rule_gate.v1",
  "product": "claude-code",
  "mechanism": "sec_default_tool_check_rule_deny_hold",
  "source_revision": "16da1ecd3ff1e18a0522248f20bce52726e653ff",
  "release_tag_observed": "v2.1.285",
  "product_test_status": "NOT_RUN",
  "original_user_tier_verdict": "allow",
  "bypass_user_verdict": { "decision": "deny", "rule": "synthetic-managed-deny-rule" },
  "policy": { "denyRulesHold": true, "memo_ms": 500 },
  "expected_observation": "held_rule_deny_replaces_user_allow",
  "negative_controls": [
    "plain_deny_without_rule_not_covered",
    "organization_and_builtin_overrides_remain_possible",
    "managed_literal_true_only_opt_out"
  ],
  "source_urls": [
    "https://raw.githubusercontent.com/anthropics/claude-code/v2.1.285/mods/sec-default/hooks/register.ts",
    "https://raw.githubusercontent.com/anthropics/claude-code/16da1ecd3ff1e18a0522248f20bce52726e653ff/mods/sec-default/hooks/policy/policy-memo-ms.ts"
  ]
}
```

## 6. 源码出处与完整性锚点

| 机制 | 证据 | 已核 URL / 状态 | SHA-256 |
|---|---|---|---|
| Codex commit: corruption recovery | commit API | `https://api.github.com/repos/openai/codex/commits/3620b2caf8afecfcedd5c5c9520c0d239c880f26` / 200 | `2e19f43a9e29cd77d2572716aeb7e69470dbd98199eedae3e9193b11899b8ea3` |
| Codex commit: typed corruption | commit API | `https://api.github.com/repos/openai/codex/commits/596ae94fb00f8325d6bf835a9ebdc90baab4ad33` / 200 | `87cbcc7ea7343c5ab5c5fadcd2a222b91d8be55733983900d3708b2887a35bfd` |
| Codex validation source | raw source | `https://raw.githubusercontent.com/openai/codex/596ae94fb00f8325d6bf835a9ebdc90baab4ad33/codex-rs/state/src/sqlite/validation.rs` / 200 | `b2253a5aec988fb2d064f29b80d4e2dd4cc2180551fcbac29d6d815dde7d24ff` |
| Codex sqlite source | raw source | `https://raw.githubusercontent.com/openai/codex/596ae94fb00f8325d6bf835a9ebdc90baab4ad33/codex-rs/state/src/sqlite.rs` / 200 | `68a0205893a5c68bbf536c9bb6e29f56d9d87a74246852b1da68c08232bbdcd0` |
| Codex stable boundary | raw source | `https://raw.githubusercontent.com/openai/codex/rust-v0.159.2/codex-rs/state/src/sqlite.rs` / 200；`validation.rs` / 404 | `c942ecd37072975d728fdd9bb94dff36c5cc3563c9a1d9b7f60dc249b33833cc` |
| Claude deny-rule commit | commit API | `https://api.github.com/repos/anthropics/claude-code/commits/16da1ecd3ff1e18a0522248f20bce52726e653ff` / 200 | `e7df5c441a27dd891fb0c3aea38255b8fedad8be559f9c9319512a7ede3e6cfa` |
| Claude tag register source | raw source | `https://raw.githubusercontent.com/anthropics/claude-code/v2.1.285/mods/sec-default/hooks/register.ts` / 200 | `73ac8734c7c8cb0097a48abff2988755b80cd12b4f24ec02015f8574e4749fb5` |
| Claude policy TTL | raw source | `https://raw.githubusercontent.com/anthropics/claude-code/16da1ecd3ff1e18a0522248f20bce52726e653ff/mods/sec-default/hooks/policy/policy-memo-ms.ts` / 200 | `41fa3dc4c6b326e32af6594bac0df6eb87b2dacc8c322f8845e2d4abbb1b277b` |
| Claude policy fail-closed | raw source | `https://raw.githubusercontent.com/anthropics/claude-code/16da1ecd3ff1e18a0522248f20bce52726e653ff/mods/sec-default/hooks/policy/decided-by-policy.ts` / 200 | `ee470328d9204da89382c6d61ec74690b3cc142935d68a6cb423f1638db14a93` |

## 7. 不可写进营销稿的限制

- Codex quick check 的 100ms 是扫描预算，不是启动总耗时 SLA。
- `Skipped`、`Incomplete`、`Complete`、`CorruptedNeedsFixed` 必须分开计量。
- `RecoveryMode::Unavailable` 不是 fail-closed。
- Claude 机制只保护“带 rule 的 deny”，不是所有 deny。
- `allowModsToOverrideDenyRules` 只有托管策略的字面布尔 true 才关闭保护。
- 500ms policy memo 意味着策略变更不是瞬时可见。
- 本文不是 native payload 审计，也不是真实 CLI 行为实测。
