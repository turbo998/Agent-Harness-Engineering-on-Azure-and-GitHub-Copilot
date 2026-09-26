# 从搜索命中到证据补齐：离线 RAG 导航隔离实验

日期：2026-09-27。**原创补强教学，不是 Mistral 上游的等价实现，也不是已完成安全评审的部署方案。**

## 1. 为什么值得做

固定 top-k 可能只取到“30 天内”，漏掉相邻块里的退款规则和“损坏商品无需收据”的例外。导航式检索把问题拆成：先 search 找锚点，再 open 补邻居，或用 read / grep / navigate 定位证据。真正交付给多租户客户时，不能只有 search 过滤权限而让 chunk lookup 或邻居查询走全局索引。

### 固定上游证据，只证明导航机制

来源：[Mistral search-starter-app 的 mcp_server.py 固定源码](https://github.com/mistralai/search-starter-app/blob/d25221fef43b12f8c31701cf63f4ee43bceb434e/template/src/entrypoints/mcp_server.py)。

- **commit**：`d25221fef43b12f8c31701cf63f4ee43bceb434e`
- **tree**：`08ea9b4228a733c74ad969f245d3c92ece74935a`

二者不是同一对象；此处引用使用 commit 固定。原文摘录：

> L106–108: “Includes the chunk `id` (pass to open()) and start_offset / end_offset (pass to navigate() / read()) so the model can drive the agentic navigation tools directly.”
>
> L134–136: “exclude_ids: Chunk `id`s to skip at query time — e.g. chunks already seen earlier in an agentic loop, so each search surfaces fresh context instead of repeating hits.”
>
> L258: “Expand context around a chunk from search: return it plus adjacent chunks in reading order.”
>
> L315: “Fetch chunks from a known offset range: direct access, no context expansion.”
>
> L339: “Lexical search for an exact term or phrase within a single document.”

调用证据：L269 是 `get_chunk(chunk_id)`，L275–280 取前后邻居；L302–304 委托 `navigate`；L328 委托 `read`；L349 委托 `grep`。这支持 **search → open/read/grep/navigate** 的工作流，**不支持身份授权保证**。已读的上游入口没有本实验加入的身份授权层；也不能据此断言整个上游部署不存在其他外部认证组件。这里不运行、下载或移植上游实现，只借鉴导航思路。

## 2. 实验契约与信任边界

- 固定 synthetic 数据：`alpha/beta` 两租户、`v1/v2` 两版本，每份 policy 三块；额外 `alpha/other/v1` 与 `alpha/other/v2` 测试同租户不同 source/revision 授权配对；`alpha/policy/v2/c0` 还故意放入一条完整引用重复行。各份文档故意复用 `c0/c1/c2`。
- `Scope(tenant, grants)` **应由服务端认证成功后，根据服务端授权表产生**，而不是从客户端 JSON、工具参数或模型输出中信任得到。这里用 `SERVER_SCOPE` 模拟这一前置结果，**没有真实登录、令牌验证或授权服务**。`Lab` 构造器不是远程工具接口；同进程恶意 Python 代码不在隔离模型内。
- 五个入口共用服务端 scope。引用采用 `(tenant, source, revision, local_id)`，引用只是定位符、不是权限凭证。chunk lookup 先检查整个文档 scope，再在该文档内找完整引用；邻居只在同一 tenant/source/revision 的有序列表中取。
- 本例用**块序号半开区间** `[start, end)`，不是上游的 offset 语义。search/grep 是大小写不敏感的字面子串匹配，不做向量排序、分词或正则。navigate 的前向/后向结果均按阅读顺序返回。
- 同一完整引用的重复行在可信合成 fixture 内采用**输入首行胜出**（含 text 与 pos），不是生产摄入冲突校验。`_rows` 在排序、锚点定位、open/navigation 切窗前先规范为唯一引用，next/previous 不会返回锚点自身；search 同样在匹配与 top-k 前规范化，冲突副本的文本不另行参与匹配。
- `exclude_ids` 是完整引用的集合；search 先排除再截 top-k，所有返回入口仍经过 `_emit` 独立去重与排除。导航窗口按规范行定位后再排除，不保证排除后补满窗口。跨租户相同 local_id 不会错误排除本租户引用；跨调用需要调用方累计传入已见引用。
- `remaining` 限制会话累计返回块数，`calls_left` 限制成功调用数（空结果也占一次）。预算不足时整次失败，不返回部分证据、不改计数。参数也有限界；这不是 CPU/内存/扫描量限流或生产成本控制器。
- 越权、过期 revision、不存在文档/块均为 `Denied('not available')`；测试验证同异常、同消息和计数不变，**不声称恒定时间或消除所有存在性侧信道**。授权的空搜索属于成功调用，正常计费。
- `effects` 只模拟已提交逻辑读取/输出计数，不是实际网络、数据库或文件访问审计。所有内容在内存中；无 ingest/delete、网络请求、真实文件摄入、真实 key 或模型调用。运行器读取的仅是你保存的本实验代码。

## 3. 保存并运行

需要 Python 3.10+，仅标准库，无安装步骤。新建一个空目录，将下面第一个代码块保存为 **`rag-scope-lab.py`**，第二个保存为 **`rag-mutation-runner.py`**。在该目录执行以下完整命令；**不是下载执行**：

```sh
python -B -c "from pathlib import Path; p=Path('rag-scope-lab.py'); compile(p.read_text(encoding='utf-8'), str(p), 'exec'); print('compile: PASS')"
python -B rag-scope-lab.py
python -B rag-mutation-runner.py
```

### 主实验 + unittest（359 行；代码行数不计末尾空白行）

```python
"""Original offline teaching model; not an authentication implementation."""
from dataclasses import dataclass
import unittest

class Denied(Exception):
    pass

class Budget(Exception):
    pass

@dataclass(frozen=True)
class Scope:
    tenant: str
    grants: frozenset  # (source, revision); constructed by trusted server only


@dataclass(frozen=True)
class Chunk:
    ref: tuple  # (tenant, source, revision, local chunk id)
    pos: int
    text: str

    @property
    def doc(self):
        return self.ref[:3]


def fixture():
    rows = []
    for tenant in ('alpha', 'beta'):
        for revision in ('v1', 'v2'):
            for pos, text in enumerate(('Policy: refunds allowed.',
                                        'Deadline: within 30 days.',
                                        'Exception: damaged goods need no receipt.')):
                rows.append(Chunk((tenant, 'policy', revision, f'c{pos}'), pos,
                                  f'{tenant}/{revision} {text}'))
    # Exact duplicate full ref: proves output dedup and budget accounting use unique refs.
    rows.append(Chunk(('alpha', 'policy', 'v2', 'c0'), 0,
                      'alpha/v2 Policy: refunds allowed. duplicate row'))
    rows.append(Chunk(('alpha', 'other', 'v1', 'c0'), 0, 'alpha/v1 Other document.'))
    rows.append(Chunk(('alpha', 'other', 'v2', 'c0'), 0, 'alpha/v2 Other document.'))
    return tuple(rows)


class Lab:
    def __init__(self, server_scope, chunks=fixture(), budget=12, call_budget=8):
        self._scope, self._chunks = server_scope, chunks
        self.remaining, self.calls_left = budget, call_budget
        self.effects = {'fetches': 0, 'emitted': 0}

    def _allowed(self, doc):
        return doc[0] == self._scope.tenant and doc[1:] in self._scope.grants

    @staticmethod
    def _unique(rows):
        # Trusted fixture policy: first input row wins, including text and position.
        canonical = {}
        for c in rows:
            canonical.setdefault(c.ref, c)
        return list(canonical.values())

    def _rows(self, doc):
        if not self._allowed(doc):
            raise Denied('not available')
        rows = sorted(self._unique(c for c in self._chunks if c.doc == doc),
                      key=lambda c: c.pos)
        if not rows:
            raise Denied('not available')
        return rows

    def _anchor(self, ref):
        rows = self._rows(ref[:3])  # authorize before resolving colliding local ids
        for c in rows:
            if c.ref == ref and self._allowed(c.doc):
                return c
        raise Denied('not available')

    def _emit(self, rows, exclude_ids=()):
        seen, out = set(exclude_ids), []
        for c in rows:
            if c.ref not in seen:
                seen.add(c.ref)
                out.append(c)
        if len(out) > self.remaining or self.calls_left <= 0:
            raise Budget('budget exhausted')
        self.remaining -= len(out)
        self.calls_left -= 1
        self.effects['fetches'] += 1  # logical committed read, not physical I/O
        self.effects['emitted'] += len(out)
        return out

    @staticmethod
    def _limit(n):
        if type(n) is not int or not 1 <= n <= 3:
            raise ValueError('limit must be 1..3')

    def search(self, query, top_k=3, exclude_ids=()):
        self._limit(top_k)
        excluded = set(exclude_ids)
        rows = [c for c in self._unique(self._chunks) if self._allowed(c.doc)
                and query.casefold() in c.text.casefold() and c.ref not in excluded]
        return self._emit(rows[:top_k], excluded)

    def open(self, ref, window=1, exclude_ids=()):
        anchor = self._anchor(ref)
        if type(window) is not int or not 0 <= window <= 2:
            raise ValueError('window must be 0..2')
        rows = self._rows(anchor.doc)
        i = rows.index(anchor)
        return self._emit(rows[max(0, i-window):i+window+1], exclude_ids)

    def read(self, doc, start=0, end=3, exclude_ids=()):
        rows = self._rows(doc)
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= 3:
            raise ValueError('invalid half-open chunk range')
        return self._emit([c for c in rows if start <= c.pos < end], exclude_ids)

    def grep(self, doc, phrase, exclude_ids=()):
        return self._emit([c for c in self._rows(doc)
                           if phrase.casefold() in c.text.casefold()], exclude_ids)

    def navigate(self, ref, direction='next', top_k=1, exclude_ids=()):
        anchor = self._anchor(ref)
        self._limit(top_k)
        if direction not in ('next', 'previous'):
            raise ValueError('invalid direction')
        rows = self._rows(anchor.doc)
        i = rows.index(anchor)
        chosen = rows[i+1:i+1+top_k] if direction == 'next' else rows[max(0, i-top_k):i]
        return self._emit(chosen, exclude_ids)


DOC = ('alpha', 'policy', 'v2')
REF = DOC + ('c1',)
SERVER_SCOPE = Scope('alpha', frozenset({('policy', 'v2')}))
PAIR_SCOPE = Scope('alpha', frozenset({('policy', 'v2'), ('other', 'v1')}))


class Tests(unittest.TestCase):
    def setUp(self):
        self.lab = Lab(SERVER_SCOPE)

    def state(self):
        return (self.lab.remaining, self.lab.calls_left, dict(self.lab.effects))

    def assert_state(self, remaining, calls_left, fetches, emitted):
        self.assertEqual(self.state(), (remaining, calls_left,
                                        {'fetches': fetches, 'emitted': emitted}))

    def test_search_scope(self):
        self.assertEqual([c.doc for c in self.lab.search('days')], [DOC])

    def test_collision_resolves_full_identity(self):
        rows = self.lab.open(REF, 0)
        self.assertEqual([c.ref for c in rows], [REF])
        self.assertTrue(rows[0].text.startswith('alpha/v2'))

    def test_duplicate_fullref_dedup_and_budget(self):
        lab = Lab(SERVER_SCOPE, budget=10)
        rows = lab.read(DOC, 0, 3)
        self.assertEqual([c.ref for c in rows], [DOC+('c0',), REF, DOC+('c2',)])
        self.assertEqual(len(rows), len({c.ref for c in rows}))
        self.assertEqual((lab.remaining, lab.calls_left, lab.effects),
                         (7, 7, {'fetches': 1, 'emitted': 3}))

    def test_duplicate_data_all_entrypoints(self):
        first = tuple(c for c in fixture() if c.doc == DOC)[:3]
        # Interleave real duplicate fullrefs BEFORE every possible window boundary.
        chunks = tuple(row for c in first for row in
                       (c, Chunk(c.ref, c.pos, 'conflicting duplicate-only text')))
        cases = [('search', ('', 3), [0, 1, 2]),
                 ('open', (DOC+('c0',), 1), [0, 1]),
                 ('read', (DOC, 0, 3), [0, 1, 2]),
                 ('grep', (DOC, ''), [0, 1, 2]),
                 ('navigate', (DOC+('c0',), 'next', 2), [1, 2])]
        for name, args, positions in cases:
            with self.subTest(name=name):
                self.lab = Lab(SERVER_SCOPE, chunks=chunks)
                rows = getattr(self.lab, name)(*args)
                self.assertEqual(rows, [first[i] for i in positions])
                self.assertEqual(len(rows), len({c.ref for c in rows}))
                self.assert_state(12-len(positions), 7, 1, len(positions))
        self.lab = Lab(SERVER_SCOPE, chunks=chunks)
        self.assertEqual(self.lab.navigate(DOC+('c0',)), [first[1]])
        self.assert_state(11, 7, 1, 1)
        self.assertEqual(self.lab.navigate(DOC+('c2',), 'previous', 2), list(first[:2]))
        self.assert_state(9, 6, 2, 3)
        self.assertEqual(self.lab.navigate(DOC+('c0',), 'previous', 2), [])
        self.assert_state(9, 5, 3, 3)
        self.assertEqual(self.lab.search('duplicate-only'), [])
        self.assert_state(9, 4, 4, 3)
        self.assertEqual(self.lab.grep(DOC, 'duplicate-only'), [])
        self.assert_state(9, 3, 5, 3)

    def test_emit_dedup_independent_of_canonical_rows(self):
        # Direct primitive test: do not route through _unique/_rows first.
        a = Chunk(DOC+('c0',), 0, 'first')
        b = Chunk(a.ref, 0, 'duplicate')
        c = Chunk(REF, 1, 'excluded')
        self.lab = Lab(SERVER_SCOPE, budget=10)
        self.assertEqual(self.lab._emit([a, b, c, c], [REF]), [a])
        self.assert_state(9, 7, 1, 1)
        self.assertEqual(self.lab._emit([a, b], [a.ref]), [])
        self.assert_state(9, 6, 2, 1)

    def test_navigate_repeated_call_budget_atomic(self):
        self.lab = Lab(SERVER_SCOPE, budget=1)
        self.assertEqual([c.ref for c in self.lab.navigate(REF)], [DOC+('c2',)])
        self.assert_state(0, 7, 1, 1)
        before = self.state()
        with self.assertRaisesRegex(Budget, '^budget exhausted$'):
            self.lab.navigate(REF)
        self.assertEqual(self.state(), before)

    def test_foreign_stale_missing_same_error_all_entrypoints(self):
        cases = [(('beta', 'policy', 'v2'), 'c1'), (('alpha', 'policy', 'v1'), 'c1'),
                 (('alpha', 'missing', 'v2'), 'c1'), (('alpha', 'other', 'v2'), 'c0')]
        for doc, local_id in cases:
            for method, args in [(self.lab.open, (doc+(local_id,),)),
                                 (self.lab.read, (doc,)), (self.lab.grep, (doc, '')),
                                 (self.lab.navigate, (doc+(local_id,),))]:
                with self.subTest(doc=doc, method=method.__name__):
                    before = self.state()
                    with self.assertRaisesRegex(Denied, '^not available$'):
                        method(*args)
                    self.assertEqual(self.state(), before)

    def test_grants_bind_source_revision_pairs_all_entrypoints(self):
        # Allowed pairs are exactly policy/v2 and other/v1.  Existing cross-pair
        # documents policy/v1 and other/v2 must be rejected, not accepted by a
        # source-set AND revision-set Cartesian product.
        lab = Lab(PAIR_SCOPE)
        self.assertEqual([c.doc for c in lab.search('Other document.', 1)],
                         [('alpha', 'other', 'v1')])
        self.assertEqual([c.ref for c in lab.open(('alpha', 'other', 'v1', 'c0'), 0)],
                         [('alpha', 'other', 'v1', 'c0')])
        self.assertEqual([c.ref for c in lab.read(DOC, 1, 2)], [REF])
        self.assertEqual([c.ref for c in lab.grep(('alpha', 'other', 'v1'), 'Other')],
                         [('alpha', 'other', 'v1', 'c0')])
        self.assertEqual([c.ref for c in lab.navigate(REF, 'next', 1)], [DOC+('c2',)])
        denied = [(lab.search, ('alpha/v1 Policy', 1)),
                  (lab.open, (('alpha', 'other', 'v2', 'c0'), 0)),
                  (lab.read, (('alpha', 'policy', 'v1'),)),
                  (lab.grep, (('alpha', 'other', 'v2'), 'Other')),
                  (lab.navigate, (('alpha', 'other', 'v2', 'c0'), 'next', 1))]
        for method, args in denied:
            with self.subTest(method=method.__name__):
                lab = Lab(PAIR_SCOPE)
                before = (lab.remaining, lab.calls_left, dict(lab.effects))
                method = getattr(lab, method.__name__)
                if method.__name__ == 'search':
                    self.assertEqual(method(*args), [])
                    self.assertEqual((lab.remaining, lab.calls_left, lab.effects),
                                     (before[0], before[1]-1,
                                      {'fetches': before[2]['fetches']+1,
                                       'emitted': before[2]['emitted']}))
                else:
                    with self.assertRaisesRegex(Denied, '^not available$'):
                        method(*args)
                    self.assertEqual((lab.remaining, lab.calls_left, lab.effects), before)

    def test_missing_chunk_same_error_no_effect(self):
        before = self.state()
        with self.assertRaisesRegex(Denied, '^not available$'):
            self.lab.open(DOC+('absent',))
        self.assertEqual(self.state(), before)

    def test_no_grants_search_no_disclosure(self):
        self.assertEqual(Lab(Scope('alpha', frozenset())).search(''), [])

    def test_open_complete_cross_chunk_evidence(self):
        hit = self.lab.search('days', 1)[0]
        rows = self.lab.open(hit.ref)
        self.assertEqual([c.pos for c in rows], [0, 1, 2])
        self.assertIn('refunds allowed', rows[0].text)
        self.assertIn('30 days', rows[1].text)
        self.assertIn('no receipt', rows[2].text)

    def test_neighbors_same_scope(self):
        self.assertEqual({c.doc for c in self.lab.open(REF, 2)}, {DOC})

    def test_read_no_expansion(self):
        self.assertEqual([c.ref for c in self.lab.read(DOC, 1, 2)], [REF])

    def test_grep_literal(self):
        self.assertEqual([c.pos for c in self.lab.grep(DOC, 'NO RECEIPT')], [2])
        self.assertEqual(self.lab.grep(DOC, '.*'), [])

    def test_navigation_order_edges(self):
        self.assertEqual([c.pos for c in self.lab.navigate(REF, 'previous')], [0])
        self.assertEqual([c.pos for c in self.lab.navigate(DOC+('c2',), 'previous', 2)], [0, 1])
        self.assertEqual([c.pos for c in self.lab.navigate(REF)], [2])
        self.assertEqual(self.lab.navigate(DOC+('c2',)), [])

    def test_exclude_search_refills(self):
        seen = self.lab.search('', 1)[0].ref
        rows = self.lab.search('', 3, [seen, seen])
        self.assertEqual([c.pos for c in rows], [1, 2])

    def test_exclude_all_navigation_tools(self):
        for name, args in [('open', (REF,)), ('read', (DOC,)),
                           ('grep', (DOC, '')), ('navigate', (DOC+('c0',),))]:
            with self.subTest(name=name):
                rows = getattr(Lab(SERVER_SCOPE), name)(*args, exclude_ids=[REF, REF])
                self.assertNotIn(REF, [c.ref for c in rows])
                self.assertEqual(len(rows), len({c.ref for c in rows}))

    def test_exclude_collision_does_not_hide_own(self):
        foreign = ('beta', 'policy', 'v2', 'c1')
        self.assertEqual([c.ref for c in self.lab.search('days', exclude_ids=[foreign])], [REF])

    def test_chunk_budget_atomic(self):
        self.lab = Lab(SERVER_SCOPE, budget=2)
        before = self.state()
        with self.assertRaises(Budget):
            self.lab.open(REF)
        self.assertEqual(self.state(), before)
        self.assertEqual(len(self.lab.read(DOC, 1, 3)), 2)
        self.assertEqual(self.state(), (0, 7, {'fetches': 1, 'emitted': 2}))
        with self.assertRaises(Budget):
            self.lab.read(DOC, 0, 1)

    def test_success_and_empty_accounting(self):
        self.lab = Lab(SERVER_SCOPE)
        self.assert_state(12, 8, 0, 0)
        self.assertEqual(len(self.lab.search('days', 1)), 1)
        self.assert_state(11, 7, 1, 1)
        self.assertEqual([c.pos for c in self.lab.open(REF)], [0, 1, 2])
        self.assert_state(8, 6, 2, 4)
        self.assertEqual([c.pos for c in self.lab.read(DOC, 1, 3)], [1, 2])
        self.assert_state(6, 5, 3, 6)
        self.assertEqual([c.pos for c in self.lab.grep(DOC, 'receipt')], [2])
        self.assert_state(5, 4, 4, 7)
        self.assertEqual([c.pos for c in self.lab.navigate(REF)], [2])
        self.assert_state(4, 3, 5, 8)
        self.assertEqual(self.lab.grep(DOC, 'unfindable'), [])
        self.assert_state(4, 2, 6, 8)

    def test_empty_calls_still_bounded(self):
        self.lab = Lab(SERVER_SCOPE, call_budget=1)
        self.assertEqual(self.lab.search('unfindable'), [])
        self.assertEqual(self.state(), (12, 0, {'fetches': 1, 'emitted': 0}))
        before = self.state()
        with self.assertRaises(Budget):
            self.lab.search('unfindable')
        self.assertEqual(self.state(), before)

    def test_invalid_bounds_no_effect(self):
        before = self.state()
        for method, args in [(self.lab.search, ('', 0)), (self.lab.open, (REF, 99)),
                             (self.lab.read, (DOC, 2, 1)),
                             (self.lab.navigate, (REF, 'sideways'))]:
            with self.assertRaises(ValueError):
                method(*args)
        self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)

```

### 小型 mutation runner（163 行；不计末尾空白行）

每个变体先 `compile`，再运行完整测试。语法错误或运行错误均为 `INVALID`，**不算 kill**。baseline 和每个 mutant 都要求完整的 **22 个测试名、带模块/类的完整 test ID、testsRun 计数**与预期精确一致，且 **skips / expectedFailures / unexpectedSuccesses 全为 0**。只有满足这些条件、出现断言失败且 errors=0 的 mutant 才记 `KILLED`；baseline 必须无失败。每个 mutation 独立从原始源码产生，不累积改动，不改写原文件。

默认运行还会通过独立子进程执行七个门禁负控，实际验证完整 runner 非零退出（exit=1）且产生 `INVALID` 报告；崩溃或无 JSON 不算有效 reject。可单独执行 `python -B rag-mutation-runner.py --negative-control skip_negative`，预期 exit=1。负控不是安全回归 mutation，也不计入 8 个 kill。完整 JSON 含测试名、ID、各计数和拒绝结果；只执行本篇可信原创合成代码，不执行外部数据或上游源码。

```python
"""Only execute the locally saved, original synthetic lab; no downloads."""
import io
import json
from pathlib import Path
import sys
import types
import unittest
import subprocess

source = Path(__file__).with_name('rag-scope-lab.py').read_text(encoding='utf-8')
EXPECTED_TESTS = {
    'test_search_scope', 'test_collision_resolves_full_identity',
    'test_duplicate_fullref_dedup_and_budget',
    'test_foreign_stale_missing_same_error_all_entrypoints',
    'test_grants_bind_source_revision_pairs_all_entrypoints',
    'test_missing_chunk_same_error_no_effect', 'test_no_grants_search_no_disclosure',
    'test_open_complete_cross_chunk_evidence', 'test_neighbors_same_scope',
    'test_read_no_expansion', 'test_grep_literal', 'test_navigation_order_edges',
    'test_exclude_search_refills', 'test_exclude_all_navigation_tools',
    'test_exclude_collision_does_not_hide_own', 'test_chunk_budget_atomic',
    'test_success_and_empty_accounting', 'test_empty_calls_still_bounded',
    'test_invalid_bounds_no_effect', 'test_duplicate_data_all_entrypoints',
    'test_emit_dedup_independent_of_canonical_rows',
    'test_navigate_repeated_call_budget_atomic',
}
mutations = {
    'tenant_gate_removed': (
        'doc[0] == self._scope.tenant and doc[1:] in self._scope.grants',
        'doc[1:] in self._scope.grants'),
    'revision_gate_removed': (
        'doc[1:] in self._scope.grants',
        'any(doc[1] == src for src, rev in self._scope.grants)'),
    'dedup_removed': ('if c.ref not in seen:', 'if True:'),
    'forget_seen_add': (
        '                seen.add(c.ref)',
        '                pass  # accidentally omit emitted-ref tracking'),
    'grant_cross_product': (
        'doc[1:] in self._scope.grants',
        '(any(doc[1] == src for src, rev in self._scope.grants) and any(doc[2] == rev for src, rev in self._scope.grants))'),
    'missing_emitted_accounting': (
        "self.effects['emitted'] += len(out)",
        "self.effects['emitted'] += 0"),
    'reverse_previous_results': (
        "return self._emit(chosen, exclude_ids)",
        "return self._emit(chosen if direction == 'next' else list(reversed(chosen)), exclude_ids)"),
    'navigate_budget_refund': (
        "return self._emit(chosen, exclude_ids)",
        "before = self.remaining\n        out = self._emit(chosen, exclude_ids)\n"
        "        self.remaining = before\n        return out"),
}


def flatten_tests(suite):
    out = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(flatten_tests(item))
        else:
            out.append(item)
    return out


def run(name, text):
    try:
        code = compile(text, name, 'exec')  # compile first; syntax errors never kill
    except SyntaxError as exc:
        return {'name': name, 'compile': 'FAIL', 'status': 'INVALID', 'error': str(exc)}
    module = types.ModuleType(name)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        tests = flatten_tests(suite)
        test_names = sorted(t._testMethodName for t in tests)
        test_ids = sorted(t.id() for t in tests)
        expected_ids = sorted(f'{name}.Tests.{method}' for method in EXPECTED_TESTS)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
        complete = (test_names == sorted(EXPECTED_TESTS) and test_ids == expected_ids
                    and result.testsRun == len(EXPECTED_TESTS))
        clean = (complete and not result.errors and not result.skipped
                 and not result.expectedFailures and not result.unexpectedSuccesses)
        status = ('PASS' if clean and result.wasSuccessful() else
                  'KILLED' if clean and result.failures else 'INVALID')
        return {'name': name, 'compile': 'PASS', 'tests': result.testsRun,
                'test_names': test_names, 'test_ids': test_ids, 'complete': complete,
                'failures': len(result.failures), 'errors': len(result.errors),
                'skips': len(result.skipped),
                'expectedFailures': len(result.expectedFailures),
                'unexpectedSuccesses': len(result.unexpectedSuccesses),
                'failed_tests': [test.id() for test, _ in result.failures],
                'error_tests': [test.id() for test, _ in result.errors],
                'skipped_tests': [test.id() for test, _ in result.skipped],
                'status': status}
    except Exception as exc:
        return {'name': name, 'compile': 'PASS', 'status': 'INVALID', 'error': repr(exc)}
    finally:
        del sys.modules[name]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Nonunique replacement target')
    return text.replace(old, new, 1)


CONTROL_NAMES = ('skip_negative', 'mutant_skip', 'expected_failure',
                 'unexpected_success', 'renamed_test', 'deleted_test', 'syntax_error')
TARGET = '    def test_missing_chunk_same_error_no_effect(self):'


def apply_control(text, control):
    if control in ('skip_negative', 'mutant_skip'):
        return replace_once(text, TARGET, '    @unittest.skip("negative control")\n'+TARGET)
    if control in ('expected_failure', 'unexpected_success'):
        replacement = '    @unittest.expectedFailure\n'+TARGET
        if control == 'expected_failure':
            replacement += '\n        self.fail("negative control")'
        return replace_once(text, TARGET, replacement)
    if control in ('renamed_test', 'deleted_test'):
        replacement = TARGET.replace('test_missing_chunk_same_error_no_effect',
                                     'test_renamed' if control == 'renamed_test' else 'not_a_test')
        return replace_once(text, TARGET, replacement)
    if control == 'syntax_error':
        return text+'\nthis is invalid Python !!!\n'
    return text


def evaluate(control=None):
    text = source if control == 'mutant_skip' else apply_control(source, control)
    reports = [run('baseline', text)]
    for name, (old, new) in mutations.items():
        mutant = replace_once(text, old, new)
        if control == 'mutant_skip' and name == 'tenant_gate_removed':
            mutant = apply_control(mutant, control)
        reports.append(run(name, mutant))
    accepted = (reports[0]['status'] == 'PASS'
                and all(r['status'] == 'KILLED' for r in reports[1:]))
    return {'accepted': accepted, 'runs': reports}


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if len(sys.argv) != 3 or sys.argv[1] != '--negative-control' or sys.argv[2] not in CONTROL_NAMES:
            raise SystemExit('Invalid negative-control option')
        report = evaluate(sys.argv[2])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report['accepted'] else 1)
    report = evaluate()
    controls = []
    for name in CONTROL_NAMES:
        child = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()),
                                '--negative-control', name], capture_output=True, text=True,
                               timeout=30)
        detail = json.loads(child.stdout)  # crash/no JSON is not a validated rejection
        target = detail['runs'][1 if name == 'mutant_skip' else 0]
        rejected = child.returncode == 1 and not detail['accepted'] and target['status'] == 'INVALID'
        controls.append({'name': name, 'exit_code': child.returncode,
                         'status': 'REJECTED' if rejected else 'CONTROL_FAILED',
                         'target_report': target})
    report['negative_controls'] = controls
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['accepted'] or not all(c['status'] == 'REJECTED' for c in controls):
        raise SystemExit('Baseline/mutation/control gate failed')

```

## 4. 实际离线运行结果

以下是本实验实际执行所得，不是预计结果。baseline 的完整 unittest 输出：

```text
test_chunk_budget_atomic (__main__.Tests.test_chunk_budget_atomic) ... ok
test_collision_resolves_full_identity (__main__.Tests.test_collision_resolves_full_identity) ... ok
test_duplicate_data_all_entrypoints (__main__.Tests.test_duplicate_data_all_entrypoints) ... ok
test_duplicate_fullref_dedup_and_budget (__main__.Tests.test_duplicate_fullref_dedup_and_budget) ... ok
test_emit_dedup_independent_of_canonical_rows (__main__.Tests.test_emit_dedup_independent_of_canonical_rows) ... ok
test_empty_calls_still_bounded (__main__.Tests.test_empty_calls_still_bounded) ... ok
test_exclude_all_navigation_tools (__main__.Tests.test_exclude_all_navigation_tools) ... ok
test_exclude_collision_does_not_hide_own (__main__.Tests.test_exclude_collision_does_not_hide_own) ... ok
test_exclude_search_refills (__main__.Tests.test_exclude_search_refills) ... ok
test_foreign_stale_missing_same_error_all_entrypoints (__main__.Tests.test_foreign_stale_missing_same_error_all_entrypoints) ... ok
test_grants_bind_source_revision_pairs_all_entrypoints (__main__.Tests.test_grants_bind_source_revision_pairs_all_entrypoints) ... ok
test_grep_literal (__main__.Tests.test_grep_literal) ... ok
test_invalid_bounds_no_effect (__main__.Tests.test_invalid_bounds_no_effect) ... ok
test_missing_chunk_same_error_no_effect (__main__.Tests.test_missing_chunk_same_error_no_effect) ... ok
test_navigate_repeated_call_budget_atomic (__main__.Tests.test_navigate_repeated_call_budget_atomic) ... ok
test_navigation_order_edges (__main__.Tests.test_navigation_order_edges) ... ok
test_neighbors_same_scope (__main__.Tests.test_neighbors_same_scope) ... ok
test_no_grants_search_no_disclosure (__main__.Tests.test_no_grants_search_no_disclosure) ... ok
test_open_complete_cross_chunk_evidence (__main__.Tests.test_open_complete_cross_chunk_evidence) ... ok
test_read_no_expansion (__main__.Tests.test_read_no_expansion) ... ok
test_search_scope (__main__.Tests.test_search_scope) ... ok
test_success_and_empty_accounting (__main__.Tests.test_success_and_empty_accounting) ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.002s

OK
```

| 运行项 | compile | 测试方法数 | 断言失败数 | errors | skips / expectedFailures / unexpectedSuccesses | 结果 |
|---|---|---:|---:|---:|---|---|
| baseline | PASS | 22 | 0 | 0 | 0 / 0 / 0 | PASS |
| tenant_gate_removed | PASS | 22 | 6 | 0 | 0 / 0 / 0 | KILLED |
| revision_gate_removed | PASS | 22 | 12 | 0 | 0 / 0 / 0 | KILLED |
| dedup_removed | PASS | 22 | 5 | 0 | 0 / 0 / 0 | KILLED |
| forget_seen_add | PASS | 22 | 1 | 0 | 0 / 0 / 0 | KILLED |
| grant_cross_product | PASS | 22 | 5 | 0 | 0 / 0 / 0 | KILLED |
| missing_emitted_accounting | PASS | 22 | 11 | 0 | 0 / 0 / 0 | KILLED |
| reverse_previous_results | PASS | 22 | 2 | 0 | 0 / 0 / 0 | KILLED |
| navigate_budget_refund | PASS | 22 | 4 | 0 | 0 / 0 / 0 | KILLED |

断言失败数含 subTest，因此不等于失败测试方法数。公开 runner 的 8 个真实源码替换 mutation 本次 8/8 均为 `KILLED`，不是 compile 错误或测试运行异常。baseline 与每个 mutant 均精确运行同一组 22 个测试方法，完整 ID 同时校验；所有常规运行 skips / expectedFailures / unexpectedSuccesses 全 0。

| runner 负控（独立子进程） | 被污染的运行 / 证据 | 实际退出码 | 结果 |
|---|---|---:|---|
| skip_negative | baseline 拒绝负例被 skip；22 tests、skips=1 | 1 | REJECTED / INVALID |
| mutant_skip | baseline 正常；tenant mutant 仍有断言失败，但 skips=1 | 1 | REJECTED / INVALID |
| expected_failure | baseline 拒绝负例改为预期失败；expectedFailures=1 | 1 | REJECTED / INVALID |
| unexpected_success | baseline 拒绝负例标为预期失败却通过；unexpectedSuccesses=1 | 1 | REJECTED / INVALID |
| renamed_test | 22 tests，但完整测试名/ID 集合不符 | 1 | REJECTED / INVALID |
| deleted_test | 方法改为非 test 前缀；仅运行 21 tests | 1 | REJECTED / INVALID |
| syntax_error | compile=FAIL；不运行测试、不计 kill | 1 | REJECTED / INVALID |

主要检出点：

1. **五入口真实重复数据**：除原 fixture 重复 c0，公开测试还将 c0/c1/c2 各自与冲突副本交错；逐入口断言精确 refs、首行内容与唯一块计费。open(c0,1) 返回 `[0,1]`，next(c0,1) 返回 `[1]`，next(c0,2) 返回 `[1,2]`，重复行不再占邻居窗口。
2. **`_emit` 去重独立有效**：直接给 `_emit` 传重复行和排除引用，绕过规范化，锁住输出与计费。`forget_seen_add` 由该测试单独产生 1 个断言失败，未因上游规范化而失去检出能力；不是靠 Budget 运行错误杀死。
3. **source+revision 成对授权**：保留 `PAIR_SCOPE={('policy','v2'),('other','v1')}` 与真实交叉配对锚点，五入口分布式反例不变；不冒称每入口都测试了四对全矩阵。
4. **五入口成功后累计计费**：同一会话按 search/open/read/成功 grep/navigate/空 grep 顺序，逐次断言 `(remaining,calls_left,fetches,emitted)` 为 `(11,7,1,1)`、`(8,6,2,4)`、`(6,5,3,6)`、`(5,4,4,7)`、`(4,3,5,8)`、`(4,2,6,8)`。独立导航预算负例首次返回 1 块且 remaining=0，第二次同调用抛 Budget 且状态不变。公开 `navigate_budget_refund` 有 4 个断言失败。
5. **正常多块 previous**：原有正常 fixture 与新增交错重复 fixture 均断言 previous(c2,2) 返回 `[0,1]`，同时覆盖左边缘空结果，反转变体被断言检出。
6. **runner 完整性**：baseline 与 mutant 共用零跳过/零预期失败/零意外成功门禁，七项实际负控拒绝如上。默认完整 runner exit=0 表示这些教学回归及拒绝控制符合预期，**不表示发布审批通过**。

这证明测试确实能捕获这些具体回归，不是完整安全证明，也不是 mutation 覆盖率声明；仍需独立复审，本文不自宣 release passed。

### 测试覆盖解读

22 个测试方法覆盖：搜索 scope、碰撞 ID 精确定位、重复完整引用去重与按唯一输出计费、跨租户/过期/不存在/未授权 source 的四入口同形拒绝、多 grant 的 `(source, revision)` 成对绑定五入口反例、缺失 chunk 无计数副作用、空授权搜索、正常跨块证据完整性、同 scope 邻居、read 不扩窗、grep 字面匹配、导航顺序和 previous 多块排序、search 排除后补齐、四个导航入口排除与不重复、跨租户碰撞排除、块预算原子失败、五入口成功与空成功累计计数、空调用预算、非法范围不改计数，以及交错重复数据的五入口窗口/内容、独立 `_emit` 去重、导航重复调用耗尽预算负例。

正常链路在 `test_open_complete_cross_chunk_evidence` 中真实执行：search 命中“30 days”中间块，open 返回 `[0, 1, 2]`，逐块断言退款规则、期限、例外全部存在。该玩具数据说明证据补齐的可测试性，不推断实际 RAG 准确率或性能收益。

## 5. 交付前还缺什么

| 项目 | 状态 / 边界 |
|---|---|
| 原创 synthetic Python lab 与 mutation | 已本地运行，结果如上；待独立复审 |
| 上游实际 host / MCP 部署 | **NOT_RUN** |
| 实际 API / 认证服务 | **NOT_RUN** |
| 实际向量模型 / embedding / OCR | **NOT_RUN** |
| 客户数据、真实密钥、文件摄入 | 未使用 |
| 独立安全审查与公开签发 | 待独立审查；本文不自宣可发布或 release passed |

接入真实系统前，应单独验证：认证到授权 scope 的不可伪造绑定、授权撤销及 revision 切换、索引过滤与 chunk lookup 的一致性、并发预算的原子性、结果序列化最小化、日志脱敏、实际后端查询计划与侧信道。内存扫描、单线程计数、公开构造的测试 fixture 都不能替代这些控制。
