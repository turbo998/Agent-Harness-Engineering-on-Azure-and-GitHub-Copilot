"""Original offline receipt consistency checker. Prepared; NOT_RUN. Linux/POSIX."""
import hashlib
import json
import os
import re
import stat
from urllib.parse import urlsplit

JSON_LIMIT = 65536
BODY_LIMIT = 1048576
KINDS = {'main_source', 'tag_source', 'release_body', 'docs', 'registry', 'release_metadata'}


class Reject(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Reject(code)


def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, 'duplicate_key')
        out[key] = value
    return out


def fail_constant(_):
    raise Reject('json_constant')


def load_json(data):
    require(type(data) is bytes and len(data) <= JSON_LIMIT, 'json_budget')
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=fail_constant)


def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names.split()), 'schema')


def token(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value)


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value)


def revision(value):
    return type(value) is str and (value == '' or re.fullmatch('[0-9a-f]{40}', value))


def url(value):
    require(type(value) is str and 0 < len(value) <= 2048, 'url')
    require(all(33 <= ord(c) <= 126 for c in value), 'url')
    require(not any(c in value for c in ('%', '\\', '?', '#')), 'url')
    p = urlsplit(value)
    require(p.scheme == 'https' and p.hostname and p.netloc == p.hostname, 'url')
    require(all(s not in ('.', '..') for s in p.path.split('/')), 'url')
    return p


def relative_name(name):
    require(type(name) is str and re.fullmatch(r'[A-Za-z0-9_./-]{1,200}', name), 'path')
    require(all(s not in ('', '.', '..') for s in name.split('/')), 'path')


def read_local(root, name, budget):
    # Walk every directory with openat + O_NOFOLLOW; never resolve a symlink.
    relative_name(name)
    root = os.fspath(root)
    require(root.startswith('/') and root != '/', 'root')
    parts = root[1:].split('/')
    require(all(s not in ('', '.', '..') for s in parts), 'root')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts + name.split('/')[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        leaf = os.open(name.split('/')[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(leaf)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'file_type')
            require(info.st_size <= budget, 'file_budget')
            with os.fdopen(leaf, 'rb', closefd=False) as stream:
                data = stream.read(budget + 1)
            require(len(data) <= budget, 'file_budget')
            return data
        finally:
            os.close(leaf)
    finally:
        os.close(fd)


def check(root, manifest_bytes, claim_bytes):
    """Caller authenticates manifest out-of-band; no self-declared trust flag."""
    result = {'status': 'REJECT', 'reason': 'input', 'byte_binding': False,
              'evidence_layer': None, 'fact_authorized': False,
              'fetch_authenticated': False, 'runtime_verified': False}
    try:
        m, c = load_json(manifest_bytes), load_json(claim_bytes)
        fields(m, 'version requested_allowlist final_allowlist receipts')
        fields(c, 'version fact_id receipt_id revision kind line_start line_end excerpt')
        require(m['version'] == 'binding-v1' and c['version'] == 'binding-v1', 'version')
        require(token(c['fact_id']) and token(c['receipt_id']), 'identity')
        for key in ('requested_allowlist', 'final_allowlist'):
            values = m[key]
            require(type(values) is list and 0 < len(values) <= 32, 'allowlist')
            for value in values:
                url(value)
            require(len(values) == len(set(values)), 'allowlist')
        receipts = m['receipts']
        require(type(receipts) is list and 0 < len(receipts) <= 32, 'receipts')
        index = {}
        for r in receipts:
            fields(r, 'id capture sha256 method status transport_exit requested_url final_url revision kind scope')
            require(token(r['id']) and r['id'] not in index, 'receipt_identity')
            relative_name(r['capture'])
            require(digest(r['sha256']) and revision(r['revision']), 'receipt_identity')
            require(type(r['kind']) is str and r['kind'] in KINDS, 'kind')
            require(r['scope'] in ('full', 'excerpt'), 'scope')
            require(type(r['status']) is int and 100 <= r['status'] <= 599, 'status_type')
            require(type(r['transport_exit']) is int, 'transport_type')
            require(type(r['method']) is str, 'method_type')
            url(r['requested_url']); url(r['final_url'])
            require(r['requested_url'] in m['requested_allowlist'], 'requested_denied')
            require(r['final_url'] in m['final_allowlist'], 'final_denied')
            index[r['id']] = r
        require(revision(c['revision']) and type(c['kind']) is str and c['kind'] in KINDS, 'claim_identity')
        require(c['receipt_id'] in index, 'receipt_missing')
        r = index[c['receipt_id']]
        require(c['revision'] == r['revision'] and c['kind'] == r['kind'], 'identity_mismatch')
        require(r['method'] == 'GET' and r['status'] == 200 and r['transport_exit'] == 0, 'get_unsuccessful')
        require(type(c['line_start']) is int and type(c['line_end']) is int, 'line_type')
        a, b = c['line_start'], c['line_end']
        require(1 <= a <= b <= 100000 and b - a < 32, 'line_range')
        require(type(c['excerpt']) is str and 0 < len(c['excerpt']) <= 8192, 'excerpt_budget')
        raw = read_local(root, r['capture'], BODY_LIMIT)
        require(hashlib.sha256(raw).hexdigest() == r['sha256'], 'sha256_mismatch')
        text = raw.decode('utf-8', errors='strict')
        # LF only; CR, BOM, whitespace and Unicode are not normalized.
        lines = text.split('\n')
        if lines[-1] == '':
            lines.pop()
        require(b <= len(lines), 'line_range')
        require('\n'.join(lines[a - 1:b]) == c['excerpt'], 'excerpt_mismatch')
        result['byte_binding'] = True
        result['evidence_layer'] = r['kind']
        if r['revision'] and any(r['revision'] not in url(r[k]).path.split('/') for k in ('requested_url', 'final_url')):
            raise Reject('revision_url_mismatch')
        if r['scope'] != 'full':
            result.update(status='UNVERIFIED', reason='excerpt_only')
        elif not r['revision']:
            result.update(status='UNVERIFIED', reason='revision_unpinned')
        elif r['kind'] in ('docs', 'registry', 'release_metadata'):
            result.update(status='UNVERIFIED', reason='signal_only')
        else:
            result.update(status='MATCH', reason='local_consistency_only')
    except Reject as exc:
        result.update(status='REJECT', reason=str(exc))
    except (OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        result.update(status='REJECT', reason='input_error')
    return result


def check_files(root, manifest_name, claim_name):
    try:
        return check(root, read_local(root, manifest_name, JSON_LIMIT),
                     read_local(root, claim_name, JSON_LIMIT))
    except (OSError, ValueError, TypeError):
        return {'status': 'REJECT', 'reason': 'input_file_error', 'byte_binding': False,
                'evidence_layer': None, 'fact_authorized': False,
                'fetch_authenticated': False, 'runtime_verified': False}
