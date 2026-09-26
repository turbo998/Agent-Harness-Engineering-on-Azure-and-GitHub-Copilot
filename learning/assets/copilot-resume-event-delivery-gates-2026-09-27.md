# Copilot Rust SDK resume 事件交付验收手册（公开复用版）

日期：2026-09-27
固定对象：`github/copilot-sdk` commit `4001c1da7d832c51bad1d38619c1a082af390efb`（parent `4cd7a043e020493b77bd6f531f130f4235f37f64`）
结论类型：源码证据驱动的验收门设计；**NOT_RUN**：未编译、未运行上游测试、未连接真实 Copilot 会话、未声明 GA/包版本可用。

## 1. 固定来源与抓取快照（已有 curl 证据；本次仅只读复核）

| 证据 | URL | curl | 内容 sha256 |
|---|---|---:|---|
| commit API | https://api.github.com/repos/github/copilot-sdk/commits/4001c1da7d83 | 200 | `3252762af5b0395525aa95ce6a386e7bc80301c45446296c21bd2d53a7ae185b` |
| commit 网页 | https://github.com/github/copilot-sdk/commit/4001c1da7d832c51bad1d38619c1a082af390efb | 200 | `1fc4b115fc8f41220616af9d2da560b20302cfc80441bb8f3e4e0ec85526a9ae` |
| 完整 diff | https://github.com/github/copilot-sdk/commit/4001c1da7d832c51bad1d38619c1a082af390efb.diff | 200 | `e49d9738734435f70c8564cfa130962435ca897a0742696c5fe87bad1067af68` |
| `rust/src/session.rs` | https://raw.githubusercontent.com/github/copilot-sdk/4001c1da7d832c51bad1d38619c1a082af390efb/rust/src/session.rs | 200 | `5d1fd9818c71114053cfcd93b7df0d7c71ef434647a0a0c0e0fd9fcb6fdae841` |
| `rust/src/subscription.rs` | https://raw.githubusercontent.com/github/copilot-sdk/4001c1da7d832c51bad1d38619c1a082af390efb/rust/src/subscription.rs | 200 | `e3ae6c212003f9ce9ac1041775713fa5860959a39b0b80217aa3772042598e6f` |
| `rust/src/subscription/tests.rs` | https://raw.githubusercontent.com/github/copilot-sdk/4001c1da7d832c51bad1d38619c1a082af390efb/rust/src/subscription/tests.rs | 200 | `6f8328072cc70508126d9ab2accf4b372f73864f214ec36c2c349169cbbbb0b2` |
| `rust/tests/prepared_session_test.rs` | https://raw.githubusercontent.com/github/copilot-sdk/4001c1da7d832c51bad1d38619c1a082af390efb/rust/tests/prepared_session_test.rs | 200 | `1231baa3bc5f1c82eae36de4413daabf65ca2219d63035eed7fd4937314a2ec3` |

补充 seam 证据：同一固定 commit 的 [`rust/src/lib.rs` L2657-L2663](https://raw.githubusercontent.com/github/copilot-sdk/4001c1da7d832c51bad1d38619c1a082af390efb/rust/src/lib.rs)，已留存 GET 200 正文，sha256 `d3f30104878006795e21067bbec7520cec4158808a9a86968994aa70c53911c7`。

证据分层：固定 commit 的 raw 源码与 diff 是语义复核依据，表中哈希用于核对该份正文；commit HTML/API 是抓取快照，不是永恒不变的网页字节。独立复核的 commit HTML 哈希为 `116d3fa33adb5e6af65487db2cb112e8273be538e037747025b4782e7bfb3dca`，与原快照不同不自动否定固定源码。后续抓取必须记录 UTC `retrieved_at`、请求及最终 URL、HTTP status、正文 sha256 与来源类型；未留存的原始抓取时间标 `unknown`，不得把 HTTP Date 或文档日期冒充实际抓取时间。动态 docs/registry 若被后续引用也只算带时间的快照。本次未重新抓取、未运行上游。

## 2. 机制摘要与明确边界

### 2.1 机制

1. 仅 `resume` 路径在启动时检查 `event_tx.receiver_count() == 0`；若没有活跃 prepared subscriber，才创建 `ResumeBootstrap`。`create` 路径不因此获得历史补发。
2. `ResumeBootstrapState` 为 `Unclaimed(VecDeque)` → `Claimed(VecDeque)` → `Disabled` 三态。第一个 `Session::subscribe()` **同步认领**启动前缀，不等首次 poll；后续订阅者直接进入 live broadcast。
3. `publish()`、认领、空队列 handoff 共用同一把 `Mutex`：启动前缀读空时，在锁内创建 live receiver 并置 `Disabled`，目标是避免切换点 gap/duplicate。
4. 启动追赶队列使用 `VecDeque`，会保存已路由到 session 的 durable 与 ephemeral 事件；追赶期新增事件也会进入该队列，同时仍发给 live 观察者。
5. handoff 后进入 `tokio::sync::broadcast` 有界 live 流；慢消费者看到 `RecvErrorKind::Lagged(Lagged(skipped))`，不是阻塞生产者。
6. `send_and_wait_structured` 内部观察者直接订阅 broadcast，避免抢走业务调用者的 resume bootstrap。
7. 清理语义：未认领队列随 event loop cleanup 释放；已认领队列可在 shutdown 后排空；owner drop 会丢弃未读 backlog，且不会转交给后续订阅者。

### 2.2 三层边界（SA 可直接问答 / POC / 架构）

- 客户问答层：该机制解决的是“恢复已有 Copilot 会话后，订阅安装窗口内的 `session.idle` / completion / ephemeral 等事件被 UI 漏看”的会话内观察问题；不是让业务任务重跑，也不是持久化 event log。
- POC 验收层：必须用假 transport / FakeServer 控制 `resume response 前`、`registerInterest 期间`、`skills.reload 期间`、`session 返回后但首 subscribe 前`、`首订阅追赶期间` 的事件时序，并用同步 fence 证明事件已被 session loop 发布，禁止 sleep 型“碰运气”断言。
- 架构层：链路应理解为 `CLI JSON-RPC → client 全局通知 router（有界，仍可丢）→ session event loop → resume 单 owner bootstrap 队列（无界）→ 锁内 handoff → live broadcast（有界/Lagged）→ UI/审计观察者`。这不是全链路 exactly-once，也不覆盖 router 溢出、跨进程恢复或服务端 SLA。

### 2.3 严禁扩大解释

- 不把 bootstrap 无界队列说成有界。
- 不把锁内 handoff 说成端到端 exactly-once。
- 不把源码测试阅读说成本地 runtime PASS。
- 不把 commit 标题中的 CLI 版本号说成 GA / 已发包证明。

## 3. 验收前统一夹具

建议 POC 使用 in-memory JSON-RPC duplex transport 和 FakeServer；这与源码测试的设计一致：排序由手写 peer 控制，timeout 只作失败 backstop，不用 sleep 等“稳定”。

- `TIMEOUT`: 5s，所有必须到达事件用 bounded wait。
- `QUIET`: 150ms，仅用于“必须无额外 wire traffic / 无额外 event”的负断言。
- `BURST`: 600 个 ordered delta 后跟 1 个 ephemeral `session.idle`。
- 同步 fence：发送 `permission.requested`，由 `PublicationFence` handler `notify_one()`；handler 能触发说明此前事件已经经过 session event loop 发布。该 fence 是观察同步点，不是业务权限处理成功证明。
- 可选原创探针：在测试 payload/harness 记录 `(observer_id, delivery_index, phase_seq, event_id, ephemeral, source_phase)`。外部日志中的 catchup/handoff 只能标为 `inferred_phase`，不能冒充私有状态实测；真实状态仅为 `Unclaimed/Claimed/Disabled`，`Lagged/Closed` 是接收结果，不是该 enum 的成员。

### 3.1 三类执行 seam（不可混用）

- **U：crate-private unit harness**。CASE-02/03/04/05/10 在固定源码树 `rust/src/subscription/tests.rs` 子模块内实现/复核；`ResumeBootstrap` 及 `new/publish/subscribe` 为 `pub(crate)`，状态 enum 私有，普通外部 SDK 无法调用或精确读取。新增内部仪表须单列补丁哈希，不得当成上游已提供指标。
- **I：internal feature / test-support integration**。CASE-01/06/07/08/09 对照固定 `rust/tests/prepared_session_test.rs` 与其 FakeServer、本地 handler/helper，在固定源码树启用 `test-support` 的测试夹具中复现。`registered_session_count_for_test` 是 `#[cfg(feature="test-support")]`、`#[doc(hidden)]` 的 **public 测试入口**，不是 crate-private，也不是受支持的普通 SDK API；`await_no_registrations` 是测试文件本地 helper，不是 SDK 方法。
- **P：public SDK 外部 POC**。仅使用公开 resume/prepare/subscribe/recv/Stream、handler 配置与 `stop_event_loop()`（确为 public）。外部只可用事件 ID/顺序、Lagged、pending、Closed、重试结果作 oracle；不能直接 publish bootstrap、读取状态或精确队列/注册数。无 test-support 时 CASE-07 仅能证实“重试无旧事件”，不能签署“router 注册数为零”。本手册 U/I 精确卡不能用 P 的弱观测代签。

### 3.2 运行证据记录规范

每卡及每个 A/B 分支独立记录：`case_id, variant, status, seam, upstream_commit, source_path, test_name, source_sha256, harness_patch_sha256, command, cwd_logical, features, toolchain, dependency_lock_sha256, os_arch, transport_kind, host_version, package_version, started_at_utc, ended_at_utc, timeout_config, fixture_config, expected, observed, exit_code, log_sha256, metrics_provenance, reviewer`。真实命令只能在运行后填写；未运行时 `status=NOT_RUN`，命令、时间、observed、exit_code、日志等无实际值字段为 `null`，不能用源码预期填 observed。固定源码测试、外部 POC、真实 host/package 分开记录；静态审查通过不等于 runtime PASS。公开记录须去除内部绝对路径、凭据和真实会话标识，仅保留脱敏逻辑路径与摘要。

## 4. 按 seam 落地的验收设计卡（全部 NOT_RUN，不宣称现成外部 SDK 配方）

### CASE-01：resume 启动全阶段前缀完整、有序、含 ephemeral

- 状态：**NOT_RUN**
- 配置输入时序：`ResumeSessionConfig(session_id).with_event_buffer_capacity(1).with_permission_handler(PublicationFence).with_mcp_auth_handler(CancelMcpAuthHandler)`；时序为 `session.resume request` 已读但未响应 → 发 `pre-durable(session.model_change, ephemeral=false)` → 发 `pre-ephemeral(session.idle, ephemeral=true)` → fence → 响应 resume → 读 `session.eventLog.registerInterest` → 发 `BURST=600` 个 `assistant.message_delta` + `evt-idle(session.idle, ephemeral=true)` → fence → 响应 interest → 读 `session.skills.reload` → 发 `during-reload(session.idle,true)` → fence → 响应 reload → session 返回 → 发 `post-setup(assistant.message,false)` → fence → 首订阅。
- observer 角色：`first = session.subscribe()` 为 bootstrap owner；`second = session.subscribe()` 为 late live observer。
- 同步 fence 方法：只在上列 pre-response、interest、reload、post-setup 四处发送 `publication-fence(permission.requested)` 并等待 handler notify；catchup/live 阶段以实际接收确认发布，不增发 fence。
- 执行 seam / 固定参照：**I**；`prepared_session_test.rs` L1081-L1192，`resume_bootstrap_retains_all_startup_phases_and_keeps_later_subscribers_live`。
- 精确 oracle 与后半段顺序：创建 first、second 后，**first 尚未首次 poll、仍保留完整启动前缀时**发送 `during-catchup(session.idle,true)`；先 bounded recv 确认 second 收到该事件，以此证明它已发布，不再插入额外 fence 事件。此后 first 顺序收到 `pre-durable,false`、`pre-ephemeral,true`、`publication-fence`、`evt-0..evt-599`、`evt-idle,true`、`publication-fence`、`during-reload`、`publication-fence`、`post-setup`、`publication-fence`、`during-catchup`，不得 Lagged。然后才对 first 空队列调用 `recv().now_or_never()`，结果为 None（pending），安装 live handoff；second 同样 pending。最后独立发送 `live(assistant.message,false)`，两者各收到一次 live 后 pending；stop、drop session 后两者 bounded recv Closed。

### CASE-02：追赶期新增事件不丢且第二观察者保持 live

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**U**；`subscription/tests.rs` L118-L136，`first_subscription_claims_before_polling_while_later_observers_stay_live`。
- 配置输入时序：broadcast capacity 8；创建 bootstrap，先 publish `bootstrap`；调用 `first=subscribe()` 但不 poll；调用 `second=subscribe()` 并断言 pending；publish `during-catchup`，先让 second 收到；first 读 bootstrap 与 during-catchup 后再 poll 空队列至 pending 完成 handoff；**此后**才 publish 独立 `live`。
- observer 角色：`first` 是 bootstrap owner，`second` 是普通 live observer。
- 同步 fence 方法：使用 `recv().now_or_never()` 断言同步 ready/pending，无 sleep。
- 精确 oracle：`second` 在 `during-catchup` 发布后立即收到 `during-catchup`，且之前不收到 `bootstrap`；`first` 顺序收到 `bootstrap`、`during-catchup`；两者随后都收到 `live`，读空后 pending。

### CASE-03：并发首订阅只能一个认领 bootstrap

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**U**；`subscription/tests.rs` L139-L169，`concurrent_subscribers_claim_bootstrap_exactly_once`。
- 配置输入时序：capacity 8；bootstrap 先 publish `bootstrap`；两个线程经 `Barrier(2)` 同时调用 `subscribe()`，join 两线程；逐一首次 poll，确认仅一人获得 bootstrap；publish during-catchup，两个 observer 各读该事件并各 poll 至 pending；此后才 publish live，再各读 live 并 poll 至 pending。
- observer 角色：两个竞争 observer，最多一个成为 owner。
- 同步 fence 方法：线程 barrier 控制 subscribe 竞争；`now_or_never()` 判定谁已同步持有前缀。
- 精确 oracle：两个 observer 中恰好 1 个可立即读到 `bootstrap`；两个 observer 都顺序收到后续 `during-catchup` 与 `live`；无 duplicate bootstrap。

### CASE-04：空队列 handoff 与并发 publish 无 gap / duplicate

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**U**；`subscription/tests.rs` L218-L253，`publication_racing_empty_queue_handoff_has_no_gap_or_duplicate`；补充 recv/Stream 关闭语义见 L172-L189。
- 配置输入时序：重复 32 轮；capacity 1024；bootstrap publish prefix，owner 读掉 prefix；**唯一强 sender tx move 进 producer，禁止残留强 sender clone**（bootstrap 仅持 weak sender）。producer 经 barrier 连续 publish event-0..event-599，线程结束即 drop tx；owner 同时从空队列 handoff 到 live。
- observer 角色：单 bootstrap owner。
- 同步 fence 方法：producer/consumer barrier + 每个 recv 5s timeout。
- 精确 oracle：每轮 owner 逐一 bounded recv event-0..event-599，每个 ID 一次且无 Lagged；600 个读完后必须 `producer.join().unwrap()`，确认唯一强 sender 已 drop。随后 `timeout(5s, events.next()).await.unwrap()` 必须为 **None（Stream 终止）**，不接受 timeout/pending/额外事件。新增 recv 等价断言：`timeout(5s, events.recv()).await.unwrap().unwrap_err().kind()` 必须为 `RecvErrorKind::Closed`；此额外断言与固定 racing 测试原有 Stream 断言分开留证。保留 sender 的另设 POC 只能用 `now_or_never()==None` 表示 pending，不得套用本卡 closure oracle。

### CASE-05：handoff 后仍是有界 live；慢消费者必须报告 Lagged

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**U**；`subscription/tests.rs` L192-L215，`bootstrap_handoff_is_cancel_safe_and_preserves_live_lag`。
- 配置输入时序：capacity 1；bootstrap publish `bootstrap`；owner 读 `bootstrap`；owner 对空队列调用一次 `recv().now_or_never()` 安装 live 并取消 pending；随后 publish `overwritten`、`live`；依次消费 Lagged(1) 与 live（overwritten 已丢失）后，用 Stream API poll 至 pending，再 publish `stream-overwritten`、`stream-live`。
- observer 角色：单 owner，已从 bootstrap 切到 live。
- 同步 fence 方法：`now_or_never()` 安装 live receiver；无需 sleep。
- 精确 oracle：第一次读取返回 `RecvErrorKind::Lagged` 且 `skipped()==1`，下一条为 `live`；Stream API 同样先返回 `Lagged(1)`，再返回 `stream-live`。这证明 SDK 没把 live 改成无限无损。

### CASE-06：structured output 内部等待不抢首个业务 observer 的 bootstrap

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**I**；`prepared_session_test.rs` L1195-L1292，`structured_output_completion_preserves_resume_bootstrap_for_first_observer` / `structured_output_cancellation_preserves_resume_bootstrap_for_first_observer`。
- 配置输入时序：resume 配置 PublicationFence permission handler，先读 resume request，在响应前发 `startup-idle(session.idle,true)` + fence；resume 完成并 answer skills reload；随后调用 `send_and_wait(MessageOptions.with_response_schema(...))`。A 响应 session.send 的 messageId 为 structured-user，随后发 structured-answer（assistant.message，originatingMessageId=structured-user，内容为符合 schema 的 JSON）与 structured-idle；B 在 session.send request 到达后 abort waiting task 并 join 确认取消。两路均在等待/取消完成后才调用业务 subscribe。
- observer 角色：`send_and_wait_structured` 内部 observer 只能是 broadcast observer；业务 `observer=session.subscribe()` 应是 bootstrap owner。
- 同步 fence 方法：startup fence；`session.send` request 作为内部等待已安装的同步点；abort join result 作为取消 fence。
- 精确 oracle：A 路业务 observer 顺序收到 `startup-idle`、`publication-fence`、`structured-answer`、`structured-idle`；B 路恰按顺序收到 startup-idle、publication-fence（此 fixture 不发送 answer/idle）。两路随后 poll 为 pending；stop、drop session 后 bounded recv Closed。A 路返回 result event id 精确为 structured-answer；该 FakeServer oracle 只验证等待/交付，不证明真实业务 side effect。

### CASE-07：setup 失败或取消后，同 session_id 重试不继承旧 backlog

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**I，必须 test-support**；`prepared_session_test.rs` L1295-L1376 的 `populated_resume_bootstrap_cleans_up_after_setup_failure` / `populated_resume_bootstrap_cleans_up_after_setup_cancellation`，共用 `check_populated_resume_cleanup`（不是其他同类失败 helper）；本地 `await_no_registrations` 见 L377-L389。
- 配置输入时序：**首次失败/取消尝试先配置 `.with_permission_handler(PublicationFence).with_mcp_auth_handler(CancelMcpAuthHandler)`**，再发 resume → 响应 resume → 读 session.eventLog.registerInterest → 发 startup burst + fence 并等 notify；MCP auth handler 是触发 interest 的条件，默认配置不保证该请求。A 对 interest 返回 RPC error -32004；B abort start task 并 join。两路等待 router 无注册及 QUIET 后，以同一 session_id 使用无 handler 默认配置 retry resume（不等待 interest），answer skills reload，subscribe，发 after-retry(session.idle,true)。
- observer 角色：失败/取消路径没有业务 observer；retry 后 observer 为新 session live/bootstrap 观察者。
- 同步 fence 方法：startup burst 后 fence；`await_no_registrations` 轮询 router count 至 0；retry request/response 为新生命周期 fence。
- 精确 oracle：失败路径返回 `ErrorKind::Rpc { code: -32004 }`；取消路径 join error is_cancelled；两路 `registered_session_count_for_test()==0` 后 retry 成功；retry observer 只收到 `after-retry`，不得回放旧 `evt-*` 或旧 `evt-idle`；随后 stop、drop session，bounded recv Closed，再等注册数归零，不能只读一条新事件就漏检尾部旧 backlog。

### CASE-08：stop/drop 语义：未认领释放、已认领可排空

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**I**（末尾注册数核验需 test-support）；`prepared_session_test.rs` L1379-L1443，`stopping_resume_releases_unclaimed_bootstrap` / `claimed_bootstrap_drains_after_stopping_and_dropping_session`。
- 配置输入时序：`prepare_resume_session(...with_event_buffer_capacity(1).with_permission_handler(PublicationFence))`；启动前先创建并 drop prepared observer；start 后在 resume response 前发 startup burst + fence；完成 skills reload；A 不 claim，先 await stop_event_loop() → late subscribe → 首次 poll pending/无旧 backlog → **drop(session)** → bounded recv Closed；B 先 subscribe claim，再 await stop_event_loop() 并 drop session，然后排空。
- observer 角色：A 为 stop 后 late observer；B 为已 claim owner。
- 同步 fence 方法：startup burst fence；`stop_event_loop()` future 完成作为停止 fence。
- 精确 oracle：A 路 session 仍存活时 `events.recv().now_or_never().is_none()`，表示 pending 而非 Closed；drop session 后 5s 内 recv 必须返回 `RecvErrorKind::Closed`。stop loop 不等于释放 Session 的强 sender。B 路 shutdown/drop 后顺序排空 evt-0..evt-599、evt-idle、publication-fence，随后 5s 内 recv Closed；两路均再核验 router 注册数为零。

### CASE-09：active prepared subscriber 是负控：保持有界，不启用隐式 bootstrap

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**I**；`prepared_session_test.rs` L1446-L1486，`active_prepared_resume_subscription_remains_bounded`。
- 配置输入时序：`prepared = prepare_resume_session(...with_event_buffer_capacity(1).with_permission_handler(PublicationFence))`；start 前保持 events=prepared.subscribe() 活跃；resume response 前发 startup burst + fence 并等 notify；完成 resume 与 skills reload → join start → **先 recv Lagged(601)，再 recv publication-fence，两次读取均完成** → 才创建 late=session.subscribe() → 才发送 live(session.idle,true)。读取 fence 前禁止任何额外 publish（包括 live 或附加 fence）。
- observer 角色：active prepared observer；late session observer。
- 同步 fence 方法：startup burst fence；start join 完成；随后 timeout recv。
- 精确 oracle：prepared 首次 recv 为 `RecvErrorKind::Lagged`，`skipped()==BURST+1==601`（600 delta + idle 被末尾 fence 覆盖）；第二次 recv 必须为 publication-fence。完成两次读取后创建 late 并发 live，两者各收到 live；stop、drop session 后两者 Closed。提前发布 live 会覆盖 fence 并导致 skipped=602，必须判为夹具时序错误，不能接受为本卡 PASS。该负控对应 receiver_count()!=0 时不创建隐式 bootstrap。

### CASE-10：owner drop 不转交 backlog，后续 observer 只能看 live

- 状态：**NOT_RUN**
- 执行 seam / 固定参照：**U**；`subscription/tests.rs` L272-L291，`dropping_unpolled_bootstrap_owner_discards_backlog_without_transfer`。
- 配置输入时序：capacity 8；bootstrap publish `discarded`；`first=subscribe()` 后不 poll；`second=subscribe()`；drop first；`third=subscribe()`；随后 publish `live`。
- observer 角色：first 为未 poll owner；second/third 为后续普通 observer。
- 同步 fence 方法：U 夹具可断言内部 Disabled；公开 API 改写版只能用 `now_or_never()` 确认 second/third 无旧事件，不得声称读到私有状态。
- 精确 oracle：second 和 third 在 publish `live` 前均无事件；publish `live` 后二者都收到 `live`；`discarded` 不转交、不重放。

## 5. 业务幂等与 UI 完成分离

- 事件补发只服务 UI/审计观察，不应触发业务命令二次执行。业务 side effect 必须以业务 request id / message id / tool invocation id 做幂等键。
- UI 完成态不要只依赖 durable message log；`session.idle` 等 ephemeral 完成/空闲信号可能无法由 `get_messages` 补回，因此 resume 后首个 UI observer 必须及时订阅并 drain bootstrap。
- UI 展示完成、RPC 请求应答和真实业务完成必须分开。`session.send` RPC response（如 messageId）通常只是请求应答/受理证据，**不得视为任务或 side effect 已完成**；tool result/structured result 也只证明其契约范围的结果，FakeServer 返回值不是真实业务执行。业务完成需按业务契约校验关联幂等键、权威结果/持久化状态及必要的外部副作用确认。UI 完成以关联 event 序列和 idle 等观察信号为准；idle 不能独自证明真实业务成功。
- 如果 live 阶段出现 `Lagged(n)`，UI 只能声明“观察流缺口”，应触发 resync / 降级 / 提示，而不能假设业务已失败或自动重跑。

## 6. 内存积压预算与退出准则

### 6.1 预算公式

bootstrap 是无界 `VecDeque<SessionEvent>`；预算必须由业务 POC 约束，而不是宣称 SDK 内置上限。

建议每个 resume session 记录：

- `q_bootstrap`: 内部锁下一致快照的当前队列长度；从 resume/start 调用起覆盖 setup 积压。新增 test-only 仪表在实际 `publish` 入 bootstrap 时计 `enqueued`，在 owner 实际 pop 时计 `drained`，cleanup/abandon 清除时计 `discarded`；同一生命周期内 `q = enqueued - drained - discarded`，与锁下长度交叉校验。不得计入 live broadcast 副本、其他 observer 的 recv 或 wire 发送数。
- `state`: 同一快照内的 Unclaimed/Claimed/Disabled；采样时钟为单调时钟，采样周期 1s，并记录 claim、handoff、close/drop 转换。计数从 start 前初始化；只有实际 bootstrap 创建后才有该队列，不启用 bootstrap 的 prepared 负控记 N/A。
- `avg_event_bytes`: 当前队列事件序列化大小的估算均值，记录统计方法/分布；`bootstrap_bytes ≈ q_bootstrap * avg_event_bytes * overhead_factor`，factor 初始取 2.0。RSS 是进程级观察，仅能辅助校准估算，不能当作精确单队列字节。
- `catchup_rate = owner_bootstrap_pops_per_sec`，`produce_rate = bootstrap_enqueues_per_sec`，来自相邻内部快照的计数差与实际时间差；不包含 live/路由前丢失事件。相同窗口若 produce_rate >= catchup_rate 且仍 Claimed，队列不会因净 drain 而下降。

### 6.2 推荐验收阈值（可按产品调整）

以下为教学起点而非厂商推荐；选定阈值前须记录测试环境、事件大小分布及业务可接受降级方式。上述真实 q/state/计数要求新增内部 test-only 仪表及其补丁哈希，不是普通 SDK 指标；本次未实现或运行仪表。public SDK POC 仅有 wire/RSS 时须标 `estimated` / `unobservable`，不得签署精确队列预算 PASS。

- warning：单 session bootstrap 估算超过 96 MiB 或 `q_bootstrap > 12288`（示例按 4 KiB/event、overhead_factor=2.0 计算）。
- hard fail：单 session bootstrap 估算超过 128 MiB 或 `q_bootstrap > 16384`；或 **resume 返回成功的单调时间起 10s** 内仍未建立首个 drain task。阈值监测从 start 起覆盖 setup，不等返回才开始。
- 停滞 hard fail：只在 **state 为 Unclaimed/Claimed（仍处于 bootstrap catchup）且 q_bootstrap > 0** 时启用。首个满足条件的 1s 样本为窗口起点；相邻样本 q 下降算净积压进展，重置 30s 窗口；有 pop 但入队更多、q 未下降不算净进展。连续有效样本跨满 30s、q 从未下降才失败。q=0 清空窗口；handoff 到 Disabled、close/drop 后立即停表；再次进入有效条件才另起窗口。采样丢失/状态未知不能声称持续停滞或预算 PASS，记观测不足。关闭后残留已 claim 队列的释放/排空另由 CASE-08 检查，不把已关闭会话算活跃停滞。
- live 阶段：任何 `Lagged(n)` 都必须记录；若 UI 完成依赖该窗口内事件，则验收失败或进入 resync 流程。

### 6.3 退出准则

验收通过必须同时满足：

1. 将来执行时，CASE-01 至 CASE-10 及 A/B 分支均需相应 U/I 实际运行证据，按 §3.2 逐项留证；另附 POC/host/package 各自状态，不能由 unit/integration PASS 推导。当前所有卡保持 NOT_RUN；仅在有真实执行记录并独立复审后才能更新对应状态。
2. 对启用了 bootstrap 的正例，首 owner 的前缀完整、有序、无 duplicate；第二及以后 observer 不收到历史前缀但能收到 live。CASE-09 是不启用 bootstrap 的负控，必须按其 Lagged(601) oracle 单独判断，不能套用正例无损门。
3. setup failure、cancel、stop、drop 均无旧 backlog 泄漏到新生命周期。
4. 内存预算在预设阈值内；超过 warning 有告警，超过 hard fail 由 POC 控制器执行并留证停止/降级（不是 SDK 已有自动保护）。未获得真实 q/state 指标则精确预算门为 NOT_RUN/观测不足，不能 PASS；外部估算结果单列。
5. 所有 `Lagged(n)` 都进入 telemetry，并有 UI 降级/补偿策略。

## 7. 本手册未完成 / 未验证

- 本文是已复核的源码级验收设计，不是运行结果、厂商背书或生产安全认证；执行时仍需目标环境的独立验收。
- NOT_RUN：未执行上游测试，未编译 SDK，未连接真实 Copilot CLI/服务端。
- 未验证 crates / NuGet / npm 包发布状态；不声明正式版本可用。
- 未做吞吐、RSS、长连接断连重连、client-global router 溢出实测。
- 未做跨进程持久化恢复；该机制本身也不承诺该能力。
