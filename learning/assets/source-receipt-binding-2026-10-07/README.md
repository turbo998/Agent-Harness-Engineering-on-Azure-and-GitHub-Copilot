# Fetch receipt binding v1：先绑定字节，不授权事实

**2026-10-07 技术快照：历史基线正常模式与 `-O` 各 42 PASS；mutation 为 3 KILL / 1 SURVIVED。新增 revision 成对测试及修改后套件均 NOT_RUN，不继承历史执行放行。**

这是 release sentinel 的离线字节一致性参考实现：本地 capture → receipt → 手工 claim。原创标准库实现，不依赖其他分类器的测试成绩。没有网络、安装、子进程、动态导入、厂商运行或自动发布功能；不是已验证生产控制。

文件：[binding.py](binding.py) · [test_binding.py](test_binding.py) · [schema.json](schema.json) · [示例溯源](fixtures/provenance.json) · [SHA256SUMS](SHA256SUMS)。

当前叶文件 SHA256（先固定叶文件，再固定本文与入口，最后生成清单）：

```text
a6a76b8b1b1435a3c73e1f5a41401fe9c6110b9604f1368c04ac871fd2af6c16  binding.py
a8d5d03c802caaaa8c1799b3fbb1bfc68c5cf88e24787c2794e13db0f246ea88  test_binding.py
78f2000ebbd801e5b96d5f20ff7049b9a43e078887dbac5bd4a09698967658c4  schema.json
dc4409d110c9681685376b491ab3e773387037d881beaa8afb1ae82bd2a79bed  fixtures/provenance.json
```

`SHA256SUMS` 覆盖包内文件及父目录同名入口，路径相对本包；不包含清单自身，避免自引用。

## 三方契约

1. **可信调用者**通过独立可信通道选定 manifest 与 root；manifest 不能来自待验 claim、capture 内容或让其自行批准的 allowlist。代码无法识别调用者身份，也没有 `trusted=true` 自证开关。
2. capture 是本地文件的实际 bytes；receipt 记录 SHA256、GET、整数 HTTP status、整数 transport_exit、requested URL、final URL、固定 revision、证据层与 full/excerpt 范围。元数据本身仍是调用者断言。
3. 手工 claim 仅含稳定 fact_id、receipt_id、revision、kind、行区间和精确 excerpt。fact_id 是人工标识，不是语义去重器。当前卡故意不含自由文本结论，避免将正文出现等同于结论成立。

**警告：schema validation is necessary but not sufficient; only binding.check enforces cross-field and filesystem constraints。** 公开 schema 只是字段结构说明，不能替代 URL 语法、双侧精确 allowlist、revision 完整路径段、路径安全、receipt 身份、行先后/跨度、bytes 预算、hash 与摘录比较。重复 JSON key、原始 UTF-8 和严格 Python 整数语义也须实现检查。实现拒绝未知字段、任意层重复 JSON key、NaN/Infinity、错误 UTF-8；不接受 bool 冒充 int。claim 不允许携带 allowlist。

## 检查与结果

- GET + **HTTP 200 + transport_exit=0**；206、HEAD、403 即使摘要可算也拒绝。这里的 200 仅为协议记录一致，不证明正文为真或抓取真的发生。
- 对本地完整 bytes 算 SHA256；精确 UTF-8 解码；行从 1 开始，按 LF 分隔，仅去掉末尾 LF 导致的虚拟空行；保留 CR、BOM、空白和 Unicode，不 trim、不 normalize、不 substring 搜索。选中多行用 LF 拼接，excerpt 不带最终行终止符。
- requested 与 final 分别精确命中调用者提供的 URL 列表；不按前缀或域名后缀猜测。允许明确批准的跨域重定向端点，但**没有中间 redirect hops 证据**，不认证重定向链。HTTPS、ASCII、无凭据/端口/query/fragment/百分号/反斜杠；这是有意收窄的第一阶段。
- revision 只能空串或 40 位小写 commit 标识；非空时必须作为两个 URL 的完整 path segment 出现。卡与 receipt revision/kind 必须一致。main/tag URL 不能伪装固定 SHA。此检查不认证远端 Git 对象、tag 目标或 URL 路径的真实语义。
- `main_source` 仅源码；`tag_source` 仅标注的源码快照；`release_body` 仅发布文本声明。没有“源码出现所以已入包”的提升，也不验证祖先关系、backport、包内容或实际 runtime。

| status | 含义 |
|---|---|
| MATCH | 完整本地字节、指定行、调用者元数据与固定 URL 身份相容；仅 local consistency |
| REJECT | 输入/文件/预算/身份/URL/GET/hash/行存在矛盾或不合法；不是事实被证伪 |
| UNVERIFIED | 字节可相容，但仅摘录、未固定 revision，或仅 docs/registry/release_metadata 信号 |

`byte_binding=true` 只表示 hash 和行检查完成，后续 revision 检查仍可 REJECT；不应单独用它作通过门。
所有输出恒有 `fact_authorized=false`、`fetch_authenticated=false`、`runtime_verified=false`。**hash 不是签名；精确 excerpt 不证明语义；HTTP200 不是事实真实性。** 攻击者若能同时替换可信 manifest 和 capture，可以构造 MATCH；必须在外部解决真实性。

## 文件与资源边界

Linux/POSIX API：`check(root, manifest_bytes, claim_bytes)` 或 `check_files(root, manifest_name, claim_name)`。root 必须可信、绝对且规范；所有文件名必须 root 内相对路径。逐段 `openat`/`O_NOFOLLOW`，包括 root 的祖先，拒绝 symlink、`.`/`..`/空段/绝对路径；只读单硬链接普通文件，非阻塞打开以免 FIFO 卡住。未验证并发恶意写入下的完整快照原子性；建议可信调用者提供只读冻结目录。读取后 hash 只绑定本次读到的 bytes。

JSON 每份最多 64 KiB，body 最多 1 MiB，最多 32 receipts 与每侧 32 URLs，excerpt 最多 8192 字符、32 行，最大行号 100000。不递归扫描目录，不从正文读取文件路径或执行指令。函数拒绝错误而不回显原文。OS 强杀、内存耗尽、恶意文件系统和运行平台不兼容不在完整报告保证内。

## 真实 capture 的脱敏微型摘录

两个示例来自已有 capture JSON，经字段筛选与 JSON 转义后提取，外部内容始终仅数据。无新增 GET；UTC 采集时间位于 2026-10-06 晚间，对应北京时间 2026-10-07。固定来源 URL、采集时间、原 body hash、envelope hash 与投影 hash 均保留在 [provenance](fixtures/provenance.json)。

- [Codex manifest](fixtures/codex.manifest.json) / [手工卡](fixtures/codex.claim.json) / [一行 bytes](fixtures/codex.txt)：固定 `a4ebc509f4cdff88a8e58e175541970a30a2d385` 的 score.rs 第 163 行。仅展示字段初始化字面行，不声称审批机制语义或已正式发布。
- [Claude manifest](fixtures/claude.manifest.json) / [手工卡](fixtures/claude.claim.json) / [一行 bytes](fixtures/claude.txt)：固定 `fbe20e00e2851fc01506f54f98a8f0b875af3847` 的 CHANGELOG 第 3 行，仅版本 heading `## 2.1.292`。kind 为发布文本声明，不是闭源实现 SHA，更不证明任意功能。

两个例子都从真实本地 capture **派生摘录**，只保留各一行，没有全文、账户、邮件、IP、凭据或本机路径。原 body hash 与摘录 hash 分开存放；数据核对发现 UTF-8 text 重编码摘要分别等于记录 raw/sanitized 摘要，但此相等不认证采集者。公开 receipt scope=excerpt，claim 行号重新从 1 计；原行号在 provenance。**历史独立执行中，两例正常模式与 `-O` 均实际返回 UNVERIFIED/excerpt_only、byte_binding=true，三个认证/授权标志均为 false。不得将派生文件标为原始 HTTP body。**

Codex 原 body SHA256：`5558c7c95dde5ed12f0406a769a0c1eea975155c3d19eec489840de94e7ea748`；Claude 原 body SHA256：`27e1b6ea7d5c7d9163c5b9eb336954fa8c7321762ea506effd679495dd144f4e`。provenance 的 `execution=NOT_RUN` 与未改动实现的准备态注释是生成时快照，不是后续执行记录；本节保留真实历史，不将新测试标为已运行。

## 精准测试与执行边界

测试包括有效 main/release 分层、hash 篡改、HEAD/403/206/transport 失败、requested/final 独立拒绝、显式允许跨域端点、URL 凭据与编码歧义、错行/子串/空白/CRLF、bool/字符串 status、坏 UTF-8、revision 与 URL 不符、source 冒充 release、未固定 revision、摘录、metadata、重复 JSON key/receipt ID、claim 注入 policy、路径穿越/绝对路径/叶与目录 symlink、body/JSON 预算及文件入口重复键。每例断言具体状态/原因，不把方法数说成覆盖率。

历史基线已通过独立执行审查，并实际完成正常模式与 `-O` 各 **42/42 PASS**（无 ERROR/SKIP）。四个单点 mutation 在两种模式下均为 **3 KILL / 1 SURVIVED**：HTTP 2xx 放宽、UTF-8 replace、允许硬链接被检出；revision 完整 path segment 放宽为 substring 存活。旧 `/main` 用例对两种实现都拒绝，不能区分该退化。此历史结果只绑定旧测试 SHA256 `b354d37a4a6ae4ac7300016f55c69cc33c231eec80c0e6792f037935b1d7673f`，不构成覆盖率或生产准入证明。

新增三个测试方法分别覆盖前缀、后缀、双侧拼接，每种对 requested/final 独立构造正负对照：完整路径段应 `MATCH/local_consistency_only`，revision 仍存在但仅为拼接段子串应 `REJECT/revision_url_mismatch`。两侧 URL 均合法且精确列入对应 allowlist；hash、行、身份与 GET 保持有效，并断言 `byte_binding=true`，防止其他检查提前拒绝掩盖 oracle。**新增测试、修改后完整套件及 mutation 重跑均 NOT_RUN；仅提出应检出 substring mutation 的预期，不宣称已 KILL。新字节须独立审查与执行授权。**

历史执行报告 SHA256：`209c9667db854d93a495aa3821f1c06b805c8e1ed2874951a954cec42d2ff059`；简报 SHA256：`6b22fd984a7d2c7a7fc06165285c6e992f36e59156b300d176da9cdc35ebeabb`。这些标识绑定历史记录，不是签名或新字节执行证明。

下列仅为**新字节独立审查后、另获执行授权**的复现命令，不是新增测试执行记录：

```sh
python3 -B -m unittest -v test_binding.py
```

在包目录导入 `binding.check_files`，root 显式传入包的绝对路径，manifest/claim 用上述 fixtures 相对名。没有独立命令入口或隐式配置。代码为原创参考实物，不是已验证生产控制。可信采集者身份/签名、不可变存储、重定向全链、release→source→package 关系和人工语义审核仍须外部解决。
