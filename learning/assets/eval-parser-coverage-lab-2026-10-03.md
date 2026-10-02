# eval_hub 解析器覆盖验收练习卡（公开版，2026-10-03）

> 目的：把一次已实跑的 `eval_hub` 窄源码切片 + 原创覆盖实验，整理成可复用的验收练习卡。本文提供结果摘要、case 设计、正负控机制与已知缺口；不附完整实验包，公众复核边界见第3节。

## 1. 结论摘要

- **实测范围**：只验证冻结的 22 个 case、三条真实 AST 赋值表达式构成的窄源码切片、原创离线 contract、6 个内置 mutation。
- **实测结果**：
  - 普通基线：`22/22 PASS`，退出码 `0`。
  - mutation 模式：`22/22 baseline PASS`，`6/6 mutation KILLED`，退出码 `0`。
  - `-O` 优化 mutation 模式：`22/22 baseline PASS`，`6/6 mutation KILLED`，退出码 `0`。
  - 两个 mutation 模式结果报告哈希一致。
- **不能外推**：这不是完整上游模块、SDK、真实 API、真实重试或端到端评测的证明；`real_api_attempts=unknown` 只是账本字段，不是 API 调用观测。
- **保留缺口**：subset oracle 没有断言源码 span/token 或全部 ledger 结构；负溢出与部分零分母形式未显式覆盖。

## 2. 来源与边界说明

本卡沿用 **2026-10-02 已审查的 eval_hub 同一仓库、同一固定提交** `d5637d5cfb420a040ad550b2125c6aa23f71f9e4`。本次从只读源码分析升级为离线窄切片与原创契约实测，不是新仓库发现或上游新版本发布。

| 类别 | 本卡公开内容 | 不公开/不声称 |
|---|---|---|
| 官方源码 | 指向官方 GitHub raw URL 与 commit；说明只抽取 3 条赋值表达式参与实测 | 不复制上游完整文件；不声称完整 upstream 正确 |
| 原创建模 | 公布可复用 case、oracle 规则、mutation 设计、学习步骤 | 不附 runner 与完整输入包 |
| 实测来源 | 公布 manifest hash、命令形态、汇总结果、报告 hash | 不公开真实本地路径、容器名、私有证据包 |

官方来源（HEAD 已核验）：

- `evaluate.py`：`https://raw.githubusercontent.com/google-deepmind/eval_hub/d5637d5cfb420a040ad550b2125c6aa23f71f9e4/eval_hub/live_math/evaluate.py`，HTTP 200。
- `LICENSE`：`https://raw.githubusercontent.com/google-deepmind/eval_hub/d5637d5cfb420a040ad550b2125c6aa23f71f9e4/LICENSE`，HTTP 200。
- `NOTICE`：同 commit 下未找到，HTTP 404；因此本文只描述“未找到”，不把它作为引用链接。

许可提醒：上游项目含 Apache-2.0 license。本文为学习卡，不替代原项目许可文本或法律审查。

## 3. 已实跑的不可变摘要

| 项 | 值 |
|---|---|
| 冻结 manifest SHA-256 | `0200d2645e232dd7ff84ed2f06154a88ff1c8591d6985c81670d79df5e72039f` |
| 上游 commit | `d5637d5cfb420a040ad550b2125c6aa23f71f9e4` |
| 上游 `evaluate.py` SHA-256 | `d40a7105f601d413f1e5c89cfbf5792abd9c435bfa6e40f3a834a0c5995cf694` |
| 实测 Python | CPython `3.11.15` |
| 基线报告 SHA-256 | `c0dec6cbe9e8451063f75cfc923ffb3537b95c94bb9f63e5ce1884da21631ba1` |
| mutation 报告 SHA-256 | `e986ddfc0b00a1fa9bcdaae856ccb9a497b34effe50766b1a8ff95216b378645` |
| `-O` mutation 报告 SHA-256 | `e986ddfc0b00a1fa9bcdaae856ccb9a497b34effe50766b1a8ff95216b378645` |
| 运行日期口径 | 本卡日期为 `2026-10-03`；实际 UTC 记录为 `2026-10-02T19:26:12Z` 至 `2026-10-02T19:26:26Z` |

哈希用途：以上 SHA-256 仅用于内容指纹与复核关联，**不是签名、认证或发布批准**。原始报告、manifest与runner不公开，因此对应hash只是本次结果的关联指纹，公众无法仅凭本卡独立复算或验证原报告；它们不是可访问的公开实证附件。公开上游源码可按固定URL另行获取并核对源码hash。

## 4. 已实跑命令与结果

| 命令形态 | 退出码 | 基线 observed | mutation observed | ERROR |
|---|---:|---:|---:|---:|
| `python3 -I -B runner.py` | 0 | 22/22 PASS | 未请求 | 0 |
| `python3 -I -B runner.py --mutations` | 0 | 22/22 PASS | 6/6 KILLED | 0 |
| `python3 -I -B -O runner.py --mutations` | 0 | 22/22 PASS | 6/6 KILLED | 0 |

实测隔离条件摘要：无下载/安装；网络关闭；只读输入；新空结果目录为唯一可写位置；逐文件 hash 校验；`-I` / `-B` 生效；容器非 privileged、capabilities 清空、no-new-privileges；无超时或 OOM。未声明 rootless Docker。

## 5. 三条真实源码切片的验收对象

本实验只把上游函数中的三条赋值表达式作为 AST 节点抽出，在原创小函数中运行：

1. 匹配正则：`Final\s*answer:\s*(-?[\d\.]+)\s*$`，flags 为 `re.IGNORECASE | re.MULTILINE`。
2. `parsed_number_str = match.group(1)`。
3. `parsed_answer = float(parsed_number_str)`。

输入位于上游 `.strip()` 之后的文本边界（post-strip seam）；切片本身不包括上游 `.strip()`、try/retry或完整调用流程。下文source侧的 `PARSED`、`NO_MATCH`、`CONVERSION_ERROR` 状态及 `INF` 序列化标记来自原创观测包装，不是上游返回协议；上游成功状态为 `SUCCESS`。contract侧标签及有限性门同样属于原创契约。

这意味着：

- `Final answer: 20` 可解析为 `20.0`。
- `Final answer: 20 units` 不匹配。
- `Final answer: 1.2.3` 匹配后 `float()` 失败，归为转换错误。
- 多个 `Final answer` 时，实测 source slice 取第一个 match；一个 mutation 专门把它改成最后一个 match 作为负控。
- 超长数字可能让 `float()` 产生非有限值；source slice 会观测到 `INF`，原创 contract 把它视为 `NONFINITE`，这是本实验刻意覆盖的契约差异。

## 6. 可复用 case 卡（12 个代表性输入/期望）

> 完整实跑集为22 case。下面12个代表例覆盖解析、转换错误、非有限值、GT排除、future失败保留与并发返回顺序，**不包含重试案例**。完整22例另含L05的原创mock重试账本，不是上游或真实API重试验证。ID保持稳定，可作为练习或验收表的种子。`null`表示JSON null；表中 `\n` 表示解码后的实际换行U+000A，不是反斜杠与字母n两个字面字符。

### 6.1 Parser cases

| ID | 输入 | source 期望 | contract 期望 | 价值 |
|---|---|---|---|---|
| P01 | `Final answer: 20` | `PARSED, 20.0` | `PARSED, 20.0` | 基础正控 |
| P03 | `Final answer: 1.2.3` | `CONVERSION_ERROR, null` | `CONVERSION_ERROR, null` | 匹配成功但 float 失败 |
| P04 | `Final answer: 20 units` | `NO_MATCH, null` | `NO_MATCH, null` | 行尾约束 |
| P06 | `Final answer: 19\nFinal answer: 20` | `PARSED, 19.0` | `PARSED, 19.0` | 首个 match 行为；M6 负控 |
| P08 | `Final answer: NaN` | `NO_MATCH, null` | `NO_MATCH, null` | 正则不接受字母 NaN |
| P10 | `Final answer: ` + `9` 重复 400 次 | `PARSED, INF` | `NONFINITE, null` | 非有限值契约门；M5 负控 |
| P11 | `fInAl AnSwEr: -0.5` | `PARSED, -0.5` | `PARSED, -0.5` | 大小写不敏感 + 负数 |
| P14 | `Final answer: .` | `CONVERSION_ERROR, null` | `CONVERSION_ERROR, null` | 正则允许点号但 float 失败 |

### 6.2 Ledger / concurrency cases

| ID | 输入摘要 | 期望摘要 | 价值 |
|---|---|---|---|
| L01 | GT=20，样本返回 `Final answer: 19` | `planned=1, retained=1, parsed=1, correct=0, correct_over_parsed=[0,1]` | “能解析”不等于“正确”；M1 负控 |
| L02 | 2 个 `future_exception` + 1 个正确 response | `planned=3, retained=3, failed_future=2, parsed=1, correct=1, mock_attempts=3, parsed_over_raw_plan=[1,3]` | future 失败也要保留到账本；M2 负控 |
| L03 | 4个无效GT：字段缺失 / 不可转数值字符串 `"twenty"` / 字符串 `"NaN"` / 字符串 `"Inf"` | `planned=4, retained=4, mock_attempts=0, valid_problems=0, excluded` 包含4条原因，`question_any_correct_over_valid=[0,0]` | 后两项经float转换为非有限值，并非JSON NaN/Infinity常量；数值字符串不因此一概无效；M3负控 |
| L04 | 控制释放顺序 `sample-003, sample-001, sample-002` | 返回顺序与稳定 ID 保持：003 返回，001/002 future exception | 并发完成顺序不能重编号；M4 负控 |

## 7. 分母与账本规则

下列 `[分子,分母]` 是未经求商的原始计数对；`[0,0]` 不表示把0/0算成0。展示比率时应另行定义零分母为未定义或不适用。

- `planned`：原始计划样本数。
- `retained`：最终账本保留行数。future exception 仍应保留，除非被 mutation 故意删掉。
- `mock_attempts`：原创 mock 动作数；不是外部 API 调用数。
- `real_api_attempts`：实测字段为 `unknown`，不能解释成真实 API 调用次数。
- `parsed_over_raw_plan=[parsed, planned]`：分母是原始计划样本数，不因 GT 无效而缩小。
- `correct_over_parsed=[correct, parsed]`：分母是可解析样本数。
- `question_any_correct_over_valid=[won_questions, valid_problems]`：分母只包括有效 ground-truth 的题目；无效 GT 被排除并进入 `excluded`。
- GT exclusion 原因：`MISSING`、`CONVERSION_ERROR`、`NONFINITE`。
- 稳定 ID：并发或异步返回不得用返回序号重编号样本 ID；L04 明确保护这一点。

## 8. 六个 mutation 负控与实测 kill 点

| Mutation | 指定 case | 实测 kill 差异 |
|---|---|---|
| M1_PARSE_IS_CORRECT | L01 | 把“能解析”错当“正确”：`correct` 从 `0` 变 `1`，`correct_over_parsed` 从 `[0,1]` 变 `[1,1]` |
| M2_DROP_FUTURE | L02 | 删除 future failure 行：`retained` 从 `3` 变 `1`，`failed_future` 从 `2` 变 `0`，`mock_attempts` 从 `3` 变 `1` |
| M3_HIDE_GT | L03 | GT 排除记录被清空：`excluded` 从 4 条变 `[]` |
| M4_RENUMBER | L04 | 并发返回记录被重新编号，稳定 sample ID 被破坏 |
| M5_ALLOW_NONFINITE | P10 | 原创有限性门失效：contract 从 `NONFINITE/null` 变 `PARSED/INF` |
| M6_LAST_FINAL | P06 | 多个 Final 时取末条：contract value 从 `19.0` 变 `20.0` |

两个 mutation 命令均观察到 10 条预期负控 oracle FAIL；这些 FAIL 是指定 mutation 被杀死的证据，不是命令失败，也不是 ERROR。所有指定 kill 均为 contract oracle mismatch；无 source oracle failure、无 ERROR。

## 9. 验收练习步骤（公开复用版）

1. **固定范围**：先写清只验解析切片、原创契约和离线账本，不验完整上游 pipeline。
2. **锁定来源**：记录上游 commit、官方 URL、源码 hash；404 的 NOTICE 只能记为“未找到”，不要作为引用。
3. **定义稳定 case ID**：至少覆盖 parser 正控、NO_MATCH、CONVERSION_ERROR、NONFINITE、多 Final、GT exclusion、future 保留、并发 ID 稳定。
4. **定义分母**：明确 `planned`、`retained`、`parsed`、`valid_problems` 的分母，尤其是 GT exclusion 不应污染有效题目分母。
5. **加负控 mutation**：每个关键契约至少一个指定 kill case；crash 不能算 kill。
6. **跑双模式**：普通模式与 `-O` 模式都跑 mutation，防止依赖 assert 或优化敏感行为。
7. **区分摘要与可复核材料**：记录hash、命令形态、PASS/KILLED计数及缺口；明确哪些输入、runner和报告可访问，不把hash代替可复核材料。
8. **不要外推**：若把本卡改造成新的单文件runner、替换case、加入真实API或改动契约，需要重新验证运行安全条件并重新执行测试，不能继承本卡的通过结果。

## 10. 公开版验收模板

可复制下面模板到自己的项目 README 或 PR 描述中：

```text
实验名称：<项目/解析器覆盖验收>
日期：<YYYY-MM-DD>
范围：仅 <窄切片/模块/契约>；不覆盖 <完整系统/真实 API/端到端>
来源：<官方 URL + commit + hash>
case：<N> baseline，<M> mutation
命令：
  - python3 -I -B <runner>
  - python3 -I -B <runner> --mutations
  - python3 -I -B -O <runner> --mutations
通过门：
  - baseline 全 PASS，无 ERROR
  - 每个 mutation 被指定 case 杀死
  - crash/timeout 不计为 mutation kill
  - 普通与 -O mutation 结果一致或差异被解释
分母规则：
  - parsed_over_raw_plan 使用原始计划分母
  - correct_over_parsed 使用 parsed 分母
  - question_any_correct_over_valid 使用有效 GT 分母
已知缺口：<明确保留的未覆盖项>
哈希：<报告 hash；说明 hash 非签名>
```

## 11. 本卡的学习结论

- 一个小解析器也需要同时验 **正则匹配、转换错误、非有限值、首末匹配策略、GT 排除、并发 ID 稳定、失败保留、分母定义**。
- mutation 不是为了制造失败，而是为了证明 oracle 能抓住“看似合理但违约”的实现。
- 公开资产应把“真实跑过什么”和“没有跑什么”分开写；未提供的原始材料不能当成公众可独立复核的附件。
- 本次真实结果支持这张练习卡的案例设计，但不授予任何新的 runner、改写版实验或完整上游系统通过结论。
