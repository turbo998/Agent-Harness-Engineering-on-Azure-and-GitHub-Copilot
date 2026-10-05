# Release sentinel：原创离线证据结构分类器 v3

**本地离线验证状态：PASS。** 在 Python 3.11.15、strict UTF-8 输出下，本版已实际通过 45 项 unittest、完整 12 条 fixtures 的文件/stdin CLI，以及独立 Unicode 错误协议检查；四个指定 mutation 均触发目标断言失败。结果只适用于本包原创结构分类器，不是厂商产品或生产功能验证；厂商产品运行仍为 **NOT_RUN**。源文件注释及 `MUTATION_DESIGNS_NOT_RUN` 名称保留作者准备阶段状态，不代表本次验证未执行，不继承旧版本运行结果。该版本仅修复 JSON 输出对 Unicode surrogate 的转义，输入 schema 与分类规则保持 v2 兼容；因此 `schema_version` 仍为 `release-evidence-contract-2026-10-06-v2`。

文件：[classifier.py](classifier.py) · [test_classifier.py](test_classifier.py) · [fixtures.json](fixtures.json) · [SHA256SUMS](SHA256SUMS)。

## 用途与可信边界

这是原创的**结构分类器，不是真实事实认证器**。它不联网、不读取远端源码、不运行厂商产品，不认证签名、采集者身份、tag 实际目标、文件存在或路径与组件的真实对应关系。`content_verified`、`incorporation`、`runtime.observed`、`synthetic` 都是调用方断言。

`ok=true` 仅表示整份输入通过闭合契约；`evidence_eligible=true` 仅表示符合结构分桶规则，**不表示事实为真、功能获准宣称、发布已完成或客户环境可用**。完整但伪造的 SHA、路径和断言也可能通过。本工具不能单独触发发布、客户通告或安全决策；真实用途需要可信采集与人工内容核验。

全部 fixtures，包括 SHA、tag、路径、时间和事实断言，均为 **synthetic**，不是厂商证据。合成 runtime 使用本地 fixture 身份，`observed=true` 是虚构输入，不是执行记录。

## 闭合输入 schema

顶层恰好为：

```json
{"schema_version":"release-evidence-contract-2026-10-06-v2","records":[...]}
```

上例的 `...` 仅表示记录占位；完整可解析输入见 [fixtures.json](fixtures.json)。`records` 必须是非空数组。任何错误都会使整文 `ok=false, records=[]`，不返回部分成功。顶层、record、runtime 均拒绝未知字段；CLI 在任意对象层拒绝重复 key、NaN 和 Infinity。

每个 record 必须包含下列全部字段：

| 字段 | 约束 |
|---|---|
| repo / component | 下列固定白名单，不自动归一化 |
| fact_id / tag | 空串或 `[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}`；区分大小写 |
| source_path | 空串或规范仓库相对 ASCII 路径，仅字母数字及 `_ . / -`；禁止绝对路径、空段、`.`/`..` 段、反斜杠和 URL |
| commit | 空串或恰好 40 位小写十六进制 SHA；表示源快照或 tag-target，不表示功能起源 commit、PR 或 backport 名 |
| channel | `main/stable/latest/alpha/next/registry/release/docs` |
| time | 收窄 RFC3339：`YYYY-MM-DDTHH:MM:SS[.1至6位小数](Z或±HH:MM)`；真实日历与时钟，offset 小时 00–23、分钟 00–59；拒绝无时区、date-only、小写 t/z、闰秒及 `-00:00` |
| evidencekind | `registry/release_metadata/release_body/main_source/tag_source/runtime` |
| http_status | 整数 100–599，明确排除 bool、浮点和字符串 |
| content_verified | 严格 boolean，1/0 不接受；仅调用方断言 |
| incorporation | 字符串 `TRUE/FALSE/UNKNOWN`；仅调用方断言 |
| runtime | 非 runtime kind 必须为 null；runtime kind 必须为下述闭合对象 |

repo/component 白名单不代表经认证的官方组件划分：

- `openai/codex`：`codex-rs`、`code-mode-runtime`、`npm-package`。
- `anthropics/claude-code`：`cli`、`npm-package`、`changelog`。
- `microsoft/agent-framework`：`python`、`dotnet`、`repo`。
- `local/release-sentinel`：`fixture-runtime`。

### 类型专属约束

- `main_source`：非空 SHA、fact_id、source_path；channel=main，tag 为空。
- `tag_source`：非空 SHA、fact_id、source_path、tag；channel 不得为 main。
- `runtime`：非空 SHA、fact_id、source_path，且具有明确局部范围。
- `release_body`：身份不完整仍可保留声明，但不 eligible。字段不能省略，缺失身份用空串；非空非法身份仍拒绝。只有完整 SHA+path+fact_id+tag、非 main 且满足内容断言条件才 eligible。
- registry/metadata 永不 eligible；HTTP 200、同日版本、HEAD/title 和 main 源码都不能据此升级为功能已发布。

runtime 恰好包含 `observed`、`synthetic` 两个 boolean，以及 `component`、`scope`、`environment`、`build_id`、`test_run_id`。scope 仅为 `local` 或 `build`；environment/build_id/test_run_id 为非空上述 token；component 必须等于 record.component。完整 runtime 原样保留，不外推到其他组件、构建、环境或全球可用。

`synthetic=true` 必须使用本地 fixture 身份，本地 fixture runtime 也必须 synthetic=true。厂商 runtime 即使自陈 synthetic=false，仍不受本工具认证。正常非 ASCII Unicode 是合法 JSON，但不因此突破本 schema 的 ASCII 标识符、枚举和闭合字段限制。

### 批次身份与冲突

1. 同 `(repo, tag)` 的非空快照 SHA 必须一致，跨 component、fact 和 channel 也相同。
2. 同 `(repo, component, fact_id, tag)` 的已知 commit/path 必须一致，TRUE/FALSE 不可并存；无 tag 时额外按 commit 隔离不同快照。
3. UNKNOWN 可与 TRUE/FALSE 并存，但每行独立分类，不自动升级 UNKNOWN。不同 fact_id 不作语义去重；同 tag 的不同事实可以一真一假，但 tag-target SHA 仍一致。
4. 同 repo/component/fact/commit/tag 加 scope/environment/build_id/test_run_id 的 runtime，observed 不可互相矛盾。
5. 冲突分别产生 `conflicting_source`、`conflicting_fact`、`conflicting_runtime` 并拒绝整文。

## 分类与错误协议

| 分类 | evidence_eligible |
|---|---|
| registry signal / release metadata | false |
| main-only | false，仅 main 源码断言 |
| release-body-declaration | false，未满足完整固定身份与内容断言 |
| release-body-assertion | true，仅 200+verified+TRUE+完整 release 身份 |
| tag-source-assertion | true，仅 200+verified+TRUE，身份另经结构校验 |
| tag-source-absent-assertion | false，仅调用方 FALSE，不认证真实缺席 |
| tag-source-unconfirmed | false |
| runtime-scoped | true，仅 200+verified+TRUE+observed 与完整局部范围 |
| runtime-unconfirmed | false |

每行保留 repo/component/fact_id/source_path/commit/tag/channel/time/incorporation，并带有 `eligibility_basis`、`source_ref`、`runtime_scope` 和 runtime。`source_ref=repo@commit:source_path` 只是供外部核验的定位引用；不输出 `feature_claim_allowed`。

CLI 支持 stdin 或一个 UTF-8 JSON 文件。有效整文 exit 0；schema、JSON、重复键、文件读取/编码和用法错误 exit 2，并向 stdout 输出完整 JSON，stderr 为空。输入读取/解析异常使用 `input_error`。输出统一 `ensure_ascii=True`，使重复键错误中出现的孤立 surrogate 也作为 JSON 转义输出，而不在 UTF-8 写出时再次失败。未承诺 OS 强杀、资源耗尽或输出管道故障仍能生成 JSON。

## 三厂商场景、QA 与 POC 落点

以下均为合成场景，不是产品版本结论：

| 场景 | 分类边界 | QA / POC 落点 |
|---|---|---|
| OpenAI Codex：main 变化、stable 缺席断言、alpha registry 信号 | main-only 与 registry signal 不能替代固定 tag 证据；不同事实共享 tag-target | QA 分开检查 main/tag/package；POC 固定组件、源码快照与本地构建，不从版本号推断功能 |
| Anthropic Claude Code：next registry、previous changelog、next 无正文 | registry 只表示信号；完整固定正文仅是 assertion；缺正文不 eligible | QA 核对 tag、正文与事实定位；POC 明确实际安装包和环境，不能把旧正文移用于 next |
| Microsoft Agent Framework：main Python 源码、旧 release metadata、本地合成 runtime | source-only 不等于 release/runtime；本地 fixture 不能冒充厂商 runtime | QA 分开 Python/.NET 与 source/runtime；POC 另行记录实际 build、environment、test_run_id 与 scope |

推荐接入点是可信采集之后、人工语义复核之前的结构检查。输入不得包含客户 secret、访问令牌或真实敏感环境信息；environment 等使用非敏感标识。本示例测试只用标准库、本地合成数据和本地子进程，**无需安装依赖、网络或客户 secret**。

## 本地验证结果与复现

本次实测使用 Python 3.11.15，强制 `PYTHONIOENCODING=utf-8:strict`。只执行本地标准库代码和合成数据，没有运行供应商产品，也没有网络请求。

| 验证对象 | 实测结果 | 边界 |
|---|---|---|
| exact unittest | 45/45 PASS，exit 0，无 skip | 包含完整 fixtures API/CLI 和 Unicode 回归；方法数不是覆盖率 |
| 普通 unittest discovery | 45/45 PASS，exit 0 | 与下列公开命令一致；不是新增 45 个不同测试 |
| 完整 fixtures，文件与 stdin CLI | 两条路径均 exit 0、ok=true、12 records、stderr 为空 | 分类、身份及 scope 符合预期；只有 index 5/9/11 为 evidence_eligible=true |
| 独立错误协议负控 | surrogate 重复 key 的顶层/stdin、嵌套/stdin、文件三例及 ASCII 对照，共 4/4 PASS | 均 exit 2、完整可解析错误 JSON、空 stderr；此前的截断输出问题未复现 |
| M1 registry 提升 | 目标断言失败，KILL | 只变更 registry 分支，不包含 metadata |
| M2 移除 bool 类型排除 | 目标断言失败，KILL | 类型错误码契约 kill；范围校验仍拒绝 bool，不是不安全放行 kill |
| M3 tag 映射加入 channel | 目标断言失败，KILL | 不同 fact 跨 channel 冲突 SHA 被错误接受；fact guard 未删除 |
| M4 runtime 分类改为正文断言 | 目标断言失败，KILL | 仅分类标签变异，不证明 scope/component guard 被移除 |

四个 mutation 均在独立临时副本使用原定义的唯一字符串替换，每个副本实际执行完整 45 项测试。均由指定断言失败判定，没有语法、导入或超时异常冒充 kill。原始 classifier、tests、fixtures 字节未因验证而改变。

[test_classifier.py](test_classifier.py) 包含 API 与真实 CLI 路径，普通 unittest discovery 覆盖完整 fixtures。新增一个 Unicode 回归方法，在 stdin/file 两条路径上检查顶层、record 嵌套及 runtime 嵌套的 escaped surrogate 重复键，要求 exit 2、完整错误 JSON、空 stderr；同时检查正常 Unicode 与转义形式按原 schema 一致接受或拒绝，强制 strict UTF-8 输出。

四个 mutation 设计保留于 `MUTATION_DESIGNS_NOT_RUN`，不会被普通测试自动应用：M1 仅 registry 提升；M2 仅删除 bool 排除，测试错误码契约且不宣称绕过范围检查；M3 仅给 tag 映射加入 channel；M4 仅把 runtime 成功分类改成正文断言。只有对应预期断言失败才算 kill，语法/导入/超时等故障不算。

将五个文件放入自选目录，再运行以下相对路径命令复现。执行日期、Python 版本和平台变化时，应以自己的实际输出为准；上述结果不承诺所有环境或所有恶意输入均已覆盖：

```bash
cd "${SENTINEL_DIR:?请先设置为存放五个文件的自选目录}"
sha256sum -c SHA256SUMS
export PYTHONIOENCODING=utf-8:strict
python3 -B -m unittest -v test_classifier.py
python3 -B -m unittest discover -v -p 'test_classifier.py'
python3 -B classifier.py fixtures.json
python3 -B classifier.py < fixtures.json
```

完整 fixtures 的预期结果由测试定义，CLI 示例不替代 unittest。先固定 classifier、tests、fixtures，再固定本文，最后生成 SHA256SUMS；清单不包含自身。哈希仅检测文件变化，不认证发布者或输入事实。
