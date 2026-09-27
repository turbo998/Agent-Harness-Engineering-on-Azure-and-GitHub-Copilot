# NVIDIA 插件交付：可移植离线验收 lab

**固定源码实测：49 个 unittest 方法通过，0 failures / 0 errors / 0 skipped，退出码 0。** 两个新增负控分别阻止远端额外资产被忽略、错误 release tag 未绑定 manifest 身份；对应两个受控变异均产生断言失败。**不是 production 验证或发布许可**。

文档日期：2026-09-28。实际验证时间为 UTC 2026-09-27T19:27:47.170092+00:00；不把文档日期当作执行日期。

## 对象与源码归属

- 上游：[NVIDIA/NeMo-Relay-Plugins，固定提交 88f0879d1e40c7f77d5c4569657563262e4b63c7](https://github.com/NVIDIA/NeMo-Relay-Plugins/tree/88f0879d1e40c7f77d5c4569657563262e4b63c7)。上游模块标注 NVIDIA CORPORATION & AFFILIATES / Apache-2.0；本附录是原创测试，不嵌入上游函数实现。
- 源码入口：[catalog.py](https://github.com/NVIDIA/NeMo-Relay-Plugins/blob/88f0879d1e40c7f77d5c4569657563262e4b63c7/scripts/catalog.py)、[bundles.py](https://github.com/NVIDIA/NeMo-Relay-Plugins/blob/88f0879d1e40c7f77d5c4569657563262e4b63c7/scripts/bundles.py)、[releases.py](https://github.com/NVIDIA/NeMo-Relay-Plugins/blob/88f0879d1e40c7f77d5c4569657563262e4b63c7/scripts/releases.py)。其余文件用清单相对路径在同一提交定位。此次仅使用已批准本地文件，不重新下载、不校验提交签名。
- 附录包含全部 21 项固定 SHA256。导入前与执行后均校验，固定源码未修改。清单是可复制的数据，不代替源码审核或依赖审核。不要为使测试通过而修改公开清单的 hash。
- **正常 import 真实上游 `scripts` 模块**；真实 jsonschema/TOML、归档、hash 与文件验证。没有复制上游算法、替换 schema 校验、伪造缺失依赖或执行上游 pytest/conftest。
- `schemas/release.schema.json` 是 `catalog.discover()` 读取的必要真实输入，不能删掉或改成 stub。每个平台的 archive、`.sha256`、`.json` metadata 三件套同样必要；`.json` 中的身份、源码提交、严格布尔值、摘要均由真实 `verify_assets` 验证。

## 覆盖与两个新增负控

| 真实入口 | 正控与拒绝边界 |
|---|---|
| `make_plan` / `validate_source_tag_pins` | 五平台矩阵、tag/SHA 绑定、错误 pin 时 host 零调用、仅测试文件 PR、branch 的明确不解析语义 |
| `verify_assets` | 完整平台三件套、身份/source commit、严格布尔值、archive/sidecar hash、缺失平台与额外本地文件 |
| `verify_bundle` | native/worker/Python 入口、attributions、入口摘要、tar/zip 往返、zip 路径穿越 |
| `publish_draft` | POST 新草稿、同身份 PATCH、坏资产/移动 tag/已发布/身份错误/竞态、上传后的名字与大小检查 |
| GitHub 适配器 | 精确 argv、JSON stdin、分页终止、异常传播；仅调用 mock，不执行 gh |

新增 `test_review_remote_extra_asset_rejected`：在正确远端资产集合中追加 `unexpected-remote.bin`，断言 `asset set` 错误，并确认 mock upload 已调用一次。这是**上传后**拒绝，不能宣称零上传。

新增 `test_review_invalid_release_tag_zero_api`：使用 `wrong-plugin-0.0.0`，断言 `invalid plugin release tag`，并确认 `api`、`pages`、`upload`、`release_notes` 全部零调用。

针对“只检查预期键，忽略额外远端资产”和“移除 release tag 校验”的既有独立变异副本，新 runner 各运行 49 个方法，均得到 **1 failure / 0 errors / 0 skipped，退出码 1**。失败来自对应新增测试的 AssertionError，不以导入失败或 hash 拒绝冒充测试杀死变异。变异副本使用独立、明确调整的清单，不改正常基线；这证明两个测试盲区已补齐，不证明上游存在这两个缺陷，也不是统计覆盖率。未在本次重跑全部其他变异。

49 是方法数，subTest 不另计；业务 branch intentional skip 不是 unittest skip。远端缺失资产、重复名称不是这两个新增方法的专门测试；不要由本结果推导所有集合边界均覆盖。

## 可复制运行方式

环境前提：Linux 支持并允许 `unshare -Urn`，已有组织批准的 Python 3.11+ 和下述依赖。跨平台指的是测试的 manifest 平台矩阵，**不是声称隔离命令能在 Windows/macOS 原生执行**。不支持 user/network namespace 的主机应停止，不回退到无隔离运行。

1. 从附录复制 hash JSON 为当前目录的 `source-hashes.json`，复制最后一个 Python 代码块为 `portable_acceptance.py`。
2. 将已独立取得并审核的同提交 21 项文件按清单目录结构放到当前目录的 `approved-source`。这不是完整可构建 checkout；本命令不会获取、安装或构建上游。
3. 选择已批准、已有依赖的 Python 解释器；若 `python3` 不是该环境，显式设置 `PYTHON` 为批准解释器的绝对路径。不要运行自动安装脚本。
4. 在三份输入文件之外建立一次性工作目录；输出和 fixture 只写此目录。每次使用新目录，runner 拒绝复用非空目录。

```sh
set -eu
PYTHON="${PYTHON:-$(command -v python3)}"
case "$PYTHON" in /*) ;; *) printf '%s\n' 'PYTHON must be an approved absolute executable path' >&2; exit 2 ;; esac
SOURCE="$(pwd)/approved-source"
MANIFEST="$(pwd)/source-hashes.json"
RUNNER="$(pwd)/portable_acceptance.py"
WORK="$(mktemp -d "$(pwd)/nvidia-lab.XXXXXX")"
unshare -Urn -- env -i HOME="$WORK" TMPDIR="$WORK" PATH=/usr/bin:/bin \
  "$PYTHON" -I -B "$RUNNER" \
  --source "$SOURCE" --manifest "$MANIFEST" --work-dir "$WORK"
```

机器结果生成在 `$WORK/execution.json`，包含完整 test ID、错误详情、环境版本、源码前后 hash 与真实函数调用事件；失败或跳过返回非零。不要在运行前把日志重定向到工作目录内，否则该目录不再为空。保留或人工清理自己创建的一次性目录，runner 不自动删除证据。

`--source`、`--manifest`、`--work-dir` 全部必填，无作者机器路径。解析为真实路径后，工作目录不能等于、包含或位于 source 内，也不能包含 manifest 或 runner；存在符号链接时按其解析目标检查。源码条目必须落在 source 内。已实测同源码目录、源码子目录、源码父目录、manifest 父目录、manifest 文件本身、runner 父目录均在写入前拒绝。该检查仍不是抵抗并发目录替换的 OS 文件沙箱。

## 依赖与安全边界

实测 Python：`3.11.15 (main, Apr 7 2026, 20:48:58) [Clang 22.1.1]`。

| 依赖 | 实测版本 | 上游 uv.lock |
|---|---|---|
| jsonschema | 4.26.0 | 4.26.0 |
| rpds-py | 0.30.0 | 2026.6.3 |
| referencing | 0.37.0 | 0.37.0 |
| attrs | 26.1.0 | 26.1.0 |
| jsonschema-specifications | 2025.9.1 | 2025.9.1 |
| typing-extensions | 4.15.0 | 4.16.0 |

这是固定源码加已记录依赖环境的结果，**不是上游 lock 环境完全复现**。不需要上游 conftest 使用的 tomli_w；没有导入 conftest，也没有用 dummy 替代。

- 解释器启动前以 `unshare -Urn` 建立 user/network namespace；`env -i` 去掉原环境凭据；`-I -B` 隔离 Python 环境变量并禁止 pyc。Python 可能补入 locale 键。
- Python/site 和可信已安装依赖先初始化，再装 audit hook，再正常导入上游。依赖初始化不受该 hook 保护。
- hook 拒绝进程/socket 审计事件与工作目录外的审计写入；业务 subprocess 全局拒绝 mock，GitHub api/pages/upload 与 release_notes 按测试显式 mock。三个 guard 实测拒绝 socket、Popen、目录外写入。适配器专项测试只核对 mock 的 argv，无真实 gh/git 调用。
- **audit hook 不是 OS 文件沙箱**；网络 namespace 不提供只读 mount 或 AF_UNIX 完全隔离，不能抵抗恶意 native 代码、未覆盖 syscall 或 TOCTOU。本 lab 不运行敌对源码，不提供内核全量 syscall 追踪证明。
- 合成 `verified=true` 只是 fixture 声明，不是实际插件执行证据。没有构建、安装、host 下载、runtime smoke、真实 GitHub 发布、release_notes/git diff 执行、wheel/crate 来源验证、签名或 attestation。
- 上传后只比远端名字/大小，错误 digest 字段仍通过；不验证远端内容 SHA。Python 只 hash 入口，辅助模块改动仍通过；本地额外目录会被忽略。这些限制保留为显式通过用例。
- 函数 profile call 事件仅证明入口被调用，不是行覆盖率；generator resume 会重复产生 call 事件。

以下结果摘要、完整固定 hash 数据和 runner 代码一并提供；不依赖任何私有报告或作者目录。

## Observed result

```json
{
  "observed_at_utc": "2026-09-27T19:27:47.170092+00:00",
  "tests_run": 49,
  "failures": 0,
  "errors": 0,
  "skipped": 0,
  "source_unchanged": true,
  "blocked_audit_events": [
    "subprocess.Popen",
    "socket.__new__"
  ],
  "real_entry_profile_call_events": {
    "scripts.plugins.make_plan": 4,
    "scripts.plugins.validate_source_tag_pins": 7,
    "scripts.bundles.verify_assets": 48,
    "scripts.bundles.verify_bundle": 12,
    "scripts.bundles.create_archive": 107,
    "scripts.bundles.extract_archive": 3,
    "scripts.releases.publish_draft": 12,
    "scripts.host.resolve_tag": 16,
    "scripts.github.GitHub.api": 2,
    "scripts.github.GitHub.pages": 102,
    "scripts.github.GitHub.upload": 1
  }
}
```

## Appendix A: complete fixed source hash JSON

Save as `source-hashes.json`. Fixed source URL template: `https://raw.githubusercontent.com/NVIDIA/NeMo-Relay-Plugins/COMMIT/PATH`. Substitute the commit and path below; this is not a download command.

```json
{
  "commit": "88f0879d1e40c7f77d5c4569657563262e4b63c7",
  "verified_downloads": [
    {
      "path": "scripts/__init__.py",
      "sha256": "7a9aa82b4939e48c4ed5132b1878b14c31915366d7ca40cc596e3c3918571e63"
    },
    {
      "path": "scripts/plugins.py",
      "sha256": "bb940f50dccd58b25baae183b1814c051747ab5adfee005d3edbb4840c2ea8bf"
    },
    {
      "path": "scripts/bundles.py",
      "sha256": "7142ce083f907abe6a3d459708e2d41459bce6b066082c624299ce72440d8a4f"
    },
    {
      "path": "scripts/catalog.py",
      "sha256": "ea47f2d536fe20344273aa8f7edf14fae5dcac919820b8dac3b2419f329759f9"
    },
    {
      "path": "scripts/host.py",
      "sha256": "5b4102570e9a7d23202136e3701f88cfee08a1b8dc43faa2a3b286f48a8b804c"
    },
    {
      "path": "scripts/releases.py",
      "sha256": "c6a3a00b281f48f6101bc35b22f62f8deb80fcce926719e46579fb82314e35a9"
    },
    {
      "path": "scripts/github.py",
      "sha256": "a6e449b5ebda5595127f8d2abcdebb138447e2f59991dc481dd9b6a49eed7ae6"
    },
    {
      "path": "scripts/package_sources.py",
      "sha256": "155ed1d1feed48bea700c39818a431cf9f02d6816f81064db04eb323dc63d0a7"
    },
    {
      "path": "pyproject.toml",
      "sha256": "b96e26b90a6534e9e39802792c4039f89683a4daec3f95a253f00878bd619e5c"
    },
    {
      "path": "tests/conftest.py",
      "sha256": "c7018960aa5076a8f7c9c104d891507aa4a5f96c60fb45ad913b26e2b2580147"
    },
    {
      "path": "tests/test_catalog.py",
      "sha256": "405b3c9e9edf450e36a896789b9dbc30a51ba208e3763b45009d07d87db93585"
    },
    {
      "path": "tests/test_bundles.py",
      "sha256": "1d26b800db6ea0b2e8c18bc49c12a422a70971c30b24c65c0c26ee3b22e90867"
    },
    {
      "path": "tests/test_host.py",
      "sha256": "5e838629d07e58c95ff441e475bf05af413e96bcf5d1b7a75e799aa5d99e0511"
    },
    {
      "path": "tests/test_releases.py",
      "sha256": "b823f5881fc6e7c8608c46d35bd972692d2a2dd049bd2ccf1535ddd2f62a4d71"
    },
    {
      "path": "tests/test_plugin_commands.py",
      "sha256": "8825bb7b7a9085e43cddbc95e5c78fd91f4aa58549cab0167962a6d4f54a054e"
    },
    {
      "path": "plugins/example-python-grpc-worker-plugin/release.toml",
      "sha256": "0d9e5dc6e41ec3130526da841eb943dc165d655942ab5f3776c1b70af21ac076"
    },
    {
      "path": "plugins/example-rust-grpc-worker-plugin/release.toml",
      "sha256": "ad2b7d53ecac3c0091df1394e849f9a3291c2b8861ba66401204e430a9c1d6b3"
    },
    {
      "path": "plugins/example-rust-native-plugin/release.toml",
      "sha256": "8d283b6cab49e1523e42be4618b2daface8496710449652b72b0fbe48bbbbe9b"
    },
    {
      "path": "plugins/switchyard-plugin/release.toml",
      "sha256": "75c28829dc16908ccd73c8fd984fda94099770883b72d5138ed7b99c61959050"
    },
    {
      "path": "schemas/release.schema.json",
      "sha256": "f052bd28b78e4a9db567950dcd8989f7615bdf92471f0788fe4812b849042f44"
    },
    {
      "path": "uv.lock",
      "sha256": "810f187769c10d998a6ffa0aaefb4d1bda2a01000c8c1bc0e954cbff3eace272"
    }
  ]
}
```

## Appendix B: complete portable runner

Save as `portable_acceptance.py`. SHA256: `26ce1c11fec8c4f553e0c2a4527df47e85a7c6c1db336ee49f3262ec9044ee16`. This code block is byte-identical to the executed runner.

```python
"""Original offline acceptance harness; invokes pinned NVIDIA modules, not copied logic."""
import sys
sys.dont_write_bytecode = True
import os, json, hashlib, tempfile, copy, unittest, subprocess, socket, time, argparse, re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, call
import importlib.metadata as metadata

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path, help='Approved local source root; read only')
parser.add_argument('--manifest', required=True, type=Path, help='Local 21-file SHA256 JSON from the appendix')
parser.add_argument('--work-dir', required=True, type=Path, help='New or empty disposable directory')
args = parser.parse_args()
SOURCE = args.source.resolve(strict=True)
MANIFEST_PATH = args.manifest.resolve(strict=True)
LAB = args.work_dir.resolve()
if not SOURCE.is_dir() or not MANIFEST_PATH.is_file():
    parser.error('source must be a directory and manifest must be a file')
if (LAB.is_relative_to(SOURCE) or SOURCE.is_relative_to(LAB)
        or MANIFEST_PATH.is_relative_to(LAB)
        or Path(__file__).resolve().is_relative_to(LAB)):
    parser.error('work-dir must not overlap source, manifest, or runner')
if LAB.exists() and (not LAB.is_dir() or any(LAB.iterdir())):
    parser.error('work-dir must be new or empty; existing results are never overwritten')
PREFLIGHT = json.loads(MANIFEST_PATH.read_text())
EXPECTED_PATHS = {
    'scripts/__init__.py', 'scripts/plugins.py', 'scripts/bundles.py',
    'scripts/catalog.py', 'scripts/host.py', 'scripts/releases.py',
    'scripts/github.py', 'scripts/package_sources.py', 'pyproject.toml',
    'tests/conftest.py', 'tests/test_catalog.py', 'tests/test_bundles.py',
    'tests/test_host.py', 'tests/test_releases.py', 'tests/test_plugin_commands.py',
    'plugins/example-python-grpc-worker-plugin/release.toml',
    'plugins/example-rust-grpc-worker-plugin/release.toml',
    'plugins/example-rust-native-plugin/release.toml',
    'plugins/switchyard-plugin/release.toml', 'schemas/release.schema.json', 'uv.lock',
}
entries = PREFLIGHT.get('verified_downloads', [])
if (PREFLIGHT.get('commit') != '88f0879d1e40c7f77d5c4569657563262e4b63c7'
        or len(entries) != 21 or {e['path'] for e in entries} != EXPECTED_PATHS
        or any(not re.fullmatch('[0-9a-f]{64}', e['sha256']) for e in entries)):
    parser.error('manifest must contain the fixed commit and exactly 21 unique relative paths with SHA256')
for entry in entries:
    target = (SOURCE / entry['path']).resolve(strict=True)
    if not target.is_relative_to(SOURCE) or not target.is_file():
        parser.error('source entries must resolve to files inside source')
# Trusted installed dependencies initialize before the audit hook. No install is performed.
import jsonschema, rpds, referencing, attrs, jsonschema_specifications
VERSIONS = {n: metadata.version(n) for n in ('jsonschema', 'rpds-py', 'referencing', 'attrs', 'jsonschema-specifications', 'typing-extensions')}

def hashes():
    result = {}
    for entry in PREFLIGHT['verified_downloads']:
        actual = hashlib.sha256((SOURCE / entry['path']).read_bytes()).hexdigest()
        if actual != entry['sha256']:
            raise RuntimeError('Pinned source changed: ' + entry['path'])
        result[entry['path']] = actual
    return result

BEFORE = hashes()
LAB.mkdir(parents=True, exist_ok=True)
BLOCKED = []

def writable(path):
    if isinstance(path, int):
        raise PermissionError('write via raw fd blocked')
    if not Path(os.fsdecode(path)).resolve().is_relative_to(LAB.resolve()):
        raise PermissionError('write outside lab blocked')

def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec', 'pty.spawn'):
        BLOCKED.append(event)
        raise PermissionError('process/network audit denial: ' + event)
    if event == 'open':
        path, mode, flags = args
        if (mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            writable(path)
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate'):
        writable(args[0])
    elif event in ('os.rename', 'os.link', 'os.symlink'):
        writable(args[0]); writable(args[1])

sys.addaudithook(audit)
sys.path.insert(0, str(SOURCE))
from scripts import catalog, plugins, bundles, releases, host
from scripts.github import GitHub
for module in (catalog, plugins, bundles, releases, host):
    assert Path(module.__file__).resolve().is_relative_to(SOURCE)
MANIFESTS = catalog.discover(root=SOURCE)
HEAD = 'a' * 40
NAME = 'switchyard-plugin'

class Acceptance(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=LAB))
        self.m = copy.deepcopy(MANIFESTS[NAME])
        self.gh = Mock(spec=GitHub)
        self.gh.api.side_effect = AssertionError('unexpected GitHub API boundary')
        self.gh.pages.side_effect = AssertionError('unexpected GitHub pages boundary')
        self.gh.upload.side_effect = AssertionError('unexpected upload boundary')
        self.process_mocks = []
        for name in ('run', 'Popen', 'check_output', 'check_call', 'call'):
            p = patch.object(subprocess, name, side_effect=AssertionError('unexpected subprocess boundary'))
            self.process_mocks.append(p.start()); self.addCleanup(p.stop)
        self.addCleanup(self.check_processes)

    def check_processes(self):
        for mock in self.process_mocks:
            mock.assert_not_called()

    def tag_reply(self, sha=None):
        self.gh.api.side_effect = None
        self.gh.api.return_value = {'object': {'type': 'commit', 'sha': sha or self.m['source']['sha']}}

    def plan(self):
        return plugins.make_plan({NAME: self.m}, {}, 'push', 'refs/heads/main', HEAD, self.gh, root=SOURCE)

    def assets(self):
        directory = self.work / 'assets'; directory.mkdir()
        # Real archive creation over inert bytes; no binary is executed.
        bundle = self.work / 'payload'; bundle.mkdir()
        (bundle / 'inert.txt').write_text('acceptance fixture, not a built plugin\n')
        for platform in self.m['platforms']:
            name = bundles.archive_name(self.m, platform)
            archive = directory / name
            bundles.create_archive(bundle, archive, 'fixture')
            digest = bundles.sha256(archive)
            data = dict(name=self.m['name'], version=self.m['version'], platform=platform,
                        repository_commit=HEAD, source_commit=self.m['source']['sha'],
                        local_host_override=False, repository_dirty=False, verified=True,
                        relay={'sha': 'b' * 40}, sha256=digest)
            (directory / (name + '.json')).write_text(json.dumps(data))
            (directory / (name + '.sha256')).write_text(f'{digest}  {name}\n')
        self.directory = directory
        self.meta = directory / (bundles.archive_name(self.m, self.m['platforms'][0]) + '.json')
        return directory

    def verify(self):
        return bundles.verify_assets(self.m, self.directory, HEAD)

    def bundle(self, kind='native', load=None):
        directory = self.work / ('bundle-' + kind); directory.mkdir()
        (directory / 'entry.bin').write_bytes(b'inert entry bytes')
        (directory / 'other.bin').write_bytes(b'other inert bytes')
        (directory / 'ATTRIBUTIONS-lab.md').write_text('Original synthetic fixture; no redistributed binary.')
        key = 'library' if kind == 'native' else 'entrypoint'
        runtime_kind = 'rust_dynamic' if kind == 'native' else 'worker'
        text = (f'[plugin]\nkind = "{runtime_kind}"\n[source]\nartifact = "entry.bin"\n'
                f'[integrity]\nsha256 = "sha256:{bundles.sha256(directory / "entry.bin")}"\n'
                f'[load]\n{key} = "{load or "entry.bin"}"\n')
        (directory / 'relay-plugin.toml').write_text(text)
        return directory

    def publication(self, existing=None, moved=False, remote_change=None, race=False):
        self.assets()
        tag = f'{NAME}-{self.m["version"]}'
        endpoint = 'repos/offline/example/releases'
        files = bundles.verify_assets(self.m, self.directory, HEAD)
        remote = [{'name': f.name, 'size': f.stat().st_size} for f in files]
        if remote_change: remote_change(remote)
        def api(path, method='GET', body=None):
            if path == f'repos/offline/example/git/ref/tags/{tag}' and method == 'GET':
                return {'object': {'type': 'commit', 'sha': 'c' * 40 if moved else HEAD}}
            if path in (endpoint, endpoint + '/7') and method in ('GET', 'POST', 'PATCH'):
                return {'id': 7, 'draft': not race}
            raise AssertionError((path, method, body))
        def pages(path):
            if path == endpoint: return [] if existing is None else [existing]
            if path == endpoint + '/7/assets': return remote
            raise AssertionError(path)
        self.gh.api.side_effect = api; self.gh.pages.side_effect = pages
        self.gh.upload.side_effect = None
        self.tag = tag

    def publish(self):
        return releases.publish_draft(self.m, self.tag, HEAD, 'offline/example', self.directory, self.gh, root=SOURCE)

    def existing(self, draft=True, match=True):
        identity = {'name': NAME, 'version': self.m['version'], 'commit': HEAD if match else 'd' * 40}
        return {'id': 7, 'tag_name': f'{NAME}-{self.m["version"]}', 'draft': draft,
                'body': '<!-- relay-plugin-release: ' + json.dumps(identity) + ' -->'}

    def no_mutations(self):
        self.gh.upload.assert_not_called()
        self.assertFalse([c for c in self.gh.api.call_args_list if len(c.args) > 1 and c.args[1] != 'GET'])

    def test_catalog_real_schema_and_four_manifests(self):
        self.assertEqual(len(MANIFESTS), 4)
        self.assertEqual(set(self.m['platforms']), set(catalog.PLATFORMS))

    def test_validate_pin_positive(self):
        self.tag_reply()
        self.assertIsNone(plugins.validate_source_tag_pins([self.m], self.gh))
        self.gh.api.assert_called_once_with('repos/NVIDIA-NeMo/Switchyard/git/ref/tags/v0.3.0')

    def test_validate_pin_negative(self):
        self.tag_reply('c' * 40)
        with self.assertRaisesRegex(ValueError, 'source.sha pins'):
            plugins.validate_source_tag_pins([self.m], self.gh)

    def test_make_plan_positive_five_platforms(self):
        self.tag_reply()
        with patch.object(plugins, 'resolve_host', return_value={'sha': 'b' * 40}) as resolve:
            result = self.plan()
        self.assertEqual({r['platform'] for r in result['matrix']['include']}, set(catalog.PLATFORMS))
        self.assertEqual(result['commit'], HEAD)
        self.assertEqual(result['ref'], 'refs/heads/main')
        resolve.assert_called_once_with({}, self.gh)

    def test_make_plan_pin_mismatch_zero_host(self):
        self.tag_reply('c' * 40)
        with patch.object(plugins, 'resolve_host') as resolve:
            with self.assertRaisesRegex(ValueError, 'source.sha pins'): self.plan()
            resolve.assert_not_called()
        self.gh.api.assert_called_once()

    def test_source_branch_intentionally_skips_pin(self):
        self.m['source']['ref'] = 'refs/heads/main'
        plugins.validate_source_tag_pins([self.m], self.gh)
        with patch.object(plugins, 'resolve_host', return_value={'sha': 'b' * 40}):
            self.assertTrue(self.plan()['matrix']['include'])
        self.gh.api.assert_not_called()

    def test_test_only_pr_zero_host_and_tag(self):
        event = {'pull_request': {'base': {'sha': 'b' * 40}, 'head': {'sha': HEAD}}}
        with patch.object(plugins, 'changed_paths', return_value=['tests/test_catalog.py']) as changed, patch.object(plugins, 'resolve_host') as resolve:
            result = plugins.make_plan({NAME:self.m}, event, 'pull_request', 'refs/pull/1/merge', HEAD, self.gh, root=SOURCE)
            resolve.assert_not_called()
            changed.assert_called_once_with('b' * 40, HEAD, pull_request=True, root=SOURCE)
        self.assertEqual(result['matrix']['include'], [])
        self.assertEqual(result['hosts'], {})
        self.gh.api.assert_not_called()

    def test_resolve_annotated_tag_positive(self):
        self.gh.api.side_effect = [{'object': {'type':'tag','sha':'d'*40}}, {'object':{'type':'commit','sha':HEAD}}]
        self.assertEqual(host.resolve_tag('v1', self.gh, 'offline/example'), HEAD)
        self.assertEqual(self.gh.api.call_count, 2)

    def test_resolve_annotated_cycle_negative(self):
        self.gh.api.side_effect = None
        self.gh.api.return_value = {'object': {'type':'tag','sha':'d'*40}}
        with self.assertRaisesRegex(ValueError, 'cyclic'): host.resolve_tag('v1', self.gh)
        self.assertEqual(self.gh.api.call_count, 2)

    def test_assets_positive_complete_platform_set(self):
        self.assets(); self.assertEqual(len(self.verify()), 3 * len(self.m['platforms']))

    def test_assets_missing_platform_negative(self):
        self.assets()
        name = bundles.archive_name(self.m, self.m['platforms'][-1])
        for suffix in ('', '.json', '.sha256'): (self.directory / (name + suffix)).unlink()
        with self.assertRaises(FileNotFoundError): self.verify()

    def test_assets_verified_strict_boolean_type(self):
        self.assets(); original = json.loads(self.meta.read_text())
        for value in (1, 'true', False, None):
            with self.subTest(value=value):
                self.meta.write_text(json.dumps(dict(original, verified=value)))
                with self.assertRaisesRegex(ValueError, 'runtime verification'): self.verify()
        self.meta.write_text(json.dumps(original)); self.verify()

    def test_assets_dirty_override_strict_boolean_type(self):
        self.assets(); original = json.loads(self.meta.read_text())
        for key in ('repository_dirty', 'local_host_override'):
            for value in (0, True, 'false', None):
                with self.subTest(key=key, value=value):
                    self.meta.write_text(json.dumps(dict(original, **{key:value})))
                    with self.assertRaises(ValueError): self.verify()
        self.meta.write_text(json.dumps(original)); self.verify()

    def test_assets_identity_and_source_negative(self):
        self.assets(); original = json.loads(self.meta.read_text())
        for key in ('name', 'version', 'platform', 'repository_commit', 'source_commit'):
            with self.subTest(key=key):
                self.meta.write_text(json.dumps(dict(original, **{key:'wrong'})))
                with self.assertRaisesRegex(ValueError, 'mismatch'): self.verify()

    def test_assets_archive_tampering_negative(self):
        self.assets()
        archive = self.directory / bundles.archive_name(self.m, self.m['platforms'][0])
        archive.write_bytes(archive.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'): self.verify()

    def test_assets_sidecar_filename_negative(self):
        self.assets()
        archive = self.directory / bundles.archive_name(self.m, self.m['platforms'][0])
        Path(str(archive) + '.sha256').write_text(bundles.sha256(archive) + '  wrong-name\n')
        with self.assertRaisesRegex(ValueError, 'checksum'): self.verify()

    def test_assets_extra_file_negative(self):
        self.assets(); (self.directory / 'unexpected').write_text('x')
        with self.assertRaisesRegex(ValueError, 'unexpected/missing'): self.verify()

    def test_assets_extra_directory_limitation(self):
        self.assets(); (self.directory / 'ignored-directory').mkdir()
        self.assertEqual(len(self.verify()), 3 * len(self.m['platforms']))

    def test_bundle_native_positive(self):
        self.assertEqual(bundles.verify_bundle(self.bundle(), 'relay-plugin.toml', 'native')['plugin']['kind'], 'rust_dynamic')

    def test_bundle_native_load_mismatch_negative(self):
        with self.assertRaisesRegex(ValueError, 'loaded library'):
            bundles.verify_bundle(self.bundle(load='other.bin'), 'relay-plugin.toml', 'native')

    def test_bundle_worker_positive(self):
        bundles.verify_bundle(self.bundle('worker'), 'relay-plugin.toml', 'worker')

    def test_bundle_worker_load_mismatch_negative(self):
        with self.assertRaisesRegex(ValueError, 'worker executable'):
            bundles.verify_bundle(self.bundle('worker', 'other.bin'), 'relay-plugin.toml', 'worker')

    def test_bundle_digest_tampering_negative(self):
        directory = self.bundle(); (directory / 'entry.bin').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'): bundles.verify_bundle(directory, 'relay-plugin.toml', 'native')

    def test_bundle_attributions_required(self):
        directory = self.bundle(); (directory / 'ATTRIBUTIONS-lab.md').unlink()
        with self.assertRaisesRegex(ValueError, 'ATTRIBUTIONS'): bundles.verify_bundle(directory, 'relay-plugin.toml', 'native')

    def test_publish_new_draft_positive(self):
        self.publication()
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            self.assertEqual(self.publish()['id'], 7)
        writes = [c for c in self.gh.api.call_args_list if len(c.args) > 1]
        self.assertEqual(len(writes), 1); self.assertEqual(writes[0].args[1], 'POST')
        self.assertIs(writes[0].args[2]['draft'], True)
        self.gh.upload.assert_called_once_with('offline/example', self.tag, bundles.verify_assets(self.m, self.directory, HEAD))

    def test_publish_same_identity_retry_patch(self):
        self.publication(existing=self.existing())
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'): self.publish()
        writes = [c for c in self.gh.api.call_args_list if len(c.args) > 1]
        self.assertEqual([c.args[1] for c in writes], ['PATCH'])
        self.assertIs(writes[0].args[2]['draft'], True)
        self.gh.upload.assert_called_once()

    def test_publish_bad_assets_zero_api_upload(self):
        self.publication(); self.meta.unlink()
        with patch.object(releases, 'release_notes') as notes:
            with self.assertRaises(FileNotFoundError): self.publish()
            notes.assert_not_called()
        self.gh.api.assert_not_called(); self.gh.pages.assert_not_called(); self.no_mutations()

    def test_publish_moved_tag_zero_mutations(self):
        self.publication(moved=True)
        with patch.object(releases, 'release_notes') as notes:
            with self.assertRaisesRegex(ValueError, 'moved'): self.publish()
            notes.assert_not_called()
        self.no_mutations(); self.gh.pages.assert_not_called()

    def test_publish_published_zero_mutations(self):
        self.publication(existing=self.existing(draft=False))
        with patch.object(releases, 'release_notes') as notes:
            with self.assertRaisesRegex(ValueError, 'refusing'): self.publish()
            notes.assert_not_called()
        self.no_mutations()

    def test_publish_wrong_identity_zero_mutations(self):
        self.publication(existing=self.existing(match=False))
        with patch.object(releases, 'release_notes') as notes:
            with self.assertRaisesRegex(ValueError, 'refusing'): self.publish()
            notes.assert_not_called()
        self.no_mutations()

    def test_publish_race_zero_upload(self):
        self.publication(existing=self.existing(), race=True)
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            with self.assertRaisesRegex(ValueError, 'published while'): self.publish()
        self.no_mutations()

    def test_publish_remote_size_mismatch_negative_after_upload(self):
        self.publication(remote_change=lambda rows: rows[0].update(size=rows[0]['size'] + 1))
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            with self.assertRaisesRegex(ValueError, 'asset set'): self.publish()
        self.gh.upload.assert_called_once()

    def test_publish_remote_filename_mismatch_negative_after_upload(self):
        self.publication(remote_change=lambda rows: rows[0].update(name='wrong-name'))
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            with self.assertRaisesRegex(ValueError, 'asset set'): self.publish()
        self.gh.upload.assert_called_once()

    def test_publish_same_name_size_wrong_digest_limitation(self):
        # These remote hash fields are ignored: success is NOT remote-content verification.
        self.publication(remote_change=lambda rows: [r.update(digest='sha256:' + '0' * 64) for r in rows])
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            self.assertEqual(self.publish()['id'], 7)
        self.gh.upload.assert_called_once()

    def python_bundle(self):
        directory = self.work / 'python-bundle'; directory.mkdir()
        package = directory / 'package'; package.mkdir()
        (package / 'pyproject.toml').write_text('[project]\nname="offline-fixture"\nversion="0.0.0"\n')
        (package / 'entry.py').write_text('# inert; never imported\n')
        (package / 'helper.py').write_text('# unhashed helper\n')
        (directory / 'ATTRIBUTIONS-lab.md').write_text('Original inert fixture')
        text = ('[plugin]\nkind="worker"\n[source]\nartifact="package/entry.py"\nmanifest_root="package"\n'
                '[integrity]\nsha256="sha256:' + bundles.sha256(package / 'entry.py') + '"\n'
                '[load]\nruntime="python"\nentrypoint="entry:main"\n')
        (directory / 'relay-plugin.toml').write_text(text)
        return directory

    def test_bundle_python_positive(self):
        bundles.verify_bundle(self.python_bundle(), 'relay-plugin.toml', 'worker')

    def test_bundle_python_entry_mismatch_negative(self):
        directory = self.python_bundle(); path = directory / 'relay-plugin.toml'
        path.write_text(path.read_text().replace('entry:main', 'helper:main'))
        with self.assertRaisesRegex(ValueError, 'Python entrypoint'):
            bundles.verify_bundle(directory, 'relay-plugin.toml', 'worker')

    def test_bundle_python_package_required(self):
        directory = self.python_bundle(); (directory / 'package/pyproject.toml').unlink()
        with self.assertRaisesRegex(ValueError, 'installable source'):
            bundles.verify_bundle(directory, 'relay-plugin.toml', 'worker')

    def test_bundle_python_unhashed_helper_limitation(self):
        directory = self.python_bundle()
        (directory / 'package/helper.py').write_text('# modified but not integrity target\n')
        bundles.verify_bundle(directory, 'relay-plugin.toml', 'worker')

    def test_real_archive_roundtrip_tar_and_zip(self):
        directory = self.bundle()
        for suffix in ('.tar.gz', '.zip'):
            with self.subTest(suffix=suffix):
                archive = self.work / ('roundtrip' + suffix)
                bundles.create_archive(directory, archive, 'plugin')
                unpacked = bundles.extract_archive(archive, self.work / ('unpack' + suffix))
                self.assertEqual(bundles.sha256(unpacked / 'entry.bin'), bundles.sha256(directory / 'entry.bin'))
                bundles.verify_bundle(unpacked, 'relay-plugin.toml', 'native')

    def test_archive_zip_escape_negative(self):
        import zipfile
        archive = self.work / 'escape.zip'
        with zipfile.ZipFile(archive, 'w') as stream: stream.writestr('../escaped', 'no')
        with self.assertRaisesRegex(ValueError, 'unsafe archive member'):
            bundles.extract_archive(archive, self.work / 'unpack')
        self.assertFalse((self.work / 'escaped').exists())

    def test_github_api_exact_argv_no_real_subprocess(self):
        gh = GitHub()
        with patch.object(subprocess, 'run', return_value=Mock(stdout='{"id":7}')) as run:
            self.assertEqual(gh.api('repos/offline/example/releases', 'POST', {'draft':True}), {'id':7})
            run.assert_called_once_with(['gh','api','repos/offline/example/releases','--method','POST','--input','-'],
                                       input=json.dumps({'draft':True}), capture_output=True, text=True, check=True)

    def test_github_api_process_failure_propagates(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['gh'])) as run:
            with self.assertRaises(subprocess.CalledProcessError): GitHub().api('offline')
            run.assert_called_once()

    def test_github_upload_exact_argv_clobber(self):
        path = self.work / 'file with spaces'
        with patch.object(subprocess, 'run') as run:
            GitHub().upload('offline/example', 'tag', [path])
            run.assert_called_once_with(['gh','release','upload','tag','--repo','offline/example','--clobber',str(path)], check=True)

    def test_github_pages_query_and_termination(self):
        gh = GitHub()
        with patch.object(gh, 'api', side_effect=[list(range(100)), [100]]) as api:
            self.assertEqual(list(gh.pages('offline?state=all')), list(range(101)))
            self.assertEqual(api.call_args_list, [call('offline?state=all&per_page=100&page=1'), call('offline?state=all&per_page=100&page=2')])

    def test_review_remote_extra_asset_rejected(self):
        self.publication(remote_change=lambda rows: rows.append({'name':'unexpected-remote.bin','size':1}))
        with patch.object(releases, 'release_notes', return_value='Offline notes\n'):
            with self.assertRaisesRegex(ValueError, 'asset set'): self.publish()
        self.gh.upload.assert_called_once()

    def test_review_invalid_release_tag_zero_api(self):
        self.assets(); self.tag = 'wrong-plugin-0.0.0'
        with patch.object(releases, 'release_notes') as notes:
            with self.assertRaisesRegex(ValueError, 'invalid plugin release tag'): self.publish()
            notes.assert_not_called()
        self.gh.api.assert_not_called(); self.gh.pages.assert_not_called(); self.gh.upload.assert_not_called()

class GuardChecks(unittest.TestCase):
    def test_audit_socket_denied(self):
        with self.assertRaises(PermissionError): socket.socket()
    def test_audit_process_denied(self):
        with self.assertRaises(PermissionError): subprocess.run(['/bin/true'])
    def test_audit_write_outside_lab_denied(self):
        outside = LAB.parent / (LAB.name + '-must-not-exist')
        self.assertFalse(outside.exists())
        with self.assertRaises(PermissionError): outside.write_text('blocked')
        self.assertFalse(outside.exists())

class Recording(unittest.TextTestResult):
    def startTest(self, test):
        self.ids.append(test.id()); super().startTest(test)
    def __init__(self, *args):
        super().__init__(*args); self.ids = []

if __name__ == '__main__':
    TARGETS = {function.__code__: function.__module__ + '.' + function.__qualname__ for function in
               (plugins.make_plan, plugins.validate_source_tag_pins, bundles.verify_assets, bundles.verify_bundle,
                bundles.create_archive, bundles.extract_archive, releases.publish_draft, host.resolve_tag,
                GitHub.api, GitHub.pages, GitHub.upload)}
    ENTRY_CALLS = {name: 0 for name in TARGETS.values()}
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code in TARGETS:
            ENTRY_CALLS[TARGETS[frame.f_code]] += 1
    sys.setprofile(profile)
    started = time.time()
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance), unittest.defaultTestLoader.loadTestsFromTestCase(GuardChecks)])
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recording).run(suite)
    sys.setprofile(None)
    after = hashes()
    output = dict(real_entry_profile_call_events=ENTRY_CALLS,
                  imported_modules={module.__name__: str(Path(module.__file__).resolve().relative_to(SOURCE)) for module in (catalog, plugins, bundles, releases, host)},
                  status='passed' if result.wasSuccessful() and result.testsRun == 49 and not result.skipped else 'failed',
                  tests_run=result.testsRun, skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                  test_ids=result.ids, failure_details=[(t.id(), tb) for t,tb in result.failures + result.errors],
                  elapsed_seconds=time.time()-started, python=sys.version, dependencies=VERSIONS,
                  source_hashes_before=BEFORE, source_hashes_after=after, source_unchanged=BEFORE == after,
                  blocked_audit_events=BLOCKED, observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  credentials_environment_keys=sorted(os.environ), commit=PREFLIGHT['commit'])
    (LAB / 'execution.json').write_text(json.dumps(output, indent=2) + '\n')
    sys.exit(0 if output['status'] == 'passed' else 1)
```
