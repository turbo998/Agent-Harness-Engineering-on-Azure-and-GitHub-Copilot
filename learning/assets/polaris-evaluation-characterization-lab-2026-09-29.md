# Polaris 固定源码离线评估行为实验（2026-09-29）

本实验针对 `google-deepmind/polaris-bench` 的固定提交 `e9b25e510e8050d4553a3161c74a1de7990dc0de`，描述加载器和评估器的实际行为，不代表产品符合性结论。它是已有源码线索的后续实跑深化，不声称首次发现。

## 范围与固定输入

仅执行三个评估模块及标准库，显式使用本地样例。没有运行上游命令行入口、安装器、模型、图像加载或在线数据集下载。

| 相对文件名 | SHA-256 |
|---|---|
| `evaluation/__init__.py` | `788746c94b66130c3943e7234b2b6b0da9fe8e9d2816c1856c800308d594f10c` |
| `evaluation/data_loader.py` | `bfa3ee33d92f78bc59df5f455a1b625b0b3fb94bdae721a88f19ef531ed6d450` |
| `evaluation/evaluate.py` | `d722721bcb843acedabfad2f852375e39b02b2ecbefc2037401e9b47739d68f0` |
| `examples/sample_tasks/sample_tasks.json` | `c9117ac2850c5243d105f7ca4a88654a9238473b4c9cd9517afa1a2c7f78c26d` |

## 复现方法与安全边界

将文末唯一的 Python 代码块保存为 `polaris_offline_runner.py`，准备上述固定文件组成的普通源码树。以下是可替换的相对路径，不是作者的执行目录。

```bash
/usr/bin/python3 -I -S -B polaris_offline_runner.py \
  --source ./source-tree --out ./new-results --mutations
```

输入与输出必须分离；输出必须不存在。输入路径拒绝符号链接，以 `O_NOFOLLOW | O_NONBLOCK` 打开，并在读取前用 `fstat` 确认普通文件。因此命名管道不等待写端，直接拒绝。预检发生在输出目录创建前。

工作进程实际通过 Linux `unshare -Urn` 建立新的用户和网络命名空间，并对比继承的父进程命名空间描述符；不相信环境标志。环境使用白名单，子进程有超时并在超时后终止进程组。运行时禁止网络、在线数据集及图像库导入、上游启动子进程。这不是文件系统沙箱，不能处理不可信代码或敌对共享路径；也不保证抵御主动伪造全部报告的恶意评估器。

## 独立报告契约

父进程持有固定的完整测试清单：行为测试 **23 项**、教学输入校验 **22 项**、变异 **6 项**，不从返回报告推导应有清单。测试标识必须完整且唯一；未知标识、空集合、缺项、重复项、跳过字段、错误字段、缺少观测值或预期值、非法字段类型均不能通过。

父进程使用独立固定预期值重算每条断言，严格区分布尔值与数字，并核对测试状态、工作进程状态及退出码。必须保留全部业务断言记录，不能只提交聚合计数。基础设施测试为第 19、22 项；网络、禁止导入、子进程计数必须为零，本地评判替身必须恰好调用一次。即使存在业务差异，任何异常记录或基础设施偏差也使整次运行成为 `INVALID`，对应变异为 `ERROR_NOT_KILL`，不计入击杀数。完整、无异常且具有实际业务观测差异时才记为 `KILLED`；完整且所有断言通过则为 `SURVIVED`。

## 实际行为与输入校验

覆盖配对样例展开、配对交集、未知预测键静默忽略、只对有效预测计入分母、二段键广播、重复真值或预测以后值覆盖、列表预测的数字零被 `or` 链丢弃、字符串零保留、浮点等价、整数片段回退接受非坐标或单位不一致文本、空预测、类别缺少一侧时的下降值、本地替身以及真实样例顺序与内容。

教学输入校验是原创代码，不冒充上游行为：仅接受非空扁平对象列表；真值必须包含 `task/index/question_type/answer`，可选 `question/category`；预测必须包含 `task/index/question_type/prediction`。所有值为非空的严格字符串，问题类型限于 `cartesian/polar`，禁止重复三元组、非法字段、未知键、缺覆盖、非字符串值和广播字典。仅预期的 `GateError` 可视为成功拒绝，其他异常不可计为通过。

## 实测结果

最终代码块抽取后重新运行，行为断言 **23/23**、教学输入校验 **22/22**，六个真实源码变异全部由业务观测差异检出。原始四个输入文件的运行前后摘要不变。真实样例为原始 20 条、展开 40 条，两种问题类型各 20 条、配对 20 组、任务 20 种。网络、禁止导入和上游子进程计数均为 0，本地替身调用 1 次。

| 变异 | 实际检出断言 |
|---|---|
| M1：禁用二段键广播 | 07 |
| M2：保留列表中的数字零 | 11 |
| M3：尝试使用完整真值分母 | 05、06、07 等业务断言 |
| M4：禁用整数片段回退 | 14、15 |
| M5：浮点容差设为零 | 13、23 |
| M6：容差从 `1e-5` 缩至 `1e-6` | 23 |

此前 M6 确实存活，不是等价变异。新增第 23 项使用 `match_answer('1.000005','1')`：原版为真、M6 为假。结果变化来自这个明确的覆盖补充，不是填充击杀配额。

第 18 项使用单条真值夹具，专门隔离本地替身调用；分母行为仍由其他业务断言检验。M3 的业务差异被七项断言检出，基础设施计数保持正确。运行器将在使用者指定的新输出目录生成 `results.json`；该文件是本地运行产物，不是本文依赖的随附文件。

## 运行器反例控制

检查空测试、空校验集合、测试缺项、重复或未知标识、跳过、隐藏失败、缺少业务观测值、错误的字段类型、伪造聚合状态、基础设施计数偏差、异常与业务差异并存、遗漏变异等情形。另实际执行网络异常变异，确认它不能计为击杀；实际构造命名管道确认预检迅速拒绝且不创建输出。所有结果以机器记录为准。

## 来源与许可证

上游作者为 Google LLC，版权年份为 2026。依据同一固定提交的[官方说明许可段落](https://github.com/google-deepmind/polaris-bench/blob/e9b25e510e8050d4553a3161c74a1de7990dc0de/README.md#licensing--disclaimer)：软件代码采用 [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)，其他材料采用 [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode)。因此三个评估模块属于 Apache-2.0 软件；[原始样例 JSON](https://github.com/google-deepmind/polaris-bench/blob/e9b25e510e8050d4553a3161c74a1de7990dc0de/examples/sample_tasks/sample_tasks.json) 属于 CC-BY-4.0 非代码材料，不能笼统写成 Apache。样例未修改；变异仅发生在独立复制的评估代码中，变更在上表与运行结果明确标出。上游说明中的第三方灵感来源亦应保留，不据此扩张授权范围。

本文内嵌的原创运行器明确采用 **MIT 许可证**，版权归 2026 年 Polaris 离线实验贡献者。完整标准授权文本内嵌如下，许可证规范见 [MIT 官方文本](https://opensource.org/license/mit)。授权免费使用、复制、修改、合并、发布、分发、再许可及销售，但须保留版权和许可声明；软件按原样提供，不作担保，作者不承担相关责任。此许可不替代上游代码或样例各自的许可证。

## 完整运行器

下列代码可独立保存执行；标识符、协议字段及命令参数保留原名，解释性文字使用中文。

### 原创运行器 MIT 授权文本

```text
MIT License

Copyright (c) 2026 Polaris Offline Lab Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

```python
#!/usr/bin/env python3
"""固定源码离线行为实验；Linux/Python 3.9 以上，仅使用标准库。
这不是文件系统沙箱；不得用于不可信代码或敌对共享路径。
"""
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Polaris 离线实验贡献者
import argparse, copy, hashlib, json, os, signal, stat, subprocess, sys
from pathlib import Path
COMMIT = 'e9b25e510e8050d4553a3161c74a1de7990dc0de'
FILES = {
    'evaluation/__init__.py': '788746c94b66130c3943e7234b2b6b0da9fe8e9d2816c1856c800308d594f10c',
    'evaluation/data_loader.py': 'bfa3ee33d92f78bc59df5f455a1b625b0b3fb94bdae721a88f19ef531ed6d450',
    'evaluation/evaluate.py': 'd722721bcb843acedabfad2f852375e39b02b2ecbefc2037401e9b47739d68f0',
    'examples/sample_tasks/sample_tasks.json': 'c9117ac2850c5243d105f7ca4a88654a9238473b4c9cd9517afa1a2c7f78c26d',
}
ALLOWED_ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8'}
# 独立固定契约：不能根据工作进程返回的测试自行推导预期集合或数量。
TEST_EXPECTED = {
 '01_loader_flat_list_kept': 5,
 '02_loader_paired_json_flattens_two_edges': [['cartesian','A'],['polar','A']],
 '03_get_paired_dataset_intersection_only': 1,
 '04_get_dataset_task_filter': 2,
 '05_unknown_prediction_key_silent_skip_denominator': 0,
 '06_missing_prediction_not_in_denominator': 1,
 '07_two_part_key_broadcasts_to_both_types': 2,
 '08_question_type_filter_limits_broadcast': 1,
 '09_duplicate_gt_last_wins': 100.0,
 '10_duplicate_prediction_last_wins': 100.0,
 '11_list_prediction_numeric_zero_lost_to_answer': 0.0,
 '12_list_prediction_string_zero_preserved': 100.0,
 '13_numeric_float_equivalence': True,
 '14_integer_tokens_accept_noncoordinate_text': True,
 '15_integer_tokens_accept_unit_mismatch': True,
 '16_empty_predictions_zero_denominator_no_crash': {'total_evaluated':0,'overall_accuracy_percent':0.0,'cartesian_accuracy_percent':None,'polar_accuracy_percent':None,'cartesian_to_polar_drop':None},
 '17_category_missing_polar_drop_encoded_as_0': 0.0,
 '18_llm_judge_actual_fallback': 0.0,
 '19_stub_called_once': 1,
 '20_real_sample_counts': {'raw_records':20,'loaded_records':40,'cartesian':20,'polar':20,'pairs':20,'unique_tasks':20},
 '21_real_sample_edge_content': True,
 '22_no_network_or_forbidden_import_attempts': [0,0,0],
 '23_numeric_tolerance_boundary': True,
}
GATE_EXPECTED = {
 'complete': True, 'duplicate_prediction': False, 'duplicate_gt': False,
 'missing_edge': False, 'broadcast_dict': False, 'empty': False,
 "prediction_task_'unknown'": False, 'prediction_index_1': False,
 'prediction_index_True': False, "prediction_question_type_'hexagonal'": False,
 'prediction_prediction_0': False, 'prediction_prediction_False': False,
 'prediction_prediction_None': False, 'prediction_prediction_[]': False,
 "prediction_prediction_''": False, "prediction_answer_'unexpected'": False,
 'GT_task': False, 'GT_index': False, 'GT_question_type': False,
 'GT_answer': False, 'GT_illegal': False, 'missing_field': False,
}
INFRA_IDS = {'19_stub_called_once', '22_no_network_or_forbidden_import_attempts'}
MUTANT_IDS = ('M1_disable_two_part_broadcast','M2_keep_numeric_zero_prediction',
 'M3_full_gt_denominator_attempt','M4_disable_integer_token_fallback',
 'M5_reduce_float_tolerance_zero','M6_uncovered_tolerance_boundary')
COUNTERS_EXPECTED = {'network_attempts':0,'forbidden_imports':0,'subprocess_attempts':0,'llm_stub_calls':1}


def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x,y) for x,y in zip(a,b))
    return a == b


def validate_report(report, expected_hashes):
    """返回独立重算的状态；任何异常记录或基础设施偏差均使整次运行无效。"""
    try:
        fields = {'status','tests','teaching_gate','sample','counters','source_hash_before',
                  'source_hash_after','hashes_unchanged','isolation'}
        if type(report) is not dict or set(report) != fields:
            raise ValueError('报告字段不完整或含未知字段')
        failures=[]
        for key, manifest, count in [('tests',TEST_EXPECTED,23),('teaching_gate',GATE_EXPECTED,22)]:
            rows=report[key]
            if type(rows) is not list or len(rows) != count or len(manifest) != count:
                raise ValueError(key+': 测试数量错误')
            names=[r.get('name') if type(r) is dict else None for r in rows]
            if any(type(n) is not str for n in names) or len(set(names)) != count or set(names) != set(manifest):
                raise ValueError(key+': 测试标识缺失、重复或未知')
            for row in rows:
                required={'name','ok','observed','expected'} | ({'upstream_issue'} if key == 'tests' else set())
                if set(row) != required:
                    raise ValueError(row['name']+': 异常、跳过或断言字段缺失')
                if type(row['ok']) is not bool or (key == 'tests' and type(row['upstream_issue']) is not bool):
                    raise ValueError('布尔字段类型错误')
                if not same(row['expected'],manifest[row['name']]):
                    raise ValueError(row['name']+': 预期值被更改')
                equal=same(row['observed'],manifest[row['name']])
                if row['ok'] is not equal:
                    raise ValueError(row['name']+': 隐藏失败或伪造聚合状态')
                if not equal:
                    if key == 'teaching_gate' or row['name'] in INFRA_IDS:
                        raise ValueError(row['name']+': 基础设施断言偏差')
                    failures.append(row)
        if not same(report['counters'],COUNTERS_EXPECTED):
            raise ValueError('运行时基础设施计数器偏差')
        if not same(report['sample'],TEST_EXPECTED['20_real_sample_counts']):
            raise ValueError('样例计数偏差')
        if not same(report['source_hash_before'],expected_hashes) or not same(report['source_hash_after'],expected_hashes) or report['hashes_unchanged'] is not True:
            raise ValueError('源码摘要偏差')
        if not same(report['isolation'],{'new_network_namespace':True,'new_user_namespace':True}):
            raise ValueError('隔离状态错误')
        return ('FAIL' if failures else 'PASS'), failures, []
    except (ValueError, TypeError, KeyError) as exc:
        return 'INVALID', [], [str(exc)]


def validate_run(run, expected_hashes):
    state, failures, errors=validate_report(run.get('report'),expected_hashes)
    if state == 'INVALID':
        return state, failures, errors
    if run['report']['status'] != state or type(run.get('returncode')) is not int or run['returncode'] != (0 if state == 'PASS' else 1):
        return 'INVALID', [], ['进程退出码或报告状态与独立重算结果不符']
    return state, failures, errors


def classify_mutation(run, expected_hashes):
    state, failures, errors=validate_run(run,expected_hashes)
    return {'PASS':'SURVIVED','FAIL':'KILLED','INVALID':'ERROR_NOT_KILL'}[state], failures, errors



class GateError(ValueError):
    pass


def strict_gate(predictions, ground_truth):
    """仅适用于教学数据：扁平记录、字符串值及两种指定问题类型。"""
    keys = {'task', 'index', 'question_type'}
    def validate(rows, value_field, optional):
        if type(rows) is not list or not rows:
            raise GateError('nonempty list required')
        seen = set()
        required = keys | {value_field}
        for row in rows:
            if type(row) is not dict or not required <= row.keys() or row.keys() - required - optional:
                raise GateError('missing or illegal fields')
            if any(type(v) is not str or not v.strip() for v in row.values()):
                raise GateError('nonempty exact strings required; no numeric/bool coercion')
            if row['question_type'] not in ('cartesian', 'polar'):
                raise GateError('unsupported teaching question_type')
            key = tuple(row[k] for k in ('task', 'index', 'question_type'))
            if key in seen:
                raise GateError('duplicate triple')
            seen.add(key)
        return seen
    gt = validate(ground_truth, 'answer', {'question', 'category'})
    pred = validate(predictions, 'prediction', set())
    if pred != gt:
        raise GateError('prediction coverage must exactly equal GT triples')
    return True


def gate_tests():
    gt = base_records()
    good = [{k:x[k] for k in ('task','index','question_type')} | {'prediction':x['answer']} for x in gt]
    cases = [('complete', good, gt, True), ('duplicate_prediction', good+[good[0]], gt, False),
             ('duplicate_gt', good, gt+[gt[0]], False), ('missing_edge', good[:-1], gt, False),
             ('broadcast_dict', {'sudoku::1':'D'}, gt, False), ('empty', [], [], False)]
    for field, value in [('task','unknown'),('index',1),('index',True),('question_type','hexagonal'),
                          ('prediction',0),('prediction',False),('prediction',None),('prediction',[]),
                          ('prediction',''),('answer','unexpected')]:
        rows=copy.deepcopy(good); rows[0][field]=value
        cases.append(('prediction_'+field+'_'+repr(value), rows, gt, False))
    for field, value in [('task',[]),('index',1),('question_type','octagonal'),('answer',False),('illegal','x')]:
        rows=copy.deepcopy(gt); rows[0][field]=value
        cases.append(('GT_'+field, good, rows, False))
    rows=copy.deepcopy(good); del rows[0]['prediction']
    cases.append(('missing_field', rows, gt, False))
    result=[]
    for name, pred, truth, expected in cases:
        try:
            observed = strict_gate(pred, truth)
        except GateError:
            observed = False
        # 非预期异常向外传播，不能把程序错误计为成功拒绝。
        result.append({'name':name, 'observed':observed, 'expected':expected, 'ok':observed == expected})
    return result


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hashes(source):
    return {rel:sha256(source/rel) for rel in FILES}


def clean_path(value):
    p=Path(os.path.abspath(value))
    for q in [p, *p.parents]:
        if q.is_symlink():
            raise ValueError('symlink path rejected: '+str(q))
    return p


def source_bytes(path):
    clean_path(path)
    fd=os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError('regular source file required')
        return f.read()


def exclusive_json(path, obj):
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def materialize(source, destination):
    for rel, expected in FILES.items():
        data=source_bytes(source/rel)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('source hash mismatch: '+rel)
        target=destination/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)


def base_records():
    return [
        {'task':'sudoku','index':'1','question_type':'cartesian','question':'q','answer':'D','category':'Algorithmic Logic & Simulation'},
        {'task':'sudoku','index':'1','question_type':'polar','question':'q','answer':'D','category':'Algorithmic Logic & Simulation'},
        {'task':'lattice_paths','index':'2','question_type':'cartesian','question':'q','answer':'11','category':'Combinatorics & Probability'},
        {'task':'bouncing_point','index':'3','question_type':'cartesian','question':'q','answer':'(7, 13)','category':'Algorithmic Logic & Simulation'},
        {'task':'zero_task','index':'z','question_type':'cartesian','question':'q','answer':'0','category':'custom'},
    ]


def write_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def assert_equal(name, got, want, detail=None):
    if got != want:
        raise AssertionError(f'{name}: got {got!r}, want {want!r}; {detail!r}')


def run_characterization(src, work, counters):
    sys.path.insert(0, str(src))
    from evaluation.data_loader import PolarisDataLoader
    from evaluation.evaluate import Evaluator, match_answer

    gt_path = work / 'gt.json'; write_json(gt_path, base_records())
    loader = PolarisDataLoader(str(gt_path))
    ev = Evaluator(loader.data)
    tests=[]
    def record(name, fn, expect, upstream_issue=False):
        try:
            obs = json.loads(json.dumps(fn()))
            expect = json.loads(json.dumps(expect))
            ok = same(obs, expect)
            tests.append({'name': name, 'ok': ok, 'observed': obs, 'expected': expect, 'upstream_issue': upstream_issue})
        except Exception as e:
            tests.append({'name': name, 'ok': False, 'error': repr(e), 'expected': expect, 'upstream_issue': upstream_issue})

    record('01_loader_flat_list_kept', lambda: len(loader.data), 5)
    paired = [{'id':'pair','index':'p1','answer':'A','category_name':'Algorithmic Logic & Simulation','cartesian':{'question':'cq','image':'c.png'},'polar':{'question':'pq','image':'p.png'}}]
    pp = work/'paired.json'; write_json(pp, paired)
    record('02_loader_paired_json_flattens_two_edges', lambda: [(x['question_type'], x['answer']) for x in PolarisDataLoader(str(pp)).data], [('cartesian','A'),('polar','A')])
    record('03_get_paired_dataset_intersection_only', lambda: len(loader.get_paired_dataset()), 1, upstream_issue=True)
    record('04_get_dataset_task_filter', lambda: len(loader.get_dataset(task='sudoku')), 2)
    record('05_unknown_prediction_key_silent_skip_denominator', lambda: ev.evaluate({'bad::1::cartesian':'D'})['summary']['total_evaluated'], 0, upstream_issue=True)
    record('06_missing_prediction_not_in_denominator', lambda: ev.evaluate({'sudoku::1::cartesian':'D'})['summary']['total_evaluated'], 1, upstream_issue=True)
    record('07_two_part_key_broadcasts_to_both_types', lambda: ev.evaluate({'sudoku::1':'D'})['summary']['total_evaluated'], 2, upstream_issue=True)
    record('08_question_type_filter_limits_broadcast', lambda: ev.evaluate({'sudoku::1':'D'}, question_type='polar')['summary']['total_evaluated'], 1)
    record('09_duplicate_gt_last_wins', lambda: Evaluator(base_records()+[{'task':'sudoku','index':'1','question_type':'cartesian','answer':'X'}]).evaluate({'sudoku::1::cartesian':'X'})['summary']['overall_accuracy_percent'], 100.0, upstream_issue=True)
    record('10_duplicate_prediction_last_wins', lambda: ev.evaluate([{'task':'sudoku','index':'1','question_type':'cartesian','prediction':'A'},{'task':'sudoku','index':'1','question_type':'cartesian','prediction':'D'}])['summary']['overall_accuracy_percent'], 100.0, upstream_issue=True)
    record('11_list_prediction_numeric_zero_lost_to_answer', lambda: ev.evaluate([{'task':'zero_task','index':'z','question_type':'cartesian','prediction':0,'answer':'BAD'}])['summary']['overall_accuracy_percent'], 0.0, upstream_issue=True)
    record('12_list_prediction_string_zero_preserved', lambda: ev.evaluate([{'task':'zero_task','index':'z','question_type':'cartesian','prediction':'0','answer':'BAD'}])['summary']['overall_accuracy_percent'], 100.0)
    record('13_numeric_float_equivalence', lambda: match_answer('11.0','11'), True)
    record('14_integer_tokens_accept_noncoordinate_text', lambda: match_answer('row 7 col 13','(7,13)'), True, upstream_issue=True)
    record('15_integer_tokens_accept_unit_mismatch', lambda: match_answer('12 apples','12 bananas'), True, upstream_issue=True)
    record('16_empty_predictions_zero_denominator_no_crash', lambda: ev.evaluate({})['summary'], {'total_evaluated':0,'overall_accuracy_percent':0.0,'cartesian_accuracy_percent':None,'polar_accuracy_percent':None,'cartesian_to_polar_drop':None})
    record('17_category_missing_polar_drop_encoded_as_0', lambda: ev.evaluate({'lattice_paths::2::cartesian':'11'})['by_category']['Combinatorics & Probability']['cartesian_to_polar_drop'], 0.0, upstream_issue=True)
    import evaluation.evaluate as module
    original_stub = module.llm_judge_fallback
    def counted_stub(*args):
        counters['llm_stub_calls'] += 1
        return original_stub(*args)
    module.llm_judge_fallback = counted_stub
    # 单条真值夹具隔离替身调用；分母变异由其他业务断言检验。
    record('18_llm_judge_actual_fallback', lambda: Evaluator(base_records()[:1]).evaluate({'sudoku::1::cartesian':'WRONG'}, use_llm_judge=True)['summary']['overall_accuracy_percent'], 0.0)
    record('19_stub_called_once', lambda: counters['llm_stub_calls'], 1)
    sample_path = src/'examples/sample_tasks/sample_tasks.json'
    with sample_path.open(encoding='utf-8') as f:
        raw_sample = json.load(f)
    sample_loader = PolarisDataLoader(data_path=str(sample_path))
    sample = {'raw_records': len(raw_sample), 'loaded_records': len(sample_loader.data),
              'cartesian': len(sample_loader.get_dataset(question_type='cartesian')),
              'polar': len(sample_loader.get_dataset(question_type='polar')),
              'pairs': len(sample_loader.get_paired_dataset()),
              'unique_tasks': len({x['task'] for x in sample_loader.data})}
    record('20_real_sample_counts', lambda: sample,
           {'raw_records':20, 'loaded_records':40, 'cartesian':20, 'polar':20, 'pairs':20, 'unique_tasks':20})
    expected_edges = [(x['id'], str(x['index']), qt, str(x['answer']), x[qt]['question'])
                      for x in raw_sample for qt in ('cartesian','polar')]
    actual_edges = [(x['task'], x['index'], x['question_type'], x['answer'], x['question'])
                    for x in sample_loader.data]
    record('21_real_sample_edge_content', lambda: actual_edges == expected_edges, True)
    record('22_no_network_or_forbidden_import_attempts',
           lambda: [counters['network_attempts'], counters['forbidden_imports'], counters['subprocess_attempts']], [0,0,0])
    record('23_numeric_tolerance_boundary', lambda: match_answer('1.000005','1'), True)
    return tests, gate_tests(), sample



MUTANTS = [
      ('M1_disable_two_part_broadcast', 'for available_type in self.by_task_index[(task, idx)]:\n                            normalized[(task, str(idx), available_type)] = v', 'pass  # mutated: no broadcast'),
      ('M2_keep_numeric_zero_prediction', 'pred = item.get("prediction") or item.get("answer") or item.get("pred")', 'pred = item["prediction"] if "prediction" in item else (item["answer"] if "answer" in item else item.get("pred"))'),
      ('M3_full_gt_denominator_attempt', 'for (task, idx, q_type), pred_ans in flat_preds.items():', 'for (task, idx, q_type), gt_example in self.ground_truth.items():\n            pred_ans = flat_preds.get((task, idx, q_type), None)'),
      ('M4_disable_integer_token_fallback', 'if pred_coords and gt_coords and pred_coords == gt_coords:\n        return True', 'if False and pred_coords and gt_coords and pred_coords == gt_coords:\n        return True'),
      ('M5_reduce_float_tolerance_zero', 'if abs(p_num - g_num) < 1e-5:', 'if abs(p_num - g_num) < 0:'),
    ]

MUTANTS.append(('M6_uncovered_tolerance_boundary', 'if abs(p_num - g_num) < 1e-5:', 'if abs(p_num - g_num) < 1e-6:'))


def worker(source, work, expected, netfd, userfd):
    # 对比继承的父进程描述符，实际核验内核命名空间，而非环境标志。
    for name, fd in [('net',netfd),('user',userfd)]:
        parent=os.fstat(fd)
        child=os.stat('/proc/self/ns/'+name)
        if (parent.st_dev,parent.st_ino) == (child.st_dev,child.st_ino):
            raise RuntimeError('required namespace isolation missing: '+name)
        os.close(fd)
    source, work=Path(source), Path(work)
    before=hashes(source)
    if before != expected:
        raise RuntimeError('worker pre-import hash mismatch')
    counters={'network_attempts':0,'forbidden_imports':0,'subprocess_attempts':0,'llm_stub_calls':0}
    def audit(event, args):
        if event.startswith('socket.'):
            counters['network_attempts'] += 1
            raise RuntimeError('socket operation forbidden')
        if event == 'import' and args[0].split('.')[0] in ('datasets','PIL'):
            counters['forbidden_imports'] += 1
            raise RuntimeError('HF/image imports forbidden')
        if event in ('subprocess.Popen','os.system','os.posix_spawn','os.exec','os.fork','os.forkpty'):
            counters['subprocess_attempts'] += 1
            raise RuntimeError('upstream child processes forbidden')
    sys.addaudithook(audit)
    tests, gate, sample=run_characterization(source, work, counters)
    after=hashes(source)
    report={'status':'INVALID', 'tests':tests, 'teaching_gate':gate,
            'sample':sample, 'counters':counters, 'source_hash_before':before, 'source_hash_after':after,
            'hashes_unchanged':before == after == expected,
            'isolation':{'new_network_namespace':True,'new_user_namespace':True}}
    state, failures, errors=validate_report(report,expected)
    report['status']=state
    exclusive_json(work/'worker.json',report)
    return {'PASS':0,'FAIL':1,'INVALID':2}[state]


def isolated_run(source, work, expected, timeout):
    netfd=os.open('/proc/self/ns/net',os.O_RDONLY)
    userfd=os.open('/proc/self/ns/user',os.O_RDONLY)
    bootstrap = "import runpy,sys,json; m=runpy.run_path(sys.argv[1]); sys.exit(m['worker'](sys.argv[2],sys.argv[3],json.loads(sys.argv[4]),int(sys.argv[5]),int(sys.argv[6])))"
    cmd=['/usr/bin/unshare','-Urn',sys.executable,'-I','-S','-B','-c',bootstrap,
         str(Path(__file__).resolve()),str(source),str(work),json.dumps(expected),str(netfd),str(userfd)]
    try:
        proc=subprocess.Popen(cmd,env=ALLOWED_ENV,cwd=work,pass_fds=(netfd,userfd),
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            stdout,stderr=proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            stdout,stderr=proc.communicate()
            return {'returncode':124,'status':'TIMEOUT','stderr':stderr[-4000:]}
        result={'returncode':proc.returncode,'stderr':stderr[-4000:]}
        report_path=work/'worker.json'
        if report_path.is_file():
            result['report']=json.loads(report_path.read_text())
        return result
    finally:
        os.close(netfd); os.close(userfd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,help='ordinary pinned source tree root')
    parser.add_argument('--out',required=True,help='NEW output directory, disjoint from source')
    parser.add_argument('--mutations',action='store_true')
    parser.add_argument('--timeout',type=float,default=30,help='seconds per isolated worker')
    args=parser.parse_args()
    if not 0 < args.timeout <= 300:
        parser.error('timeout must be in (0,300]')
    source,out=clean_path(args.source),clean_path(args.out)
    if not source.is_dir() or not out.parent.is_dir():
        parser.error('source and output parent must exist')
    if source == out or source in out.parents or out in source.parents:
        parser.error('source and output must be disjoint')
    if out.exists():
        parser.error('output must not exist; refusing overwrite')
    # 创建输出前读取并核验所有输入；此处不执行输入源码。
    for rel,expected in FILES.items():
        if hashlib.sha256(source_bytes(source/rel)).hexdigest() != expected:
            raise ValueError('input hash mismatch: '+rel)
    out.mkdir(mode=0o700)
    baseline_dir=out/'baseline'; baseline_dir.mkdir()
    materialize(source,baseline_dir/'source')
    baseline=isolated_run(baseline_dir/'source',baseline_dir,FILES,args.timeout)
    mutations=[]
    baseline_state, baseline_failures, baseline_errors=validate_run(baseline,FILES)
    baseline_ok=baseline_state == 'PASS'
    if args.mutations and baseline_ok:
        for name,old,new in MUTANTS:
            work=out/name; work.mkdir()
            materialize(source,work/'source')
            target=work/'source/evaluation/evaluate.py'
            text=target.read_text()
            if text.count(old) != 1:
                mutations.append({'name':name,'status':'NOT_APPLIED'}); continue
            target.write_text(text.replace(old,new,1))
            try:
                compile(target.read_text(),str(target),'exec')
            except SyntaxError as e:
                mutations.append({'name':name,'status':'INVALID_SYNTAX_NOT_KILL','error':str(e)}); continue
            expected_hashes=hashes(work/'source')
            run=isolated_run(work/'source',work,expected_hashes,args.timeout)
            status, failures, errors=classify_mutation(run,expected_hashes)
            mutations.append({'name':name,'status':status,'source_sha256':sha256(target),
                              'returncode':run['returncode'],'failures':failures,'validation_errors':errors,'stderr':run.get('stderr','')})
    source_unchanged=hashes(source)==FILES
    expected_mutants=list(MUTANT_IDS) if args.mutations else []
    infrastructure_ok=([m['name'] for m in mutations] == expected_mutants and
                       all(m['status'] in ('KILLED','SURVIVED') for m in mutations))
    ok=baseline_ok and source_unchanged and infrastructure_ok
    report={'commit':COMMIT,'status':'PASS' if ok else 'FAIL','baseline':baseline,
            'baseline_validation':baseline_state,'validation_errors':baseline_errors,
            'original_source_unchanged':source_unchanged,'mutations':mutations,
            'summary':{'tests_total':len(baseline.get('report',{}).get('tests',[])),
                       'tests_ok':sum(type(t) is dict and t.get('ok') is True for t in baseline.get('report',{}).get('tests',[])),
                       'gate_total':len(baseline.get('report',{}).get('teaching_gate',[])),
                       'gate_ok':sum(type(t) is dict and t.get('ok') is True for t in baseline.get('report',{}).get('teaching_gate',[])),
                       'killed':sum(m['status']=='KILLED' for m in mutations),
                       'survived':sum(m['status']=='SURVIVED' for m in mutations)}}
    exclusive_json(out/'results.json',report)
    print(json.dumps({'status':report['status'],'summary':report['summary']}))
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError,RuntimeError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr)
        sys.exit(2)
```
