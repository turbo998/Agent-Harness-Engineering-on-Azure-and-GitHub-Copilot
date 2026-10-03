# UserSim：manifest 意图不等于结果提交——离线单模块 Lab

日期：2026-10-04。固定源码：`NVIDIA-NeMo/UserSim`，commit `2945592c6d5b473c8b7158f432b16490a2d04aa0`。这是 **10-03 旧雷达在同一 SHA 上的离线实测升级**，不是新提交或新特性发现。

**已实际离线执行：10 个 baseline case 全部 PASS，5 个源码 mutant 与 2 个原创策略 mutant 全部 KILLED，总状态 PASS。** 实验使用 Python 3.11.15、断网/只读/非 root/移除 capabilities 的 Docker 容器。实测绑定下列 runner 与源文件原始字节；可移植包装命令本身未另行实测。

这是**完整 `eval_manifest.py` 单模块 import**，不是完整 SDK import、发布 wheel 验证、上游测试套件、notebook/CLI 复现、模型质量评测，也不是授权、并发或原子写验证。此处的“完整”仅指没有抽取或重写该模块的函数。

## 1. 下载物与证据边界

同目录交付，保留以下文件名：

- [下载原字节 runner：usersim_manifest_runner.py](./usersim_manifest_runner.py)
- [公开源码、URL 核验与实测摘要 JSON](./usersim-public-sources.json)

Runner SHA-256：

```text
70ab7c0c754805808e1da57f5e8f7605fb42686d6836a6e7a1e54b6a23f93f64
```

Runner 是本 lab 的原创标准库程序，并非 NVIDIA 上游文件；公开伴随文件与实际执行的 runner 字节完全相同，大小 15050 bytes。上述 SHA-256 绑定 runner 文件的全部原始字节，不是包装命令、文档或摘要 JSON 的 hash。

执行证据来自既有 runner stdout JSON；原始 stdout SHA-256：

```text
e361357b4b0f0883617d340e0270ca8fab8082c9f9e8750273508e78db397d9b
```

公开 JSON 机械摘录了每个 variant 的逐 case 状态、失败消息与目标 case，保留原始 stdout hash，而不依赖任何私有文件路径。原始 stdout 全文未随本页复制；可按下文重新生成自己的 stdout 证据。摘要 hash 与原始 stdout hash 不同，不能混用；这些 hash 是完整性标识，不是签名或来源认证。

## 2. 从真实源码到实验假设

以下全部固定在同一 commit；公开 JSON 保存逐文件 SHA、字节数、实际 `curl -sI -L` 检查时间、HTTP 状态、最终 URL 和重定向次数。全部 9 个源 URL 本次检查均返回 HTTP 200。**HEAD 只证明可访问；SHA 来自对已留存正文的重新计算，不是 HEAD 返回的内容摘要。** 检查时间用 UTC；标题日期是 lab 日期。

| 证据 | 静态读取发现与用途 | 本次是否执行 |
|---|---|---|
| [eval_manifest.py][source] | 模块开头把 eval store 定义为实际评估结果的事实来源；manifest 记录采样/评估 pass 历史。`from_dict`、`consensus_mode`、`record_eval_sample_pass` 是直接实验对象 | 完整单模块 import；5 个变体仅改临时副本 |
| [02_evaluate_simulation.ipynb][notebook] | JSON cell 索引 10 先写 manifest；12 才做模型 smoke/evaluate/结果写入；14 读取 `consensus_mode` 给 dashboard 标注 | 仅按 JSON 文本读取，未执行任何 cell |
| [storage.py][storage] | `write_run_partition` 仅在 `overwrite=True` 且旧 run 目录存在时先删除再写（默认 False）；`write_run_locales_partition` 默认 `overwrite=True`，在 locale 输入校验通过、df 非空且对应旧目录存在时删除指定 locale 再写，空 df 不删除 | 仅静态读取，不导入 parquet/storage |
| [CLI evaluate.py][cli] | CLI 有删除/重写 eval 目录的路径，文件中没有 `record_eval_sample_pass` 调用；不能把 notebook 路径外推给所有入口 | 仅静态读取 |
| [_pipeline.py][pipeline]、[capability_report.py][report] | 对照评估入口与报告代码；本 lab 的缺失预测分母策略并不等于真实 pandas/report 聚合实现 | 仅静态读取 |
| [reporting/__init__.py][init]、[上游 manifest tests][tests] | 核对公开导出与源码已有测试背景；本 lab 是另写的 10-case suite | 未导入 package，未跑上游 tests |
| [LICENSE][license] | 根 LICENSE 为 Apache-2.0；目标模块头部另有 SPDX Apache-2.0 声明 | 仅文本核对 |

关键调用顺序（源码阅读，不是 notebook 运行轨迹）：仅在非 `_render_only`，且 eval run 不存在、`OVERWRITE_EVAL_RUN=True` 或 `EVAL_LOCALES` 非空之一成立时进入采样/评估路径；否则跳过或加载既有结果。cell 12 评估成功后，locale 分支调用 `write_run_locales_partition`（默认 `overwrite=True`）；无 locale 分支调用 `write_run_partition(..., overwrite=OVERWRITE_EVAL_RUN)`。

```text
notebook cell 10: 采样 → record_eval_sample_pass(fresh=not bool(EVAL_LOCALES))
notebook cell 12: 可选模型 smoke → evaluate_dataframe → 写 run/locale 分区
notebook cell 14: 读 manifest 的 consensus_mode + 读 eval store → 报告
```

直接模块语义：

- `fresh=False` 正常追加历史；已有**非空** `run_id` 与请求不同时，抛出 `ValueError` 且不写文件。
- `fresh=True` 不读取旧 manifest，重建历史，因此也绕过旧 run ID 检查。这是调用方选择的行为，**不是授权边界**。
- `passes` 是否为 list 是格式分支依据，不强制 `schema_version == 2`；legacy v1 会提升为单 pass。
- `consensus_mode` 在无 pass 时为 `unknown`，所有 mode 相同时取该值，否则为 `mixed`。
- 最终使用 `Path.write_text` 写 JSON；这里没有跨 manifest/parquet 的事务或并发写协调。

### 严格区分两类代码

**真实上游代码**：固定 SHA 的整个 `eval_manifest.py`，通过正常 import machinery 加载，不执行 `usersim` package initializer。

**原创小模型**：`SyntheticStore`、`synthetic_flow`、`reconciled_commit` 和 `planned_denominator`。它们只模拟“先记意图、后评估、再提交”的顺序及故障，数据保存在内存中；不实现真实 UserSim 存储，不是新增的上游 API。

尤其 `reconciled_commit(manifest, receipts)` **实际上仅返回 `bool(receipts)`，没有核验 manifest，也没有关联 receipt 与 run/pass/结果版本**。名称中的 reconciled 不代表完整对账。`successful_receipt` 只能说明这个成功 fixture 产生 receipt 后 toy oracle 为真，绝不能推导“任意 receipt 都足以证明生产提交”。

## 3. 每个 case 验证什么、为什么有价值

下表的 PASS 表示断言符合预期；故障注入 case 的 PASS 并不表示下游评估/提交成功。

| Case ID | 输入/故障与断言 | SA 价值及反例 | 实测 |
|---|---|---|---|
| `append_sequence` | 两次记录 `[t1,t2]`、`[t2,t3]`；保留顺序、latest、locale 标志与 full consensus；selected 累加为 4、唯一 ID 为 3 | 历史 pass 数、累计采样次数、唯一计划对象不是同一计数；反例：第二次覆盖第一次 | PASS |
| `cross_run_rejection` | 先 r1，随后 `fresh=False` 写 r2；要求 `ValueError` **且文件字节不变** | 避免错路径混入其他 run；只有异常而仍改文件也不能验收；不验证调用者身份 | PASS |
| `fresh_cross_run` | r1 后以 `fresh=True` 写 r2；只剩新 pass/ID | 暴露 fresh 的显式重置边界；反例：把 cross-run 拒绝解释为无条件隔离 | PASS |
| `schema_edges` | 缺文件→None；损坏 JSON/非 object→ValueError；版本 999 + 空 list 按 v2 解析；legacy 提升；空 run ID 不自动补齐；`passes:[null]`→AttributeError；非 list passes 回落 v1 | 检查真实兼容性而非理想 schema；预期异常是 case 输入契约，不是执行错误被冒充 mutant kill | PASS |
| `mixed_consensus` | full 与 per_locale 两次历史返回 mixed | dashboard 不应把最后一次采样方式当全 run 的统一模式；反例：直接取 latest.mode | PASS |
| `prewrite_eval_failure` | 真实 manifest 写成功后，原创 evaluate 抛错；旧 rows 保留、receipt 为空、commit 调用为零 | manifest 中出现 ID 不能证明该 ID 已有评估结果；失败顺序是小模型，不是 notebook 故障实测 | PASS |
| `prewrite_commit_failure` | 原创 evaluate 成功后，原创 commit 在改 rows 前抛错；无 receipt、旧 rows 不变 | 评估完成与结果提交完成是不同事件；反例：以 intent 宣称 committed | PASS |
| `fresh_history_loss` | 先写旧 pass，再 fresh 写新意图并在原创 evaluate 阶段失败；manifest 旧历史消失，toy store 保留旧 rows | 展示意图与结果可能不一致的窗口；不能外推真实存储发生部分写时也保留全部旧 rows | PASS |
| `missing_prediction_denominator` | 计划 t1/t2/t3，仅得到 t1/t2；显式缺失 t3，原创 planned 分母为 3，observed 为 2 | 防止仅有结果对象进入分母掩盖缺失；不是上游评分 bug 实测，也不计算模型分数 | PASS |
| `successful_receipt` | 原创成功流为 intent_written→evaluate→commit_attempt→receipt；toy rows 为预期值 | 正向控制，避免把所有路径一律判失败；但外来、伪造、旧 receipt 不在该断言覆盖内 | PASS |

### Mutation 证据：5 个源码变体 + 2 个策略变体

每个 variant 都运行同一组 10 个 case。源码变体通过唯一锚点做单次替换，仅写临时副本；原源文件不改。策略变体只切换原创 oracle，不修改 UserSim 源码。

| 类别 | Mutant | 目标 case | 实测 |
|---|---|---|---|
| 源码 | `append_to_replace`：追加变覆盖 | `append_sequence` | KILLED |
| 源码 | `remove_cross_run_guard`：移除旧 run 检查 | `cross_run_rejection` | KILLED |
| 源码 | `ignore_fresh`：忽略 fresh | `fresh_history_loss` | KILLED |
| 源码 | `latest_not_consensus`：mixed 变 latest.mode | `mixed_consensus` | KILLED |
| 源码 | `version_gate`：按版本号强制分支 | `schema_edges` | KILLED |
| 原创策略 | `intent_as_commit`：有 pass 就认为已提交 | `prewrite_eval_failure` | KILLED |
| 原创策略 | `observed_denominator`：只数已观测且属于计划的预测 | `missing_prediction_denominator` | KILLED |

KILLED 的条件是目标 case 出现 `BUSINESS_ORACLE_FAILURE`，且该 variant 的其他结果只能为 PASS 或业务断言失败。Syntax/import/KeyError 等运行错误、超时、缺 case 不计有效 kill。公开 JSON 保留额外受影响 case，未把它们误算成更多独立 mutant。审计 hook 的 network/process 禁止事件计数均为 0；这只是所监测事件的观测，不能单凭 Python hook 宣称进程级所有 I/O 均不存在。

## 4. 可移植复现：准备联网，执行断网

### 前置条件

- Linux Docker 容器运行能力、Bash、`curl`、`sha256sum`、GNU `timeout`。macOS 可使用支持 Linux 容器的 Docker 与相应 GNU 工具，但本页未实测其他宿主。
- 固定镜像为 `linux/amd64`、Python **3.11.15**；其他架构需可用的 amd64 运行支持，不能声称已验证原生 ARM。
- 自选一个**新的、专用于此 lab、非敏感**的目录作为 `LAB_ROOT`，把本页两个伴随下载物保存进去。不要把家目录、工作仓库、密钥、Docker socket 或旧 Python 缓存加入挂载。
- 不需要 UserSim 安装、pip、pandas、pyarrow、IPython、模型 endpoint、API key 或 `.env`。Runner 及目标模块仅用 Python 标准库。
- 源码与镜像的首次准备需要网络；**lab 执行**使用 `--network none --pull never`。准备阶段只下载文件/镜像，不执行网上获取的 notebook、CLI 或安装脚本。

以下命令在 Bash 中按顺序执行。先把 `LAB_ROOT` 改成自己选定的目录；要求它已经包含伴随 runner 和 JSON。示例不引用任何作者机器目录。

```bash
export LAB_ROOT="$PWD/usersim-lab"  # 自选：先将两个伴随下载物保存到这里
(
  set -euo pipefail
  LAB_ROOT="$(cd "$LAB_ROOT" && pwd -P)"
  cd "$LAB_ROOT"
  test -f usersim_manifest_runner.py
  test -f usersim-public-sources.json
  printf '%s  %s\n' \
    '70ab7c0c754805808e1da57f5e8f7605fb42686d6836a6e7a1e54b6a23f93f64' \
    'usersim_manifest_runner.py' | sha256sum -c -

  # 必须在只读 bind mount 之前建好 runtime 挂载点。
  mkdir -p source/src/usersim/reporting runtime evidence
  # -B 不禁止读取既有 pyc，因此本实验不允许带入旧模块缓存。
  test ! -e source/src/usersim/reporting/__pycache__
  test ! -e source/src/usersim/reporting/eval_manifest.pyc
  BASE='https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0'
  curl -q --fail --silent --show-error --location --max-time 30 \
    --proto '=https' --proto-redir '=https' \
    "$BASE/src/usersim/reporting/eval_manifest.py" \
    -o "$LAB_ROOT/source/src/usersim/reporting/eval_manifest.py"
  curl -q --fail --silent --show-error --location --max-time 30 \
    --proto '=https' --proto-redir '=https' \
    "$BASE/LICENSE" -o "$LAB_ROOT/source/LICENSE"
  printf '%s  %s\n' \
    '8788999297e5048e197cefa939248683e5beb7b57dcbe3b9f28329dd430acfa3' \
    'source/src/usersim/reporting/eval_manifest.py' \
    'ee4829788960ba974f402c4d9f5b86e702e51037ef5407ec5ffdb93d3b391f33' \
    'source/LICENSE' | sha256sum -c -

  IMAGE='python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0'
  # 镜像已预置时不拉取；否则只在准备阶段从公开 registry 获取。
  docker image inspect "$IMAGE" >/dev/null 2>&1 || \
    docker pull --platform linux/amd64 "$IMAGE"
)
```

不复制上游整个源码树：运行时只需要以上单个 Python 源文件；下载 LICENSE 是保留许可证据。其他固定文件用于静态推理，可通过文末链接按需读取，**不是隐藏的执行依赖**。

### 运行并保留 stdout

以下包装使用用户选择的目录，并按本次专属容器 ID 清理。容器内 `/lab`、`/lab/runtime`、`/tmp` 是可移植挂载点，不是宿主机路径。

```bash
(
  set -euo pipefail
  LAB_ROOT="$(cd "$LAB_ROOT" && pwd -P)"
  cd "$LAB_ROOT"
  mkdir -p runtime evidence
  # 每次新证据目录；cidfile 必须尚不存在。
  RUN_EVIDENCE="$(mktemp -d "$LAB_ROOT/evidence/run.XXXXXXXX")"
  CIDFILE="$RUN_EVIDENCE/container.cid"
  cleanup() {
    # 只清理由本条 docker run 创建并写入 cidfile 的容器。
    if [ -s "$CIDFILE" ]; then
      CID="$(< "$CIDFILE")"
      if [[ "$CID" =~ ^[0-9a-f]{64}$ ]]; then
        docker rm -f "$CID" >/dev/null 2>&1 || true
      fi
    fi
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  IMAGE='python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0'
  set +e
  timeout --signal=TERM --kill-after=5s 40s \
    docker run --rm --pull never --platform linux/amd64 --cidfile "$CIDFILE" \
      --network none --read-only --cap-drop ALL \
      --security-opt no-new-privileges --user 65534:65534 \
      --pids-limit 32 --memory 256m --cpus 1 --ulimit nofile=64:64 \
      --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 \
      --mount "type=bind,src=$LAB_ROOT,dst=/lab,readonly" \
      --tmpfs /lab/runtime:rw,nosuid,nodev,noexec,size=16m,uid=65534,gid=65534,mode=700 \
      --workdir /lab --entrypoint /usr/bin/env "$IMAGE" \
      -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/nonexistent \
      /usr/local/bin/python3 -I -S -B usersim_manifest_runner.py \
      > "$RUN_EVIDENCE/stdout.json" 2> "$RUN_EVIDENCE/stderr.txt"
  RC=$?
  set -e
  printf '%s\n' "$RC" > "$RUN_EVIDENCE/exit-code.txt"
  sha256sum "$RUN_EVIDENCE/stdout.json"
  printf 'Evidence: %s\nExit code: %s\n' "$RUN_EVIDENCE" "$RC"
  exit "$RC"
)
```

执行期间只有临时 tmpfs 可写；host 端由 shell 把 stdout/stderr 写入本次 evidence 目录。runner 自动删除自身临时 suite；不自动删除宿主证据、不运行 `docker system prune`、不批量停止任何其他容器。退出/超时清理仅依据本次 cidfile，`--rm` 已删除时清理可安全无操作。非 root 容器用户不代表 Docker daemon 自身为 rootless。

**验收 stdout**：进程 exit code 为 0，JSON `status == "PASS"`；`source_sha256` 与 `runner_sha256` 对应上文；baseline 的 10 行全部 PASS；7 个 mutant 各自 `accepted == true`、`mutation_killed == true`，目标 case 为业务断言失败；`blocked_effect_attempts` 两项均为 0。不能只看退出码，也不能要求每个 mutant 的每行都 PASS。Docker 报错、空 stdout、无 JSON、超时或任何 ERROR 均不得记作实验通过。

**复现 pitfall**：只读 bind mount 前先在宿主执行 `mkdir -p runtime`，保证 tmpfs 挂载点存在；`-B` 不阻止读取既有 pyc，必须使用新 lab 目录并排除旧 `__pycache__` 与 `eval_manifest.pyc`，不要挂载其他 Python 缓存。

## 5. SA takeaway：把它用作验收问题，不当生产事务实现

1. **分别计数和呈现意图、尝试、已观测结果、已持久化结果。** Manifest 中的计划 ID 不能单独成为成功率的已提交分母。多 pass 重叠、locale 重评估覆盖也不能用 selected 简单累加替代唯一有效结果数。
2. **对账应绑定具体对象和版本，而非看有没有 receipt。** 生产设计至少需要核验 run/pass/attempt 标识、计划集合、输出集合与摘要、存储版本/提交标识、来源可信度、重放/幂等语义。这里没有实现这些要求。
3. **fresh 是破坏性重建语义，不是可随意“重试”的标志。** 评估前重置历史与结果提交之间存在需要产品层面定义的失败恢复窗口。真实存储还可能发生删除后写失败，toy commit 的“先失败不改旧 rows”不能覆盖它。
4. **采样模式标签与完成状态分离。** `mixed` 是历史采样模式描述，不是结果已提交或质量合格的证明。

一个**尚未加入 suite 的反例**：给新 manifest 传入另一个 run 的旧 receipt，当前 `bool(receipts)` 仍为真；因此不能把成功 fixture 的 PASS 作为跨 run 对账安全证明。另一个未覆盖反例是先删除旧 parquet 后写入一半失败；本 lab 的内存 store 故障发生在改 rows 前，没有模拟真实部分持久化。

### 仍待独立验证

- 正式 notebook/CLI 各入口的端到端顺序、render-only/locale/overwrite 组合、真实 evaluator 与 provider 行为。
- pandas/parquet/report 对缺失预测、重复 ID、多 scorer/locale、重评估覆盖与最终统计分母的实现。
- receipt 真实性、run/pass/attempt/结果内容关联、旧 receipt 重放、部分提交、恢复与幂等。
- 并发 read-modify-write、原子替换、fsync、进程崩溃/磁盘满、删除后写失败；本次不提供原子写或一致性保证。
- 身份认证、授权、租户隔离、恶意输入安全边界；run_id guard 不是这些能力。
- 其他 Python/架构/容器运行时，以及源码 HEAD 或后续版本。固定旧源码的本次实验不声称发现了当天新特性或已修复上游问题。

## 6. License 与独立复用说明

上游目标源的 SPDX 与根 LICENSE 一致为 Apache-2.0，LICENSE SHA 为 `ee4829788960ba974f402c4d9f5b86e702e51037ef5407ec5ffdb93d3b391f33`。本公开包不嵌入上游整个源码；上述下载保持源码版权头并单独保留 LICENSE。若再分发源码/派生物，仍须按许可处理 notices 等义务；未审计外部数据、persona、模型、依赖和镜像的完整许可闭包。

原创 runner 没有单独许可证声明，**不能把上游 Apache-2.0 自动套用到原创 runner**。本页提供实验复现材料与出处，不额外声明未经确认的再许可条款；商业再分发等许可需求应另行确认。

**依赖完整性结论**：伴随 runner 与公开 JSON 齐全；唯一上游执行源的固定下载 URL、目标路径和 SHA、LICENSE 下载与 SHA、固定 Python 镜像及平台、隔离运行/证据/清理步骤均已列出。无需私有笔记、准入文件、私有路径或账号才能理解和复现。源码与镜像未打包，因此这不是无需预置依赖的离线压缩包；完成联网准备后才可断网执行。

[source]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/reporting/eval_manifest.py
[notebook]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/notebooks/02_evaluate_simulation.ipynb
[cli]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/cli/evaluate.py
[tests]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/tests/test_eval_manifest.py
[license]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/LICENSE
[pipeline]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/cli/_pipeline.py
[storage]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/engine/core/storage.py
[init]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/reporting/__init__.py
[report]: https://raw.githubusercontent.com/NVIDIA-NeMo/UserSim/2945592c6d5b473c8b7158f432b16490a2d04aa0/src/usersim/reporting/capability_report.py
