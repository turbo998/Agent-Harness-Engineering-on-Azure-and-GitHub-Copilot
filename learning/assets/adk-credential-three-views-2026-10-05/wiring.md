# 出站接线静态证据：成功路径不代表全部出口

固定提交见[来源](sources.md)。以下为完整固定文件中人工定位的调用链，不是运行时调用栈。所有传输观察状态均为 **NOT_RUN**。

## 成功路径

| 出口 | 静态调用链与行号 | 独立观察层 / 未证明内容 |
|---|---|---|
| HTTP `POST /run` | api_server.py:1964–2008 `run_agent → worker → runner.run_async → public_event`；2031–2043 `event.model_dump(exclude_none=True, by_alias=True, mode="json") → _redact_credential_secrets → JSONResponse` | 客户端HTTP响应体；仅正常事件数组有此接线。2033的events调试日志在出站helper之前，不能据此保证任意dict内容的日志安全。 |
| SSE `POST /run_sse` 正常事件 | api_server.py:2051–2052入口；2102–2145 `event_generator → _produce_events → runner.run_async → event_queue`；2150–2184消费队列，可能拆content/artifact两事件；`public_event → model_dump → redact → pydantic_core.to_json → data帧yield`；2235–2238 `StreamingResponse` | SSE消费者逐帧解析，覆盖原事件及拆分后两帧；不能只查helper返回值或第一帧。 |
| WS `/run_live` 正常文本 | api_server.py:2240–2241入口；2300–2349 `forward_events → runner.run_live → public_event → model_dump → redact → to_json.decode → websocket.send_text`；2361–2371任务调度及异常重新抛出 | 独立WebSocket消费者记录每个文本帧；这条链不覆盖close原因、其他ASGI错误或自定义路由。 |
| session GET / LIST | api_server.py:1574–1588 `get_session → SessionService.get_session → _redacted_session_response`；1590–1606 `list_sessions → SessionService.list_sessions → 过滤eval session → helper` | 每个路由分别观察HTTP body；LIST过滤和单session序列化不能互相代替。 |
| session CREATE | api_server.py:1608–1629旧带ID POST；1631–1665新POST，含空请求分支1641–1643、状态/事件恢复分支；都调用 `_redacted_session_response` | 单独覆盖旧/新/空请求/恢复事件响应，不宣称真实持久化加密。 |
| session PATCH | api_server.py:1675–1724 `update_session → get_session → Event(state_delta) → append_event → _redacted_session_response` | HTTP响应与服务内部状态分开观察；应保留内部凭据，不应把删除数据库字段当成脱敏成功。 |
| session共用出口 | api_server.py:633–654 `public_session → model_dump(exclude_none=True, by_alias=True, mode="json") → redact → JSONResponse`；list分支逐项处理 | state及events中的已知载体可被后续递归定位；不能仅因为存在helper就宣称所有session出口/错误安全。 |
| eval case GET（两个路径） | dev_server.py:1238–1265 `/dev/apps/{app_name}/eval-sets/{eval_set_id}/eval-cases/{eval_case_id}` 与旧 `/dev/apps/{app_name}/eval_sets/{eval_set_id}/evals/{eval_case_id}` → `get_eval → eval_sets_manager.get_eval_case → model_dump → redact → JSONResponse` | 两个URL各自HTTP消费者观察，缺失case的404是另一路径。 |
| eval result GET 新路径 | dev_server.py:1433–1455 `/dev/apps/{app_name}/eval-results/{eval_result_id}` → manager → `EvalResult(**eval_set_result.model_dump()) → eval_result.model_dump(alias/json) → redact → JSONResponse` | EvalResult转换也应纳入观察，不能把manager对象当实际响应。 |
| eval result GET legacy | dev_server.py:1115–1139 `/dev/apps/{app_name}/eval_results/{eval_result_id}` → manager → `eval_set_result.model_dump(alias/json) → redact → JSONResponse` | 与新EvalResult投影不同；独立观察。eval执行、列表、trace下载等未由这些GET接线证明。 |

`events/_internal_metadata.py:126–157`：`public_event`仅过滤custom_metadata内部键，可能原样返回对象；`public_session`映射events，必要时model_copy。两者不是凭据sanitizer，也不是保证无共享引用的深拷贝。

## 必须分开的错误与旁路

| 出口/位置 | 静态看到的行为 | 验收要求与结论边界 |
|---|---|---|
| HTTP异常 | api_server.py:2007–2008将SessionNotFoundError的`str(e)`放HTTP detail；SSE入口2080–2081将RunConfig ValidationError转422 detail。dev_server.py:1140–1143、1456–1459的eval错误也用`str(ve)`。 | 这些语句未经过credential helper。必须分别抓HTTP错误响应；不得推广credential基类的hide_input_in_errors到RunConfig或任意异常。此处不证明真实秘密可达。 |
| SSE错误帧 | api_server.py:2204–2227：`original_exc → str(original_exc)`同时进入error/error_message；DEBUG时加入格式化stacktrace；直接`json.dumps → yield data`，不经过redact。 | 独立SSE消费者观察错误帧与DEBUG开/关；用合成异常canary。正常帧已脱敏不能推导错误帧安全；有旁路不等于已实证漏洞。 |
| WS close reason | api_server.py:2375–2383：异常logger/traceback后 `websocket.close(code=1011, reason=str(e)[:123])`，未经过redact。 | 独立消费者记录关闭码和reason；长度截断不是脱敏。源码按字符切片，不能当成严格UTF-8字节限长保证。未实际触发。 |
| WS入站验证日志 | api_server.py:2351–2358 `receive_text → LiveRequest.model_validate_json → logger.error(ve)`。 | 这是入站失败日志，不是正常出站文本helper；日志接收器需独立观察。 |
| HTTP/events日志 | api_server.py:2033直接打印events；SSE正常事件2181–2182在脱敏后记录sse_event；错误日志2210/2376走另一条路。 | 分开model repr、任意业务dict、错误字符串与日志后端；仅凭凭据模型repr不能声称全日志安全。 |

## helper输入边界（auth_credential.py）

1. **模型显示**：77–103 `extra="allow"`与extra repr值替换；声明的`repr=False`字段不影响dump。70–76描述错误显示保护，不是结构化`errors()/json()`递归过滤承诺。结构化错误input默认可能留有原值，须独立表征。
2. **已知载体内部的递归删键**：367–377对dict/list递归删除精确`_CREDENTIAL_SECRET_KEYS`，不区分子字段业务语义。不是整个payload无条件同名删除；载体内部同名业务字段也可能被删，客户需定义数据契约。
3. **普通对象递归寻找载体**：395–401先识别authType/auth_type已知值（字符串/枚举）；451–454处理普通dict/list，未知标量原样返回。字符串化JSON不解析。
4. **重要例外：args浅拷贝**：403–418在`name=adk_request_credential`分支只改`args.authConfig/auth_config`，不对args其他字段再递归；C08特设`args.other.authType=apiKey`的canary保留负控。因此“全局查找所有已知carrier”也不准确。
5. **附加载体**：response、requestedAuthConfigs与raw/exchanged的指定子树用全键递归；其他siblings通常走载体查找。控制流按分支顺序提前返回，多类carrier并存应另设组合用例，十卡不证明组合完备性。
6. **非变更不等于全深拷贝**：正常JSON树的返回投影不写原输入；args浅拷贝可能保留共享子对象，任意非JSON对象可原样返回。真实SessionService存储、加密、OAuth、LLM及路由均未运行。

## 交付到独立harness的最小要求

[→harness](README.md#harness)：禁止把本文件的静态“已接线”换成“已覆盖”。至少分别提供model显示、内部dump、helper结构、HTTP正常/错误、SSE正常/错误、WS文本/close、session各路由、eval各路由的独立观察。当前所有凭据均为空、NOT_RUN，未进行真实网络服务调用。
