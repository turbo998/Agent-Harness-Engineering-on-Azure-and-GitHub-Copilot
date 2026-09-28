# MAF reasoning replay：固定源码离线可复演 lab（2026-09-29）

正常 import 固定源码完整 package，不抽取函数、不 exec 上游片段、不伪造 package。
原创 asyncio runner 保留原 14 cases，增加 content 非 list case，总计 15 项。
**不是 upstream pytest 执行，不代表完整 upstream suite 通过；未证明任何发行包包含修复；未验证云实机或真实服务协议接受度。**

## 固定来源与环境

- Commit：`62337887116c604ff542dbec44dd4cddd814295c`；[固定快照](https://github.com/microsoft/agent-framework/tree/62337887116c604ff542dbec44dd4cddd814295c)。
- [源码归档](https://api.github.com/repos/microsoft/agent-framework/tarball/62337887116c604ff542dbec44dd4cddd814295c)；SHA256 `061a8acc5b4427401dab10a1d848fa572470e793757ef75e3f85daae08641783`；获取记录 `2026-09-28T19:14:56.161746+00:00`。归档 hash 如变更必须停止，不自动接受。
- 观察平台：CPython 3.11.15 / Linux x86_64 / glibc 2.35；锁不保证跨平台。Python、操作系统及 ensurepip 的启动文件不属于 wheel 锁，须自行可信配置。
- 45 个精确 wheel 的版本、文件名、SHA256、URL、大小和源码文件 hashes 见必需配套文件 `maf-replay-dependencies-2026-09-29.json`。
- [Foundry replay 校验](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/agent_framework_foundry/_chat_client.py#L299-L334)；[OpenAI 组校验](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/agent_framework_openai/_chat_client.py#L1756-L1848)。

## 原始七目标映射（不是原 pytest）

| Case | 固定测试出处 |
|---|---|
| `test_stateless_replay_uses_foundry_reasoning_item_without_encrypted_content` | [L544–L613](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/test_foundry_chat_client.py#L544-L613) |
| `test_streaming_stateless_replay_prefers_completed_foundry_reasoning_item` | [L616–L655](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/test_foundry_chat_client.py#L616-L655) |
| `test_stateless_replay_rejects_incomplete_foundry_reasoning_item` | [L658–L684](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/test_foundry_chat_client.py#L658-L684) |
| `test_stateless_replay_rejects_malformed_stored_foundry_reasoning_item` | [L687–L721](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/foundry/tests/foundry/test_foundry_chat_client.py#L687-L721) |
| `test_stateless_reasoning_group_without_encrypted_content_is_rejected_before_transport` | [L1878–L1905](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/tests/openai/test_openai_chat_client.py#L1878-L1905) |
| `test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport` | [L1908–L1952](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/tests/openai/test_openai_chat_client.py#L1908-L1952) |
| `test_partially_compacted_reasoning_group_is_rejected_before_transport` | [L1955–L1993](https://github.com/microsoft/agent-framework/blob/62337887116c604ff542dbec44dd4cddd814295c/python/packages/openai/tests/openai/test_openai_chat_client.py#L1955-L1993) |

原七项覆盖完整无密文回放、stream done 优先、缺失/畸形 replay 拒绝、无密文工具组拒绝、跨组 ID 复用拒绝、部分 compaction 拒绝。
新增八项覆盖缺 response_id、summary/content 分别非 list、未知字段过滤、完整组 compaction、复用 ID 逆序、两组有效 payload 复用 ID、不同 ID 顺序正控。非 list 各用字符串代表，不穷尽 malformed 类型。负控核对异常类型、诊断关键字及 transport 零调用；完整 compaction 正控允许且要求一次 mock create。

## 实测与结果完整性

Baseline **15/15 PASS**，固定原 14 cases 均保留。五项真实 source mutation 分别改变 response_id guard、summary type guard、allowlist、reused-ID guard、content type guard；**5 KILLED / 0 SURVIVED / 0 INVALID**，每项都完成 15 cases。完整结果见下方观察。
`lab_support.py` 独立枚举确切 case IDs；runner 同时检查注册清单和结果清单，校准器独立检查结果顺序、计数和状态，拒绝零 tests、重复、缺项及 SKIP。语法/import/不完整结果不计 kill；kill 须完整结果、exit 1，且每个失败均是显式测试 oracle 的专用 `BusinessOracleFailure`。只接受该异常本身，或固定 SDK 已验证的单层、精确 `ChatClientException` → 显式直接 cause `BusinessOracleFailure`；不遍历普通 `AssertionError`、隐式 context 或任意 wrapper。外层或中间 `PermissionError` 一律 INVALID；混合业务与基础设施失败也 INVALID。
每次 mutation 都复制三个完整源码包，单点修改实际文件后重新 import；校验仅允许指定 mutation 的指定行变更，逆向恢复后必须匹配 canonical hash，其余 source/wheel hashes 均重新验证。手选小样本不代表全局覆盖率；未覆盖 payload.type 错误的专门 case/mutant。

分类回归实测：6 个运行时负控（普通 AssertionError 直接/SDK 包装、PermissionError from AssertionError 直接/SDK 包装、隐式 context、PermissionError 包裹业务标记）各为 14 PASS + 1 FAIL、完整 15 结果、exit 1，全部 INVALID。另实跑 compile/import 故障均 INVALID；混合业务与 infra 的合成结果负控也 INVALID。reused-ID 的三个真实业务失败仍经固定 SDK 单层 wrapper 计 kill。下方 `assertion_failures` 字段仅记录专用业务 oracle，不包含普通 AssertionError。

## 使用方法

保留本文及同目录 `maf-replay-dependencies-2026-09-29.json`。将下列六个文件代码块保存为标题中的文件名。
使用可信 CPython 3.11.15（带 venv/ensurepip）和 Linux unshare。不可用 `unshare -Urn` 时失败关闭，不应移除隔离仍声称等价。

```sh
export SOURCE="$PWD/source" WHEELHOUSE="$PWD/wheels" WORK="$PWD/acquisition"
export PYTHON="$(command -v python3.11)"
# 唯一显式联网阶段；三个目录须不存在。已持有相同材料可跳过。
"$PYTHON" -I -B materials.py fetch
export WORK="$PWD/baseline-work"
sh replay.sh
export WORK="$PWD/mutation-work"
"$PWD/baseline-work/venv/bin/python" -I -B calibrate.py
```

SOURCE、WHEELHOUSE、WORK 须绝对路径、两两不同且互不嵌套；路径祖先和输入树拒绝 symlink/FIFO/特殊文件。所有入口在首次写入前预检；WORK 必须不存在，禁止复用旧输出。每个 Python 入口拒绝 optimized (`-O`/`-OO`)；每次运行均验材料。replay 输出在 WORK/run，校准输出在其 WORK。原始失败日志可能含使用者机器路径，不宜直接公开。

## 隔离和证明边界

- 官方 replay/calibrate 命令使用 env 白名单、私有 HOME/TMPDIR、unshare -Urn 网络 namespace；禁用户 site/dotenv，关闭 OTEL；无真实云凭据与真实服务地址。直接调用 runner/materials verify 不自动创建网络 namespace，需调用者提供。
- Python audit **open guard** 限制路径式 open 的读写根；另对 os.rename/os.replace 的 audit rename 事件限定两端在 WORK，拒绝 dir_fd 变体；阻断列出的 socket/子进程事件。这不是对全部 filesystem 操作的限制：未承诺 unlink/link/chmod/mkdir 等全覆盖，也不约束 native/继承 fd/并发路径替换。
- 路径检查假定输入树不被并发敌对修改，不是 race-proof 文件系统沙箱。unshare 网络隔离不是 mount/seccomp 容器；审计不是恶意 native 代码安全边界。可信 Python/ensurepip 启动文件与 45 wheels 的内容安全审计不在证明范围。
- 端点均 mock，仅模拟服务返回；不证明服务接受协议。源码正常 import 并记录模块相对路径/hash，未安装三个 MAF 发行包；不能推广到其他 provider、发行包或云端 background 恢复。

## 配套数据 hash

`maf-replay-dependencies-2026-09-29.json` SHA256 `676ab4344e529cb2e95ad270f58624a03d8c4c81e682276327391da8d033dfd2`

## 文件：requirements.lock

SHA256 `3a8d05f13f6a5f5eb7c7d32233a0e7f5491d3e8a35f9bb1d7675caa4d21c6dc8`

```text
aiohappyeyeballs==2.7.1 --hash=sha256:9243213661e29250eb41368e5daa826fc017156c3b8a11440826b2e3ed376472
aiohttp==3.14.3 --hash=sha256:53e7b4ce82b54a8bcc71b3b67a5cbd177ca1d7f592cbc92cd38b7349f73482db
aiosignal==1.4.0 --hash=sha256:053243f8b92b990551949e63930a839ff0cf0b0ebbe0597b0f3fb19e1a0fe82e
annotated-types==0.8.0 --hash=sha256:f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0
anyio==4.15.1 --hash=sha256:6152fdbbf9a77fdec97731721bebf7c4c44f7c29b424b0065826173efc7ed101
attrs==26.1.0 --hash=sha256:c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309
azure-ai-inference==1.0.0b9 --hash=sha256:49823732e674092dad83bb8b0d1b65aa73111fab924d61349eb2a8cdc0493990
azure-ai-projects==2.6.1 --hash=sha256:bc698227391ad1e00bc983b87d918eed8a348319152bce554c47a9bf141f4fee
azure-core==1.41.0 --hash=sha256:522b4011e8180b1a3dcd2024396a4e7fe9ac37fb8597db47163d230b5efe892d
azure-identity==1.25.3 --hash=sha256:f4d0b956a8146f30333e071374171f3cfa7bdb8073adb8c3814b65567aa7447c
azure-storage-blob==12.30.3 --hash=sha256:80729a5397e5f0a63dbbdff74da675c5db1eacaf25fd5db0074b7ba6c17e2498
certifi==2026.7.22 --hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775
cffi==2.1.1 --hash=sha256:34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632
charset-normalizer==3.5.1 --hash=sha256:c7b742bf31c88566b4bb6335a7f393bb322e580b6bb98df7bd0c25e6e3519ce8
cryptography==50.0.1 --hash=sha256:51afcfceb15597cf2635068e4ac9a56b2abde622edde17f37d85fd7b5306497a
frozenlist==1.8.0 --hash=sha256:2552f44204b744fba866e573be4c1f9048d6a324dfe14475103fd51613eb1d1f
h11==0.16.0 --hash=sha256:63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86
httpcore==1.0.9 --hash=sha256:2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55
httpcore2==2.13.1 --hash=sha256:e1e05d4f25f7d7d496bfb96748f6f4b67657b03da069b3a68c36069f3db73d0a
httpx==0.28.1 --hash=sha256:d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad
httpx2==2.13.1 --hash=sha256:6dff50fabc270ee5fd25d845d0b078ed20564579744d6d962850975996d2f9a4
idna==3.20 --hash=sha256:ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c
isodate==0.7.2 --hash=sha256:28009937d8031054830160fce6d409ed342816b543597cece116d966c6d99e15
jiter==0.17.0 --hash=sha256:5888fe5abc1ca2fa834a3e1b4c7ef0dcece286a7d7e95a609ef0934b777b9fc9
msal==1.39.0 --hash=sha256:2d2577886906cd7293850dffa2da29119966c213bfc6ec0cecf8bf7621e1ca77
msal-extensions==1.3.1 --hash=sha256:96d3de4d034504e969ac5e85bae8106c8373b5c6568e4c8fa7af2eca9dbe6bca
msgspec==0.21.1 --hash=sha256:6badc03b9725352219cca017bfe71c61f2fbd0fb5982b410ac17c97c213deb30
multidict==6.9.1 --hash=sha256:e8f1e362c9352b50ed120f001046fdbb80810c9d56580f4c3fc13bbe30823387
openai==3.20.0 --hash=sha256:fb1b109e3423ed51c6ade96bbb0fffddae39c8e64bb9b6e501659bcbaa5ad30c
opentelemetry-api==1.45.0 --hash=sha256:80e068aba7cd56c8b58512d6a36f8d25cb1dfaa0c0a4cc1c938ccf9f362d9cb3
propcache==0.5.4 --hash=sha256:6e9368e87a3efc285e559131092c5db643eb8e56de4ee42064d5baec22ef2bb5
pycparser==3.0 --hash=sha256:b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992
pydantic==2.13.5 --hash=sha256:346a034f080da3755d8e9cb5e00e8b07de1d39e4f6e2c87d8ab7cafa0b269a73
pydantic-core==2.46.5 --hash=sha256:49776eab08766a08dfff7012f8b422dcd7e25e43b316eedf0477c24fcfa84b7c
pyjwt==2.15.1 --hash=sha256:42d59d631f7768a1028a64c7ff581a9bf7519804daf91fc5b6c56e30eec5e193
python-dotenv==1.2.3 --hash=sha256:904552145e8bfed22162c09dab1c2b9b54fefa7b23ba780f4f26ca0316b0f0d9
pyyaml==6.0.3 --hash=sha256:b8bb0864c5a28024fac8a632c443c87c5aa6f215c0b126c449ae1a150412f31d
regex==2026.9.10 --hash=sha256:0acee94b480dd853e39434aa9a575f95385b1b4b8fa3feae56db363ca5cad782
requests==2.34.2 --hash=sha256:2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0
sniffio==1.3.1 --hash=sha256:2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2
truststore==0.10.4 --hash=sha256:adaeaecf1cbb5f4de3b1959b42d41f6fab57b2b1666adb59e89cb0b53361d981
typing-extensions==4.16.0 --hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8
typing-inspection==0.4.4 --hash=sha256:65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147
urllib3==2.8.0 --hash=sha256:0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3
yarl==1.25.1 --hash=sha256:d5add7b4ca7afeea91d52e4d4e4db3b1fe9885b71f07054560d8c4296b7441a2
```

## 文件：runner.py

SHA256 `3378881eadfa0e3747b40b6a4b9b306b89a49e176f5512946dbc9c3d8e268a01`

```python
"""原创等价断言runner，不是上游pytest原test；真实固定源码正常import。"""
import sys
if sys.flags.optimize: raise RuntimeError('optimized Python is not supported')
sys.dont_write_bytecode = True
import os, pathlib, json, hashlib, traceback, asyncio, importlib.metadata
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from lab_support import paths, verify, require, EXPECTED_CASES, valid_results, install_audit
SOURCE,W,R = paths()
verify(SOURCE,W,os.environ.get('LAB_MUTATION'))
R.mkdir(parents=True)
for n in ('home','tmp'): (R/n).mkdir()
os.environ['HOME']=str(R/'home'); os.environ['TMPDIR']=str(R/'tmp')
blocked=install_audit(R,SOURCE)
from unittest.mock import MagicMock, AsyncMock
for p in ['core','openai','foundry']: sys.path.insert(0,str(SOURCE/'python/packages'/p))
results=[]
try:
    from agent_framework import ChatResponse,Content,Message
    from agent_framework.exceptions import ChatClientInvalidRequestException, ChatClientException
    from agent_framework_foundry import FoundryChatClient
    from agent_framework_openai import OpenAIChatClient
    from pydantic import BaseModel
except Exception:
    (R/'results.json').write_text(json.dumps({'status':'IMPORT_BLOCKED','traceback':traceback.format_exc()},indent=2)); raise
class BusinessOracleFailure(Exception):
    """Only explicit test-oracle checks emit this marker; never SDK/infra assertions."""

def oracle(condition, detail='business oracle mismatch'):
    if not condition: raise BusinessOracleFailure(detail)

def business_failure(exc):
    # Fixed source _chat_client.py:805-811 wraps transport errors with an
    # exact ChatClientException and explicit direct cause. No context walk,
    # subclasses, arbitrary intermediate exceptions, or nested wrappers.
    return (type(exc) is BusinessOracleFailure or
            (type(exc) is ChatClientException and
             type(exc.__cause__) is BusinessOracleFailure))

class Reasoning(BaseModel):
    type:str='reasoning'
    id:str
    response_id:str
    summary:list
    content:list

def sdk():
    m=MagicMock(); m.default_headers={}
    for obj in [m.responses,m.responses.with_raw_response]:
        for n in ['create','parse','retrieve']: setattr(obj,n,AsyncMock(side_effect=BusinessOracleFailure('unexpected transport')))
    return m

def foundry():
    s=sdk(); p=MagicMock(); p.get_openai_client.return_value=s
    return FoundryChatClient(project_client=p,model='test-model'),s

def group(rid,cid,protected=None,extra=None):
    kw={'id':rid,'text':'reasoning'}
    if protected: kw['protected_data']=protected
    if extra: kw['additional_properties']=extra
    return Message(role='assistant',contents=[Content.from_text_reasoning(**kw),Content.from_function_call(call_id=cid,name='lookup_probe',arguments='{"step":1}')])
def output(cid): return Message(role='tool',contents=[Content.from_function_result(call_id=cid,result='probe-result-step-1')])
def untouched(s):
    for obj in [s.responses,s.responses.with_raw_response]:
        for n in ['create','parse','retrieve']: oracle(getattr(obj,n).call_count == 0, 'unexpected transport call')
async def reject(c,s,msgs,tokens,public=False):
    try:
        if public: await c.get_response(msgs,options={'store':False})
        else: await c._prepare_request(msgs,{'store':False})
    except ChatClientInvalidRequestException as e:
        for token in tokens: oracle(token in str(e),(token,str(e)))
        untouched(s); return str(e)
    raise BusinessOracleFailure('not rejected')
async def f_positive():
    c,s=foundry(); ri=Reasoning(id='rs_foundry',response_id='resp_background',summary=[],content=[])
    fc=MagicMock(type='function_call',id='fc_foundry',call_id='call_foundry',arguments='{"step":1}',status='completed'); fc.name='lookup_probe'
    raw=MagicMock(id='resp_background',model='test-model',created_at=1000000000,metadata={},output_parsed=None,output=[ri,fc],usage=None,conversation=None,status='completed',incomplete_details=None)
    parsed=c._parse_response_from_openai(raw,options={'store':False})
    _,opts,_=await c._prepare_request([Message(role='user',contents=['Run the probe.']),*parsed.messages,output('call_foundry')],{'store':False})
    oracle(opts['input']==[
        {'type':'message','role':'user','content':[{'type':'input_text','text':'Run the probe.'}]},
        {'type':'reasoning','id':'rs_foundry','response_id':'resp_background','summary':[],'content':[]},
        {'call_id':'call_foundry','id':'fc_foundry','type':'function_call','name':'lookup_probe','arguments':'{"step":1}','status':'completed'},
        {'call_id':'call_foundry','type':'function_call_output','output':'probe-result-step-1'}])
    untouched(s); return opts['input']
async def f_stream():
    c,s=foundry(); updates=[]
    for event,rid in [('added','resp_incomplete'),('done','resp_complete')]:
        chunk=MagicMock(); chunk.type='response.output_item.'+event; chunk.output_index=0; chunk.item=Reasoning(id='rs_foundry',response_id=rid,summary=[],content=[])
        updates.append(c._parse_chunk_from_openai(chunk,{},{}))
    got=c._prepare_reasoning_items_for_openai(ChatResponse.from_updates(updates).messages)
    oracle(got=={'rs_foundry':{'type':'reasoning','id':'rs_foundry','response_id':'resp_complete','summary':[],'content':[]}})
    untouched(s); return got
async def f_missing():
    c,s=foundry(); return await reject(c,s,[group('rs_incomplete','call_incomplete'),output('call_incomplete')],['rs_incomplete','required reasoning replay data is missing or invalid'])
async def f_malformed():
    c,s=foundry(); return await reject(c,s,[group('rs_malformed','call_malformed',extra={'__foundry_reasoning_replay_item__':{'id':'rs_malformed'}}),output('call_malformed')],['rs_malformed','required reasoning replay data is missing or invalid'])
def oa(**kwargs):
    s=sdk(); return OpenAIChatClient(model='test-model',async_client=s,**kwargs),s
async def o_missing():
    c,s=oa(); msg=group('rs_missing','call_one'); msg.contents.append(Content.from_function_call(call_id='call_two',name='second_tool',arguments='{}'))
    return await reject(c,s,[msg],['rs_missing','call_one','call_two','required reasoning replay data is missing or invalid','service-side continuation','atomic compaction'],True)
async def o_reused():
    c,s=oa(); msgs=[group('rs_reused','call_first'),output('call_first'),Message(role='user',contents=['Start a separate tool group.']),group('rs_reused','call_second','encrypted-second-group'),output('call_second')]
    return await reject(c,s,msgs,['rs_reused','call_first','call_second','required reasoning replay data is missing or invalid'],True)
async def o_compacted():
    async def compact(msgs): msgs[0].additional_properties['_excluded']=True; return True
    c,s=oa(compaction_strategy=compact)
    msgs=[Message(role='assistant',contents=[Content.from_text_reasoning(id='rs_compacted',text='I need a tool.',protected_data='encrypted-reasoning')]),Message(role='assistant',contents=[Content.from_function_call(call_id='call_compacted',name='tool',arguments='{}')])]
    return await reject(c,s,msgs,['group_msg_0','call_compacted','atomic compaction'],True)

def payload(rid='rs_edge'):
    return {'type':'reasoning','id':rid,'response_id':'resp_edge','summary':[],'content':[]}
async def f_no_response():
    c,s=foundry(); p=payload(); del p['response_id']
    return await reject(c,s,[group('rs_edge','call_edge',extra={'__foundry_reasoning_replay_item__':p}),output('call_edge')],['rs_edge','required reasoning replay data is missing or invalid'])
async def f_summary_type():
    c,s=foundry(); p=payload(); p['summary']='not-a-list'
    return await reject(c,s,[group('rs_edge','call_edge',extra={'__foundry_reasoning_replay_item__':p}),output('call_edge')],['rs_edge','required reasoning replay data is missing or invalid'])
async def f_unknown():
    c,s=foundry(); p=payload(); p['unexpected_lab_field']={'marker':'must-not-leak'}
    _,opts,_=await c._prepare_request([group('rs_edge','call_edge',extra={'__foundry_reasoning_replay_item__':p}),output('call_edge')],{'store':False})
    oracle(opts['input'][0]==payload(),opts['input'])
    oracle('unexpected_lab_field' not in json.dumps(opts['input']))
    untouched(s); return opts['input'][0]
async def o_complete():
    seen=[]
    async def compact(msgs):
        seen.append(True)
        for m in msgs[:3]: m.additional_properties['_excluded']=True
        return True
    c,s=oa(compaction_strategy=compact)
    msgs=[Message(role='assistant',contents=[Content.from_text_reasoning(id='rs_drop',text='old')]),Message(role='assistant',contents=[Content.from_function_call(call_id='call_drop',name='tool',arguments='{}')]),output('call_drop'),Message(role='user',contents=['Fresh request.'])]
    raw=MagicMock(headers={})
    raw.parse.return_value=MagicMock(id='resp_mock',model='test-model',created_at=1000000000,metadata={},output_parsed=None,output=[],usage=None,conversation=None,status='completed',incomplete_details=None)
    s.responses.with_raw_response.create.side_effect=None
    s.responses.with_raw_response.create.return_value=raw
    await c.get_response(msgs,options={'store':False})
    oracle(seen==[True])
    oracle(s.responses.with_raw_response.create.await_count == 1, 'expected one mock create await')
    got=s.responses.with_raw_response.create.call_args.kwargs['input']
    oracle(got==[{'type':'message','role':'user','content':[{'type':'input_text','text':'Fresh request.'}]}],got)
    for obj in [s.responses,s.responses.with_raw_response]:
        for n in ['create','parse','retrieve']:
            if obj is s.responses.with_raw_response and n=='create': continue
            oracle(getattr(obj,n).call_count == 0, 'unexpected transport call')
    return got
async def o_reverse():
    c,s=oa()
    msgs=[group('rs_reused','call_second','encrypted-second-group'),output('call_second'),Message(role='user',contents=['Separate group.']),group('rs_reused','call_first'),output('call_first')]
    return await reject(c,s,msgs,['rs_reused','call_first','call_second'],True)
async def o_both_valid_reused():
    c,s=oa()
    msgs=[group('rs_reused','call_z','encrypted-z'),output('call_z'),Message(role='user',contents=['Separate group.']),group('rs_reused','call_a','encrypted-a'),output('call_a')]
    return await reject(c,s,msgs,['rs_reused','call_z','call_a'],True)
async def o_distinct_order():
    c,s=oa()
    msgs=[group('rs_z','call_z','encrypted-z'),output('call_z'),Message(role='user',contents=['Separate group.']),group('rs_a','call_a','encrypted-a'),output('call_a')]
    _,opts,_=await c._prepare_request(msgs,{'store':False})
    got=[x['id'] for x in opts['input'] if x['type']=='reasoning']
    oracle(got==['rs_z','rs_a'],got)
    untouched(s); return got

cases=[('test_stateless_replay_uses_foundry_reasoning_item_without_encrypted_content',f_positive),('test_streaming_stateless_replay_prefers_completed_foundry_reasoning_item',f_stream),('test_stateless_replay_rejects_incomplete_foundry_reasoning_item',f_missing),('test_stateless_replay_rejects_malformed_stored_foundry_reasoning_item',f_malformed),('test_stateless_reasoning_group_without_encrypted_content_is_rejected_before_transport',o_missing),('test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport',o_reused),('test_partially_compacted_reasoning_group_is_rejected_before_transport',o_compacted)]
cases += [('added_missing_response_id',f_no_response),('added_summary_non_list',f_summary_type),('added_unknown_field_stripped',f_unknown),('added_complete_group_compaction',o_complete),('added_reused_id_reverse_order',o_reverse),('added_reused_id_both_payloads_valid',o_both_valid_reused),('added_distinct_id_order_positive',o_distinct_order)]
async def f_content_type():
    c,s=foundry(); p=payload(); p['content']='not-a-list'
    return await reject(c,s,[group('rs_edge','call_edge',extra={'__foundry_reasoning_replay_item__':p}),output('call_edge')],['rs_edge','required reasoning replay data is missing or invalid'])
cases.append(('added_content_non_list',f_content_type))
require([name for name,fn in cases] == list(EXPECTED_CASES), 'case inventory mismatch')
async def main():
    for name,fn in cases:
        try: detail=await fn(); results.append({'case':name,'status':'PASS','detail':detail})
        except Exception as exc:
            results.append({'case':name,'status':'FAIL','business_oracle_failed':business_failure(exc),'exception_type':type(exc).__name__,'traceback':traceback.format_exc()})
asyncio.run(main())
modules={}
for name,m in list(sys.modules.items()):
    f=getattr(m,'__file__',None)
    if f and name.startswith(('agent_framework','agent_framework_openai','agent_framework_foundry')):
        p=pathlib.Path(f).resolve()
        assert p.is_relative_to(SOURCE), 'source provenance mismatch'
        modules[name]={'file':str(p.relative_to(SOURCE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(R/'loaded-source.json').write_text(json.dumps(modules,indent=2))
report={'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL','implementation':'原创runner；非上游原pytest；未exec或伪造package','python':sys.version,'results':results,'blocked_io':blocked,'source_modules':len(modules)}
require(valid_results(report), 'incomplete, skipped, duplicate or hidden result inventory')
(R/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(0 if report['status']=='PASS' else 1)
```

## 文件：materials.py

SHA256 `56131b37e3dec6b144d25b3523f8e45c7354aeee999a39a6d4c14977ff29837e`

```python
"""Explicit online acquisition OR offline verification; no writes before path checks."""
import sys
if sys.flags.optimize: raise RuntimeError('optimized Python is not supported')
sys.dont_write_bytecode=True
import os, pathlib, json, hashlib, urllib.request, tarfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lab_support import paths, verify, require, P, MANIFEST
SOURCE,W,WORK = paths()
require(sys.argv[1:] in (['fetch'],['verify']), 'use fetch or verify')
if sys.argv[1:] == ['fetch']:
    require(not SOURCE.exists(), 'SOURCE must be new for acquisition')
    require(not W.exists(), 'WHEELHOUSE must be new for acquisition')
    D=json.loads((P/MANIFEST).read_text())
    WORK.mkdir(parents=True)
    def fetch(url,path,sha):
        with urllib.request.urlopen(url,timeout=120) as r: data=r.read()
        require(hashlib.sha256(data).hexdigest()==sha, 'download hash mismatch')
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    archive=WORK/'source.tar.gz'; fetch(D['source']['url'],archive,D['source']['sha256'])
    SOURCE.mkdir(parents=True)
    with tarfile.open(archive) as t:
        for m in t:
            parts=pathlib.PurePosixPath(m.name).parts[1:]
            if not parts: continue
            require('..' not in parts and not m.name.startswith('/'), 'unsafe archive path')
            dest=SOURCE.joinpath(*parts)
            if m.isdir(): dest.mkdir(parents=True,exist_ok=True)
            elif m.isfile():
                dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(t.extractfile(m).read())
            else: raise RuntimeError('archive link/special file rejected')
    for w in D['wheels']: fetch(w['url'],W/w['filename'],w['sha256'])
verify(SOURCE,W)
print('Verified fixed source and wheel hashes.')
```

## 文件：replay.sh

SHA256 `b83642728cb535a3b7c1ab1c4ca6a4aa200b1dbcb632b52c8cc432722cb8215f`

```sh
#!/bin/sh
set -eu
: "${SOURCE:?set absolute source directory}"
: "${WHEELHOUSE:?set absolute wheel directory}"
: "${WORK:?set absolute NEW output directory}"
: "${PYTHON:=python3.11}"
P=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# No writes before isolated stdlib preflight; WORK must not exist.
# Fail closed if unprivileged user/network namespaces are unavailable.
# Isolated stdlib-only interpreter verifies inputs before third-party imports.
env -i PATH=/usr/bin:/bin SOURCE="$SOURCE" WHEELHOUSE="$WHEELHOUSE" WORK="$WORK" unshare -Urn "$PYTHON" -I -B "$P/materials.py" verify
mkdir -p "$WORK/home" "$WORK/tmp"
# This entire rebuild plus experiment is offline and gets no host credential environment.
exec env -i PATH=/usr/bin:/bin HOME="$WORK/home" TMPDIR="$WORK/tmp" LANG=C.UTF-8 SOURCE="$SOURCE" WHEELHOUSE="$WHEELHOUSE" WORK="$WORK" PYTHON="$PYTHON" ASSET="$P" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHON_DOTENV_DISABLED=1 OTEL_SDK_DISABLED=true unshare -Urn /bin/sh -eu -c '
  test ! -e "$WORK/venv"
  "$PYTHON" -I -m venv "$WORK/venv"
  "$WORK/venv/bin/python" -I -m pip --isolated install --no-index --find-links "$WHEELHOUSE" --only-binary=:all: --require-hashes -r "$ASSET/requirements.lock"
  "$WORK/venv/bin/python" -I -m pip --isolated check
  WORK="$WORK/run" "$WORK/venv/bin/python" -I -B "$ASSET/runner.py"
'
```

## 文件：calibrate.py

SHA256 `7bac82aae43a5de67825a57d8fb2f07ea8ff8f888f80124adcec651525ffbfbc`

```python
"""Each mutation runs in a fresh process and exact independently checked case inventory."""
import sys
if sys.flags.optimize: raise RuntimeError('optimized Python is not supported')
sys.dont_write_bytecode=True
import os,json,pathlib,hashlib,shutil,subprocess,ast
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from lab_support import paths,verify,require,MUTATIONS,EXPECTED_CASES,valid_results,classify_mutation,P
SOURCE,W,WORK=paths()
verify(SOURCE,W)
WORK.mkdir(parents=True)
reports=[]
def run(label,source,mutation=None):
    out=WORK/label
    env={'PATH':'/usr/bin:/bin','HOME':str(out/'home'),'TMPDIR':str(out/'tmp'),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PYTHON_DOTENV_DISABLED':'1','OTEL_SDK_DISABLED':'true','SOURCE':str(source),'WHEELHOUSE':str(W),'WORK':str(out)}
    if mutation: env['LAB_MUTATION']=mutation
    p=subprocess.run(['unshare','-Urn',sys.executable,'-I','-B',str(P/'runner.py')],env=env,capture_output=True,text=True,timeout=90)
    (WORK/(label+'-stdout.txt')).write_text(p.stdout); (WORK/(label+'-stderr.txt')).write_text(p.stderr)
    f=out/'results.json'; r=json.loads(f.read_text()) if f.exists() else {'status':'PROCESS_ERROR'}
    return p.returncode,r
code,base=run('baseline',SOURCE)
require(code==0 and base.get('status')=='PASS' and valid_results(base),'baseline not green/complete')
for label,pkg,line,old,new in MUTATIONS:
    clone=WORK/(label+'-source')
    for component in ['core','openai','foundry']:
        shutil.copytree(SOURCE/'python/packages'/component,clone/'python/packages'/component,ignore=shutil.ignore_patterns('__pycache__'))
    target=clone/f'python/packages/{pkg}/agent_framework_{pkg}/_chat_client.py'
    original=target.read_bytes(); lines=original.decode().splitlines(keepends=True)
    require(old in lines[line-1], 'source anchor changed')
    lines[line-1]=lines[line-1].replace(old,new)
    changed=''.join(lines); ast.parse(changed); target.write_text(changed)
    code,r=run(label,clone,label)
    failures=[x for x in r.get('results',[]) if x['status']=='FAIL']
    valid=valid_results(r)
    assertion_failures=[x['case'] for x in failures if x.get('business_oracle_failed') is True]
    outcome=classify_mutation(code,r)
    reports.append({'mutation':label,'file':str(target.relative_to(clone)),'line':line,'old_fragment':old,'new_fragment':new,'original_sha256':hashlib.sha256(original).hexdigest(),'mutant_sha256':hashlib.sha256(changed.encode()).hexdigest(),'outcome':outcome,'exit_code':code,'assertion_failures':assertion_failures,'failed_cases':[x['case'] for x in failures],'imports_completed':valid,'result_count':len(r.get('results',[]))})
summary={'baseline':base['status'],'baseline_cases':len(base['results']),'expected_cases':list(EXPECTED_CASES),'mutations':reports,'note':'Hand-selected calibration, not a general mutation score; incomplete/import failures INVALID.'}
(WORK/'calibration.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
require(len(reports)==5 and all(x['outcome']=='KILLED' for x in reports),'mutation calibration failed')
```

## 文件：lab_support.py

SHA256 `5e8b712f4a574419d548ec4ba36ef414fa9d4b17666c66bcb8f24dc6d70b09b6`

```python
"""Fail-closed input checks and exact case contract (not an OS sandbox)."""
import sys
if sys.flags.optimize:
    raise RuntimeError('optimized Python is not supported')
import os, pathlib, stat, json, hashlib, zipfile
P = pathlib.Path(__file__).resolve().parent
MANIFEST = 'maf-replay-dependencies-2026-09-29.json'
EXPECTED_CASES = (
 'test_stateless_replay_uses_foundry_reasoning_item_without_encrypted_content',
 'test_streaming_stateless_replay_prefers_completed_foundry_reasoning_item',
 'test_stateless_replay_rejects_incomplete_foundry_reasoning_item',
 'test_stateless_replay_rejects_malformed_stored_foundry_reasoning_item',
 'test_stateless_reasoning_group_without_encrypted_content_is_rejected_before_transport',
 'test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport',
 'test_partially_compacted_reasoning_group_is_rejected_before_transport',
 'added_missing_response_id', 'added_summary_non_list', 'added_unknown_field_stripped',
 'added_complete_group_compaction', 'added_reused_id_reverse_order',
 'added_reused_id_both_payloads_valid', 'added_distinct_id_order_positive',
 'added_content_non_list',
)
MUTATIONS = [
 ('missing_response_guard','foundry',310,'if not isinstance(response_id, str) or not response_id:','if False:'),
 ('summary_type_guard','foundry',312,'if not isinstance(typed_payload.get("summary"), list) or not isinstance(typed_payload.get("content"), list):','if not isinstance(typed_payload.get("content"), list):'),
 ('unknown_field_allowlist','foundry',314,'for key in _FOUNDRY_REASONING_REPLAY_FIELDS','for key in typed_payload'),
 ('reused_id_guard','openai',1833,'or content.id in reasoning_ids_reused_across_groups','or False'),
 ('content_type_guard','foundry',312,'if not isinstance(typed_payload.get("summary"), list) or not isinstance(typed_payload.get("content"), list):','if not isinstance(typed_payload.get("summary"), list):'),
]
def require(condition, message):
    if not condition: raise RuntimeError(message)
def check_path(path):
    require(path.is_absolute(), 'paths must be absolute')
    require('..' not in path.parts, 'parent traversal is not admitted')
    for p in [*reversed(path.parents), path]:
        try: mode = p.lstat().st_mode
        except FileNotFoundError: continue
        require(not stat.S_ISLNK(mode), 'symlink path rejected')
        require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'special file rejected')
def check_tree(root):
    if not root.exists(): return
    require(root.is_dir(), 'root must be a directory')
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            mode = (pathlib.Path(parent)/name).lstat().st_mode
            require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'symlink/special file in input tree rejected')
def paths():
    roots = tuple(pathlib.Path(os.environ[k]) for k in ('SOURCE','WHEELHOUSE','WORK'))
    for root in roots: check_path(root)
    for i, a in enumerate(roots):
        for b in roots[i+1:]:
            require(not a.is_relative_to(b) and not b.is_relative_to(a), 'roots must be distinct and non-nested')
    require(not roots[2].exists(), 'WORK must be new')
    for root in roots[:2]: check_tree(root)
    return roots

def verify(source, wheels, mutation=None):
    d = json.loads((P/MANIFEST).read_text())
    selected = [m for m in MUTATIONS if m[0] == mutation]
    require(mutation is None or len(selected) == 1, 'unknown mutation')
    for name, sha in d['source_files'].items():
        path = source/name
        check_path(path)
        require(path.is_file(), 'missing source file: '+name)
        data = path.read_bytes()
        if selected:
            _,pkg,line,old,new = selected[0]
            if name == f'python/packages/{pkg}/agent_framework_{pkg}/_chat_client.py':
                lines = data.decode().splitlines(keepends=True)
                require(new in lines[line-1] and old not in lines[line-1], 'mutation anchor mismatch')
                lines[line-1] = lines[line-1].replace(new,old,1)
                data = ''.join(lines).encode()
        require(hashlib.sha256(data).hexdigest() == sha, 'source hash mismatch: '+name)
    for package in ('core','openai','foundry'):
        actual = {str(p.relative_to(source)) for p in (source/'python/packages'/package).rglob('*.py')}
        expected = {n for n in d['source_files'] if n.startswith('python/packages/'+package+'/') and n.endswith('.py')}
        require(actual == expected, 'unexpected/missing Python source files')
    for w in d['wheels']:
        path = wheels/w['filename']; check_path(path)
        require(path.is_file(), 'wheel must be regular')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == w['sha256'], 'wheel hash mismatch')
        with zipfile.ZipFile(path) as z:
            require(not any(n.endswith('.pth') or pathlib.PurePosixPath(n).name in ('sitecustomize.py','usercustomize.py') for n in z.namelist()), 'wheel startup hook rejected')
    return d

def valid_results(report):
    rows = report.get('results', [])
    return (isinstance(rows,list) and len(rows) == len(EXPECTED_CASES)
        and [r.get('case') for r in rows] == list(EXPECTED_CASES)
        and all(r.get('status') in ('PASS','FAIL') for r in rows)
        and report.get('status') == ('PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL'))

def classify_mutation(code, report):
    if not valid_results(report): return 'INVALID'
    failures = [r for r in report['results'] if r['status'] == 'FAIL']
    if code == 0 and not failures: return 'SURVIVED'
    # Infrastructure failures poison the run even alongside a business failure.
    if code == 1 and failures and all(r.get('business_oracle_failed') is True for r in failures):
        return 'KILLED'
    return 'INVALID'

def install_audit(work, source):
    blocked = []
    def deny(event):
        blocked.append({'event':event,'note':'blocked by audit hook'})
        raise PermissionError('lab boundary: '+event)
    def audit(event,args):
        if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.bind','subprocess.Popen','os.system','os.posix_spawn'): deny(event)
        if event == 'os.rename':
            # Only absolute/path-based renames wholly within WORK; dir_fd forms denied.
            if any(fd not in (-1,None) for fd in args[2:]): deny(event)
            for value in args[:2]:
                if not pathlib.Path(os.fsdecode(value)).resolve().is_relative_to(work): deny(event)
        if event == 'open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p = pathlib.Path(os.fsdecode(args[0])).resolve()
            mode,flags = args[1:3]
            writing = (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
            if writing and not p.is_relative_to(work): deny(event)
            if not writing and not any(p.is_relative_to(pathlib.Path(x)) for x in [str(work),str(source),sys.prefix,sys.base_prefix,'/usr','/lib','/lib64','/etc/ssl','/proc/self']):
                if str(p) not in ['/dev/null','/etc/mime.types','/etc/localtime']: deny(event)
    sys.addaudithook(audit)
    return blocked
```

## 真实 mutation 观察

```json
{
  "baseline": "PASS",
  "baseline_cases": 15,
  "expected_cases": [
    "test_stateless_replay_uses_foundry_reasoning_item_without_encrypted_content",
    "test_streaming_stateless_replay_prefers_completed_foundry_reasoning_item",
    "test_stateless_replay_rejects_incomplete_foundry_reasoning_item",
    "test_stateless_replay_rejects_malformed_stored_foundry_reasoning_item",
    "test_stateless_reasoning_group_without_encrypted_content_is_rejected_before_transport",
    "test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport",
    "test_partially_compacted_reasoning_group_is_rejected_before_transport",
    "added_missing_response_id",
    "added_summary_non_list",
    "added_unknown_field_stripped",
    "added_complete_group_compaction",
    "added_reused_id_reverse_order",
    "added_reused_id_both_payloads_valid",
    "added_distinct_id_order_positive",
    "added_content_non_list"
  ],
  "mutations": [
    {
      "mutation": "missing_response_guard",
      "file": "python/packages/foundry/agent_framework_foundry/_chat_client.py",
      "line": 310,
      "old_fragment": "if not isinstance(response_id, str) or not response_id:",
      "new_fragment": "if False:",
      "original_sha256": "c5c4c7aa1660bc842571041edd6e07c389d5be1f8e21236ce510acedd485fa82",
      "mutant_sha256": "ab262c57c058d52607a45b40e280236c9b53ba69e974f9e8a72c7eb1f08c157f",
      "outcome": "KILLED",
      "exit_code": 1,
      "assertion_failures": [
        "added_missing_response_id"
      ],
      "failed_cases": [
        "added_missing_response_id"
      ],
      "imports_completed": true,
      "result_count": 15
    },
    {
      "mutation": "summary_type_guard",
      "file": "python/packages/foundry/agent_framework_foundry/_chat_client.py",
      "line": 312,
      "old_fragment": "if not isinstance(typed_payload.get(\"summary\"), list) or not isinstance(typed_payload.get(\"content\"), list):",
      "new_fragment": "if not isinstance(typed_payload.get(\"content\"), list):",
      "original_sha256": "c5c4c7aa1660bc842571041edd6e07c389d5be1f8e21236ce510acedd485fa82",
      "mutant_sha256": "caa17195ab16ee2ce72d9207079d0e9ea52e07ca01eeb2cd679db404b7871af6",
      "outcome": "KILLED",
      "exit_code": 1,
      "assertion_failures": [
        "added_summary_non_list"
      ],
      "failed_cases": [
        "added_summary_non_list"
      ],
      "imports_completed": true,
      "result_count": 15
    },
    {
      "mutation": "unknown_field_allowlist",
      "file": "python/packages/foundry/agent_framework_foundry/_chat_client.py",
      "line": 314,
      "old_fragment": "for key in _FOUNDRY_REASONING_REPLAY_FIELDS",
      "new_fragment": "for key in typed_payload",
      "original_sha256": "c5c4c7aa1660bc842571041edd6e07c389d5be1f8e21236ce510acedd485fa82",
      "mutant_sha256": "c9792d47aa303ade003058d6c736c7e12151f6203ec9659a8ca2233c45d5b415",
      "outcome": "KILLED",
      "exit_code": 1,
      "assertion_failures": [
        "added_unknown_field_stripped"
      ],
      "failed_cases": [
        "added_unknown_field_stripped"
      ],
      "imports_completed": true,
      "result_count": 15
    },
    {
      "mutation": "reused_id_guard",
      "file": "python/packages/openai/agent_framework_openai/_chat_client.py",
      "line": 1833,
      "old_fragment": "or content.id in reasoning_ids_reused_across_groups",
      "new_fragment": "or False",
      "original_sha256": "16b086bdbb7fd4b813469075e0680b7d58f28dbdd5d619f0b1448d9e16dd250b",
      "mutant_sha256": "d0e3723cfa88fe23f174ab8ed81e02131521b39471fb7e5f9b2fe136c53f684c",
      "outcome": "KILLED",
      "exit_code": 1,
      "assertion_failures": [
        "test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport",
        "added_reused_id_reverse_order",
        "added_reused_id_both_payloads_valid"
      ],
      "failed_cases": [
        "test_stateless_reasoning_id_reused_across_groups_is_rejected_before_transport",
        "added_reused_id_reverse_order",
        "added_reused_id_both_payloads_valid"
      ],
      "imports_completed": true,
      "result_count": 15
    },
    {
      "mutation": "content_type_guard",
      "file": "python/packages/foundry/agent_framework_foundry/_chat_client.py",
      "line": 312,
      "old_fragment": "if not isinstance(typed_payload.get(\"summary\"), list) or not isinstance(typed_payload.get(\"content\"), list):",
      "new_fragment": "if not isinstance(typed_payload.get(\"summary\"), list):",
      "original_sha256": "c5c4c7aa1660bc842571041edd6e07c389d5be1f8e21236ce510acedd485fa82",
      "mutant_sha256": "5176f4e596b55168a9c1ea5fa6bb2fc4bf4be549a04304021d0a8636df5a24e6",
      "outcome": "KILLED",
      "exit_code": 1,
      "assertion_failures": [
        "added_content_non_list"
      ],
      "failed_cases": [
        "added_content_non_list"
      ],
      "imports_completed": true,
      "result_count": 15
    }
  ],
  "note": "Hand-selected calibration, not a general mutation score; incomplete/import failures INVALID."
}
```

## 负控观察

```json
{
  "status": "PASS",
  "controls": [
    {
      "control": "materials.py-O",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py-OO",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 1)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 1)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 1)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(0, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(1, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(1, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py(1, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py-existing",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.pysymlink",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.pyfifo",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py-O",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py-OO",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 1)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 1)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 1)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(0, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(1, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(1, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py(1, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py-existing",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.pysymlink",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.pyfifo",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py-O",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py-OO",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 1)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 1)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 1)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(0, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(1, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(1, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py(1, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py-existing",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.pysymlink",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.pyfifo",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 1)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 1)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 1)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(0, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(1, 2)equal",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(1, 2)nested",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh(1, 2)reverse",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh-existing",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.shsymlink",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.shfifo",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "materials.py-bad-hash",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "runner.py-bad-hash",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "calibrate.py-bad-hash",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "replay.sh-bad-hash",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": true
    },
    {
      "control": "result-zero",
      "rejected": true
    },
    {
      "control": "result-skip",
      "rejected": true
    },
    {
      "control": "result-hidden",
      "rejected": true
    },
    {
      "control": "result-duplicate",
      "rejected": true
    },
    {
      "control": "result-extra",
      "rejected": true
    },
    {
      "control": "zero-cases",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": false
    },
    {
      "control": "zero-results",
      "exit_code": 1,
      "rejected": true,
      "no_home_tmp_write": false
    },
    {
      "control": "limited-python-audit",
      "checks": {
        "open-write": true,
        "rename": true,
        "replace": true,
        "inside-rename-allowed": true
      },
      "outside_unchanged": true,
      "rejected": true
    }
  ],
  "scope": "Python open and rename audit only; not a full filesystem sandbox."
}
```
