# 模型显示与错误观察契约（静态计划；NOT_RUN）

本文件补充十卡，不增加案例，不提供上游启动器，不解除 NO_GO。产品模型、变异与所有 wire 观察仍 NOT_RUN；本版 schema 不容纳实测输出。

## 固定入口及依赖前提

- 固定 ADK 源码提交见 [sources.md](sources.md)，不是浮动发行版本。
- C01/C02/C05/C06 模型全名：`google.adk.auth.auth_credential.AuthCredential`。
- 计划构造 API：`AuthCredential.model_validate(fixture.input)`，默认参数，无自定义 validator、context 或额外预清洗；每次使用输入的独立深拷贝并保留构造前快照。
- 这是 Pydantic v2 API 契约。**尚无获准、经过验证的模型依赖锁**；未来执行前必须记录并冻结 Python、pydantic、pydantic-core、ADK 及传递依赖精确版本/包 hash。缺锁或不同版本只能标 BLOCKED，不能凭本文声称已复现；本次不得安装或导入 ADK/Pydantic 模型来补这一缺口。
- 仅离线 JSON/schema 工具使用已有 `jsonschema`；实际版本记录在 [schema-validation.json](schema-validation.json)。它不证明任何模型依赖兼容性。

## C01/C02/C05：两个显示观察，两个结构观察

1. 分别取得 `repr(model)` 与 `str(model)`；对**每一个**字符串逐项要求 `fixture.repr_hidden` 子串不出现、`fixture.repr_visible` 子串出现。空列表仅表示没有该类断言，不表示整段显示被证明安全。不能将 repr 结果复用为 str 观察，也不比较易随版本变化的完整格式。
2. C01 隐藏 API canary；C02 隐藏已列 OAuth 敏感 canary、保留 clientId；C05 隐藏两个 extra **值**而显示 extra 键、`<redacted>` 与公开 clientId。具体子串均以 fixtures 为唯一静态 oracle。
3. 内部视图：`model.model_dump(exclude_none=True, by_alias=True, mode="json")` 与 `fixture.expected_dump` 作完整结构相等比对；保留类型、键集合、列表次序。显示隐藏不能替代此检查。
4. 出站 helper 计划入口：`google.adk.auth.auth_credential._redact_credential_secrets`，输入为内部 dump 的独立深拷贝；结果与 `fixture.expected_outbound` 完整结构相等比对。前后比对输入快照及内部 dump；不宣称所有输出节点都是深拷贝。
5. 观察者不能用被测 helper 生成 expected；网络消费者另行观察原始 HTTP/SSE/WS/session/eval，不以本地 helper 结果替代。

## C06：构造失败契约

`fixture.input` 的 `apiKey` 是 `["SYNTHETIC_BAD_API"]`。计划要求：

- 构造抛出 `pydantic.ValidationError`；不接受成功构造或任意其他异常作为通过。
- `str(error)` 不包含 canary，也不包含 `input_value=` 或 `input_type=`；应包含位置 `apiKey` 和类型码 `string_type`。不固定错误 URL、版本号、完整英文消息或空白格式。
- 分别调用默认参数 `error.errors()` 与 `error.json()`，后者经独立 `json.loads` 解码。两路都应只有一条错误：`type == "string_type"`、`input == ["SYNTHETIC_BAD_API"]`；前者 `loc == ("apiKey",)`，后者 `loc == ["apiKey"]`。不将 tuple/list 表示差异误判为清洗。
- 此处刻意要求默认结构化 input 保留 canary，是 hide_input_in_errors 的负控，不是生产错误脱敏承诺。若版本改变行为，记录差异并复审，不悄悄更新 oracle。
- 构造失败意味着没有成功模型的 repr/dump 或 credential outbound oracle；HTTP 422、SSE 错误与 WS close 不是由此列表自动触发/证明的，仍需各自可达性与独立传输计划。

以上为待验规范，**没有实际模型 repr、dump、错误原文或云端/网络执行证据**。只能公开合成输入、规范、hash 与 schema 机械结果，不能公开真实凭据或客户载荷。
