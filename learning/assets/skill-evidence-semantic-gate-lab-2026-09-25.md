# S01 Snapshot Equality 语义 Gate 离线 Lab

日期：2026-09-25<br>
性质：公开原创教学 lab。它不是 Codex、Claude Code、ADK 或任何生产系统的 smoke test；也不是安全认证、签名系统或授权服务。`approvals` 与 `manifest` 只代表本 toy 单测中的可信输入，不代表生产签名、认证或身份校验。

## 范围

本 lab 只实现 **S01 snapshot equality toy case**：同一个 `(run_id, case_id, host, host_version, source_revision, snapshot_id)` 下，比较 `approved`、`model`、`materialized` 三视图的 instructions/resources/metadata 投影是否与一个非空 trusted manifest 和批准对象一致。

它不宣称覆盖 C01-C10 的全部 host 语义，也不执行真实 host 采集。测试中的 projected instructions 与 materialized resources 是受控模型 evidence 输入快照。

先前模板来源：

- https://github.com/turbo998/Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot/blob/9cdcaf9e66a57553032434b4e5aa9ad56ed58ec4/learning/assets/skill-snapshot-and-instruction-boundary-gates-2026-09-24.md
- 上述模板原文 SHA-256：`90dc9af846ccefd0d001f0195710f708288ab8000d55953640aeed60b5168798`

## S01 子契约

1. identity 必须跨 `manifest`、`approval`、每条 record、每条 evidence 完全一致。
2. approvals 是可信 toy 映射，key 为完整 identity tuple，value 必须含同 identity、`status=APPROVED` 与 approved 三 hash；不能只检查 snapshot_id 是否存在。
3. records 只能包含 `approved`、`model`、`materialized` 三条，空 records 或重复/缺失 view 一律 `DENY`。
4. evidence_map 的 value 必须是结构化对象：同 identity、同 view、payload。仅 key 命中不算解析成功。
5. verdict 不信任 record 自带 hash；每次从 evidence payload 重算 projection，再与 record 和 approval 对齐。
6. view null 规则：approved 三 hash 均非空；model 的 `resources_hash` 必须为 null 且有 `NOT_APPLICABLE`；materialized 的 `instructions_hash` 必须为 null 且有 `NOT_APPLICABLE`。
7. 全部 `None`、伪 hash、错 view、错 payload、跨 run/revision/case/snapshot、错 approval status、空 evidence、NOT_RUN/SKIP/FAIL records 均拒绝。
8. 仅支持适用 S01；不支持 NOT_APPLICABLE/NA。NA 文本不能作为认证或绕过。
9. 在下述已解码、无并发修改的数据边界内，malformed 输入返回 `('DENY', reason)`；不是任意 Python 代码的安全沙箱。
10. `semantic_verdict` 只输出 `decision + reason`，不返回或自评分 `PASS`。unittest harness 用 expected gate result 断言 case outcome。
11. hash 向量保留三组：instructions/resources/metadata。
12. 资源 `present` 必须是精确 bool；instruction/source 只接受无 BOM 的 UTF-8 `str`；resource bytes 可为任意 bytes，包括 BOM 字节；metadata 先检查 key/value 类型再按 UTF-8 key 排序。

输入边界：`semantic_verdict` 接收**已解码数据**，不负责解码、反序列化或插件隔离。仅允许精确内置 `dict/list/tuple/str/bytes/bool/int/None`；拒绝 float、所有 subclass、未知对象，包含未使用字段及 dict key 内的对象。tuple/bytes 是本 Python toy 的扩展，不等同于原始 JSON。
先用 `data_snapshot` 递归复制所有输入，再进行 schema/相等性/hash 检查；仅对通过精确类型检查的容器迭代，不调用输入对象的 `__deepcopy__/__eq__/__iter__`。hash/project 等 helper 为内部函数，不是独立不可信 Python 对象入口。
调用方必须保证整个调用期间无人并发修改输入；本 lab 不提供锁或原子快照。不执行 hook 不等于可沙箱化任意 Python：进程内恶意代码、线程/信号/终结器、内存耗尽等不在承诺内。
固定限额：根 tuple 深度为 0，最大深度 32、访问节点数 20000、聚合数据预算 1 MiB；每个 key/value/重复引用均计数，循环引用拒绝。str 按每字符 4 字节保守计费，bytes 按长度，int 按 magnitude 字节数（至少 1）；容器/标量对象开销由节点上限约束，不声称精确限制进程内存。不可变叶可共享，所有可变容器复制，原输入不写入。
`capabilities` 仅为记录性字段，不参与 S01 ALLOW，也不代表能力授权。

## 运行

```bash
python3 semantic_gate_lab_test.py -v
```

## 完整可抽取代码（Python 标准库 + unittest）

```python
import copy
import hashlib
import re
import struct
import unittest

SCHEME = 'poc-length-framed-v1'
IDENTITY = ('run_id', 'case_id', 'host', 'host_version', 'source_revision', 'snapshot_id')
VIEWS = ('approved', 'model', 'materialized')
HASHES = ('instructions_hash', 'resources_hash', 'metadata_hash')
NULLS = {'approved': {}, 'model': {'resources_hash': 'NOT_APPLICABLE'},
         'materialized': {'instructions_hash': 'NOT_APPLICABLE'}}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


MAX_DEPTH, MAX_NODES, MAX_BYTES = 32, 20000, 1024 * 1024


def data_snapshot(root):
    # No isinstance, type membership/equality, deepcopy, repr or user hooks.
    active, nodes, budget = set(), 0, 0
    def visit(obj, depth):
        nonlocal nodes, budget
        nodes += 1
        need(depth <= MAX_DEPTH and nodes <= MAX_NODES, 'snapshot depth/nodes')
        t = type(obj)
        if obj is None or t is bool or t is int or t is str or t is bytes:
            size = (4 * len(obj) if t is str else len(obj) if t is bytes else
                    max(1, (obj.bit_length() + 7) // 8) if t is int else 1)
            budget += size
            need(budget <= MAX_BYTES, 'snapshot aggregate bytes')
            return obj
        need(t is dict or t is list or t is tuple, 'snapshot exact builtin type')
        oid = id(obj)
        need(oid not in active, 'snapshot cycle')
        active.add(oid)
        try:
            need(nodes + len(obj) * (2 if t is dict else 1) <= MAX_NODES, 'snapshot nodes')
            if t is dict:
                result = {}
                for key, value in obj.items():
                    k = visit(key, depth + 1)
                    v = visit(value, depth + 1)
                    result[k] = v  # Only copied builtin keys can be hashed/compared.
                return result
            items = [visit(value, depth + 1) for value in obj]
            return tuple(items) if t is tuple else items
        finally:
            active.remove(oid)
    return visit(root, 0)


def utf8(s):
    need(type(s) is str and not s.startswith('\ufeff'), 'UTF8 string without BOM required')
    return s.encode('utf-8', 'strict')


def frame(b):
    if type(b) is str:
        b = utf8(b)
    need(type(b) is bytes, 'bytes required')
    return struct.pack('>Q', len(b)) + b


def sha(b):
    return hashlib.sha256(b).hexdigest()


def hash_instructions(items):
    need(type(items) is list, 'instruction list')
    out, seen = b'POC-LF-V1\nVIEW:instructions\n', set()
    for item in items:
        need(type(item) in (tuple, list) and len(item) == 2, 'instruction pair')
        sid, text = item
        utf8(sid); utf8(text)
        need(sid not in seen, 'duplicate source')
        seen.add(sid)
        out += frame('I') + frame(sid) + frame(text)
    return sha(out)


def norm_resources(items):
    need(type(items) is list, 'resource list')
    out, seen = [], set()
    for r in items:
        need(type(r) is dict and set(r) == {'kind', 'path', 'present', 'bytes'}, 'resource fields')
        k, p, present, data = r['kind'], r['path'], r['present'], r['bytes']
        need(type(k) is str and k in ('reference', 'asset', 'script'), 'kind')
        need(type(p) is str and re.fullmatch(r'[A-Za-z0-9._/-]+', p) is not None, 'path')
        need(all(x not in ('', '.', '..') for x in p.split('/')) and p not in seen, 'path components/duplicate')
        need(type(present) is bool and type(data) is bytes, 'presence/bytes type')
        need(present or data == b'', 'absent carries bytes')
        seen.add(p); out.append(dict(r))
    return sorted(out, key=lambda r: r['path'].encode('ascii'))


def hash_resources(items):
    out = b'POC-LF-V1\nVIEW:resources\n'
    for r in norm_resources(items):
        out += frame('R') + frame(r['kind']) + frame(r['path'])
        out += frame('B' if r['present'] else 'A') + frame(r['bytes'])
    return sha(out)


def hash_metadata(meta):
    need(type(meta) is dict, 'metadata map')
    for k, v in meta.items():
        utf8(k); utf8(v)
    out = b'POC-LF-V1\nVIEW:metadata\n'
    for k in sorted(meta, key=lambda x: utf8(x)):
        out += frame('M') + frame(k) + frame(meta[k])
    return sha(out)


def resource_union(approved, actual):
    amap = {r['path']: r for r in norm_resources(approved)}
    xmap = {r['path']: r for r in norm_resources(actual)}
    paths = sorted(set(amap) | set(xmap))
    a, x = [], []
    for p in paths:
        kind = (amap.get(p) or xmap[p])['kind']
        absent = dict(kind=kind, path=p, present=False, bytes=b'')
        a.append(amap.get(p, absent)); x.append(xmap.get(p, absent))
    return a, x, set(xmap) - set(amap)


def project(view, payload):
    keys = {'approved': {'instructions', 'resources', 'metadata'},
            'model': {'instructions', 'metadata'}, 'materialized': {'resources', 'metadata'}}
    need(type(payload) is dict and set(payload) == keys[view], 'payload fields')
    return dict(instructions_hash=hash_instructions(payload['instructions']) if view != 'materialized' else None,
                resources_hash=hash_resources(payload['resources']) if view != 'model' else None,
                metadata_hash=hash_metadata(payload['metadata']))


def identity(obj):
    need(type(obj) is dict, 'identity object')
    for k in IDENTITY:
        need(type(obj[k]) is str and bool(obj[k]), 'identity string')
        utf8(obj[k])
    need(obj['case_id'] == 'S01' and obj['host'] == 'toy', 'S01 toy subset only')
    return tuple(obj[k] for k in IDENTITY)


def digests(d, view):
    need(type(d) is dict and set(d) == set(HASHES), 'hash fields')
    for k in HASHES:
        if k in NULLS[view]:
            need(d[k] is None, 'unobserved projection must be null')
        else:
            need(type(d[k]) is str and re.fullmatch('[0-9a-f]{64}', d[k]) is not None, 'observed digest required')


def semantic_verdict(records, evidence_map, approvals, manifest):
    # Snapshot first; all semantic operations below see only copied builtins.
    # Manifest/approvals are trusted TEST data, not extracted from evidence.
    try:
        records, evidence_map, approvals, manifest = data_snapshot((records, evidence_map, approvals, manifest))
        need(type(manifest) is dict and set(manifest) == set(IDENTITY), 'nonempty trusted manifest')
        expected_id = identity(manifest)
        need(type(records) is list and len(records) == 3, 'exactly three records')
        need(type(evidence_map) is dict and type(approvals) is dict, 'mapping inputs')
        approval = approvals[expected_id]
        need(type(approval) is dict and set(approval) == {'identity', 'hashes', 'status'}, 'approval object')
        need(identity(approval['identity']) == expected_id and approval['status'] == 'APPROVED', 'approval binding/status')
        digests(approval['hashes'], 'approved')
        views, payloads, projections = {}, {}, {}
        for r in records:
            need(type(r) is dict and set(r) == set(IDENTITY) | {'view', 'applicability', 'hash_scheme', 'hashes', 'null_reasons', 'capabilities', 'case_status', 'evidence'}, 'record fields')
            rid = identity(r)
            view = r['view']
            need(type(view) is str and view in VIEWS and view not in views, 'unique view')
            need(r['applicability'] == 'APPLICABLE' and r['hash_scheme'] == SCHEME, 'subset/scheme')
            caps = r['capabilities']
            need(type(caps) is list and all(type(c) is str for c in caps), 'capability strings')
            need(len(caps) == len(set(caps)), 'duplicate capability')
            need(r['case_status'] == 'PASS', 'unfinished/failed record')
            digests(r['hashes'], view)
            need(r['null_reasons'] == NULLS[view], 'per-field null reasons')
            ref = r['evidence']
            need(type(ref) is str and bool(ref), 'evidence reference')
            e = evidence_map[ref]
            need(type(e) is dict and set(e) == {'identity', 'view', 'payload'}, 'structured evidence')
            eid = identity(e['identity'])
            need(rid == eid == expected_id and e['view'] == view, 'record/evidence binding')
            computed = project(view, e['payload'])
            need(r['hashes'] == computed, 'projection recomputation')
            views[view], payloads[view], projections[view] = r, e['payload'], computed
        need(set(views) == set(VIEWS), 'complete views')
        a, m, x = (projections[v] for v in VIEWS)
        need(a == approval['hashes'], 'approved content binding')
        need(a['instructions_hash'] == m['instructions_hash'], 'instructions drift')
        need(a['metadata_hash'] == m['metadata_hash'] == x['metadata_hash'], 'metadata drift')
        av, xv, extra = resource_union(payloads['approved']['resources'], payloads['materialized']['resources'])
        need(not extra and hash_resources(av) == hash_resources(xv), 'resource union drift/residue')
        return 'ALLOW', 'S01 snapshot equality'
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return 'DENY', 'invalid, incomplete, unbound or drifting S01 evidence'


def fixture():
    manifest = dict(zip(IDENTITY, ('run-1', 'S01', 'toy', 'v1', 'rev-a', 'snap-a')))
    payload = dict(instructions=[('SKILL.md', '使用规则A')],
                   resources=[dict(kind='reference', path='r.txt', present=True, bytes=b'A')],
                   metadata={'approver': 'toy-reviewer', 'revision': '1'})
    evidence, records = {}, []
    for view in VIEWS:
        p = copy.deepcopy(payload)
        if view == 'model': del p['resources']
        if view == 'materialized': del p['instructions']
        evidence[view] = dict(identity=dict(manifest), view=view, payload=p)
        records.append(dict(manifest, view=view, applicability='APPLICABLE', hash_scheme=SCHEME,
                            hashes=project(view, p), null_reasons=dict(NULLS[view]), capabilities=[],
                            case_status='PASS', evidence=view))
    approvals = {identity(manifest): dict(identity=dict(manifest), hashes=dict(records[0]['hashes']), status='APPROVED')}
    return records, evidence, approvals, manifest


def refresh(f):
    for r in f[0]:
        r['hashes'] = project(r['view'], f[1][r['evidence']]['payload'])


class Tests(unittest.TestCase):
    def check(self, f, expected='DENY'):
        result = semantic_verdict(*f)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], expected)  # Harness assertion, NOT gate self-grading.

    def test_vectors(self):
        self.assertEqual(hash_instructions([('SKILL.md', 'hi')]), '4de757fcacfd69bf203bc2643c0b5faa7e24d70fde56fde62c36dd28282e602f')
        self.assertEqual(hash_resources([dict(kind='script', path='a.txt', present=False, bytes=b''), dict(kind='reference', path='b.txt', present=True, bytes=b'')]), 'e21ab0473f27871971c22a76dbd27c890b9a2247011c53ee9aca2f57d5ca807a')
        self.assertEqual(hash_metadata({'z': '9', 'a': 'α'}), '72972bc064d2842c094a513479bb63feea0e03090e38ffa22e03de1972df335b')

    def test_allow(self):
        self.check(fixture(), 'ALLOW')

    def test_forged_hashes(self):
        for value in (None, '0'*64):
            f = fixture()
            for r in f[0]: r['hashes'] = dict.fromkeys(HASHES, value)
            self.check(f)

    def test_recomputation_mutation_target(self):
        f = fixture(); f[0][1]['hashes']['instructions_hash'] = '0'*64
        self.check(f)

    def test_payload_drift(self):
        for view, key, value in [('model', 'instructions', [('SKILL.md', 'B')]), ('materialized', 'resources', []), ('model', 'metadata', {'revision': '2'})]:
            for refresh_hash in (False, True):
                f = fixture(); f[1][view]['payload'][key] = value
                if refresh_hash: refresh(f)
                self.check(f)

    def test_binding_mutation_target(self):
        f = fixture(); f[1]['model']['identity']['run_id'] = 'other-run'
        self.check(f)

    def test_identities(self):
        for k in IDENTITY:
            for target in ('record', 'evidence', 'approval'):
                f = fixture()
                obj = f[0][1] if target == 'record' else f[1]['model']['identity'] if target == 'evidence' else next(iter(f[2].values()))['identity']
                obj[k] = 'other'; self.check(f)

    def test_evidence(self):
        for value in (None, False, {}, 'exists'):
            f = fixture(); f[1]['model'] = value; self.check(f)
        f = fixture(); del f[1]['model']; self.check(f)
        f = fixture(); f[1]['model']['view'] = 'approved'; self.check(f)
        f = fixture(); f[0][1]['evidence'] = 'approved'; self.check(f)
        f = fixture(); f[1]['model']['payload'] = None; self.check(f)

    def test_approvals(self):
        for value in (None, False, {}, 'APPROVED'):
            f = fixture(); f[2][identity(f[3])] = value; self.check(f)
        f = fixture(); next(iter(f[2].values()))['status'] = 'REVOKED'; self.check(f)
        f = fixture()
        for view in ('approved', 'model'): f[1][view]['payload']['instructions'] = [('SKILL.md', 'unapproved')]
        refresh(f); self.check(f)

    def test_status_mutation_target(self):
        for status in ('NOT_RUN', 'SKIP', 'FAIL'):
            f = fixture(); f[0][1]['case_status'] = status; self.check(f)

    def test_subset_na_and_views(self):
        for case in ('C01', 'C06', 'C99'):
            f = fixture(); f[0][0]['case_id'] = case; self.check(f)
        for view in ('gate', 'model', None, []):
            f = fixture(); f[0][0]['view'] = view; self.check(f)
        f = fixture(); f[0][0]['applicability'] = 'NOT_APPLICABLE'; self.check(f)
        f = fixture(); f[0][0]['reason'] = 'not applicable: authenticated'; self.check(f)

    def test_null_matrix(self):
        for i in range(3):
            for k in HASHES:
                f = fixture(); f[0][i]['hashes'][k] = '0'*64 if k in NULLS[VIEWS[i]] else None
                self.check(f)
        f = fixture(); f[0][1]['null_reasons'] = {}; self.check(f)

    def test_malformed(self):
        for index in range(4):
            for value in (None, False, [], {}, 1, 'bad'):
                f = list(fixture()); f[index] = value; self.check(f)
        f = fixture(); f[0][0] = None; self.check(f)
        for key, value in [('capabilities', [{}]), ('capabilities', [123]), ('capabilities', ['a', 'a']), ('host_version', True), ('host_version', []), ('source_revision', 123), ('evidence', [])]:
            f = fixture(); f[0][1][key] = value; self.check(f)
        f = fixture(); f[0].pop(); self.check(f)
        f = fixture(); f[0].append(copy.deepcopy(f[0][0])); self.check(f)
        f = fixture(); f[1]['model']['payload']['metadata'] = {1: 'x', 'a': 'b'}; self.check(f)

    def test_union_mutation_target_missing_present(self):
        f = fixture(); f[1]['materialized']['payload']['resources'] = []; refresh(f); self.check(f)

    def test_union_tombstone_allow(self):
        f = fixture(); f[1]['approved']['payload']['resources'][0].update(present=False, bytes=b'')
        f[1]['materialized']['payload']['resources'] = []; refresh(f)
        next(iter(f[2].values()))['hashes'] = dict(f[0][0]['hashes'])
        self.check(f, 'ALLOW')

    def test_union_residue_kind_and_empty(self):
        for change in ('extra', 'kind', 'bytes', 'empty'):
            f = fixture(); r = f[1]['materialized']['payload']['resources'][0]
            if change == 'extra': r['path'] = 'extra.txt'
            if change == 'kind': r['kind'] = 'asset'
            if change == 'bytes': r['bytes'] = b'B'
            if change == 'empty': r.update(present=False, bytes=b'')
            refresh(f); self.check(f)
        self.assertNotEqual(hash_resources([dict(kind='asset', path='x', present=False, bytes=b'')]), hash_resources([dict(kind='asset', path='x', present=True, bytes=b'')]))

    def test_hash_input_validation(self):
        for text in (b'\xff', b'\xef\xbb\xbfhi', '\ufeffhi', '\ud800'):
            with self.assertRaises(ValueError): hash_instructions([('s', text)])
        for meta in ({1: 'v'}, {'v': 1}, {'v': '\ufeffB'}, {'\ud800': 'v'}):
            with self.assertRaises(ValueError): hash_metadata(meta)
        with self.assertRaises(ValueError): hash_instructions([('s', 'a'), ('s', 'b')])
        for p in ('../x', './x', '/x', 'x/', 'a\\b', 'a//b', '非ascii'):
            with self.assertRaises(ValueError): hash_resources([dict(kind='asset', path=p, present=True, bytes=b'')])
        for present in (1, 0.0, None):
            with self.assertRaises(ValueError): hash_resources([dict(kind='asset', path='x', present=present, bytes=b'')])
        for data in ('a', bytearray(b'a')):
            with self.assertRaises(ValueError): hash_resources([dict(kind='asset', path='x', present=True, bytes=data)])
        r = dict(kind='asset', path='x', present=True, bytes=b'\xff\xef\xbb\xbf')
        self.assertEqual(len(hash_resources([r])), 64)
        with self.assertRaises(ValueError): hash_resources([r, r])

    def test_empty_observed(self):
        f = fixture()
        for e in f[1].values():
            for key in e['payload']: e['payload'][key] = {} if key == 'metadata' else []
        refresh(f); next(iter(f[2].values()))['hashes'] = dict(f[0][0]['hashes'])
        self.check(f, 'ALLOW')

    def test_snapshot_hooks_never_run(self):
        calls = []
        def hook(*args, **kwargs):
            calls.append('hook'); raise RuntimeError('must never execute')
        class Meta(type):
            __eq__ = hook
        hooks = dict(__deepcopy__=hook, __eq__=hook, __iter__=hook,
                     __len__=hook, __repr__=hook, __hash__=object.__hash__)
        probes = [factory('Probe', (base,), hooks)() for factory in (type, Meta)
                  for base in (object, dict, list, tuple, str, bytes, int)]
        for probe in probes:
            for where in ('extra', 'status', 'key', 'tuple-key', 0, 1, 2, 3):
                f = list(fixture())
                if where == 'extra': f[1]['unused'] = probe
                elif where == 'status': f[0][0]['case_status'] = probe
                elif where == 'key': f[1][probe] = None
                elif where == 'tuple-key': f[1][(probe,)] = None
                else: f[where] = probe
                calls.clear()
                self.check(f)
                self.assertEqual(calls, [])

    def test_snapshot_limits_and_cycles(self):
        cycle = []; cycle.append(cycle)
        cycle_dict = {}; cycle_dict['self'] = cycle_dict
        deep = None
        for _ in range(MAX_DEPTH + 1): deep = [deep]
        for value in (cycle, cycle_dict, deep, [None] * MAX_NODES,
                      [b'x' * (MAX_BYTES // 2)] * 3, 'x' * MAX_BYTES,
                      1 << (MAX_BYTES * 8), 1.0):
            with self.assertRaises(ValueError): data_snapshot(value)
            f = fixture(); f[1]['unused'] = value; self.check(f)
        self.assertIs(cycle[0], cycle)
        self.assertIs(cycle_dict['self'], cycle_dict)

    def test_snapshot_exact_boundaries(self):
        deep = None
        for _ in range(MAX_DEPTH): deep = [deep]
        self.assertEqual(data_snapshot(deep), deep)
        self.assertEqual(len(data_snapshot([None] * (MAX_NODES - 1))), MAX_NODES - 1)
        self.assertEqual(data_snapshot(b'x' * MAX_BYTES), b'x' * MAX_BYTES)
        with self.assertRaises(ValueError): data_snapshot(b'x' * (MAX_BYTES + 1))
        with self.assertRaises(ValueError): data_snapshot([b'x' * MAX_BYTES, b'y'])

    def test_snapshot_input_unchanged(self):
        for invalid in (False, True):
            f = fixture()
            if invalid: f[0][0]['case_status'] = 'FAIL'
            before = data_snapshot(f)
            self.check(f, 'DENY' if invalid else 'ALLOW')
            self.assertEqual(f, before)
        shared = []; original = {'a': shared, 'b': shared}
        cloned = data_snapshot(original); cloned['a'].append('new')
        self.assertEqual(original, {'a': [], 'b': []})
        self.assertIsNot(cloned['b'], shared)

    def test_harness_expected_not_gate_self_pass(self):
        with self.assertRaises(AssertionError): self.check(fixture(), 'DENY')
        f = fixture(); f[0][1]['case_status'] = 'NOT_RUN'
        with self.assertRaises(AssertionError): self.check(f, 'ALLOW')


if __name__ == '__main__':
    unittest.main()
```

## 离线验证与测试敏感性

- S01 子契约：23 个测试方法通过（含 112 个恶意对象位置/类型组合，hook 触发次数为零）；仅为原创教学模型结果。
- `copy` 只用于可信 fixture/单测构造；不在 verdict 的不可信输入路径中。
- 新增无 hook 快照测试：精确类型/恶意 metaclass、循环引用、深度/节点/聚合字节上限及精确边界、ALLOW/DENY 原输入不变和共享容器隔离。
- 新增真实 mutation：恢复 deepcopy、跳过 snapshot、删除 depth/node/aggregate bytes/cycle 限制、改用类型相等性 membership；7 个均被测试杀死，且均通过语法解析。原 7 个语义 mutation 亦重新运行并全部杀死。
- 真实源码 mutation（均为语义删除，不以语法错误算 kill）：
  - 删除 projection 重算检查：被 `test_recomputation_mutation_target` 杀死。
  - 删除 record/evidence/identity 绑定检查：被 `test_binding_mutation_target`、`test_evidence`、`test_identities` 杀死。
  - 删除 `case_status == PASS` 检查：被 `test_status_mutation_target`、`test_harness_expected_not_gate_self_pass` 杀死。
  - 删除资源并集漂移检查：被 `test_union_mutation_target_missing_present`、`test_union_residue_kind_and_empty` 等杀死。
