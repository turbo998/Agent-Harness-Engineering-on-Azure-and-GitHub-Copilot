# Fetch receipt binding：离线字节一致性（2026-10-07）

**2026-10-07 技术快照：历史基线正常模式与 `-O` 各 42 PASS，mutation 为 3 KILL / 1 SURVIVED；新增 revision 成对测试与修改后套件均 NOT_RUN。历史执行放行不自动覆盖新字节。**

原创离线标准库参考实现，将本地 capture bytes、手工 claim 卡与可信调用者 manifest 绑定：GET/HTTP 200/transport_exit=0、SHA256、精确 UTF-8 行、requested/final 双侧精确 allowlist、固定 revision 完整路径段及 source/release 证据分层。结果仅 `MATCH / REJECT / UNVERIFIED`；MATCH 只表示本地一致性，不授权事实、不认证抓取或 runtime。

- [契约、历史结果与来源 hash](source-receipt-binding-2026-10-07/README.md)
- [原创实现（字节未改）](source-receipt-binding-2026-10-07/binding.py)
- [精准测试（历史 42 PASS；新增三方法 NOT_RUN）](source-receipt-binding-2026-10-07/test_binding.py)
- [JSON Schema（结构校验不足以完成判定）](source-receipt-binding-2026-10-07/schema.json)
- [Codex / Claude 真实微型摘录与溯源](source-receipt-binding-2026-10-07/fixtures/provenance.json)
- [字节 SHA256 清单](source-receipt-binding-2026-10-07/SHA256SUMS)

历史存活项是 revision 完整路径段退化为 substring。新增前缀、后缀、双侧拼接的 requested/final 正负对照：两侧 URL 均合法且精确命中 allowlist，负例应仅在 revision 检查拒绝。尚未执行新测试或重跑 mutation，不能宣称存活项已经 KILL；新字节须独立审查与执行授权。

两个公开示例来自真实 capture 的单行派生摘录，并非完整 HTTP body；历史正常模式与 `-O` 均实际返回 `UNVERIFIED/excerpt_only`、`byte_binding=true`，三个认证/授权标志均为 false。provenance 的 `execution=NOT_RUN` 和实现准备态注释是生成时快照，不否定后续实跑。来源 URL、原始/投影/envelope hash 保留不变。

**schema validation is necessary but not sufficient**：跨字段、严格 URL/路径/整数、行跨度、文件系统、hash 与摘录约束仍须 `binding.check`。哈希不是签名，200 不是事实真实性，精确 excerpt 不证明语义；manifest/capture 真实性仍依赖外部可信通道，未认证重定向全链、Git/tag/package 或 runtime。历史 PASS 不等于生产准入或自动发布授权。

历史执行报告 SHA256：`209c9667db854d93a495aa3821f1c06b805c8e1ed2874951a954cec42d2ff059`。当前叶文件 hash 见 README；清单覆盖包内文件及本入口，不包含清单自身。
