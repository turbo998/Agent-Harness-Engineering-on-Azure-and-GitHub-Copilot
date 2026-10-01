# MAF ZIP 冲突：可复演的真实源码切片实验

**范围先行：这是固定提交的真实 Python 源码 AST 函数切片，不是完整 MAF SDK 实测。** 不 import 上游模块，不下载/落盘 ZIP，不执行归档成员，不把上游源码复制入本发布包。

2026-10-02 已对本页最终 runner 与隔离 Shell 模板独立审查后复演：**11 个基线 case PASS、6 个专属变异 KILLED，Shell/容器退出码均为 0，无 OOM**；CPython 3.11.15 / Unicode 14.0.0。该证据绑定公开 runner hash `0bd47d0fcb5d1dfbae84c75d8513c468cae8218a0bb4607096d698746b3fd224`。完整 SDK、MCP 下载/YAML、.NET、多OS与云端仍为 NOT_RUN。

## 来源、制品与哈希

- 固定[提交](https://github.com/microsoft/agent-framework/commit/501989469265894443ba0812264397aec986e4cd)；[Python 完整原始源码](https://raw.githubusercontent.com/microsoft/agent-framework/501989469265894443ba0812264397aec986e4cd/python/packages/core/agent_framework/_skills.py)；[可定位行号的源码](https://github.com/microsoft/agent-framework/blob/501989469265894443ba0812264397aec986e4cd/python/packages/core/agent_framework/_skills.py#L4876-L5287)。读者在独立审查的获取环节取得原始 bytes，保存为 `trusted-skills.py`；不要转换换行或从 HTML 复制。
- [.NET 对照源码](https://raw.githubusercontent.com/microsoft/agent-framework/501989469265894443ba0812264397aec986e4cd/dotnet/src/Microsoft.Agents.AI.Mcp/Skills/Loaders/AgentMcpSkillArchiveExtractor.cs)只作静态参考，不参与动态结论，其 hash 在 companion 中。
- [Companion JSON](maf-zip-collision-manifest-2026-10-02.json)：节点行范围、完整 source hash、runner hash、历史逐项结果、专属变异映射和复演边界；不是签名或安全授权。
- Python source SHA-256：`48024920a29885bd883f0605eb56ebf2f31789a4b61733e5fd58e272481c9c32`
- 历史已执行 runner SHA-256：`441847f9a2bce2c0d16fc07b1b155e5f81750d90da7396c7620dd31fbbb8e185`
- **本页公开 runner SHA-256**：`0bd47d0fcb5d1dfbae84c75d8513c468cae8218a0bb4607096d698746b3fd224`
- Companion 原始文件 SHA-256：`ff554e75ba9cb5e883da4d4e0ccd84aa2710b128da27431f4fab99553f454bc1`

## 方法与可得结论

按 AST 精确选择 10 个节点：两个常量、`_ArchiveFormat`、五个归档函数，以及 `_ArchiveEntryLoader` 的 `_verify_digest` / `_find_skill_md`。两静态方法提升为函数时只去除已核对的 `@staticmethod`；函数体不变。显式推迟注解求值，绑定标准库 `Enum/io/zipfile/hashlib/re/logger` 与 builtins；没有 SDK stub。先核对**完整源文件 bytes**，再选节点；负控仅修改深拷贝 AST。

- 同规范化 `.lower()` key 保留 ZIP 中首项内容及首拼写，重排可改变结果；不等同 `casefold`，尾点不折叠。
- 目录先跳过，其他条目先计数再规范化/去重；重复项和退化非目录名也耗计数。重复项在 `open` 前跳过，不消耗实际读取的字节预算。
- 反斜杠改斜杠、剥前导斜杠、去空段和 `.`；字面 `..` 导致拒绝整个归档；不做百分号解码。这不是跨平台文件系统安全证明。
- `_find_skill_md` 先最浅、再 key 字典序；不同目录间不是全局 archive-first。digest 绑定归档 bytes，不决定哪个逻辑成员可信。
- `digest-mismatch` 执行真实 verifier，但“验证后提取”由原创 harness 编排，**不证明 `_download` 的集成顺序**。直接给 verifier 的 `None` 被拒绝，不能推导实际下载必须有 digest。
- 不覆盖 MCP/base64 集成、YAML/frontmatter、缓存、资源构建、完整 SDK、.NET 或真实文件系统；不证明首项可信、发行包或生产系统安全。仅 ZIP_STORED 小样本，不是 DEFLATE/压缩炸弹/中央目录内存压测。

11 个 case 及各自多条断言见完整 runner 与 companion。`skipped-no-read` 使用真实 ZipFile/ZipExtFile，spy 只观测真实调用：1 字节首项与 4096 字节重复项，预算 1，要求一次 open、两次 read（数据及 EOF）。

| 变异 | 真实 AST 修改 | 唯一专属 case |
|---|---|---|
| M1-last-wins | 删除 duplicate gate | first-order |
| M2-casefold | lower → casefold | unicode-lower |
| M3-count-after-dedup | 计数及上限检查移至去重之后 | count-before-dedup |
| M4-read-skipped | 跳过前额外 open/read | skipped-no-read |
| M5-no-normalize | 直接使用 info.filename | normalized-alias |
| M6-digest-bypass | SHA-256 mismatch 条件置 False | digest-mismatch |

历史执行是 **11 个基线 + 六个变异各跑一个专属 case**，不是全 case × 全 mutation 矩阵或代码覆盖率。只有专属业务 `AssertionError` 才可计 KILLED，其他异常为 ERROR；构造/编译/加载失败不计 kill。验收还须逐项匹配 companion 中的 case 和精确 error，不能只看总状态。

## 提取与静态核对（不执行实验）

先检查本文与 companion，再在新的专用工作目录保存二者。下述本地标准库脚本只提取围栏、核对 hash、解析语法，不 import/执行 runner 或上游：

```sh
python3 -I -S -B - <<'PY'
from pathlib import Path
import ast, hashlib, json
m = Path('maf-zip-collision-source-lab-2026-10-02.md').read_bytes()
j = Path('maf-zip-collision-manifest-2026-10-02.json').read_bytes()
assert hashlib.sha256(j).hexdigest() == 'ff554e75ba9cb5e883da4d4e0ccd84aa2710b128da27431f4fab99553f454bc1'
c = json.loads(j)
p = m.split(b'<!-- runner.py:start -->\n```python\n', 1)[1].split(b'```\n<!-- runner.py:end -->', 1)[0]
assert hashlib.sha256(p).hexdigest() == c['runner']['sha256']
assert hashlib.sha256(Path('trusted-skills.py').read_bytes()).hexdigest() == c['sources'][0]['sha256']
ast.parse(p)
with open('runner.py', 'xb') as f: f.write(p)
PY
```

## 独立批准后的隔离执行模板（已作一次固定环境复演）

**先审查最终 runner、原始源码和现成本地镜像，再批准执行。** AST、hash、`--execution-go` 的确认字串都不是授权机制或沙箱。读者自行锁定可信 CPython 3.11+ 镜像的本地 `sha256:` image ID；不要拉取未审镜像、安装依赖或改用浮动 tag。核对镜像无声明 VOLUME、解释器路径正确、只有标准库需求。历史运行时版本仅作对照，不承诺其他版本完全相同。

以下要求本地 Linux Docker daemon、GNU timeout、已有已审镜像、非敏感专用工作目录；不要挂 home、项目目录、凭据或 docker socket 到容器。容器只挂载两个普通输入文件且只读；默认 `/proc`、`/dev`、`/sys` 系统挂载仍存在，非 root 容器进程不等于 rootless daemon 或 VM。不要关闭 daemon 默认 seccomp；可用时优先选择已审 rootless/更强隔离环境，另行核对连接参数。

```sh
# 必须先人工批准；填入本地已审 image ID 及镜像内 Python 绝对路径。
IMAGE='sha256:REPLACE_WITH_REVIEWED_LOCAL_IMAGE_ID'
PYTHON_IN_IMAGE='/usr/local/bin/python3'
set -eu
printf '%s\n' "$IMAGE" | /usr/bin/grep -Eq '^sha256:[0-9a-f]{64}$'
RUNNER="$(pwd -P)/runner.py"; SOURCE="$(pwd -P)/trusted-skills.py"
test -f "$RUNNER" && test ! -L "$RUNNER" && test -f "$SOURCE" && test ! -L "$SOURCE"
# 目录名避免逗号（Docker --mount 分隔符）；UID 65534 须能读两个文件。
d() { /usr/bin/env -i PATH=/usr/bin:/bin /usr/bin/docker -H unix:///var/run/docker.sock "$@"; }
test "$(d image inspect --format '{{.Id}}' "$IMAGE")" = "$IMAGE"
VOLUMES="$(d image inspect --format '{{json .Config.Volumes}}' "$IMAGE")"
test "$VOLUMES" = null || test "$VOLUMES" = '{}'
CID=''
cleanup() { if test -n "$CID"; then d rm -f "$CID" >/dev/null; fi; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
CID=$(d create --pull=never --network=none --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges=true --user=65534:65534 \
  --memory=256m --memory-swap=256m --cpus=0.5 --pids-limit=32 \
  --ulimit=cpu=10:10 --ulimit=nofile=128:128 --ulimit=core=0:0 \
  --shm-size=8m --log-driver=none --restart=no --workdir=/ \
  --mount "type=bind,src=$RUNNER,dst=/runner.py,readonly" \
  --mount "type=bind,src=$SOURCE,dst=/source.py,readonly" \
  --entrypoint=/usr/bin/env "$IMAGE" -i "$PYTHON_IN_IMAGE" -I -S -B -X utf8 -c \
  'import os,runpy,sys; os.environ.clear(); sys.argv=["/runner.py","--source","/source.py","--execution-go","INDEPENDENT_REVIEW_APPROVED"]; runpy.run_path("/runner.py",run_name="__main__")')
d inspect "$CID" > container-config.json
# 启动前静态检查实际配置及当前输入；不 import/执行实验代码。
python3 -I -S -B - <<'PY'
from pathlib import Path
import hashlib, json
c, = json.loads(Path('container-config.json').read_bytes())
h, cfg = c['HostConfig'], c['Config']
assert h['NetworkMode'] == 'none' and h['ReadonlyRootfs'] and not h['Privileged']
assert h['CapDrop'] == ['ALL'] and not h['CapAdd']
assert h['SecurityOpt'] == ['no-new-privileges=true'] and cfg['User'] == '65534:65534'
assert h['Memory'] == h['MemorySwap'] == 268435456
assert h['NanoCpus'] == 500000000 and h['PidsLimit'] == 32
assert any(u == {'Name':'cpu','Soft':10,'Hard':10} for u in h['Ulimits'])
expected = {'/runner.py': Path('runner.py').resolve(), '/source.py': Path('trusted-skills.py').resolve()}
assert len(c['Mounts']) == len(expected)
for m in c['Mounts']:
    assert m['Type'] == 'bind' and not m['RW']
    assert Path(m['Source']) == expected.pop(m['Destination'])
assert not expected and not cfg['Volumes']
j = json.loads(Path('maf-zip-collision-manifest-2026-10-02.json').read_bytes())
for name, digest in [('runner.py', j['runner']['sha256']), ('trusted-skills.py', j['sources'][0]['sha256'])]:
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
PY
# 超时后 trap 强制清理容器；执行期间不要修改输入文件。
RC=0
/usr/bin/timeout --signal=TERM --kill-after=2s 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/docker -H unix:///var/run/docker.sock start --attach "$CID" > result.json 2> result.stderr || RC=$?
d inspect --format '{{json .State}}' "$CID" > container-state.json
printf '%s\n' "$RC" > client-exit-code.txt
test "$RC" -eq 0
```

公开模板已仅替换本地镜像ID实际复演；其他环境仍须重新审查。提取与启动前检查依赖 assert，请保持原命令且勿添加 -O/-OO；本轮未使用优化模式。新模板采集的是 inspect 配置与进程入口/退出状态，未采旧 launcher 的进程内 /proc attestation，两者证据不可互换。启动前须核对配置：network none、rootfs/输入只读、非 root、无 capabilities、no-new-privileges、限额和无额外用户挂载。独立验收须确认容器退出码 0、未超时/OOM、stdout 完整有效 JSON，source hash 与公开 runner **新** hash 正确，11 个基线全 PASS、六个专属变异及错误逐项匹配；保存实际 runtime、配置和 stdout/stderr。CLI 退出码或一个 PASS 字段不足以证明隔离生效。不要公开可能含本地路径/镜像环境变量的原始 inspect 文件。

## 完整 runner

围栏使用 UTF-8、LF，包含文件末尾换行；不要格式化、删注释或转义反斜杠。任何字节改变都需重新计算 hash、审查与复演。

<!-- runner.py:start -->
```python
#!/usr/bin/env python3
"""原创离线真实源码切片实验；仅在独立审查并批准隔离执行后运行。
不 import MAF，不下载、不落盘 ZIP，不执行归档成员。AST 抽取不是沙箱。
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import logging
from pathlib import Path
import platform
import re
import sys
import unicodedata
import warnings
import zipfile
from enum import Enum
from types import SimpleNamespace
from unittest.mock import patch

SOURCE_SHA256 = "48024920a29885bd883f0605eb56ebf2f31789a4b61733e5fd58e272481c9c32"
COMMIT = "501989469265894443ba0812264397aec986e4cd"
TOP = {
    "SKILL_FILE_NAME", "_ARCHIVE_READ_BUFFER_SIZE", "_ArchiveFormat",
    "_detect_archive_format", "_normalize_archive_member_name",
    "_read_member_with_limit", "_extract_archive_to_memory", "_extract_zip_to_memory",
}
METHODS = {"_verify_digest", "_find_skill_md"}
MUTATIONS = {
    "M1-last-wins": "first-order",
    "M2-casefold": "unicode-lower",
    "M3-count-after-dedup": "count-before-dedup",
    "M4-read-skipped": "skipped-no-read",
    "M5-no-normalize": "normalized-alias",
    "M6-digest-bypass": "digest-mismatch",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def select_source(raw):
    require(hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, "source hash mismatch")
    tree = ast.parse(raw, filename="trusted-upstream-_skills.py")
    selected = []
    for node in tree.body:
        name = getattr(node, "name", None)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in TOP:
            selected.append(copy.deepcopy(node))
        if isinstance(node, ast.ClassDef) and node.name == "_ArchiveEntryLoader":
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in METHODS:
                    require(len(method.decorator_list) == 1 and
                            isinstance(method.decorator_list[0], ast.Name) and
                            method.decorator_list[0].id == "staticmethod", "unexpected decorator")
                    method = copy.deepcopy(method)
                    method.decorator_list = []  # 单独函数无需 descriptor；函数体不改。
                    selected.append(method)
    names = [getattr(n, "name", None) or n.target.id for n in selected]
    require(len(names) == len(TOP | METHODS) and set(names) == TOP | METHODS,
            "selection not exact")
    return selected


def mutated(nodes, mutation):
    """仅修改内存中的真实函数 AST；每个变异须唯一定位，否则硬失败。"""
    nodes = copy.deepcopy(nodes)
    if mutation is None:
        return nodes
    extract = next(n for n in nodes if getattr(n, "name", None) == "_extract_zip_to_memory")
    loop = next(n for n in extract.body if isinstance(n, ast.For))
    gates = [n for n in loop.body if isinstance(n, ast.If) and
             isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name) and
             n.test.left.id == "lookup_name"]
    require(len(gates) == 1, "duplicate gate locator")
    gate = gates[0]
    hits = 0
    if mutation == "M1-last-wins":
        loop.body.remove(gate)
        hits = 1
    elif mutation == "M2-casefold":
        for n in ast.walk(extract):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "lower":
                n.func.attr = "casefold"
                hits += 1
    elif mutation == "M3-count-after-dedup":
        increments = [n for n in loop.body if isinstance(n, ast.AugAssign) and
                      isinstance(n.target, ast.Name) and n.target.id == "file_count"]
        require(len(increments) == 1, "counter locator")
        pos = loop.body.index(increments[0])
        block = loop.body[pos:pos + 2]
        require(isinstance(block[1], ast.If), "limit gate locator")
        del loop.body[pos:pos + 2]
        pos = loop.body.index(gate) + 1
        loop.body[pos:pos] = block
        hits = 1
    elif mutation == "M4-read-skipped":
        extra = ast.parse("with archive.open(info) as skipped:\n    skipped.read()\n").body
        gate.body[0:0] = extra
        hits = 1
    elif mutation == "M5-no-normalize":
        for n in ast.walk(extract):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and \
                    isinstance(n.value.func, ast.Name) and n.value.func.id == "_normalize_archive_member_name":
                n.value = ast.Attribute(value=ast.Name(id="info", ctx=ast.Load()),
                                        attr="filename", ctx=ast.Load())
                hits += 1
    elif mutation == "M6-digest-bypass":
        verify = next(n for n in nodes if getattr(n, "name", None) == "_verify_digest")
        for n in verify.body:
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and \
                    "hashlib.sha256" in ast.unparse(n.test):
                n.test = ast.Constant(value=False)
                hits += 1
    require(hits == 1, "mutation must match exactly once")
    return nodes


def load_slice(nodes):
    # 不拷贝/import 源模块顶层；只编译审核白名单节点。非安全执行隔离。
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future] + nodes, type_ignores=[]))
    log = logging.Logger("zip-lab", level=logging.WARNING)
    log.addHandler(logging.NullHandler())
    env = {"__name__": "reviewed_maf_slice", "Enum": Enum, "io": io, "zipfile": zipfile,
           "hashlib": hashlib, "re": re, "logger": log}
    exec(compile(module, "reviewed-maf-slice", "exec"), env)
    return env


def archive_bytes(entries):
    out = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # zipfile 对重复原名的预期提示。
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as z:
            for name, data in entries:
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                z.writestr(info, data)
    return out.getvalue()


def run_case(env, case):
    norm = env["_normalize_archive_member_name"]
    extract = env["_extract_archive_to_memory"]
    fmt = env["_ArchiveFormat"].ZIP
    def unpack(entries, count=20, size=10000):
        return extract(archive_bytes(entries), fmt, count, size)
    def raises_value(call, message):
        try:
            call()
        except ValueError as exc:
            require(message in str(exc), "wrong ValueError: " + str(exc))
        else:
            raise AssertionError("expected ValueError: " + message)
    if case == "first-order":
        pair = [("a.md", b"FIRST"), ("a.md", b"SECOND")]
        require(unpack(pair) == {"a.md": b"FIRST"}, "first content lost")
        require(unpack(pair[::-1]) == {"a.md": b"SECOND"}, "archive order ignored")
        require(unpack([("A.md", b"A"), ("a.md", b"B")]) == {"A.md": b"A"}, "first spelling lost")
    elif case == "normalized-alias":
        entries = [("./r//A.md", b"first"), ("r\\a.md", b"second"), ("/r/A.md", b"third")]
        require(unpack(entries) == {"r/A.md": b"first"}, "normalized aliases not collapsed")
    elif case == "unicode-lower":
        require(unpack([("straße.md", b"s"), ("STRASSE.md", b"S")]) ==
                {"straße.md": b"s", "STRASSE.md": b"S"}, "casefold merged lower-distinct names")
    elif case == "trailing-dot":
        require(len(unpack([("x.md", b"a"), ("x.md.", b"b")])) == 2, "trailing dot merged")
    elif case == "count-before-dedup":
        raises_value(lambda: unpack([("a", b"a"), ("a", b"b")], count=1), "file count")
        raises_value(lambda: unpack([(".", b""), ("a", b"a")], count=1), "file count")
        require(unpack([("d/", b""), ("a", b"a")], count=1) == {"a": b"a"}, "directory counted")
    elif case == "skipped-no-read":
        raw = archive_bytes([("A.md", b"x"), ("a.md", b"z" * 4096)])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            # 真 ZipFile、真 ZipExtFile；wraps 只观测，不返回假内容。
            with patch.object(z, "open", wraps=z.open) as opened:
                with patch.object(zipfile.ZipExtFile, "read", autospec=True,
                                  side_effect=zipfile.ZipExtFile.read) as reads:
                    result = env["_extract_zip_to_memory"](z, 2, 1)
                    require(result == {"A.md": b"x"}, "duplicate spent byte budget")
                    require(opened.call_count == 1, "skipped duplicate opened")
                    require(opened.call_args.args[0] is z.infolist()[0], "wrong ZipInfo opened")
                    require(reads.call_count == 2, "expected data read then EOF only")
    elif case == "actual-byte-budget":
        raises_value(lambda: unpack([("a", b"xy")], size=1), "uncompressed size")
        require(unpack([("a", b"x"), ("b", b"y")], size=2) == {"a": b"x", "b": b"y"}, "shared exact budget")
        raises_value(lambda: unpack([("a", b"x"), ("b", b"y")], size=1), "uncompressed size")
    elif case == "path-boundary":
        require(norm("/a//./b") == "a/b", "root stripping")
        require(norm(".") is None and norm("/") is None, "degenerate path")
        raises_value(lambda: norm("a/../b"), "escape")
        raises_value(lambda: unpack([("ok", b"x"), ("../bad", b"y")]), "escape")
        require(norm("%2e%2e/x") == "%2e%2e/x", "archive normalizer unexpectedly percent-decodes")
    elif case == "digest-mismatch":
        raw = archive_bytes([("a", b"first"), ("a", b"second")])
        verify = env["_verify_digest"]
        entry = SimpleNamespace(name="safe-fixture", digest="sha256:" + hashlib.sha256(raw).hexdigest())
        require(verify(entry, raw), "matching digest rejected")
        expected = extract(raw, fmt, 20, 10000)
        # 原创门控，不代表执行了 _download；验证器自身是真实源码。
        gated = extract(raw, fmt, 20, 10000) if verify(entry, raw) else None
        require(gated == expected == {"a": b"first"}, "digest changes collision policy")
        other = archive_bytes([("a", b"second"), ("a", b"first")])
        require(not verify(entry, other), "old digest accepted reordered archive")
        entry.digest = "sha256:" + "0" * 64
        require(not verify(entry, raw), "mismatch accepted")
        for bad in [None, 42, "SHA256:" + "0" * 64, "sha256:" + "A" * 64, "sha256:abc"]:
            entry.digest = bad
            require(not verify(entry, raw), "invalid digest syntax accepted")
    elif case == "skill-selection":
        files = unpack([("z/SKILL.md", b"z"), ("a/SKILL.md", b"a"),
                        ("a/skill.md", b"later"), ("a/reference.md", b"ok")])
        require(env["_find_skill_md"](files) == "a/SKILL.md", "tie is lexical, not archive first")
        require(files["a/SKILL.md"] == b"a" and files["a/reference.md"] == b"ok", "collision blocked unrelated file")
        files["SKILL.md"] = b"root"
        require(env["_find_skill_md"](files) == "SKILL.md", "shallowest selection")
    elif case == "format-boundary":
        detect = env["_detect_archive_format"]
        require(detect(b"\x1f\x8bxx", "application/zip", "x.zip") is env["_ArchiveFormat"].UNKNOWN, "gzip hint bypass")
        require(detect(archive_bytes([]), None, None) is fmt, "empty ZIP magic")
    else:
        raise AssertionError("unknown case")


CASES = ["first-order", "normalized-alias", "unicode-lower", "trailing-dot",
         "count-before-dedup", "skipped-no-read", "actual-byte-budget", "path-boundary",
         "digest-mismatch", "skill-selection", "format-boundary"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="预先核验的固定提交完整 _skills.py")
    parser.add_argument("--execution-go", required=True, choices=["INDEPENDENT_REVIEW_APPROVED"])
    args = parser.parse_args()
    nodes = select_source(args.source.read_bytes())
    baseline = load_slice(nodes)
    checks = []
    for case in CASES:
        try:
            run_case(baseline, case)
        except Exception as exc:
            checks.append({"case": case, "status": "FAIL", "error": type(exc).__name__ + ": " + str(exc)})
        else:
            checks.append({"case": case, "status": "PASS"})
    mutations = []
    if all(c["status"] == "PASS" for c in checks):
        for mutation, case in MUTATIONS.items():
            # 编译/载入错误不计作 killed；异常将导致非零退出，不能蒙混通过。
            env = load_slice(mutated(nodes, mutation))
            try:
                run_case(env, case)
            except AssertionError as exc:
                mutations.append({"mutation": mutation, "case": case, "status": "KILLED", "error": str(exc)})
            except Exception as exc:
                mutations.append({"mutation": mutation, "case": case, "status": "ERROR", "error": type(exc).__name__ + ": " + str(exc)})
            else:
                mutations.append({"mutation": mutation, "case": case, "status": "SURVIVED"})
    success = all(c["status"] == "PASS" for c in checks) and len(mutations) == len(MUTATIONS) and all(m["status"] == "KILLED" for m in mutations)
    print(json.dumps({"status": "PASS" if success else "FAIL", "scope": "real-source AST slice; not full SDK",
                      "commit": COMMIT, "source_sha256": SOURCE_SHA256,
                      "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "python": sys.version, "platform": platform.platform(),
                      "unicode_version": unicodedata.unidata_version,
                      "baseline": checks, "mutations": mutations}, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
```
<!-- runner.py:end -->
